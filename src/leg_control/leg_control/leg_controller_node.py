import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, Float32, String

from leg_control.leg_command import LegCommand


class LegControllerNode(Node):
    """Host-side semantic leg controller for one leg."""

    def __init__(self) -> None:
        super().__init__("leg_controller")

        self.declare_parameter("leg_id", "L0")
        self.declare_parameter("command_timeout_s", 0.25)
        self.leg_id = self.get_parameter("leg_id").get_parameter_value().string_value
        self._command_timeout_s = float(self.get_parameter("command_timeout_s").value)

        self.create_subscription(Float32, "executor/leg_target_velocity", self._on_target_velocity, 10)
        self.create_subscription(Float32, "executor/leg_target_turn_rate", self._on_target_turn_rate, 10)
        self.create_subscription(Bool, "/enabled", self._on_enabled, 10)

        self.command_pub = self.create_publisher(String, "leg/command", 10)
        self.status_pub = self.create_publisher(String, "leg/status", 10)
        self.timer = self.create_timer(0.1, self._on_timer)

        self._last_velocity = 0.0
        self._last_turn_rate = 0.0
        self._enabled = False
        self._sequence = 0
        self._last_motion_command_time_ns = self.get_clock().now().nanoseconds

        self.get_logger().info(f"LegControllerNode initialised for leg {self.leg_id}.")

    def _on_target_velocity(self, msg: Float32) -> None:
        self._last_velocity = float(msg.data)
        self._last_motion_command_time_ns = self.get_clock().now().nanoseconds
        self.get_logger().info(f"[{self.leg_id}] Received leg target velocity {self._last_velocity:.3f}")

    def _on_target_turn_rate(self, msg: Float32) -> None:
        self._last_turn_rate = float(msg.data)
        self._last_motion_command_time_ns = self.get_clock().now().nanoseconds
        self.get_logger().info(f"[{self.leg_id}] Received leg target turn rate {self._last_turn_rate:.3f}")

    def _on_enabled(self, msg: Bool) -> None:
        self._enabled = bool(msg.data)

    def _on_timer(self) -> None:
        now_ns = self.get_clock().now().nanoseconds
        command_stale = (now_ns - self._last_motion_command_time_ns) > int(
            self._command_timeout_s * 1_000_000_000
        )

        command = LegCommand(
            leg_id=self.leg_id,
            sequence=self._sequence,
            host_time_ns=now_ns,
            enabled=self._enabled and not command_stale,
            safe_stop=(not self._enabled) or command_stale,
            velocity_target=self._last_velocity,
            turn_rate_target=self._last_turn_rate,
        )
        self._sequence += 1

        command_msg = String()
        command_msg.data = command.to_json()
        self.command_pub.publish(command_msg)

        status = String()
        status.data = (
            f"{self.leg_id}: enabled={command.enabled} safe_stop={command.safe_stop} "
            f"(v={self._last_velocity:.3f}, w={self._last_turn_rate:.3f})"
        )
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
