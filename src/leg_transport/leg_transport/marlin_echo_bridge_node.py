import os

import rclpy
from rclpy.node import Node
from std_msgs.msg import String

from leg_transport.marlin_echo_protocol import encode_marlin_echo_command
from leg_transport.marlin_echo_protocol import extract_echo_payload
from leg_transport.raw_serial import RawSerialTransport


class MarlinEchoBridgeNode(Node):
    """ROS 2 bridge for sending echo requests to Marlin and republishing replies."""

    def __init__(self) -> None:
        super().__init__("marlin_echo_bridge")

        self.declare_parameter("device_path", "/dev/ttyUSB0")
        self.declare_parameter("baudrate", 115200)
        self.declare_parameter("poll_period_s", 0.05)

        self._device_path = str(self.get_parameter("device_path").value)
        self._baudrate = int(self.get_parameter("baudrate").value)
        self._poll_period_s = float(self.get_parameter("poll_period_s").value)

        self.echo_rx_pub = self.create_publisher(String, "ender_echo_rx", 10)
        self.raw_rx_pub = self.create_publisher(String, "ender_serial_rx", 20)
        self.status_pub = self.create_publisher(String, "ender_echo_status", 10)
        self.create_subscription(String, "ender_echo_tx", self._on_echo_tx, 10)

        self._transport = RawSerialTransport(self._device_path, self._baudrate)
        self._ensure_transport_open()
        self.create_timer(self._poll_period_s, self._poll_serial)

        self.get_logger().info(
            f"MarlinEchoBridgeNode initialised on {self._device_path} at {self._baudrate} baud."
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

    def _on_echo_tx(self, msg: String) -> None:
        self._ensure_transport_open()
        if not self._transport.is_open:
            return
        command = encode_marlin_echo_command(msg.data)
        try:
            self._transport.write_line(command)
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

            payload = extract_echo_payload(line)
            if payload is None:
                continue

            echo_msg = String()
            echo_msg.data = payload
            self.echo_rx_pub.publish(echo_msg)

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
    node = MarlinEchoBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
