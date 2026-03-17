"""ROS 2 node for the Jetson <-> Pico per-leg wireless bridge."""

from __future__ import annotations

import socket
import threading
import time

from geometry_msgs.msg import Quaternion, Vector3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, UInt32, UInt8

from leg_transport import CalibrationAction

from .bridge_runtime import PicoLegBridgeRuntime


class PicoLegBridgeNode(Node):
    """Bridge one ROS leg namespace to one Pico W over UDP."""

    def __init__(self) -> None:
        super().__init__("pico_leg_bridge")

        self.declare_parameter("leg_id", "L0")
        self.declare_parameter("pico_host", "192.168.4.2")
        self.declare_parameter("command_port", 15120)
        self.declare_parameter("bind_ip", "0.0.0.0")
        self.declare_parameter("telemetry_port", 15121)
        self.declare_parameter("command_period_s", 0.05)
        self.declare_parameter("heartbeat_period_s", 0.5)
        self.declare_parameter("telemetry_timeout_s", 0.5)

        self._leg_id = self.get_parameter("leg_id").value
        self._pico_host = self.get_parameter("pico_host").value
        self._command_port = int(self.get_parameter("command_port").value)
        self._bind_ip = self.get_parameter("bind_ip").value
        self._telemetry_port = int(self.get_parameter("telemetry_port").value)
        self._heartbeat_period_s = float(self.get_parameter("heartbeat_period_s").value)
        telemetry_timeout_s = float(self.get_parameter("telemetry_timeout_s").value)

        self._runtime = PicoLegBridgeRuntime(self._leg_id, telemetry_timeout_s=telemetry_timeout_s)
        self._tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._rx_sock.bind((self._bind_ip, self._telemetry_port))
        self._rx_sock.settimeout(0.1)
        self._running = True
        self._start_time = time.monotonic()
        self._last_heartbeat_sent = 0.0

        self.create_subscription(Bool, "command/enable", self._on_enable, 10)
        self.create_subscription(Bool, "command/safe_stop", self._on_safe_stop, 10)
        self.create_subscription(Float32, "command/servo_target_deg", self._on_servo_target, 10)
        self.create_subscription(Float32, "command/body_velocity_hint", self._on_velocity_hint, 10)
        self.create_subscription(Float32, "command/body_turn_rate_hint", self._on_turn_rate_hint, 10)
        self.create_subscription(UInt8, "command/calibration_action", self._on_calibration_action, 10)

        self._enabled_pub = self.create_publisher(Bool, "state/enabled", 10)
        self._calibration_pub = self.create_publisher(UInt8, "state/calibration_state", 10)
        self._limit_pub = self.create_publisher(UInt8, "state/limit_switch_bits", 10)
        self._fault_pub = self.create_publisher(UInt32, "state/fault_bits", 10)
        self._last_command_pub = self.create_publisher(UInt32, "state/last_command_sequence", 10)
        self._last_stepper_pub = self.create_publisher(UInt32, "state/last_stepper_sequence", 10)
        self._orientation_pub = self.create_publisher(Quaternion, "imu/fused_orientation", 10)

        self._imu_accel_pubs = {
            index: self.create_publisher(Vector3, f"imu/{index}/accel_g", 10)
            for index in range(3)
        }
        self._imu_gyro_pubs = {
            index: self.create_publisher(Vector3, f"imu/{index}/gyro_dps", 10)
            for index in range(3)
        }

        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()

        command_period_s = float(self.get_parameter("command_period_s").value)
        self.create_timer(command_period_s, self._send_command)
        self.create_timer(0.1, self._publish_state)

        self.get_logger().info(
            f"Bridging leg {self._leg_id} to Pico {self._pico_host}:{self._command_port} "
            f"with telemetry on {self._bind_ip}:{self._telemetry_port}"
        )

    def destroy_node(self) -> bool:
        self._running = False
        try:
            self._rx_sock.close()
            self._tx_sock.close()
        finally:
            return super().destroy_node()

    def _on_enable(self, msg: Bool) -> None:
        self._runtime.set_enable(bool(msg.data))

    def _on_safe_stop(self, msg: Bool) -> None:
        self._runtime.set_safe_stop(bool(msg.data))

    def _on_servo_target(self, msg: Float32) -> None:
        self._runtime.set_servo_target(float(msg.data))

    def _on_velocity_hint(self, msg: Float32) -> None:
        self._runtime.set_motion_hints(velocity=float(msg.data))

    def _on_turn_rate_hint(self, msg: Float32) -> None:
        self._runtime.set_motion_hints(turn_rate=float(msg.data))

    def _on_calibration_action(self, msg: UInt8) -> None:
        self._runtime.set_calibration_action(CalibrationAction(int(msg.data)))

    def _send_command(self) -> None:
        _, frame = self._runtime.build_command_frame()
        self._tx_sock.sendto(frame, (self._pico_host, self._command_port))

        now = time.monotonic()
        if now - self._last_heartbeat_sent >= self._heartbeat_period_s:
            uptime_ms = int((now - self._start_time) * 1000.0)
            _, heartbeat_frame = self._runtime.build_heartbeat_frame(uptime_ms=uptime_ms)
            self._tx_sock.sendto(heartbeat_frame, (self._pico_host, self._command_port))
            self._last_heartbeat_sent = now

    def _rx_loop(self) -> None:
        while self._running:
            try:
                frame, _ = self._rx_sock.recvfrom(1024)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                frame_kind = self._runtime.accept_frame(frame)
            except Exception as exc:  # pragma: no cover
                self.get_logger().warning(f"Dropped invalid telemetry frame: {exc}")
                continue

            if frame_kind == "imu":
                latest_index = max(self._runtime.last_imu_samples)
                sample = self._runtime.last_imu_samples[latest_index]
                self._publish_imu_sample(latest_index, sample)

    def _publish_state(self) -> None:
        telemetry = self._runtime.refresh_faults()

        enabled_msg = Bool()
        enabled_msg.data = telemetry.enabled
        self._enabled_pub.publish(enabled_msg)

        calibration_msg = UInt8()
        calibration_msg.data = int(telemetry.calibration_state)
        self._calibration_pub.publish(calibration_msg)

        limit_msg = UInt8()
        limit_msg.data = telemetry.limit_switches.to_bits()
        self._limit_pub.publish(limit_msg)

        fault_msg = UInt32()
        fault_msg.data = int(telemetry.fault_bits)
        self._fault_pub.publish(fault_msg)

        last_command_msg = UInt32()
        last_command_msg.data = int(telemetry.last_command_sequence)
        self._last_command_pub.publish(last_command_msg)

        last_stepper_msg = UInt32()
        last_stepper_msg.data = int(telemetry.last_stepper_sequence)
        self._last_stepper_pub.publish(last_stepper_msg)

        orientation_msg = Quaternion()
        orientation_msg.x = float(telemetry.fused_orientation.x)
        orientation_msg.y = float(telemetry.fused_orientation.y)
        orientation_msg.z = float(telemetry.fused_orientation.z)
        orientation_msg.w = float(telemetry.fused_orientation.w)
        self._orientation_pub.publish(orientation_msg)

    def _publish_imu_sample(self, index: int, sample) -> None:
        accel_msg = Vector3()
        accel_msg.x = float(sample.accel_g.x)
        accel_msg.y = float(sample.accel_g.y)
        accel_msg.z = float(sample.accel_g.z)
        self._imu_accel_pubs[index].publish(accel_msg)

        gyro_msg = Vector3()
        gyro_msg.x = float(sample.gyro_dps.x)
        gyro_msg.y = float(sample.gyro_dps.y)
        gyro_msg.z = float(sample.gyro_dps.z)
        self._imu_gyro_pubs[index].publish(gyro_msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PicoLegBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
