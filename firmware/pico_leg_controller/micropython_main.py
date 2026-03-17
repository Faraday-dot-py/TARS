"""MicroPython Pico W UDP/UART bridge for Thonny upload.

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


uart = UART(UART_ID, baudrate=UART_BAUD, tx=Pin(UART_TX_PIN), rx=Pin(UART_RX_PIN))

wifi = network.WLAN(network.STA_IF)
sock = None
last_remote = None
uart_line = bytearray()


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


def handle_udp_packet():
    global last_remote
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

    uart.write(message)
    uart.write("\n")


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
                reply_udp(bytes(uart_line) + b"\n")
            uart_line = bytearray()
            continue
        if len(uart_line) < 255:
            uart_line.append(byte)
        else:
            uart_line = bytearray()


def main():
    print("Starting TARS Pico W MicroPython UDP/UART bridge")
    print("UART{} baud={} tx=GP{} rx=GP{}".format(UART_ID, UART_BAUD, UART_TX_PIN, UART_RX_PIN))
    connect_wifi()
    start_udp_socket()
    print("Ready. Send UDP to Pico at {}:{}.".format(wifi.ifconfig()[0], UDP_PORT))

    while True:
        handle_udp_packet()
        handle_uart_input()
        time.sleep(POLL_DELAY_S)


main()
