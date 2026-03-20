from mpu6050 import MPU6050
import numpy as np
from ahrs.filters import Madgwick
from tca9548a import TCA9548A

class FakeMPU6050:
    def read_accel_g(self):
        return [0.0, 0.0, 1.0]  # gravity pointing down
    def read_gyro_dps(self):
        return [0.0, 0.0, 0.0]  # no rotation


class IMU:
    def __init__(self, sensor_id: int, channel: int, mux: TCA9548A, address: int, sample_rate: int = 50, beta: float = 0.033):
        """
        :param sensor_id: logical ID for this sensor (0-5) out of six sensors
        :param channel:   I2C channel on the multiplexer (0–7)
        :param mux:       TCA9548A multiplexer instance
        :param address:   I2C address — 0x68 or 0x69 for real sensors, 0 for fake sensor that returns static data
        :param sample_rate: Hz, must match imu_pub.py — 50Hz is the default 
        :param beta: Madgwick gain — 0.033 is 6-axis default
        """
        self.sensor_id   = sensor_id
        self.channel     = channel
        self.sample_rate = sample_rate
        self._mux         = mux

        # All sensors can share 0x68 because the mux isolates them
        self._sensor = FakeMPU6050() if address == 0 else MPU6050(address)
        self._filter = Madgwick(frequency=sample_rate, beta=beta)

        # Filter needs an initial quaternion to update from
        self._q = np.array([1.0, 0.0, 0.0, 0.0])

        # Public state
        self.w, self.x, self.y, self.z = 1.0, 0.0, 0.0, 0.0

    def update(self):
        # Select this sensor's channel before reading
        self._mux.select(self.channel)

        accel = self._sensor.read_accel_g()
        gyro  = self._sensor.read_gyro_dps()

        acc_vec = np.array(accel, dtype=float)
        gyr_vec = np.array(gyro,  dtype=float) * (np.pi / 180.0)  # dps → rad/s

        self._q = self._filter.updateIMU(q=self._q, gyr=gyr_vec, acc=acc_vec)

        self.w, self.x, self.y, self.z = self._q

    def packet(self) -> str:
        return f"{self.sensor_id},{self.w:.4f},{self.x:.4f},{self.y:.4f},{self.z:.4f}"


if __name__ == "__main__":
    id = 1
    address = 0
    channel = 0
    sensor_guy = IMU(sensor_id=id, address=address, channel=channel, mux=TCA9548A())
    for _ in range(100):
        sensor_guy.update()
    print(sensor_guy.packet())
