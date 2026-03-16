# LED Test Notes

This is the simplest real-world firmware test target for the Ender board.

## Important caveats

Validated from direct hardware inspection:

- MCU is GD32F303RET6
- host serial path reaches the board through the CH340 bridge and `/dev/ttyUSB1`

Inference / engineering judgment:

- flash image is placed at `0x08007000` for the Creality bootloader path
- provisional LED pin is `PC13`

That LED pin is not validated yet. If the board does not blink after flashing and publishing commands, the next likely cause is incorrect LED pin assignment rather than a broken serial protocol.

## Build command

```bash
cd /home/faraday/TARS/firmware/ender_v4_2_2
make clean && make
```

The flashable image will be:

```bash
/home/faraday/TARS/firmware/ender_v4_2_2/build/tars_led_test.bin
```

## Flash command

This board is most likely updated by microSD bootloader rather than direct USB flashing.

Assuming your microSD card is mounted at `/mnt/<drive>` in WSL:

```bash
cp /home/faraday/TARS/firmware/ender_v4_2_2/build/tars_led_test.bin /mnt/<drive>/firmware.bin && sync
```

Then:

1. power the printer board off
2. insert the microSD card
3. power the board on
4. wait for the bootloader to consume the image
5. power cycle again if needed

## Host command path

Run the ROS bridge:

```bash
source /opt/ros/humble/setup.bash
source /home/faraday/TARS/install/setup.bash
ros2 run leg_transport led_test_bridge --ros-args -p device_path:=/dev/ttyUSB1
```

Publish commands:

```bash
ros2 topic pub /set_blinking_state std_msgs/msg/Bool "{data: true}" --once
ros2 topic pub /set_blinking_rate_khz std_msgs/msg/Int32 "{data: 1}" --once
```
