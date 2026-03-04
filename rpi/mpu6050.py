# mpu6050.py
from typing import Tuple


class mpu6050:
    """
    Placeholder MPU6050 interface.

    The main node will call these methods.
    Do not implement I2C or device specifics here yet.
    """

    def __init__(self) -> None:
        pass

    def configure(self) -> None:
        """
        Configure sensor ranges, filters, sample rates, offsets, etc.
        """
        raise NotImplementedError

    def read_gyro_dps(self) -> Tuple[float, float, float]:
        """
        Return gyro in degrees per second as (x, y, z).
        """
        raise NotImplementedError

    def read_accel_g(self) -> Tuple[float, float, float]:
        """
        Return acceleration in g as (x, y, z).
        """
        raise NotImplementedError