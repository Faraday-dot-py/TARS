"""
INIT:
- Confirm connection to jetson
Dynamic leg identification:
- If Active Carriage and no fixed: L1
- If Fixed Carriage and no active: L3
- If Both and OS is RPI: L2
- If Both and OS is Jetson: L1
- Configure IMUs
- Start subscribers based on what leg was detected
- Start publishing based on what leg was detected

THREADS:
- IMU madgewick AHRS filter
- Stepper controller
- Servo controller

Publishers:
- IMU data

Subscribers:
- Status
- Active Carriage Goal (optional based off leg (L0-2))
- Fixed Carriage Goal (optional based off leg (L1-3))
- Angle goal (optional based off leg (L0-2))
"""

#!/usr/bin/env python3
import json
import socket
import threading
import time

# Hardware control files
from mpu6050 import mpu6050
from carriage import Carriage
from servo import ServoController

# Servo controller
ila = ServoController(gpio_pin=18, start_angle_deg=0.0, max_speed_dps=180.0)
ila.start()

# Hard-coded network config
ZERO_BIND_IP = "0.0.0.0"
ZERO_BIND_PORT = 15120

JETSON_IP = "10.42.0.1"       # set to your Jetson IP on the Wi-Fi network
JETSON_TELEM_PORT = 15121       # Jetson listens here for telemetry

# Behavior
TELEM_HZ = 50.0
CMD_TIMEOUT_S = 0.20            # if no command in this time, go safe
LEG_ID = 1

# Shared state
state_lock = threading.Lock()
last_cmd_time = 0.0
last_cmd_seq = -1

# Pretend actuator targets and sensor values
enabled = False
target = {"hip": 0.0, "knee": 0.0, "ankle": 0.0}
gyro = {"gx": 0.0, "gy": 0.0, "gz": 0.0}

def now_s() -> float:
    return time.monotonic()

def safe_disable():
    global enabled
    # Put any real actuator disable here
    enabled = False

def handle_command(msg: dict):
    print("Got data: ", msg.items())
    ila.set_goal(float(msg['ila_goal']))

def udp_rx_loop(sock: socket.socket):
    while True:
        data, _addr = sock.recvfrom(2048)
        try:
            msg = json.loads(data.decode("utf-8"))
        except Exception:
            continue
        handle_command(msg)

def simulate_sensors_and_actuators(dt: float):
    # Replace with real sensor read and actuator write
    # Here we just "move" gyro a tiny bit when enabled
    global gyro
    with state_lock:
        if enabled:
            gyro["gx"] += 0.01 * dt
            gyro["gy"] += 0.02 * dt
            gyro["gz"] += 0.03 * dt
        else:
            # drift back toward 0
            gyro["gx"] *= 0.98
            gyro["gy"] *= 0.98
            gyro["gz"] *= 0.98

def watchdog_check():
    with state_lock:
        if enabled and (now_s() - last_cmd_time) > CMD_TIMEOUT_S:
            safe_disable()

def udp_tx_telemetry_loop(tx_sock: socket.socket):
    period = 1.0 / TELEM_HZ
    next_t = now_s()

    seq = 0
    while True:
        t = now_s()
        dt = max(0.0, t - next_t + period)

        simulate_sensors_and_actuators(dt)
        watchdog_check()

        with state_lock:
            msg = {
                "type": "telem",
                "leg_id": LEG_ID,
                "seq": seq,
                "enabled": enabled,
                "target": target,
                "gyro": gyro,
                "t_monotonic": t,
            }

        payload = json.dumps(msg).encode("utf-8")
        tx_sock.sendto(payload, (JETSON_IP, JETSON_TELEM_PORT))

        seq += 1
        next_t += period
        sleep_s = next_t - now_s()
        if sleep_s > 0:
            time.sleep(sleep_s)
        else:
            next_t = now_s()

def main():
    rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    rx_sock.bind((ZERO_BIND_IP, ZERO_BIND_PORT))

    tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    t_rx = threading.Thread(target=udp_rx_loop, args=(rx_sock,), daemon=True)
    t_tx = threading.Thread(target=udp_tx_telemetry_loop, args=(tx_sock,), daemon=True)
    t_rx.start()
    t_tx.start()

    print(f"[ZeroW] Listening for commands on UDP {ZERO_BIND_IP}:{ZERO_BIND_PORT}")
    print(f"[ZeroW] Sending telemetry to UDP {JETSON_IP}:{JETSON_TELEM_PORT}")

    while True:
        time.sleep(1.0)

if __name__ == "__main__":
    main()
