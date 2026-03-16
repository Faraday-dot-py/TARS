from setuptools import find_packages, setup

package_name = "leg_transport"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=False,
    maintainer="TARS Team",
    maintainer_email="todo@example.com",
    description="Transport adapters and embedded framing for leg devices.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "serial_leg_bridge = leg_transport.serial_leg_bridge_node:main",
            "led_test_bridge = leg_transport.led_test_bridge_node:main",
            "marlin_echo_bridge = leg_transport.marlin_echo_bridge_node:main",
            "marlin_servo_bridge = leg_transport.marlin_servo_bridge_node:main",
            "marlin_imu_bridge = leg_transport.marlin_imu_bridge_node:main",
            "marlin_servo_imu_bridge = leg_transport.marlin_servo_imu_bridge_node:main",
        ],
    },
)
