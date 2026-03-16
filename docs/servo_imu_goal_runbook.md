# Goal 1+2 Combined Servo And IMU Runbook

## Evidence status

Validated from repo code:

- the custom board firmware path is Marlin `2.1.2.5` on the official `Ender-3 V2 / CrealityV422 / MarlinUI` base
- the servo path already uses Marlin `SERVO0_PIN`, which maps to `PB0` on the Creality `4.2.2` board family
- the combined firmware in this step keeps the servo on `PB0` and moves the MPU6050 software-I2C bus to `PA5` and `PA6`
- the ROS side now has a combined serial bridge node so servo commands and IMU polling share one UART connection cleanly

Validated from direct hardware behavior:

- the custom Marlin image path boots on the real board
- the servo already worked on the `G V IN` probe header path
- the earlier IMU firmware worked when the probe header was repurposed for IMU-only testing
- ROS 2 already round-trips commands and responses over the board UART

Inference / engineering judgment:

- the cleanest first simultaneous wiring is to keep the servo on the proven `G V IN` probe header path and move the IMU signal lines to unused endstop signal pins
- for this combined bring-up, use `X-` signal as `SDA` and `Y-` signal as `SCL`, which map to `PA5` and `PA6`
- power the MPU6050 from the same regulated `5V` / `GND` source used for the successful probe-header tests, with common ground to the board

## Wiring

### Servo

Keep the servo where it already worked:

- servo `GND` -> BLTouch / probe header `G`
- servo `+5V` -> BLTouch / probe header `V` or external regulated `5V`
- servo `signal` -> BLTouch / probe header `IN`

Header silk:

```text
G   V   IN   G   OUT
^   ^   ^
|   |   +-- servo signal
|   +------ servo +5V
+---------- servo GND
```

### IMU

Move the MPU6050 signal lines off the probe header:

- IMU `SDA` -> `X-` endstop signal pin (`PA5`)
- IMU `SCL` -> `Y-` endstop signal pin (`PA6`)
- IMU `VCC` -> regulated `5V`
- IMU `GND` -> board ground

Recommended power wiring for the first combined test:

- IMU `VCC` -> BLTouch / probe header `V`
- IMU `GND` -> BLTouch / probe header spare `G`

Combined text diagram:

```text
Probe header: G   V   IN   G   OUT
              |   |   |    |
              |   |   |    +---- IMU GND
              |   |   +--------- Servo signal
              |   +------------- Servo +5V and IMU VCC
              +----------------- Servo GND

X- endstop signal pin (PA5) ---- IMU SDA
Y- endstop signal pin (PA6) ---- IMU SCL
```

Important physical note:

- the pin names `PA5` and `PA6` are validated from the Marlin pin map
- the exact left-to-right order of pins on your `X-` and `Y-` endstop connectors is not validated by direct continuity probing here, so connect to the signal position on those headers rather than assuming power pins from them

## Firmware image

The build output for this combined step will be copied to:

- `firmware/ender_v4_2_2/build/tars_marlin_servo_imu_20260314.bin`

Expected boot marker:

- `TARS_MARLIN_SERVO_IMU_READY SERVO=PB0 IMU=PA5_PA6`

## ROS topics

Use one bridge node for both functions:

- publish servo angle: `/servo_angle_deg` (`std_msgs/msg/Float32`)
- receive servo acknowledgement: `/servo_angle_ack_deg` (`std_msgs/msg/Float32`)
- receive IMU data: `/imu/data_raw` (`sensor_msgs/msg/Imu`)
- receive roll/pitch summary: `/imu/roll_pitch_deg` (`std_msgs/msg/String`)
- watch raw board serial: `/ender_serial_rx` (`std_msgs/msg/String`)

## Validation flow

1. Flash the combined firmware image.
2. Keep the servo on `G V IN`.
3. Wire the IMU with `SDA -> X- signal`, `SCL -> Y- signal`, and shared `5V/GND`.
4. Start the combined ROS bridge.
5. Watch `/imu/data_raw`.
6. Publish a safe servo angle like `30` or `90`.
7. Confirm the servo still moves while IMU data continues to update.
