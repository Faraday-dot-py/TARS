from setuptools import find_packages, setup

package_name = "leg_control"

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
    description="Leg-level control nodes for L0-L3.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "leg_controller = leg_control.leg_controller_node:main",
        ],
    },
)
