from setuptools import setup

package_name = "b0_interface"

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
    description="Base station (B0) interface.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "b0_interface = b0_interface.b0_interface_node:main",
        ],
    },
)

