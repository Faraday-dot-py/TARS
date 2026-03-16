from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Launch a minimal software stack suitable for basic system tests."""

    use_serial_bridge = LaunchConfiguration("use_serial_leg_bridge")
    serial_leg_id = LaunchConfiguration("serial_leg_id")
    serial_device = LaunchConfiguration("serial_device")

    nodes = [
        DeclareLaunchArgument("use_serial_leg_bridge", default_value="false"),
        DeclareLaunchArgument("serial_leg_id", default_value="L0"),
        DeclareLaunchArgument("serial_device", default_value="/dev/ttyACM0"),
        Node(
            package="robot_controller",
            executable="robot_controller",
            name="robot_controller",
            output="screen",
        ),
        Node(
            package="motion",
            executable="motion_planner",
            name="motion_planner",
            output="screen",
        ),
        Node(
            package="motion",
            executable="motion_executor",
            name="motion_executor",
            output="screen",
        ),
        Node(
            package="state_estimation",
            executable="leg_pose_estimator",
            name="leg_pose_estimator",
            output="screen",
        ),
        Node(
            package="b0_interface",
            executable="b0_interface",
            name="b0_interface",
            output="screen",
        ),
    ]

    for leg_id in ("L0", "L1", "L2", "L3"):
        nodes.append(
            Node(
                package="leg_control",
                executable="leg_controller",
                namespace=leg_id,
                name="leg_controller",
                parameters=[{"leg_id": leg_id}],
                output="screen",
            )
        )

    nodes.append(
        Node(
            package="leg_transport",
            executable="serial_leg_bridge",
            namespace=serial_leg_id,
            name="serial_leg_bridge",
            parameters=[
                {"leg_id": serial_leg_id},
                {"device_path": serial_device},
            ],
            condition=IfCondition(use_serial_bridge),
            output="screen",
        )
    )

    return LaunchDescription(nodes)
