import os

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
from std_msgs.msg import Float32
from std_msgs.msg import String

from leg_transport.marlin_imu_protocol import accel_g_to_m_s2
from leg_transport.marlin_imu_protocol import build_imu_poll_command
from leg_transport.marlin_imu_protocol import gyro_dps_to_rad_s
from leg_transport.marlin_imu_protocol import parse_imu_line
from leg_transport.marlin_servo_protocol import encode_servo_ack_command
from leg_transport.marlin_servo_protocol import encode_servo_command
from leg_transport.marlin_servo_protocol import extract_servo_ack_angle
from leg_transport.marlin_servo_protocol import normalize_servo_angle
from leg_transport.raw_serial import RawSerialTransport


class MarlinServoImuBridgeNode(Node):
    """Shared serial bridge for servo commands and IMU telemetry."""

    def __init__(self) -> None:
        super().__init__("marlin_servo_imu_bridge")

        self.declare_parameter("device_path", "/dev/ttyUSB0")
        self.declare_parameter("baudrate", 115200)
        self.declare_parameter("imu_poll_period_s", 0.1)
        self.declare_parameter("frame_id", "ender_imu")
        self.declare_parameter("servo_index", 0)

        self._device_path = str(self.get_parameter("device_path").value)
        self._baudrate = int(self.get_parameter("baudrate").value)
        self._imu_poll_period_s = float(self.get_parameter("imu_poll_period_s").value)
        self._frame_id = str(self.get_parameter("frame_id").value)
        self._servo_index = int(self.get_parameter("servo_index").value)

        self.servo_ack_pub = self.create_publisher(Float32, "servo_angle_ack_deg", 10)
        self.imu_pub = self.create_publisher(Imu, "imu/data_raw", 10)
        self.roll_pitch_pub = self.create_publisher(String, "imu/roll_pitch_deg", 10)
        self.raw_rx_pub = self.create_publisher(String, "ender_serial_rx", 20)
        self.status_pub = self.create_publisher(String, "servo_imu_bridge_status", 10)
        self.create_subscription(Float32, "servo_angle_deg", self._on_servo_angle, 10)

        self._transport = RawSerialTransport(self._device_path, self._baudrate)
        self._ensure_transport_open()
        self.create_timer(self._imu_poll_period_s, self._on_imu_timer)

        self.get_logger().info(
            f"MarlinServoImuBridgeNode initialised on {self._device_path} at {self._baudrate} baud."
        )

    def _ensure_transport_open(self) -> None:
        if self._transport.is_open:
            return
        if not os.path.exists(self._device_path):
            self._publish_status(f"waiting for serial device {self._device_path}")
            return
        try:
            self._transport.open()
        except Exception as exc:
            self._publish_status(f"serial open failed: {exc}")
            return
        self._publish_status(f"serial link ready on {self._device_path}")

    def _on_servo_angle(self, msg: Float32) -> None:
        self._ensure_transport_open()
        if not self._transport.is_open:
            return

        normalized = normalize_servo_angle(msg.data)
        command = encode_servo_command(normalized, servo_index=self._servo_index)
        ack_command = encode_servo_ack_command(normalized)

        try:
            self._transport.write_line(command)
            self._transport.write_line(ack_command)
            lines = self._transport.read_lines(timeout_s=0.02)
        except Exception as exc:
            self._publish_status(f"servo serial transaction failed: {exc}")
            self._transport.close()
            return

        self.get_logger().info(f"sent: {command}")
        self._process_lines(lines)

    def _on_imu_timer(self) -> None:
        self._ensure_transport_open()
        if not self._transport.is_open:
            return

        try:
            self._transport.write_line(build_imu_poll_command())
            lines = self._transport.read_lines(timeout_s=0.02)
        except Exception as exc:
            self._publish_status(f"imu serial transaction failed: {exc}")
            self._transport.close()
            return

        self._process_lines(lines)

    def _process_lines(self, lines: list[str]) -> None:
        for line in lines:
            raw_msg = String()
            raw_msg.data = line
            self.raw_rx_pub.publish(raw_msg)
            self.get_logger().info(f"rx: {line}")

            ack_angle = extract_servo_ack_angle(line)
            if ack_angle is not None:
                ack_msg = Float32()
                ack_msg.data = float(ack_angle)
                self.servo_ack_pub.publish(ack_msg)
                continue

            parsed = parse_imu_line(line)
            if parsed is None:
                continue

            imu_msg = Imu()
            imu_msg.header.stamp = self.get_clock().now().to_msg()
            imu_msg.header.frame_id = self._frame_id
            imu_msg.orientation_covariance[0] = -1.0
            imu_msg.angular_velocity.x = gyro_dps_to_rad_s(parsed["gx"])
            imu_msg.angular_velocity.y = gyro_dps_to_rad_s(parsed["gy"])
            imu_msg.angular_velocity.z = gyro_dps_to_rad_s(parsed["gz"])
            imu_msg.linear_acceleration.x = accel_g_to_m_s2(parsed["ax"])
            imu_msg.linear_acceleration.y = accel_g_to_m_s2(parsed["ay"])
            imu_msg.linear_acceleration.z = accel_g_to_m_s2(parsed["az"])
            self.imu_pub.publish(imu_msg)

            roll_pitch_msg = String()
            roll_pitch_msg.data = (
                f"roll_deg={parsed['roll']:.2f},pitch_deg={parsed['pitch']:.2f}"
            )
            self.roll_pitch_pub.publish(roll_pitch_msg)

    def destroy_node(self) -> bool:
        self._transport.close()
        return super().destroy_node()

    def _publish_status(self, text: str) -> None:
        msg = String()
        msg.data = text
        self.status_pub.publish(msg)
        self.get_logger().info(text)



def main(args=None) -> None:
    rclpy.init(args=args)
    node = MarlinServoImuBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
