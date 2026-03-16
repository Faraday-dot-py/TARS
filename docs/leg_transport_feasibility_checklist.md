# TARS One-Leg Feasibility Verification Checklist

This checklist is for determining whether the proposed Jetson-to-Ender per-leg architecture is fundamentally feasible.

Evidence handling rules:

- Treat the current repo code as the source of truth for software structure.
- Distinguish clearly between:
  - validated from repo code
  - validated from direct hardware inspection
  - inference or engineering judgment
- Do not mark hardware-dependent items as passed unless they were tested on real hardware.
- Do not treat placeholder nodes or the current motion executor as stable interface contracts.
- Preserve the old Raspberry Pi endpoint behavior as reference when comparing watchdog and safe-stop expectations.

## Current Status Snapshot

### Validated from repo code

- `leg_control` now owns transport-agnostic leg command semantics.
- `leg_transport` now owns framed serial protocol scaffolding and one-leg bridge scaffolding.
- The host-side protocol includes framing, versioning, message type, sequence, payload length, payload, and CRC16.
- Host-side safe-stop and watchdog concepts are represented in code.
- `motion_executor` is still incomplete and should be treated as unstable placeholder logic.

### Not yet validated

- Any Ender 3 v4.2.2 hardware capability
- Any real serial device behavior
- Any timer allocation assumptions
- Any real stepper, servo, or IMU integration
- Any combined-load behavior on one physical board

## Gate 0: Host-Side Sanity

Goal: prove the host architecture is coherent before touching hardware.

### Test 0.1: Protocol unit tests

What to test:

- CRC known-vector correctness
- frame encode/decode round-trip
- payload size expectations
- optional target flag packing
- malformed frame rejection

Current repo coverage:

- `src/leg_transport/test/test_protocol.py`

Pass criteria:

- all protocol tests pass
- malformed frames are rejected deterministically

Fail criteria:

- any frame ambiguity
- CRC mismatch acceptance
- payload sizing inconsistencies

Use of result:

- Pass: keep the protocol shape and move to transport simulation.
- Fail: fix protocol before any board testing.

Hardware needed:

- No

### Test 0.2: Host compile/import sanity

What to test:

- Python compile success for `leg_control`, `leg_transport`, `motion`, and `bringup`
- import path sanity for the new package boundaries

Pass criteria:

- compile passes with no syntax failures

Fail criteria:

- syntax or import failures in the new host-side path

Use of result:

- Pass: host-side refactor is structurally ready for staged validation.
- Fail: do not proceed to hardware.

Hardware needed:

- No

### Test 0.3: Simulated bridge behavior

What to test:

- enabled command emits `SET_ENABLE`
- active command emits `SET_COMMAND`
- stale command path emits `SAFE_STOP`
- missing device path fails safe
- telemetry decoding path rejects malformed payloads safely

Recommended method:

- inject a fake transport object into `serial_leg_bridge_node`
- assert sent frames and state transitions

Pass criteria:

- bridge behavior matches the intended safety semantics

Fail criteria:

- stale or disabled states can still emit active commands
- bridge fails open instead of safe

Use of result:

- Pass: host-side safety logic is strong enough to test against a real board.
- Fail: revise bridge semantics before hardware testing.

Hardware needed:

- No

## Gate 1: Physical Board Identification

Goal: confirm the board you actually have matches the assumed bring-up path.

### Test 1.1: Board revision inspection

What to inspect:

- printed board revision
- MCU part marking
- accessible USB interface
- visible stepper driver arrangement
- likely I2C access points
- possible servo-capable output pin candidates

Pass criteria:

- revision is confirmed as a real board you can repeatedly identify
- MCU can be named from direct inspection
- candidate pins/interfaces are identified for later validation

Fail criteria:

- board revision unclear
- MCU not identifiable
- board differs materially from the expected control assumptions

Use of result:

- Pass: document the exact board under test and proceed.
- Fail: stop making hardware assumptions and re-scope.

Hardware needed:

- Yes

What you may need to plug in:

- One real Creality Ender 3 v4.2.2 board
- Power only if needed for safe visual inspection
- USB cable if you want to confirm enumeration later

## Gate 2: Serial Link Feasibility

Goal: prove direct USB serial is a workable first transport.

### Test 2.1: USB serial enumeration and open/close behavior

What to test:

- board enumerates over USB
- host can open the device path reliably
- reconnect behavior is understandable
- bridge remains safe when the device disappears

Pass criteria:

- one stable device path can be used for repeated tests
- unplug/replug does not leave the bridge in an active unsafe state

Fail criteria:

- enumeration is unreliable
- serial path is unstable even before actuator work

Use of result:

- Pass: keep USB serial as the foundational transport.
- Fail: re-evaluate board suitability or host/USB assumptions.

Hardware needed:

- Yes

What you may need to plug in:

- Board USB to host

### Test 2.2: Framing robustness over the real link

What to test:

- valid frames are received by firmware test code or loopback harness
- corrupted frames are rejected
- partial reads do not create false-valid packets
- sequence numbers remain traceable

Pass criteria:

- valid frames survive end-to-end transport
- invalid frames are rejected safely

Fail criteria:

- framing is too fragile for embedded serial transport

Use of result:

- Pass: protocol framing is suitable for firmware integration.
- Fail: change framing before adding actuators.

Hardware needed:

- Yes, unless replaced by a loopback harness on the same host

## Gate 3: Safety Principle Test

Goal: prove the embedded-controller concept can fail safe.

### Test 3.1: Watchdog and disable behavior

What to test:

- explicit disable transitions outputs to safe-stop
- command timeout transitions outputs to safe-stop
- malformed or missing traffic does not keep outputs active
- startup default is safe

Pass criteria:

- no stale command can keep the leg active
- safe-stop is the default on loss of command traffic

Fail criteria:

- outputs can remain active on stale commands or transport loss

Use of result:

- Pass: the architecture is safety-plausible.
- Fail: do not continue to actuator integration.

Hardware needed:

- Yes

What you may need to plug in:

- Board power
- USB serial
- Preferably no motors yet for the first watchdog proof if firmware allows that

## Gate 4: Timer and Output Feasibility

Goal: determine whether the board can realistically satisfy the intended per-leg load.

### Test 4.1: Servo-only timing test

What to test:

- stable pulse output for one ANNIMOS servo
- no watchdog disruption during repeated command traffic
- no serial collapse while servo commands update

Pass criteria:

- servo remains stable while serial and heartbeat traffic are active

Fail criteria:

- pulse timing is unstable or interferes with core link behavior

Use of result:

- Pass: servo is not immediately disqualifying.
- Fail: timer budget may already be too constrained.

Hardware needed:

- Yes

What you may need to plug in:

- Board
- USB serial
- Servo and safe power source

### Test 4.2: First stepper test

What to test:

- one stepper command path
- stop behavior
- watchdog-triggered stop behavior under active stepping

Pass criteria:

- stepper responds correctly and stops safely on timeout/disable

Fail criteria:

- stop behavior is not reliable
- stepping destabilizes communication or watchdog handling

Use of result:

- Pass: basic actuator control is plausible.
- Fail: board may not be suitable for this role.

Hardware needed:

- Yes

What you may need to plug in:

- Board
- USB serial
- One stepper path with safe wiring and power

### Test 4.3: Second stepper concurrency test

What to test:

- both steppers active under command updates
- watchdog remains effective
- serial link remains stable

Pass criteria:

- dual-stepper operation is stable enough to continue

Fail criteria:

- timing, link quality, or stop behavior degrades materially with the second stepper

Use of result:

- Pass: the two-stepper premise remains viable.
- Fail: this is a likely feasibility blocker for the current board choice.

Hardware needed:

- Yes

## Gate 5: Sensor Feasibility

Goal: prove the board can sample the intended sensors while the control loop remains healthy.

### Test 5.1: First MPU6050 test

What to test:

- bus access
- sampling rate stability
- telemetry framing under load

Pass criteria:

- reliable sampling and transport of first IMU data

Fail criteria:

- unstable reads or telemetry corruption

Use of result:

- Pass: sensor path is plausible.
- Fail: board pinout, noise, or firmware approach needs revision.

Hardware needed:

- Yes

### Test 5.2: Second MPU6050 test

What to test:

- second sensor integration without destabilizing the first
- bus/address arrangement remains workable

Pass criteria:

- both sensors can operate together reliably

Fail criteria:

- dual-IMU arrangement is not supportable with acceptable stability

Use of result:

- Pass: the two-IMU premise remains viable.
- Fail: reconsider sensor topology or board role.

Hardware needed:

- Yes

## Gate 6: Combined One-Leg Feasibility Test

Goal: determine whether one full leg controller is fundamentally feasible on this board.

### Test 6.1: Combined-load endurance test

What to test:

- serial bridge active
- watchdog active
- servo active
- stepper 1 active
- stepper 2 active
- both IMUs active
- telemetry flowing back to host

Pass criteria:

- no unsafe persistence of motion after command loss
- no serial collapse under combined load
- no obvious timing starvation causing unacceptable behavior
- telemetry remains coherent enough for host-side status tracking

Fail criteria:

- safety behavior degrades under combined load
- actuator control becomes unstable under realistic concurrency
- telemetry becomes too unreliable to support supervision

Use of result:

- Pass: one-board-per-leg architecture is fundamentally feasible enough to continue.
- Fail: stop scaling and revisit the board choice, responsibility split, or transport assumptions.

Hardware needed:

- Yes

## Feasibility Decision Rule

Call the concept fundamentally feasible only if all of the following are true on one real board:

- USB serial link is stable enough for command and telemetry
- watchdog safe-stop behavior works reliably
- one servo can run acceptably
- two steppers can run acceptably
- two MPU6050 sensors can be sampled acceptably
- combined-load behavior remains safe and understandable

If any one of those fails badly, treat it as architecture evidence, not as a minor bug to hand-wave away.

## Suggested Result Logging Template

For each gate, capture:

- Date
- Tester
- Hardware present
- Firmware revision or test harness revision
- Host code revision
- Test performed
- Result: PASS / FAIL / BLOCKED
- Evidence type:
  - validated from repo code
  - validated from direct hardware inspection
  - inference or engineering judgment
- Notes
- Next action

## When You Need To Plug Something In

You do not need to plug anything in for:

- Gate 0 host-side tests

You do need hardware for:

- Gate 1 and beyond

Minimum first hardware step:

- one Ender 3 v4.2.2 board
- one USB cable to the host

First actuator step after serial proof:

- add only the servo or one stepper first, not the whole leg at once
