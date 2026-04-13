import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from std_msgs.msg import Bool, String


class RobotControllerNode(Node):
    """Top-level robot controller and operation-mode manager."""

    def __init__(self) -> None:
        super().__init__("robot_controller")

        # Parameters representing current operation mode and enable state.
        self.declare_parameter("operation_mode", "DISABLED")
        self.declare_parameter("enabled", False)

        # Publishers exposing current mode and enable state.
        self.mode_pub = self.create_publisher(String, "operation_mode", 10)
        self.enabled_pub = self.create_publisher(Bool, "enabled", 10)

        # Subscriptions for external commands (e.g. from B0 or safety system).
        self.create_subscription(String, "set_operation_mode", self._on_set_mode, 10)
        self.create_subscription(Bool, "set_enabled", self._on_set_enabled, 10)

        # Timer to periodically publish current state.
        period_s = self.declare_parameter("status_publish_period", 0.1).value
        self.timer = self.create_timer(period_s, self._on_timer)

        self.get_logger().info("RobotControllerNode initialised.")

    def _on_set_mode(self, msg: String) -> None:
        mode = msg.data.upper()
        # TODO: enforce mode transitions and safety rules here.
        self.get_logger().info(f"Requested mode change to '{mode}'")
        self.set_parameters([Parameter("operation_mode", Parameter.Type.STRING, mode)])

    def _on_set_enabled(self, msg: Bool) -> None:
        enabled = bool(msg.data)
        # TODO: integrate Safe-stop, E-stop, and fault handling here.
        self.get_logger().info(f"Requested enabled state change to {enabled}")
        self.set_parameters([Parameter("enabled", Parameter.Type.BOOL, enabled)])

    def _on_timer(self) -> None:
        mode = self.get_parameter("operation_mode").get_parameter_value().string_value
        enabled = self.get_parameter("enabled").get_parameter_value().bool_value

        mode_msg = String()
        mode_msg.data = mode
        enabled_msg = Bool()
        enabled_msg.data = enabled

        self.mode_pub.publish(mode_msg)
        self.enabled_pub.publish(enabled_msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = RobotControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


