import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String


class B0InterfaceNode(Node):
    """Base station interface for sending commands and receiving telemetry."""

    def __init__(self) -> None:
        super().__init__("b0_interface")

        # Inputs from CLI (acting as B0 operator)
        self.create_subscription(Float32, "b0/target_velocity", self._on_b0_velocity, 10)
        self.create_subscription(Float32, "b0/target_turn_rate", self._on_b0_turn_rate, 10)

        # Outputs towards robot stack
        self.velocity_pub = self.create_publisher(Float32, "target_velocity", 10)
        self.turn_pub = self.create_publisher(Float32, "target_turn_rate", 10)

        # Telemetry from robot
        self.create_subscription(String, "operation_mode", self._on_mode, 10)
        self.create_subscription(Bool, "enabled", self._on_enabled, 10)

        self._latest_mode = "TELEOP"
        self._latest_enabled = False

        self.status_pub = self.create_publisher(String, "b0/status", 10)
        self.timer = self.create_timer(1.0, self._on_timer)

        self.get_logger().info("B0InterfaceNode initialised.")

    def _on_b0_velocity(self, msg: Float32) -> None:
        self.get_logger().info(f"B0: CLI set target velocity to {msg.data:.3f}")
        self.velocity_pub.publish(msg)

    def _on_b0_turn_rate(self, msg: Float32) -> None:
        self.get_logger().info(f"B0: CLI set target turn rate to {msg.data:.3f}")
        self.turn_pub.publish(msg)

    def _on_mode(self, msg: String) -> None:
        self._latest_mode = msg.data

    def _on_enabled(self, msg: Bool) -> None:
        self._latest_enabled = bool(msg.data)

    def _on_timer(self) -> None:
        status = String()
        status.data = f"B0: mode={self._latest_mode}, enabled={self._latest_enabled}"
        self.status_pub.publish(status)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = B0InterfaceNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


