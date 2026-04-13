import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String


class MotionPlannerNode(Node):
    """Consumes B0 commands and produces motion goals for the executor."""

    def __init__(self) -> None:
        super().__init__("motion_planner")

        self.declare_parameter("enabled_modes", ["AUTONOMOUS", "TELEOPERATED"])

        # Internal state
        self._current_mode = "DISABLED"
        self._enabled = False
        self._target_velocity = 0.0
        self._target_turn_rate = 0.0

        # Inputs
        self.create_subscription(String, "operation_mode", self._on_mode, 10)
        self.create_subscription(Bool, "enabled", self._on_enabled, 10)
        self.create_subscription(Float32, "target_velocity", self._on_target_velocity, 10)
        self.create_subscription(Float32, "target_turn_rate", self._on_target_turn_rate, 10)

        # Outputs
        self.goal_velocity_pub = self.create_publisher(Float32, "motion/goal_velocity", 10)
        self.goal_turn_pub = self.create_publisher(Float32, "motion/goal_turn_rate", 10)

        # Timer to periodically publish current goals
        period_s = self.declare_parameter("goal_publish_period", 0.05).value
        self.timer = self.create_timer(period_s, self._on_timer)

        self.get_logger().info("MotionPlannerNode initialised.")

    def _on_mode(self, msg: String) -> None:
        self._current_mode = msg.data.upper()
        self.get_logger().debug(f"MotionPlanner: mode updated to {self._current_mode}")

    def _on_enabled(self, msg: Bool) -> None:
        self._enabled = bool(msg.data)
        self.get_logger().debug(f"MotionPlanner: enabled updated to {self._enabled}")

    def _on_target_velocity(self, msg: Float32) -> None:
        self._target_velocity = float(msg.data)
        self.get_logger().info(f"Received target velocity {self._target_velocity:.3f}")

    def _on_target_turn_rate(self, msg: Float32) -> None:
        self._target_turn_rate = float(msg.data)
        self.get_logger().info(f"Received target turn rate {self._target_turn_rate:.3f}")

    def _on_timer(self) -> None:
        """Publish motion goals gated by mode and enable state."""
        enabled_modes = set(self.get_parameter("enabled_modes").get_parameter_value().string_array_value)
        can_move = self._enabled and self._current_mode in enabled_modes

        goal_vel = Float32()
        goal_turn = Float32()

        if can_move:
            goal_vel.data = self._target_velocity
            goal_turn.data = self._target_turn_rate
        else:
            goal_vel.data = 0.0
            goal_turn.data = 0.0

        self.goal_velocity_pub.publish(goal_vel)
        self.goal_turn_pub.publish(goal_turn)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MotionPlannerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


