import socket
import time
from mpu6050 import mpu6050

# Setup
JETSON_IP = "10.42.0.1" 
UDP_PORT = 5005
sensor = mpu6050()
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print(f"Broadcasting IMU to {JETSON_IP}...")

try:
    while True:
        accel = sensor.read_accel_g()
        gyro = sensor.read_gyro_dps()
        
        # Pack data into a simple string: "ax,ay,az,gx,gy,gz"
        message = f"{accel[0]:.2f},{accel[1]:.2f},{accel[2]:.2f},{gyro[0]:.2f},{gyro[1]:.2f},{gyro[2]:.2f}"
        
        sock.sendto(message.encode(), (JETSON_IP, UDP_PORT))
        
        # 50Hz is a good standard for robot balancing
        time.sleep(0.02) 

except KeyboardInterrupt:
    sock.close()