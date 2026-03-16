import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Int32, String

from leg_transport.protocol import ConfigKey
from leg_transport.protocol import MessageType
from leg_transport.protocol import PROTOCOL_VERSION
from leg_transport.protocol import ProtocolFrame
from leg_transport.protocol import SetConfigPayload
from leg_transport.serial_transport import SerialLegTransport


class LedTestBridgeNode(Node):
    """ROS topic bridge for a simple board-side LED blink test."""

    def __init__(self) -> None:
        super().__init__("led_test_bridge")

        self.declare_parameter("device_path", "/dev/ttyUSB0")
        self.declare_parameter("baudrate", 115200)

        self._device_path = str(self.get_parameter("device_path").value)
        self._sequence = 0
        self._transport = SerialLegTransport(
            device_path=self._device_path,
            baudrate=int(self.get_parameter("baudrate").value),
        )

        self.status_pub = self.create_publisher(String, "blinking_status", 10)
        self.create_subscription(Bool, "set_blinking_state", self._on_set_state, 10)
        self.create_subscription(Int32, "set_blinking_rate_khz", self._on_set_rate_khz, 10)

        self._ensure_transport_open()
        self.get_logger().info(f"LedTestBridgeNode ready for {self._device_path}.")

    def _ensure_transport_open(self) -> None:
        if self._transport.is_open:
            return
        if not os.path.exists(self._device_path):
            self._publish_status(f"waiting for {self._device_path}")
            return
        try:
            self._transport.open()
        except Exception as exc:
            self._publish_status(f"open failed: {exc}")
            return
        self._publish_status(f"serial link ready on {self._device_path}")

    def _on_set_state(self, msg: Bool) -> None:
        self._ensure_transport_open()
        if not self._transport.is_open:
            return
        payload = SetConfigPayload(
            config_key=ConfigKey.LED_BLINK_STATE,
            value_u32=1 if msg.data else 0,
        ).encode()
        self._send_config(payload)
        self._publish_status(f"set_blinking_state={bool(msg.data)}")

    def _on_set_rate_khz(self, msg: Int32) -> None:
        self._ensure_transport_open()
        if not self._transport.is_open:
            return
        payload = SetConfigPayload(
            config_key=ConfigKey.LED_BLINK_RATE_KHZ,
            value_u32=max(0, int(msg.data)),
        ).encode()
        self._send_config(payload)
        self._publish_status(f"set_blinking_rate_khz={int(msg.data)}")

    def _send_config(self, payload: bytes) -> None:
        frame = ProtocolFrame(
            version=PROTOCOL_VERSION,
            message_type=MessageType.SET_CONFIG,
            sequence=self._next_sequence(),
            payload=payload,
        )
        self._transport.send_frame(frame)

    def _next_sequence(self) -> int:
        sequence = self._sequence
        self._sequence = (self._sequence + 1) % 256
        return sequence

    def _publish_status(self, text: str) -> None:
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)
        self.get_logger().info(text)

    def destroy_node(self) -> bool:
        self._transport.close()
        return super().destroy_node()


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LedTestBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
