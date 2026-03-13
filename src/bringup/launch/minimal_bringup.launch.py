from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    """Launch a minimal software stack suitable for basic system tests."""

    nodes = [
        # Top-level controller
        Node(
            package="robot_controller",
            executable="robot_controller",
            name="robot_controller",
            output="screen",
        ),
        # Motion stack
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
        # State estimation
        Node(
            package="state_estimation",
            executable="leg_pose_estimator",
            name="leg_pose_estimator",
            output="screen",
        ),
        # Base station interface
        Node(
            package="b0_interface",
            executable="b0_interface",
            name="b0_interface",
            output="screen",
        ),
    ]

    # Leg controllers for L0–L3
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

    return LaunchDescription(nodes)


