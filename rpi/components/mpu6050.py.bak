import smbus2
import threading
import time
from typing import Tuple, Optional

# Assuming you have a simple dataclass for Pose3D
from dataclasses import dataclass

@dataclass
class Pose3D:
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0

class MPU6050:
    def __init__(self, address: int = 0x68) -> None:
        self.bus = smbus2.SMBus(1)
        self.address = address
        self.bus.write_byte_data(self.address, 0x6B, 0)
        
        # Threading setup
        self.current_pose = Pose3D()
        self._lock = threading.Lock()
        self._running = True
        
        # Start the background sensing thread
        self._thread = threading.Thread(target=self._update_loop, daemon=True)
        self._thread.start()

    def _read_word(self, register: int) -> int:
        high = self.bus.read_byte_data(self.address, register)
        low = self.bus.read_byte_data(self.address, register + 1)
        value = (high << 8) + low
        if value > 32768: value -= 65536
        return value

    def read_gyro_dps(self) -> Tuple[float, float, float]:
        FS_SEL = 131.0
        return (self._read_word(0x43)/FS_SEL, self._read_word(0x45)/FS_SEL, self._read_word(0x47)/FS_SEL)

    def read_accel_g(self) -> Tuple[float, float, float]:
        AFS_SEL = 16384.0
        return (self._read_word(0x3B)/AFS_SEL, self._read_word(0x3D)/AFS_SEL, self._read_word(0x3F)/AFS_SEL)

    def _update_loop(self):
        """ This runs in the background at ~100Hz """
        while self._running:
            try:
                accel = self.read_accel_g()
                # Basic tilt math (Roll/Pitch)
                # You can swap this for the Madgwick math if you want filtered data here
                import math
                new_roll = math.atan2(accel[1], accel[2]) * 57.2958
                new_pitch = math.atan2(-accel[0], math.sqrt(accel[1]**2 + accel[2]**2)) * 57.2958
                
                with self._lock:
                    self.current_pose.roll = new_roll
                    self.current_pose.pitch = new_pitch
                
                time.sleep(0.01) # 100Hz
            except Exception as e:
                print(f"IMU Thread Error: {e}")

    def get_pose(self) -> Pose3D:
        """ Non-blocking call to get the latest calculated pose """
        with self._lock:
            return self.current_pose

    def stop(self):
        self._running = False
        self._thread.join()