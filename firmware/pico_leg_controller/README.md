# Pico Leg Controller Demo

## Intent

- Validated from repo code: this bring-up image is limited to Wi-Fi UDP on the Pico W and UART bridging into the Ender board.
- Validated from direct hardware inspection: none.
- Inference / engineering judgment: this is a temporary bench image for the first communications milestone, not the final leg-controller firmware.

## Build

```bash
cd firmware/pico_leg_controller
~/.local/bin/pio run -e pico_w_udp_uart_bridge
```

## Thonny / MicroPython Upload

If the Arduino/PlatformIO hotspot is not coming up, use the MicroPython version in
[`micropython_main.py`](/home/faraday/TARS/firmware/pico_leg_controller/micropython_main.py).

1. Flash standard MicroPython onto the Pico W if needed.
2. Open [`micropython_main.py`](/home/faraday/TARS/firmware/pico_leg_controller/micropython_main.py) in Thonny.
3. In Thonny, choose `Run -> Select interpreter -> MicroPython (Raspberry Pi Pico)`.
4. Save the file to the Pico as `main.py`.
5. Reset the Pico W.

The current script is set to join Wi-Fi SSID `SAMB0 2`.
If that network needs a password, edit `WIFI_PASSWORD` near the top of the file before saving it.

You should then see a serial message like:

```text
Starting TARS Pico W MicroPython UDP/UART bridge
Connecting to Wi-Fi SSID 'SAMB0 2'
Pico W Wi-Fi connected: ('<pico-ip>', '255.255.255.0', '<gateway>', '<dns>')
UDP bridge listening on port 15120
```

## Runtime Defaults

- Wi-Fi SSID: `SAMB0 2`
- Wi-Fi password: `None` in the current script
- UDP port: `15120`
- UART pins: `GP4` TX, `GP5` RX
- UART baud: `115200`

## Behavior

- `PING` over UDP returns `PICO:PONG`.
- Any other UDP payload is sent as a line over UART to the Ender board.
- Any UART line from the Ender board is returned over UDP to the last sender.

## Bench Test

```bash
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> PING
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> M115
```

Expected:

- `PING` returns `PICO:PONG`
- `M115` returns a Marlin line containing `FIRMWARE_NAME`
