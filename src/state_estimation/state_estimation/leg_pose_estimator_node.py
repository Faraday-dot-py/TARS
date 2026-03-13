import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class LegPoseEstimatorNode(Node):
    """Placeholder leg pose and acceleration estimator."""

    def __init__(self) -> None:
        super().__init__("leg_pose_estimator")

        self.status_pub = self.create_publisher(String, "state_estimation/status", 10)
        self.timer = self.create_timer(0.5, self._on_timer)

        self.get_logger().info("LegPoseEstimatorNode initialised.")

    def _on_timer(self) -> None:
        msg = String()
        msg.data = "LegPoseEstimator: OK (placeholder telemetry)"
        self.status_pub.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = LegPoseEstimatorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


