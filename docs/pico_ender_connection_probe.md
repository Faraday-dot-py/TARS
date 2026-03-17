# Pico-Ender Connection Probe

## Goal

- Validated from repo code: the current uploadable Pico image is a temporary UDP-to-UART bridge, not the final leg-controller firmware.
- Validated from repo code: the current Ender-side comms path for bench testing is Marlin responding to `M115` over `SERIAL_PORT_2`.
- Validated from repo code: `pico_ender_connection_probe` is the ROS 2 node that confirms Jetson -> Pico and Pico -> Ender reachability using the firmware that actually exists on this branch.
- Validated from direct hardware inspection: none.

## Firmware Sources

- Pico W source: [firmware/pico_leg_controller/src/main.cpp](/home/faraday/TARS/firmware/pico_leg_controller/src/main.cpp)
- Pico W build config: [firmware/pico_leg_controller/platformio.ini](/home/faraday/TARS/firmware/pico_leg_controller/platformio.ini)
- Ender Marlin source: [firmware/marlin_upstream](/home/faraday/TARS/firmware/marlin_upstream)
- Ender serial config: [firmware/marlin_upstream/Marlin/Configuration.h](/home/faraday/TARS/firmware/marlin_upstream/Marlin/Configuration.h)

## Intended Build Outputs

- Pico W artifact after a successful build: `firmware/pico_leg_controller/.pio/build/pico_w_udp_uart_bridge/firmware.uf2`
- Ender artifact after a successful build: `firmware/marlin_upstream/.pio/build/STM32F103RE_creality/firmware.bin`

## Build Commands

```bash
cd /home/faraday/TARS/firmware/pico_leg_controller
PLATFORMIO_CORE_DIR=/tmp/pio-core ~/.local/bin/pio run -e pico_w_udp_uart_bridge

cd /home/faraday/TARS/firmware/marlin_upstream
PLATFORMIO_CORE_DIR=/tmp/pio-core ~/.local/bin/pio run -e STM32F103RE_creality
```

## Current Build Limitation In This Environment

- Validated from direct command execution: local builds in this sandbox are blocked because PlatformIO needs writable cache space and network/package access.
- Validated from direct command execution: the Pico build additionally depends on `https://github.com/maxgerhardt/platform-raspberrypi.git`, which could not be resolved here.
- Inference / engineering judgment: on a normal development machine with PlatformIO internet access, the commands above are the intended way to produce the firmware files.

## ROS 2 Probe Node

- Node executable: `pico_ender_connection_probe`
- Launch file: [src/bringup/launch/pico_ender_connection_probe.launch.py](/home/faraday/TARS/src/bringup/launch/pico_ender_connection_probe.launch.py)

### What It Checks

1. Sends `PING` to the Pico bridge over UDP and expects `PICO:PONG`
2. Sends `M115` through the Pico UART bridge to the Ender board
3. Confirms the Ender board answers with a Marlin `FIRMWARE_NAME` string

### Topics

- `/probe/pico_connected`
- `/probe/ender_connected`
- `/probe/pico_response`
- `/probe/ender_response`
- `/probe/summary`

### Run

```bash
ros2 launch bringup pico_ender_connection_probe.launch.py
```

### Expected Result

- `pico_connected` becomes `true` when Jetson reaches the Pico W
- `ender_connected` becomes `true` when the Ender responds to `M115`
- `summary` reports whether the failure is on the Jetson->Pico leg or the Pico->Ender leg
