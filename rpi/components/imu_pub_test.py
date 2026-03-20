import socket
import time
from imu import IMU
from tca9548a import TCA9548A

JETSON_IP = "10.42.0.1"
UDP_PORT  = 5005
RATE      = 50
INTERVAL  = 1.0 / RATE

mux = TCA9548A(bus=1, address=0x70)

sensors = [
    IMU(sensor_id=0, channel=0, mux=mux),
    IMU(sensor_id=1, channel=1, mux=mux),
    IMU(sensor_id=2, channel=2, mux=mux),
    IMU(sensor_id=3, channel=3, mux=mux),
    IMU(sensor_id=4, channel=4, mux=mux),
    IMU(sensor_id=5, channel=5, mux=mux),
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
    mux.close_all()
    sock.close()