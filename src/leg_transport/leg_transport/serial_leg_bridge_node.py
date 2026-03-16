import json
import os
from typing import Optional

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from leg_control.leg_command import LegCommand
from leg_transport.protocol import HeartbeatPayload
from leg_transport.protocol import MessageType
from leg_transport.protocol import PROTOCOL_VERSION
from leg_transport.protocol import ProtocolFrame
from leg_transport.protocol import SafeStopPayload
from leg_transport.protocol import SetCommandPayload
from leg_transport.protocol import SetEnablePayload
from leg_transport.protocol import TelemetryPayload
from leg_transport.serial_transport import SerialLegTransport

SAFE_STOP_REASON_DISABLED = 1
SAFE_STOP_REASON_WATCHDOG = 2


class SerialLegBridgeNode(Node):
    """One-leg serial bridge from host-side semantics to embedded frames."""

    def __init__(self) -> None:
        super().__init__("serial_leg_bridge")

        self.declare_parameter("leg_id", "L0")
        self.declare_parameter("device_path", "/dev/ttyACM0")
        self.declare_parameter("baudrate", 115200)
        self.declare_parameter("watchdog_timeout_s", 0.25)
        self.declare_parameter("heartbeat_period_s", 0.1)

        self.leg_id = str(self.get_parameter("leg_id").value)
        self._device_path = str(self.get_parameter("device_path").value)
        self._watchdog_timeout_s = float(self.get_parameter("watchdog_timeout_s").value)
        self._heartbeat_period_s = float(self.get_parameter("heartbeat_period_s").value)

        self.telemetry_pub = self.create_publisher(String, "leg/telemetry", 10)
        self.transport_status_pub = self.create_publisher(String, "leg/transport_status", 10)
        self.fault_pub = self.create_publisher(String, "leg/fault", 10)
        self.create_subscription(String, "leg/command", self._on_command, 10)

        self._sequence = 0
        self._last_command_time_ns = self.get_clock().now().nanoseconds
        self._last_command: Optional[LegCommand] = None
        self._transport = SerialLegTransport(
            device_path=self._device_path,
            baudrate=int(self.get_parameter("baudrate").value),
        )

        self._ensure_transport_open()
        self.create_timer(self._heartbeat_period_s, self._on_timer)
        self.get_logger().info(
            f"SerialLegBridgeNode initialised for {self.leg_id} on {self._device_path}."
        )

    def _ensure_transport_open(self) -> None:
        if self._transport.is_open:
            return
        if not os.path.exists(self._device_path):
            self._publish_status(f"{self.leg_id}: waiting for serial device {self._device_path}")
            return
        try:
            self._transport.open()
        except Exception as exc:
            self._publish_status(f"{self.leg_id}: serial open failed: {exc}")
            return
        self._publish_status(f"{self.leg_id}: serial link ready on {self._device_path}")

    def _on_command(self, msg: String) -> None:
        try:
            command = LegCommand.from_json(msg.data)
        except Exception as exc:
            self._publish_fault(f"{self.leg_id}: invalid leg command payload: {exc}")
            return

        self._last_command = command
        self._last_command_time_ns = self.get_clock().now().nanoseconds

        if not self._transport.is_open:
            return

        self._transport.send_frame(
            ProtocolFrame(
                version=PROTOCOL_VERSION,
                message_type=MessageType.SET_ENABLE,
                sequence=self._next_sequence(),
                payload=SetEnablePayload(enabled=command.enabled).encode(),
            )
        )

        if command.safe_stop:
            self._transport.send_frame(
                ProtocolFrame(
                    version=PROTOCOL_VERSION,
                    message_type=MessageType.SAFE_STOP,
                    sequence=self._next_sequence(),
                    payload=SafeStopPayload(reason_code=SAFE_STOP_REASON_DISABLED).encode(),
                )
            )
            return

        self._transport.send_frame(
            ProtocolFrame(
                version=PROTOCOL_VERSION,
                message_type=MessageType.SET_COMMAND,
                sequence=self._next_sequence(),
                payload=SetCommandPayload.from_optional_targets(
                    host_time_ms=command.host_time_ns // 1_000_000,
                    stepper_1_target=command.stepper_1_target,
                    stepper_2_target=command.stepper_2_target,
                    servo_target=command.servo_target,
                ).encode(),
            )
        )

    def _on_timer(self) -> None:
        self._ensure_transport_open()
        if not self._transport.is_open:
            return

        now_ns = self.get_clock().now().nanoseconds
        if now_ns - self._last_command_time_ns > int(self._watchdog_timeout_s * 1_000_000_000):
            self._transport.send_frame(
                ProtocolFrame(
                    version=PROTOCOL_VERSION,
                    message_type=MessageType.SAFE_STOP,
                    sequence=self._next_sequence(),
                    payload=SafeStopPayload(reason_code=SAFE_STOP_REASON_WATCHDOG).encode(),
                )
            )
        else:
            self._transport.send_frame(
                ProtocolFrame(
                    version=PROTOCOL_VERSION,
                    message_type=MessageType.HEARTBEAT,
                    sequence=self._next_sequence(),
                    payload=HeartbeatPayload(host_time_ms=now_ns // 1_000_000).encode(),
                )
            )

        incoming = self._transport.read_frame(timeout_s=0.0)
        if incoming is None:
            return

        if incoming.message_type == MessageType.TELEMETRY:
            try:
                telemetry = TelemetryPayload.decode(incoming.payload)
            except Exception as exc:
                self._publish_fault(f"{self.leg_id}: telemetry decode failed: {exc}")
                return

            msg = String()
            msg.data = json.dumps(
                {
                    "leg_id": self.leg_id,
                    "board_state": telemetry.board_state,
                    "fault_bits": telemetry.fault_bits,
                    "watchdog_state": telemetry.watchdog_state,
                    "applied_sequence": telemetry.applied_sequence,
                    "board_time_ms": telemetry.board_time_ms,
                },
                separators=(",", ":"),
                sort_keys=True,
            )
            self.telemetry_pub.publish(msg)
        elif incoming.message_type == MessageType.FAULT:
            self._publish_fault(f"{self.leg_id}: board fault frame received")

    def destroy_node(self) -> bool:
        self._transport.close()
        return super().destroy_node()

    def _next_sequence(self) -> int:
        sequence = self._sequence
        self._sequence = (self._sequence + 1) % 256
        return sequence

    def _publish_status(self, text: str) -> None:
        msg = String()
        msg.data = text
        self.transport_status_pub.publish(msg)
        self.get_logger().info(text)

    def _publish_fault(self, text: str) -> None:
        msg = String()
        msg.data = text
        self.fault_pub.publish(msg)
        self.get_logger().warning(text)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = SerialLegBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
