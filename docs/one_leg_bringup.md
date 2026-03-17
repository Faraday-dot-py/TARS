# One-Leg Bring-Up

## Scope

- Validated from repo code: the current ROS 2 stack is Jetson-centered, `leg_control` and `state_estimation` are placeholders, `rpi_bridge` is an isolated UDP JSON experiment, and the meaningful legacy endpoint behavior lives in `rpi/main.py`.
- Validated from repo code: the new host-side scaffolding in this change introduces explicit `Jetson <-> Pico` and `Pico <-> Ender` protocol packages, watchdog semantics, and one-leg bring-up launch support.
- Validated from direct hardware inspection: none in this change.
- Inference / engineering judgment: Pico W is the right home for per-leg wireless, servo, IMU, Madgwick fusion, and calibration orchestration; the Ender board is the right home for step timing and stepper watchdog enforcement.
- Inference / engineering judgment: the Ender board 5V rail may be a practical source for the Pico-side logic, but current capacity, servo suitability, and grounding margin remain unvalidated in repo code.

## Architecture Summary

- Jetson remains the ROS 2 host and speaks transport-agnostic leg semantics.
- `src/pico_leg_bridge` owns the Jetson-side wireless bridge to one Pico W.
- `src/ender_stepper_transport` defines the Pico-to-Ender stepper contract only; Jetson does not own Ender timing.
- `firmware/pico_leg_controller` is a scaffold for wireless command handling, servo PWM, three MPU6050 sensors, Madgwick fusion, limit switch inputs, and startup calibration orchestration.
- `firmware/ender_stepper_controller` is a scaffold for dual-stepper execution, watchdog safe-stop, and status/fault reporting.

## 1. Wireless link / Jetson-to-Pico connectivity

Purpose: Validate the Jetson-side bridge, binary framing, sequence handling, and stale-telemetry fault path before depending on any leg actuation.

Validated from repo code vs inference:
- Validated from repo code: `src/pico_leg_bridge/pico_leg_bridge/protocol.py` defines compact framed messages with versioning, sequence numbers, and CRC16.
- Validated from repo code: `src/pico_leg_bridge/pico_leg_bridge/bridge_runtime.py` marks wireless link loss when telemetry goes stale.
- Inference / engineering judgment: Wi-Fi is adequate for command/telemetry and debug visibility, but not deterministic enough for step timing.

Required wiring/setup:
- Jetson on the same wireless network as one Pico W.
- Pico W firmware listening on the configured command port and replying on the configured telemetry port.
- No Ender board required for this first check.

Commands or test hooks:
```bash
pytest src/leg_transport/test src/pico_leg_bridge/test -q
ros2 launch bringup pico_one_leg_bringup.launch.py leg_id:=L0 pico_host:=192.168.4.2
ros2 topic pub /L0/command/enable std_msgs/msg/Bool "{data: true}" -1
ros2 topic echo /L0/state/fault_bits
```

Expected behavior:
- Unit tests pass.
- `fault_bits` clears the wireless-link-loss bit once valid Pico telemetry arrives.
- If the Pico is absent, the bridge should keep reporting a fault instead of hanging or pretending to be healthy.

Failure interpretation:
- Failing protocol tests means host framing changed unexpectedly or CRC handling regressed.
- A persistent wireless fault during live bring-up means connectivity, port, firmware, or framing mismatch.

How the results should influence the next implementation step:
- Do not move on to servo or IMU validation until telemetry is arriving and stale-link behavior is understood.

## 2. Pico-to-Ender local transport

Purpose: Validate the local wired transport contract independently from wireless transport.

Validated from repo code vs inference:
- Validated from repo code: `src/ender_stepper_transport/ender_stepper_transport/protocol.py` defines the framed Pico-to-Ender contract with SOF, version, type, sequence, payload length, payload, and CRC16.
- Validated from repo code: the contract keeps stepper execution local to the Ender and excludes servo, IMU, fusion, and limit switch ownership.
- Inference / engineering judgment: UART is the preferred first transport unless later repo code proves a better local link.

Required wiring/setup:
- Pico UART TX/RX/GND wired to the Ender-side UART chosen for the leg controller path.
- Shared ground between Pico-side logic and the Ender board.

Commands or test hooks:
```bash
pytest src/ender_stepper_transport/test -q
```

Expected behavior:
- Stepper command/status frames encode and decode cleanly.
- Watchdog timeout, applied sequence, and fault fields remain intact across round trips.

Failure interpretation:
- Failing protocol tests mean the Pico/Ender contract is not stable enough to scaffold firmware against yet.

How the results should influence the next implementation step:
- Only start live UART bring-up after the contract is stable in tests.

## 3. Servo functionality

Purpose: Validate that servo responsibility stays on the Pico boundary and is not leaked into the Ender contract.

Validated from repo code vs inference:
- Validated from repo code: the Jetson-to-Pico command includes `servo_target_deg`.
- Validated from repo code: the Ender protocol has no servo field.
- Validated from repo code: legacy Raspberry Pi behavior already treated servo control as local-per-leg behavior in `rpi/components/ila.py`.
- Inference / engineering judgment: future external servo power may be required if the Ender 5V rail proves insufficient.

Required wiring/setup:
- Pico servo PWM pin wired to the ANNIMOS signal input.
- Servo power and ground wired with shared ground back to the Pico/Ender power domain.
- Current budget and voltage sag are unvalidated; monitor carefully.

Commands or test hooks:
```bash
ros2 topic pub /L0/command/servo_target_deg std_msgs/msg/Float32 "{data: 90.0}" -1
ros2 topic pub /L0/command/servo_target_deg std_msgs/msg/Float32 "{data: 135.0}" -1
```

Expected behavior:
- The Pico should update servo output locally without any Ender involvement.
- Ender logs or status should remain unchanged for servo-only tests.

Failure interpretation:
- Servo movement issues with clean wireless telemetry point to Pico PWM, power, wiring, or servo limits, not the Ender contract.

How the results should influence the next implementation step:
- If servo power is noisy or brown-outs appear, pause and plan external servo power before further combined tests.

## 4. IMU functionality

Purpose: Validate raw IMU data flow from three MPU6050 devices into the Pico boundary.

Validated from repo code vs inference:
- Validated from repo code: the new bridge publishes three indexed IMU channels under `/imu/0`, `/imu/1`, and `/imu/2`.
- Validated from repo code: legacy `rpi/components/mpu6050.py` only covered a single sensor and basic tilt math, so tri-IMU acquisition remains scaffolded, not proven.
- Validated from direct hardware inspection: none.

Required wiring/setup:
- Three MPU6050 devices wired to the Pico-side I2C topology intended for the leg controller.
- Address selection or bus multiplexing resolved in firmware before expecting three unique streams.

Commands or test hooks:
```bash
ros2 topic echo /L0/imu/0/accel_g
ros2 topic echo /L0/imu/1/accel_g
ros2 topic echo /L0/imu/2/accel_g
ros2 topic echo /L0/imu/0/gyro_dps
```

Expected behavior:
- Each configured sensor index should publish independently.
- Missing sensors should be surfaced as faults or absent streams, not silently aliased data.

Failure interpretation:
- Identical data on all three channels suggests addressing or mux issues.
- No data with healthy wireless transport suggests Pico-side sensor or firmware issues.

How the results should influence the next implementation step:
- Do not attempt Madgwick validation until each raw IMU path is distinct and believable.

## 5. Madgwick fusion functionality

Purpose: Validate that fused orientation is produced on the Pico side and reported separately from raw IMU data.

Validated from repo code vs inference:
- Validated from repo code: the Jetson-to-Pico boundary includes a distinct fused-orientation frame and ROS topic.
- Validated from repo code: existing tracked code does not yet implement Madgwick itself; firmware scaffolding is still required.
- Inference / engineering judgment: fusion belongs on the Pico to keep Jetson wireless traffic compact.

Required wiring/setup:
- Same tri-IMU setup as above.
- Pico firmware implementing Madgwick with a known sample period.

Commands or test hooks:
```bash
ros2 topic echo /L0/imu/fused_orientation
```

Expected behavior:
- Quaternion output should update smoothly and remain finite.
- Orientation should continue even if Jetson-side consumers are disconnected.

Failure interpretation:
- NaNs, jumps, or a static quaternion with changing IMU data suggest sample-timing, sensor-axis, or filter-state issues.

How the results should influence the next implementation step:
- Only use fused orientation in higher-level estimation after raw IMUs and quaternion stability both look credible.

## 6. Limit switch functionality

Purpose: Validate the two Pico-side limit switch inputs before any homing sequence uses them.

Validated from repo code vs inference:
- Validated from repo code: limit switch state is part of leg telemetry and calibration state.
- Validated from repo code: the Ender protocol intentionally does not own limit switch sensing.

Required wiring/setup:
- One limit switch per motor wired to Pico GPIO inputs with the intended pull-up or pull-down strategy.

Commands or test hooks:
```bash
ros2 topic echo /L0/state/limit_switch_bits
```

Expected behavior:
- Each switch toggles the expected bit independently.
- Idle state polarity should be documented before homing starts.

Failure interpretation:
- Chatter or both bits toggling together suggests grounding, debounce, or wiring faults.

How the results should influence the next implementation step:
- Do not enable startup calibration until switch polarity and stability are understood.

## 7. Startup calibration / homing functionality

Purpose: Validate the intended ownership split where Pico orchestrates calibration and Ender executes the local motion.

Validated from repo code vs inference:
- Validated from repo code: calibration action/state is present in the Jetson-to-Pico boundary.
- Validated from repo code: Pico-to-Ender command modes include a `HOME_TO_LIMIT` stepper mode.
- Inference / engineering judgment: the higher-level calibration state machine belongs on the Pico so switch interpretation and sequencing remain local.

Required wiring/setup:
- Working limit switches on the Pico.
- Working Pico-to-Ender local transport.
- Stepper mechanics safe to move slowly into the home direction.

Commands or test hooks:
```bash
ros2 topic pub /L0/command/calibration_action std_msgs/msg/UInt8 "{data: 1}" -1
ros2 topic echo /L0/state/calibration_state
ros2 topic echo /L0/state/fault_bits
```

Expected behavior:
- Calibration state should progress explicitly instead of being implicit or hidden.
- Faults should latch if a switch never arrives, the Ender watchdog trips, or motion aborts.

Failure interpretation:
- A calibration request with no state transition suggests Pico firmware state-machine gaps.
- Ender sequence stalls during homing suggest local transport or stepper execution issues.

How the results should influence the next implementation step:
- Complete homing validation before running dual-stepper coordinated motion.

## 8. Stepper 1 functionality

Purpose: Validate single-axis Ender execution while keeping the second axis idle.

Validated from repo code vs inference:
- Validated from repo code: Ender commands carry independent axis-1 and axis-2 targets and modes.
- Inference / engineering judgment: single-axis validation should come before dual-axis concurrency to isolate wiring and tuning issues.

Required wiring/setup:
- Stepper 1 driver and motor connected to the Ender board.
- Pico-to-Ender link operational.

Commands or test hooks:
```bash
pytest src/ender_stepper_transport/test -q
```

Expected behavior:
- Axis 1 status updates should reflect commanded mode changes and applied sequence movement.
- Axis 2 should remain disabled throughout the test.

Failure interpretation:
- Any axis-2 movement during an axis-1-only test is a contract, firmware-routing, or pin-map issue.

How the results should influence the next implementation step:
- Do not energize both axes until axis 1 can move and stop safely on its own.

## 9. Stepper 2 functionality

Purpose: Repeat the single-axis check for the second motor channel.

Validated from repo code vs inference:
- Validated from repo code: axis-2 fields are independent in the Pico-to-Ender contract.

Required wiring/setup:
- Stepper 2 driver and motor connected to the Ender board.

Commands or test hooks:
```bash
pytest src/ender_stepper_transport/test -q
```

Expected behavior:
- Axis 2 moves independently and reports its own state.
- Axis 1 remains disabled.

Failure interpretation:
- Cross-axis behavior again points to routing, state-machine, or board-pin confusion.

How the results should influence the next implementation step:
- Only proceed to concurrent motion after both axes behave independently.

## 10. Dual-stepper concurrent functionality

Purpose: Validate concurrent Ender execution without pushing coordination back onto Wi-Fi.

Validated from repo code vs inference:
- Validated from repo code: dual-axis commands and applied sequence reporting exist in the Ender contract.
- Inference / engineering judgment: local concurrency belongs on the Ender because wireless jitter should not own step timing.

Required wiring/setup:
- Both stepper channels wired and mechanically safe.

Commands or test hooks:
```bash
pytest src/ender_stepper_transport/test -q
```

Expected behavior:
- Both axes accept a single applied command sequence and report local execution status.
- Wireless link timing should not affect per-step pulse timing.

Failure interpretation:
- If motion quality depends on Jetson packet timing, the design has leaked real-time behavior onto Wi-Fi.

How the results should influence the next implementation step:
- Keep command granularity high-level and localize all pulse scheduling on the Ender.

## 11. Combined leg functionality

Purpose: Validate servo, IMUs, fusion, calibration, and steppers together for one leg.

Validated from repo code vs inference:
- Validated from repo code: the bridge topics and protocols expose all required hardware-function seams separately.
- Validated from direct hardware inspection: none.
- Inference / engineering judgment: one-leg combined testing should happen only after the individual function checks above are credible.

Required wiring/setup:
- Full one-leg wiring: Pico W, Ender board, servo, three IMUs, two limit switches, and both steppers.

Commands or test hooks:
```bash
ros2 launch bringup pico_one_leg_bringup.launch.py leg_id:=L0 pico_host:=192.168.4.2
ros2 topic echo /L0/state/fault_bits
ros2 topic echo /L0/imu/fused_orientation
```

Expected behavior:
- Telemetry stays coherent while servo, IMU, calibration, and stepper activities occur together.
- Fault reporting remains explicit instead of failing silently.

Failure interpretation:
- Brown-outs, noisy IMUs, or intermittent wireless faults during combined tests suggest grounding or power-budget issues first, not software correctness alone.

How the results should influence the next implementation step:
- Stabilize one-leg combined bring-up before scaling to more legs.

## 12. Watchdog / safe-stop / fault behavior

Purpose: Validate that stale commands and transport loss produce safe behavior on both links.

Validated from repo code vs inference:
- Validated from repo code: `PicoLegBridgeRuntime` marks stale wireless telemetry as a fault.
- Validated from repo code: both protocol layers carry explicit watchdog-related fields and fault bits.
- Validated from repo code: legacy `rpi/main.py` already treated command timeout as a safety boundary, so the new design preserves that idea while formalizing it.

Required wiring/setup:
- None for host-side tests.
- Full one-leg wiring for live safe-stop testing.

Commands or test hooks:
```bash
pytest src/leg_transport/test src/pico_leg_bridge/test src/ender_stepper_transport/test -q
ros2 topic pub /L0/command/safe_stop std_msgs/msg/Bool "{data: true}" -1
ros2 topic echo /L0/state/fault_bits
```

Expected behavior:
- Host tests prove stale-link and watchdog metadata behavior.
- Live tests should stop local actuation safely when commands stop or safe-stop is requested.

Failure interpretation:
- Any condition where motion continues after command loss is a stop-ship safety issue for further bring-up.

How the results should influence the next implementation step:
- Do not scale up hardware testing until safe-stop and watchdog paths behave predictably on one leg.
