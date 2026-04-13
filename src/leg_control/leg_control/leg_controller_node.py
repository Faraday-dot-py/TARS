import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String


class LegControllerNode(Node):
    """Placeholder leg controller for one leg (L0–L3)."""

    def __init__(self) -> None:
        super().__init__("leg_controller")

        self.declare_parameter("leg_id", "L0")
        self.leg_id = self.get_parameter("leg_id").get_parameter_value().string_value

        # Inputs from motion executor
        self.create_subscription(Float32, "executor/leg_target_velocity", self._on_target_velocity, 10)
        self.create_subscription(Float32, "executor/leg_target_turn_rate", self._on_target_turn_rate, 10)

        # Simple status publisher
        self.status_pub = self.create_publisher(String, "leg/status", 10)
        self.timer = self.create_timer(0.5, self._on_timer)

        self._last_velocity = 0.0
        self._last_turn_rate = 0.0

        self.get_logger().info(f"LegControllerNode initialised for leg {self.leg_id}.")

    def _on_target_velocity(self, msg: Float32) -> None:
        self._last_velocity = float(msg.data)
        self.get_logger().info(f"[{self.leg_id}] Received leg target velocity {self._last_velocity:.3f}")

    def _on_target_turn_rate(self, msg: Float32) -> None:
        self._last_turn_rate = float(msg.data)
        self.get_logger().info(f"[{self.leg_id}] Received leg target turn rate {self._last_turn_rate:.3f}")

    def _on_timer(self) -> None:
        status = String()
        status.data = f"{self.leg_id}: OK (v={self._last_velocity:.3f}, w={self._last_turn_rate:.3f})"
        self.status_pub.publish(status)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LegControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


