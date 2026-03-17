from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node



def generate_launch_description() -> LaunchDescription:
    leg_id = LaunchConfiguration("leg_id")
    pico_host = LaunchConfiguration("pico_host")
    command_port = LaunchConfiguration("command_port")
    telemetry_port = LaunchConfiguration("telemetry_port")
    run_connection_probe = LaunchConfiguration("run_connection_probe")

    return LaunchDescription(
        [
            DeclareLaunchArgument("leg_id", default_value="L0"),
            DeclareLaunchArgument("pico_host", default_value="192.168.4.1"),
            DeclareLaunchArgument("command_port", default_value="15120"),
            DeclareLaunchArgument("telemetry_port", default_value="15121"),
            DeclareLaunchArgument("run_connection_probe", default_value="true"),
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
                package="leg_control",
                executable="leg_controller",
                namespace=leg_id,
                name="leg_controller",
                parameters=[{"leg_id": leg_id}],
                output="screen",
            ),
            Node(
                package="pico_leg_bridge",
                executable="pico_leg_bridge",
                namespace=leg_id,
                name="pico_leg_bridge",
                parameters=[
                    {
                        "leg_id": leg_id,
                        "pico_host": pico_host,
                        "command_port": command_port,
                        "telemetry_port": telemetry_port,
                    }
                ],
                output="screen",
            ),
            Node(
                package="pico_leg_bridge",
                executable="pico_ender_connection_probe",
                namespace=leg_id,
                name="pico_ender_connection_probe",
                parameters=[
                    {
                        "pico_host": pico_host,
                        "command_port": command_port,
                    }
                ],
                condition=IfCondition(run_connection_probe),
                output="screen",
            ),
        ]
    )
