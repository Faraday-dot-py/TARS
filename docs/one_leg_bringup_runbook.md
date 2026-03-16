# TARS One-Leg Bring-Up Runbook

This runbook turns the feasibility checklist into an execution sequence for the first real one-leg validation.

Use the current repo code as the source of truth for software structure.
Do not treat placeholder nodes or the current motion executor as stable final APIs.
Do not mark any hardware step as complete unless it was performed on real hardware.

## Evidence Labels

For each step, record one of:

- validated from repo code
- validated from direct hardware inspection
- inference or engineering judgment

## Stage A: Host Preparation

Goal: verify the host-side scaffold before connecting hardware.

### Step A1: Protocol unit tests

Run:

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:PYTHONPATH='src\leg_transport;src\leg_control'
python -m pytest src\leg_transport\test\test_protocol.py
```

Expected result:

- protocol tests pass

Stop if:

- CRC or framing tests fail
- payload sizing or optional field handling fails

Evidence type:

- validated from repo code

### Step A2: Compile sanity

Run:

```powershell
python -m compileall src\leg_control src\leg_transport src\motion src\bringup
```

Expected result:

- compile succeeds for the host-side packages

Stop if:

- any syntax or import error appears

Evidence type:

- validated from repo code

### Step A3: Review the active host boundary

Inspect these files before touching hardware:

- `src/leg_control/leg_control/leg_command.py`
- `src/leg_control/leg_control/leg_controller_node.py`
- `src/leg_transport/leg_transport/protocol.py`
- `src/leg_transport/leg_transport/serial_leg_bridge_node.py`
- `src/bringup/launch/minimal_bringup.launch.py`

Confirm:

- `leg_control` owns command semantics
- `leg_transport` owns framing and serial I/O
- watchdog and safe-stop semantics exist on the host side
- one-leg serial bridge launch path exists

Stop if:

- the boundary is unclear or coupled back into Pi-specific assumptions

Evidence type:

- validated from repo code

## Stage B: First Hardware Contact

You need hardware starting here.

Plug in now:

- one Creality Ender 3 v4.2.2 board
- one USB cable to the host

Do not connect motors or sensors yet unless a step explicitly asks for them.

Goal: identify the actual board and confirm the transport starting point.

### Step B1: Physical board inspection

Inspect directly:

- printed board revision text
- MCU package marking
- USB connector style
- accessible headers or pads that may matter later
- any visible clues about stepper driver arrangement

Record:

- exact board revision text
- exact MCU marking
- any uncertainty about pin access or timer use

Stop if:

- the board revision is not actually confirmed
- the MCU cannot be identified from direct inspection

Evidence type:

- validated from direct hardware inspection

### Step B2: USB enumeration check

With the board connected, identify whether the host sees a serial device.

Suggested checks on the host:

```powershell
Get-ChildItem /dev/ttyACM*
Get-ChildItem /dev/ttyUSB*
```

If your environment differs, use the equivalent device listing that is actually available.

Expected result:

- one plausible serial device appears

Stop if:

- no device appears
- the device appears and disappears repeatedly without explanation

Evidence type:

- validated from direct hardware inspection

### Step B3: Launch the host stack with one serial bridge

Suggested launch shape:

```powershell
ros2 launch bringup minimal_bringup.launch.py use_serial_leg_bridge:=true serial_leg_id:=L0 serial_device:=/dev/ttyACM0
```

Adjust the device path only if the host proves a different path.

Expected result:

- normal host nodes start
- `L0/serial_leg_bridge` starts
- the bridge reports either a ready serial link or a coarse wait/error state

Stop if:

- the bridge crashes on device open
- the bridge reports an active state when no valid device is present

Evidence type:

- validated from direct hardware inspection for the device path
- validated from repo code for expected node behavior

## Stage C: Transport and Safety Principle Test

Goal: prove the basic command link can fail safe before any meaningful actuator work.

### Step C1: Idle safety check

With the board connected and no real actuator load yet:

- start the bridge
- do not send active commands
- observe whether the system remains in a safe or waiting state

Expected result:

- no active motion intent is inferred from idle startup
- no unsafe "enabled by default" behavior is observed

Stop if:

- startup defaults active instead of safe

Evidence type:

- validated from direct hardware inspection if confirmed on a real board

### Step C2: Enable then stop traffic

When firmware test support exists, exercise:

- explicit enable
- active command traffic
- command timeout
- explicit disable

Expected result:

- explicit enable is required before active behavior
- timeout causes safe-stop
- disable causes safe-stop

Stop if:

- stale traffic can keep the board active
- serial interruption leaves outputs logically active

Evidence type:

- validated from direct hardware inspection once actually performed

### Step C3: Corrupted-frame behavior

When firmware test support exists, inject malformed frames or truncated reads.

Expected result:

- malformed frames are rejected
- the board remains safe

Stop if:

- corrupted traffic can produce accepted motion state

Evidence type:

- validated from direct hardware inspection once actually performed

## Stage D: Incremental Output Bring-Up

Do not attach everything at once.

Goal: test one timing-sensitive feature at a time.

### Step D1: Servo-only test

Plug in now if you have not already:

- servo
- safe external power as needed

Test:

- repeated servo targets
- bridge heartbeat at the same time
- timeout or disable behavior

Expected result:

- stable servo output
- no serial collapse
- safe-stop still works

Stop if:

- watchdog behavior breaks under servo activity
- servo timing is visibly unstable

Evidence type:

- validated from direct hardware inspection

### Step D2: First stepper test

Plug in now if you are ready:

- one stepper path with safe power and wiring

Test:

- simple commanded movement
- explicit stop
- watchdog stop

Expected result:

- stepper responds correctly
- timeout and disable stop it safely

Stop if:

- stop behavior is not reliable
- serial link becomes unstable during stepping

Evidence type:

- validated from direct hardware inspection

### Step D3: Second stepper test

Plug in now if the first stepper test passed:

- second stepper path

Test:

- both steppers active
- repeated command updates
- watchdog behavior under load

Expected result:

- both paths remain stable enough to continue

Stop if:

- concurrency materially degrades timing, link quality, or safe-stop behavior

Evidence type:

- validated from direct hardware inspection

## Stage E: Sensor Bring-Up

Goal: test whether the board can support the intended telemetry load.

### Step E1: First MPU6050

Plug in now if available:

- first MPU6050

Test:

- bus access
- repeated samples
- telemetry return while the bridge remains healthy

Expected result:

- stable readable samples
- telemetry stays coherent

Stop if:

- reads are unstable or telemetry becomes corrupted

Evidence type:

- validated from direct hardware inspection

### Step E2: Second MPU6050

Plug in now if the first IMU test passed:

- second MPU6050

Test:

- both sensors present
- sustained sample collection
- no regression in transport stability

Expected result:

- both sensors remain usable together

Stop if:

- the two-IMU arrangement is not stable enough to supervise a leg

Evidence type:

- validated from direct hardware inspection

## Stage F: Combined One-Leg Feasibility Check

Only do this if prior stages passed.

Goal: answer whether one board per leg is fundamentally feasible.

### Step F1: Combined-load run

Run with:

- serial bridge active
- watchdog active
- servo active
- both steppers active
- both IMUs active

Observe:

- safe-stop still works on timeout and disable
- serial transport remains stable
- telemetry remains usable for supervision
- no obvious timing starvation appears

Pass only if:

- safety behavior survives combined load
- command and telemetry link remain understandable
- actuator behavior remains controlled enough to continue development

Fail if:

- combined load breaks safety behavior
- combined load breaks transport reliability
- combined load makes timing too unstable to trust

Evidence type:

- validated from direct hardware inspection

## Decision Rule

You can call the architecture fundamentally feasible only after Stage F passes on one real board.

Before that point:

- host-side success means the software architecture is plausible
- hardware-side partial success means specific principles are promising
- full feasibility is still unproven

## Operator Log Template

For each session, record:

- Date
- Operator
- Hardware connected
- Device path used
- Host commit or working-tree note
- Stage and step
- PASS / FAIL / BLOCKED
- Evidence label
- Notes
- Next action

## What You Need To Plug In, In Order

1. Nothing for Stage A
2. One board and one USB cable for Stage B
3. Still no actuators for Stage C if possible
4. Servo for Step D1
5. First stepper for Step D2
6. Second stepper for Step D3
7. First IMU for Step E1
8. Second IMU for Step E2

That ordering is intentional. Do not jump straight to the fully populated leg.
