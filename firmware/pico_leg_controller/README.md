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
- Compact Ender commands such as `S50,100E` are passed straight through over UART.
- Human-friendly UDP commands are translated to compact Ender commands.
- Any UART line from the Ender board is returned over UDP to the last sender.

Supported UDP commands:

- `ENABLE` -> `A1E`
- `DISABLE` -> `A0E`
- `UART_TELEMETRY ON` -> enable `Got uart line:` console/UDP forwarding
- `UART_TELEMETRY OFF` -> disable `Got uart line:` console/UDP forwarding
- `ENDER_TELEMETRY ON` -> `T1E`
- `ENDER_TELEMETRY OFF` -> `T0E`
- `STATUS` -> `Q0E`
- `BOARD` -> `B0E`
- `LIMITS` -> `L0E`
- `MODE ABS` -> `M0E`
- `MODE REL` -> `M1E`
- `RATE 120` -> `R120E`
- `RATE 5000` -> `R5000E`
- `MOVE 50 100` -> `S50,100E`
- `INNER 50 OUTER 100` -> `S50,100E`
- `HOME X` / `HOME Y` / `HOME BOTH` -> `H10E` / `H01E` / `H11E`
- `ZERO X` / `ZERO Y` / `ZERO BOTH` -> `Z10E` / `Z01E` / `Z11E`
- raw compact strings like `S050100E`
- raw bench commands like `M114` or `G1 X20 Y20 R100`

## Bench Test

```bash
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> PING
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> ENABLE
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> STATUS
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> RATE\ 120
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> MOVE\ 050\ 100
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> LIMITS
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> BOARD
```

Expected:

- `PING` returns `PICO:PONG`
- `ENABLE` returns `ok`
- `STATUS` returns X/Y position and target info plus fault/endstop state
- `MOVE 50 100` returns `ok` and the Ender should begin stepping
- `LIMITS` returns the X/Y endstop state
- `BOARD` returns the Ender firmware pin mapping summary
- while the Ender is active, you should also see periodic telemetry lines beginning with `T,`

The Pico can also suppress forwarded UART telemetry at runtime:

```bash
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> UART_TELEMETRY\ OFF
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> UART_TELEMETRY\ ON
```

And the Ender can stop or resume generating the source telemetry stream:

```bash
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> ENDER_TELEMETRY\ OFF
python3 /home/faraday/TARS/tools/udp_bridge_probe.py --host <pico-ip> ENDER_TELEMETRY\ ON
```
