from mpu6050 import MPU6050
import numpy as np
import time
from ahrs.filters import madgwick


class IMU:
    def __init__(self, sensor_id: int, address: int, sample_rate: int = 50, beta: float = 0.033):
        """
        :param sensor_id: logical ID for this sensor (0-5) out of six sensors
        :param address:   I2C address — 0x68 or 0x69 (set via AD0 pin)
        :param sample_rate: Hz, must match imu_pub.py — 50Hz is the default 
        :param beta: Madgwick gain — 0.033 is 6-axis default
        """
        self.sensor_id   = sensor_id
        self.sample_rate = sample_rate

        self._sensor = MPU6050(address)
        self._filter = madgwick(frequency=sample_rate, beta=beta)

        # Filter needs an initial quaternion to update from
        self._q = np.array([1.0, 0.0, 0.0, 0.0])

        # Public state
        self.w, self.x, self.y, self.z = 1.0, 0.0, 0.0, 0.0

    def update(self):
        accel = self._sensor.read_accel_g()
        gyro  = self._sensor.read_gyro_dps()

        acc_vec = np.array(accel, dtype=float)
        gyr_vec = np.array(gyro,  dtype=float) * (np.pi / 180.0)  # dps → rad/s

        self._q = self._filter.updateIMU(q=self._q, gyr=gyr_vec, acc=acc_vec)

        self.w, self.x, self.y, self.z = self._q

    def packet(self) -> str:
        return f"{self.sensor_id},{self.w:.4f},{self.x:.4f},{self.y:.4f},{self.z:.4f}"