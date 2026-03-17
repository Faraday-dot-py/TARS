from setuptools import find_packages, setup

package_name = "ender_stepper_transport"

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
    description="Pico <-> Ender stepper transport contract and validation helpers.",
    license="MIT",
    tests_require=["pytest"],
)
