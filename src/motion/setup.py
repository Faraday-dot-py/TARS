from setuptools import setup

package_name = "motion"

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
    description="Motion planner and executor nodes.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "motion_planner = motion.motion_planner_node:main",
            "motion_executor = motion.motion_executor_node:main",
        ],
    },
)

