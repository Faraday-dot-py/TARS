#!/usr/bin/env python3
# ==============================================================
#                              SETUP
import logging
import os
from datetime import datetime

# Set up logging
if not os.path.exists('log'):
    os.mkdir('log')

LOG_DIR = "log"
logging.basicConfig(
    filename=os.path.join(LOG_DIR, str(datetime.now())),
    level=logging.DEBUG,  # Options are: debug, info, warning, error, critical
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# General utilities
import json
import socket
import threading
import time
import types
logging.debug("Imported general files")

# Hardware control files
from components.carriage import Carriage
from components.display import Display
from components.ila import ServoController
from components.mpu6050 import MPU6050

logging.debug("Imported components")


# ==============================================================
#                           Autodetect config
# Auto-detect the host name as the leg id
import platform

hostname = platform.node()
MANUAL_LEG_ID = "l2"
if MANUAL_LEG_ID:
    LEG_ID = MANUAL_LEG_ID
    logging.debug(f"Override leg id as [{MANUAL_LEG_ID}]")
else:
    LEG_ID = "l1" if hostname == "sam" else hostname
    logging.debug(f"Autodetected leg as [{LEG_ID}]")

# Load config from leg_config.json
with open('config/leg_config.json', 'r') as f:
    config = json.load(f)
    config = config[LEG_ID]

logging.debug(f"Loaded config for {LEG_ID}: {config}")

# Setup and load components
leg_components = types.SimpleNamespace()

if config['a_carr']:
    leg_components.a_carr = Carriage(pins=config['a_carr_pins'])
else:
    leg_components.a_carr = None

if config['f_carr']:
    leg_components.f_carr = Carriage(pins=config['f_carr_pins'])
else:
    leg_components.f_carr = None

leg_components.ila = ServoController(pin=config['ila_pin'])
leg_components.imu = MPU6050()

if config['display']:
    leg_components.display = Display()
else:
    leg_components.display = None

# ==============================================================
#                            Network Setup
# Hard-coded network config
ZERO_BIND_IP = "0.0.0.0"
ZERO_BIND_PORT = 15120

JETSON_IP = "10.42.0.1"        # set to your Jetson IP on the Wi-Fi network
JETSON_TELEM_PORT = 15121       # Jetson listens here for telemetry

# Behavior
TELEM_HZ = 50.0
CMD_TIMEOUT_S = 0.20            # if no command in this time, go safe

# Shared state
state_lock = threading.Lock()
last_cmd_time = 0.0
last_cmd_seq = -1
enabled = True


# ==============================================================
#                     Define networking functions
def now_s() -> float:
    return time.monotonic()

def safe_disable():
    global enabled
    enabled = False
    logging.warning("Watchdog triggered: disabling due to command timeout")

def handle_command(msg: dict):
    global last_cmd_time, last_cmd_seq
    logging.debug(f"Got data: {list(msg.items())}")

    with state_lock:
        last_cmd_time = now_s()
        last_cmd_seq = msg.get('seq', last_cmd_seq)

    if msg.get('ila_goal') is not None:
        leg_components.ila.set_goal(float(msg['ila_goal']))
    if msg.get('a_carr_goal') is not None and leg_components.a_carr is not None:
        leg_components.a_carr.set_goal(float(msg['a_carr_goal']))
    if msg.get('f_carr_goal') is not None and leg_components.f_carr is not None:
        leg_components.f_carr.set_goal(float(msg['f_carr_goal']))

def udp_rx_loop(sock: socket.socket):
    while True:
        data, _addr = sock.recvfrom(2048)
        try:
            msg = json.loads(data.decode("utf-8"))
        except Exception:
            continue
        handle_command(msg)

def watchdog_check():
    global enabled
    with state_lock:
        if enabled and (now_s() - last_cmd_time) > CMD_TIMEOUT_S:
            safe_disable()


# ==============================================================
#                      Main telemetry TX loop
def udp_tx_telemetry_loop(tx_sock: socket.socket):
    global enabled
    period = 1.0 / TELEM_HZ
    next_t = now_s()

    seq = 0
    while True:
        t = now_s()

        watchdog_check()

        with state_lock:
            a_carr_state = (
                (leg_components.a_carr.get_pos(), leg_components.a_carr.get_goal())
                if leg_components.a_carr is not None else None
            )
            f_carr_state = (
                (leg_components.f_carr.get_pos(), leg_components.f_carr.get_goal())
                if leg_components.f_carr is not None else None
            )
            ila_state = (leg_components.ila.get_pos(), leg_components.ila.get_goal())
            pose = leg_components.imu.get_pose()
            msg = {
                "type": "telem",
                "leg_id": LEG_ID,
                "seq": seq,
                "enabled": enabled,
                "pose": pose,
                "a_carr": a_carr_state,
                "f_carr": f_carr_state,
                "ila": ila_state,
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
    global last_cmd_time
    last_cmd_time = now_s()  # initialize so watchdog doesn't fire immediately

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