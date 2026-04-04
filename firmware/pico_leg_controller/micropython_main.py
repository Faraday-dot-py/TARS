"""MicroPython Pico W UDP/UART bridge for the compact Ender command set.

Save this file to the Pico W as ``main.py``.
"""

from machine import Pin, UART
import network
import socket
import time


WIFI_SSID = "SAMB0 2"
WIFI_PASSWORD = None
UDP_PORT = 15120
UART_ID = 1
UART_BAUD = 115200
UART_TX_PIN = 4
UART_RX_PIN = 5
POLL_DELAY_S = 0.001

COMPACT_OPCODES = ("S", "A", "M", "R", "H", "Q", "L", "B", "Z", "T")


uart = UART(UART_ID, baudrate=UART_BAUD, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))

wifi = network.WLAN(network.STA_IF)
sock = None
last_remote = None
uart_line = bytearray()
uart_telemetry_enabled = True


def connect_wifi():
    wifi.active(True)
    if wifi.isconnected():
        print("Pico W Wi-Fi connected:", wifi.ifconfig())
        return

    print("Connecting to Wi-Fi SSID '{}'".format(WIFI_SSID))
    if WIFI_PASSWORD:
        wifi.connect(WIFI_SSID, WIFI_PASSWORD)
    else:
        wifi.connect(WIFI_SSID)

    deadline = time.ticks_add(time.ticks_ms(), 10000)
    while not wifi.isconnected():
        if time.ticks_diff(deadline, time.ticks_ms()) <= 0:
            raise RuntimeError("Timed out connecting to Wi-Fi '{}'".format(WIFI_SSID))
        time.sleep(0.1)

    print("Pico W Wi-Fi connected:", wifi.ifconfig())


def start_udp_socket():
    global sock
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(False)
    sock.bind(("0.0.0.0", UDP_PORT))
    print("UDP bridge listening on port", UDP_PORT)


def reply_udp(message):
    if not last_remote:
        return
    if isinstance(message, str):
        message = message.encode("utf-8")
    sock.sendto(message, last_remote)


def send_uart_command(command):
    uart.write(command)
    if not command.endswith("\n"):
        uart.write("\n")
    print("Sent to Ender:", command)


def zero_pad(value):
    value = int(value)
    if value < 0:
        value = 0
    if value > 999:
        value = 999
    return "{:03d}".format(value)


def signed_text(value):
    return str(int(value))


def positive_text(value):
    value = int(value)
    if value < 1:
      value = 1
    return str(value)


def axis_mask(token):
    token = token.upper()
    if token in ("X", "INNER"):
        return "10"
    if token in ("Y", "OUTER"):
        return "01"
    if token in ("XY", "BOTH"):
        return "11"
    return None


def build_compact_command(message):
    raw = message.strip()
    upper = raw.upper()
    if not raw:
        return None

    if raw[0] in COMPACT_OPCODES and raw.endswith("E"):
        return raw

    if upper.startswith("M") or upper.startswith("G"):
        return raw

    parts = upper.split()
    if not parts:
        return None

    if parts[0] == "ENABLE":
        return "A1E"
    if parts[0] in ("DISABLE", "STOP"):
        return "A0E"
    if parts[0] == "STATUS":
        return "Q0E"
    if parts[0] == "BOARD":
        return "B0E"
    if parts[0] == "LIMITS":
        return "L0E"
    if parts[0] == "ENDER_TELEMETRY" and len(parts) == 2:
        if parts[1] == "ON":
            return "T1E"
        if parts[1] == "OFF":
            return "T0E"
        return None

    if parts[0] == "MODE" and len(parts) == 2:
        if parts[1] == "ABS":
            return "M0E"
        if parts[1] == "REL":
            return "M1E"
        return None

    if parts[0] == "RATE" and len(parts) == 2:
        try:
            return "R{}E".format(positive_text(float(parts[1])))
        except ValueError:
            return None

    if parts[0] == "MOVE" and len(parts) == 3:
        try:
            return "S{},{}E".format(signed_text(float(parts[1])), signed_text(float(parts[2])))
        except ValueError:
            return None

    if len(parts) == 4 and parts[0] == "INNER" and parts[2] == "OUTER":
        try:
            return "S{},{}E".format(signed_text(float(parts[1])), signed_text(float(parts[3])))
        except ValueError:
            return None

    if parts[0] == "HOME" and len(parts) == 2:
        mask = axis_mask(parts[1])
        if mask is None:
            return None
        return "H{}E".format(mask)

    if parts[0] == "ZERO" and len(parts) == 2:
        mask = axis_mask(parts[1])
        if mask is None:
            return None
        return "Z{}E".format(mask)

    return None


def handle_udp_packet():
    global last_remote, uart_telemetry_enabled
    try:
        packet, remote = sock.recvfrom(256)
    except OSError:
        return

    last_remote = remote
    message = packet.decode("utf-8", "replace").strip()
    if not message:
        return

    if message == "PING":
        reply_udp("PICO:PONG\n")
        return

    upper = message.upper()
    if upper in ("UART_TELEMETRY ON", "UART TELEMETRY ON"):
        uart_telemetry_enabled = True
        reply_udp("UART_TELEMETRY:ON\n")
        return

    if upper in ("UART_TELEMETRY OFF", "UART TELEMETRY OFF"):
        uart_telemetry_enabled = False
        reply_udp("UART_TELEMETRY:OFF\n")
        return

    command = build_compact_command(message)
    if command is None:
        reply_udp("ERR BAD_CMD\n")
        return

    send_uart_command(command)


def handle_uart_input():
    global uart_line
    data = uart.read()
    if not data:
        return

    for byte in data:
        if byte == 13:
            continue
        if byte == 10:
            if uart_line:
                try:
                    line = bytes(uart_line).decode("utf-8", "replace")
                except Exception:
                    line = str(bytes(uart_line))
                if uart_telemetry_enabled:
                    print("Got uart line:", line)
                    reply_udp(line + "\n")
            uart_line = bytearray()
            continue
        if len(uart_line) < 255:
            uart_line.append(byte)
        else:
            uart_line = bytearray()


def main():
    print("Starting TARS Pico W compact UDP/UART bridge")
    print("UART{} baud={} tx=GP{} rx=GP{}".format(UART_ID, UART_BAUD, UART_TX_PIN, UART_RX_PIN))
    connect_wifi()
    start_udp_socket()
    print("Ready. Send UDP to Pico at {}:{}.".format(wifi.ifconfig()[0], UDP_PORT))

    while True:
        handle_udp_packet()
        handle_uart_input()
        time.sleep(POLL_DELAY_S)


main()
