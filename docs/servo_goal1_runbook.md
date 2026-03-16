# Goal 1 Servo Runbook

## Evidence status

Validated from repo code:

- the current board firmware path is Marlin `2.1.2.5` built from the official `Ender-3 V2 / CrealityV422 / MarlinUI` configuration
- the board pin map for the Creality V4 family defines `SERVO0_PIN` as `PB0` when a Pin-27 board is not in use
- Marlin supports servo movement through `M280 P<index> S<angle>` when `NUM_SERVOS` is enabled
- the current ROS 2 host bridge can already exchange serial commands with the board

Validated from direct hardware behavior:

- the board accepts and boots the custom Marlin image
- the serial console is readable at `115200`
- ROS 2 messages can already round-trip over UART through the board

Inference / engineering judgment:

- the best first servo wiring target is the board's BLTouch / probe PWM output path associated with `SERVO0_PIN`
- on Creality 4.2.2 boards this is commonly the probe-style 3-wire signal path, but that exact physical connector mapping is not validated by direct continuity probing here

## Wiring

Use only one servo for this test.
Do not connect steppers or IMUs yet.
Prefer an external regulated 5V servo supply instead of drawing servo current from USB.

Candidate connections:

- Servo signal wire (often orange or yellow) -> board `SERVO0_PIN` signal path on the Creality V4 probe / BLTouch output connector
- Servo ground wire (often brown or black) -> board ground on the same connector or a shared board ground
- Servo +5V wire (often red) -> regulated 5V supply
- External 5V supply ground -> board ground

Text diagram:

```text
External 5V supply +  ----> Servo V+
External 5V supply GND ---> Servo GND
                         \-> Ender board GND
Ender board SERVO0/PB0 --> Servo signal
```

Safety notes:

- Do not power the servo from USB alone.
- Keep ground common between the servo supply and the Ender board.
- Start with the horn unloaded if possible.
- Keep fingers clear before commanding angles.

## ROS topic

- publish target angle in degrees on `/servo_angle_deg`
- receive echoed angle acknowledgements on `/servo_angle_ack_deg`
- watch raw board serial on `/ender_serial_rx`

## Firmware image

The build output for this step will be copied to:

- `firmware/ender_v4_2_2/build/tars_marlin_servo_20260314.bin`

## Validation flow

1. Flash the servo image.
2. Start the ROS servo bridge.
3. Watch `/servo_angle_ack_deg`.
4. Publish a few safe angles like `30`, `90`, and `150`.
5. Confirm the physical servo moves and the UART acknowledgement appears.
