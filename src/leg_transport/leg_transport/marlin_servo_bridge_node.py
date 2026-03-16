import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from std_msgs.msg import String

from leg_transport.marlin_servo_protocol import encode_servo_ack_command
from leg_transport.marlin_servo_protocol import encode_servo_command
from leg_transport.marlin_servo_protocol import extract_servo_ack_angle
from leg_transport.marlin_servo_protocol import normalize_servo_angle
from leg_transport.raw_serial import RawSerialTransport


class MarlinServoBridgeNode(Node):
    """ROS 2 bridge from servo-angle topics to Marlin M280 commands."""

    def __init__(self) -> None:
        super().__init__("marlin_servo_bridge")

        self.declare_parameter("device_path", "/dev/ttyUSB0")
        self.declare_parameter("baudrate", 115200)
        self.declare_parameter("poll_period_s", 0.05)
        self.declare_parameter("servo_index", 0)

        self._device_path = str(self.get_parameter("device_path").value)
        self._baudrate = int(self.get_parameter("baudrate").value)
        self._poll_period_s = float(self.get_parameter("poll_period_s").value)
        self._servo_index = int(self.get_parameter("servo_index").value)

        self.servo_ack_pub = self.create_publisher(Float32, "servo_angle_ack_deg", 10)
        self.raw_rx_pub = self.create_publisher(String, "ender_serial_rx", 20)
        self.status_pub = self.create_publisher(String, "servo_bridge_status", 10)
        self.create_subscription(Float32, "servo_angle_deg", self._on_servo_angle, 10)

        self._transport = RawSerialTransport(self._device_path, self._baudrate)
        self._ensure_transport_open()
        self.create_timer(self._poll_period_s, self._poll_serial)

        self.get_logger().info(
            f"MarlinServoBridgeNode initialised on {self._device_path} at {self._baudrate} baud."
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
        except Exception as exc:
            self._publish_status(f"serial write failed: {exc}")
            self._transport.close()
            return

        self.get_logger().info(f"sent: {command}")

    def _poll_serial(self) -> None:
        self._ensure_transport_open()
        if not self._transport.is_open:
            return

        try:
            lines = self._transport.read_lines(timeout_s=0.0)
        except Exception as exc:
            self._publish_status(f"serial read failed: {exc}")
            self._transport.close()
            return

        for line in lines:
            raw_msg = String()
            raw_msg.data = line
            self.raw_rx_pub.publish(raw_msg)
            self.get_logger().info(f"rx: {line}")

            ack_angle = extract_servo_ack_angle(line)
            if ack_angle is None:
                continue

            ack_msg = Float32()
            ack_msg.data = float(ack_angle)
            self.servo_ack_pub.publish(ack_msg)

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
    node = MarlinServoBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
