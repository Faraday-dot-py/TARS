from mpu6050 import MPU6050
import socket
import threading
import numpy as np
from ahrs import madgwick

# Setup
UDP_PORT = 5005
SAMPLE_RATE = 50  # 50 Hz matching imu_pub.py

class IMU:
    
