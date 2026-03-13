from setuptools import setup

package_name = "robot_controller"

setup(
    name=package_name,
    version="0.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=False,
    maintainer="TARS Team",
    maintainer_email="todo@example.com",
    description="Top-level robot controller and mode manager.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "robot_controller = robot_controller.robot_controller_node:main",
        ],
    },
)

