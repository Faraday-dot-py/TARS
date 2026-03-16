import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

from constants import LEG_NAMES


class MotionExecutorNode(Node):
    """Consumes motion goals and fans them out into per-leg placeholder commands."""

    def __init__(self) -> None:
        super().__init__("motion_executor")

        self._goal_velocity = 0.0
        self._goal_turn_rate = 0.0

        self.create_subscription(Float32, "motion/goal_velocity", self._on_goal_velocity, 10)
        self.create_subscription(Float32, "motion/goal_turn_rate", self._on_goal_turn_rate, 10)

        # The executor remains incomplete; for now it mirrors shared goals into
        # namespaced per-leg topics so the leg boundary can be exercised.
        self.leg_vel_pubs = {
            leg: self.create_publisher(Float32, f"/{leg}/executor/leg_target_velocity", 10)
            for leg in LEG_NAMES
        }
        self.leg_turn_pubs = {
            leg: self.create_publisher(Float32, f"/{leg}/executor/leg_target_turn_rate", 10)
            for leg in LEG_NAMES
        }

        period_s = self.declare_parameter("leg_command_publish_period", 0.05).value
        self.timer = self.create_timer(period_s, self._on_timer)

        self.get_logger().info("MotionExecutorNode initialised.")

    def _on_goal_velocity(self, msg: Float32) -> None:
        self._goal_velocity = float(msg.data)
        self.get_logger().debug(f"Executor: goal velocity updated to {self._goal_velocity:.3f}")

    def _on_goal_turn_rate(self, msg: Float32) -> None:
        self._goal_turn_rate = float(msg.data)
        self.get_logger().debug(f"Executor: goal turn rate updated to {self._goal_turn_rate:.3f}")

    def _on_timer(self) -> None:
        vel_msg = Float32()
        vel_msg.data = self._goal_velocity
        turn_msg = Float32()
        turn_msg.data = self._goal_turn_rate

        for leg in LEG_NAMES:
            self.leg_vel_pubs[leg].publish(vel_msg)
            self.leg_turn_pubs[leg].publish(turn_msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = MotionExecutorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
