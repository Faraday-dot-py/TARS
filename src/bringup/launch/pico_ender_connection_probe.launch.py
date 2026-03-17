from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description() -> LaunchDescription:
    pico_host = LaunchConfiguration("pico_host")
    command_port = LaunchConfiguration("command_port")
    probe_period_s = LaunchConfiguration("probe_period_s")
    response_timeout_s = LaunchConfiguration("response_timeout_s")

    return LaunchDescription(
        [
            DeclareLaunchArgument("pico_host", default_value="192.168.4.1"),
            DeclareLaunchArgument("command_port", default_value="15120"),
            DeclareLaunchArgument("probe_period_s", default_value="2.0"),
            DeclareLaunchArgument("response_timeout_s", default_value="1.0"),
            Node(
                package="pico_leg_bridge",
                executable="pico_ender_connection_probe",
                name="pico_ender_connection_probe",
                output="screen",
                parameters=[
                    {
                        "pico_host": pico_host,
                        "command_port": command_port,
                        "probe_period_s": probe_period_s,
                        "response_timeout_s": response_timeout_s,
                    }
                ],
            ),
        ]
    )
