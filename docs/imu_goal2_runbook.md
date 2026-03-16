# Goal 2 IMU Runbook

## Evidence status

Validated from repo code:

- the current custom board firmware path is Marlin `2.1.2.5` on the official `Ender-3 V2 / CrealityV422 / MarlinUI` base
- the board-side custom IMU path in this step uses the already accessible `G V IN G OUT` header
- the IMU firmware image repurposes `IN` and `OUT` as a software I2C pair for one MPU6050
- the ROS side publishes decoded samples to `/imu/data_raw`

Validated from direct hardware behavior:

- the custom Marlin image path already boots on the board
- UART command / response is already working with ROS 2

Inference / engineering judgment:

- for this first IMU bring-up, use `IN/PB0` as `SDA` and `OUT/PB1` as `SCL`
- this is a deliberate repurposing of the probe header for an IMU-only test, not a final leg wiring decision

## Wiring

Use one MPU6050 breakout only.
Do not keep the servo connected to `IN` during this step.

Header used on the board:

```text
G   V   IN   G   OUT
|   |    |   |    |
|   |    |   |    +-- IMU SCL  (PB1)
|   |    |   +------- IMU GND  (optional alternate ground)
|   |    +----------- IMU SDA  (PB0)
|   +---------------- IMU VCC
+-------------------- IMU GND
```

Connect:

- MPU6050 `GND` -> board `G`
- MPU6050 `VCC` -> board `V`
- MPU6050 `SDA` -> board `IN`
- MPU6050 `SCL` -> board `OUT`

Practical note:

- this assumes a common MPU6050 breakout module with onboard regulation / pullups, such as a GY-521-style board
- if your module is a bare 3.3V-only sensor board, do not connect it to `V` without confirming regulator and logic compatibility first

## Firmware image

The build output for this step will be copied to:

- `firmware/ender_v4_2_2/build/tars_marlin_imu_20260314.bin`

## ROS topics

- `/imu/data_raw` (`sensor_msgs/msg/Imu`)
- `/imu/roll_pitch_deg` (`std_msgs/msg/String`)
- `/ender_serial_rx` (`std_msgs/msg/String`)

## Validation flow

1. Flash the IMU image.
2. Wire one MPU6050 breakout to the `G V IN G OUT` header.
3. Start the ROS IMU bridge.
4. Watch `/imu/data_raw` and `/imu/roll_pitch_deg`.
5. Move the sensor by hand and confirm the values change plausibly.
