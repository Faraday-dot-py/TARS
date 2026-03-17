import socket
import time
from imu import IMU

JETSON_IP = "10.42.0.1"
UDP_PORT  = 5005
RATE      = 50
INTERVAL  = 1.0 / RATE

# AD0 low = 0x68, AD0 high = 0x69
# For more than 2 sensors on one bus you need a TCA9548A multiplexer
sensors = [
    IMU(sensor_id=0, address=0x68),
    IMU(sensor_id=1, address=0x69),
    # IMU(sensor_id=2, address=0x68, mux_channel=2),  # expand when mux is wired
]

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"Sending {len(sensors)} IMUs to {JETSON_IP}:{UDP_PORT}")

try:
    last = time.time()
    while True:
        for imu in sensors:
            imu.update()
            sock.sendto(imu.packet().encode(), (JETSON_IP, UDP_PORT))

        next_tick = last + INTERVAL
        time.sleep(max(0, next_tick - time.time()))
        last = next_tick
except KeyboardInterrupt:
    sock.close()