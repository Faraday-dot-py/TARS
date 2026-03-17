from setuptools import find_packages, setup

package_name = "pico_leg_bridge"

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
    description="Jetson-side wireless bridge for one leg Pico W controller.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "pico_leg_bridge = pico_leg_bridge.pico_leg_bridge_node:main",
            "pico_ender_connection_probe = pico_leg_bridge.connection_probe_node:main",
        ],
    },
)
