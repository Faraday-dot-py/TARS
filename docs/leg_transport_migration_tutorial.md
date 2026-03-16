# TARS Leg Transport Migration Tutorial

## 1. Current Repo Reality

### Validated from repo code

- The Jetson-side ROS 2 stack is present in `src/robot_controller`, `src/motion`, `src/leg_control`, `src/state_estimation`, `src/b0_interface`, and `src/bringup`.
- `robot_controller` currently manages only operation mode and enabled state publication.
- `motion_planner` gates velocity and turn-rate goals based on enable state and operation mode.
- `motion_executor` is incomplete. It now fans out shared motion goals to per-leg topics, but it does not yet implement real gait generation or actuator target synthesis.
- `leg_control` now defines a transport-agnostic host-side `LegCommand` boundary and publishes semantic per-leg commands on `leg/command`.
- `rpi_bridge` is Pi-specific and tied to a hard-coded UDP/JSON path for one leg.
- `rpi/main.py` contains the most concrete legacy leg-endpoint behavior in the repo: component setup, watchdog timeout handling, command ingestion, and telemetry transmission.
- `state_estimation` is currently placeholder-level.
- `bringup` starts the high-level stack and one namespaced `leg_controller` per leg. It now also supports an optional one-leg serial bridge.

### Why the old Pi path is reference behavior, not final architecture

`rpi/main.py` contains behavior that is still useful:

- command timeout watchdog
- safe disable behavior
- actuator goal application
- telemetry packaging cadence

But it also bakes in assumptions that should not define the new architecture:

- Raspberry Pi specific runtime and component imports
- hard-coded UDP/IP transport
- JSON payloads over the control link
- hostname-based leg identity
- direct coupling between transport and device behavior

Use it as behavioral reference, not as the new interface contract.

## 2. Target Control Boundary

### Jetson side

The Jetson should remain responsible for:

- ROS 2 graph ownership
- robot-level enable and safety state
- planning, coordination, and gait logic
- per-leg command generation
- transport bridge nodes
- ROS telemetry republishing

### Ender board side

The per-leg embedded board should eventually own:

- step generation for 2 steppers
- servo pulse generation for 1 ANNIMOS servo
- IMU sampling for 2 MPU6050 devices
- optional sensor fusion
- watchdog enforcement
- fault detection and safe-stop behavior
- telemetry framing back to the Jetson

### Why this split is a good fit

- Timing-sensitive motor pulse generation belongs close to the hardware.
- ROS 2 coordination, planning, and debugging are easier to keep on the Jetson.
- The host can remain transport-agnostic while the embedded side stays hardware-focused.
- Debugging one leg over USB serial is simpler than debugging four wireless links at once.

## 3. Transport-Agnostic Refactor

### Validated from repo code

The new host-side boundary is now split like this:

- `leg_control` owns leg command semantics through `leg_control/leg_command.py`.
- `leg_transport` owns framing, serial device I/O, watchdog signaling, and telemetry decoding.

### Recommended structure

- `src/leg_control/leg_control/leg_command.py`
- `src/leg_control/leg_control/leg_controller_node.py`
- `src/leg_transport/leg_transport/protocol.py`
- `src/leg_transport/leg_transport/serial_transport.py`
- `src/leg_transport/leg_transport/serial_leg_bridge_node.py`

### Why this matters

- Transport can change later without rewriting host-side leg semantics.
- Pi assumptions are no longer baked into the leg boundary.
- The firmware contract is defined in one place instead of being inferred from UDP JSON blobs.

## 4. Serial Protocol Design

### Why direct USB serial is the preferred first transport

- It is simpler to inspect and debug during one-leg bring-up.
- It avoids making wireless reliability a foundational dependency.
- It matches the immediate need: Jetson to one smart leg controller.

### Why wireless should stay optional

- Wireless adds failure modes before the actuator and sensor contract is stable.
- One-leg validation is easier with a cable and deterministic enumeration.
- The repo does not currently validate a robust wireless transport contract.

### Framing now scaffolded on the host side

`leg_transport/protocol.py` defines a compact binary frame with:

- start-of-frame marker
- protocol version
- message type
- sequence number
- payload length
- payload
- CRC16-CCITT-FALSE

### Message families scaffolded

- `SET_COMMAND`
- `SET_ENABLE`
- `SET_CONFIG`
- `PING`
- `TELEMETRY`
- `FAULT`
- `ACK`
- `HEARTBEAT`
- `SAFE_STOP`

### What crosses the Jetson-to-leg link

Currently scaffolded on the host side:

- enable or disable state
- safe-stop reason signaling
- sequence numbers
- host timestamps
- optional stepper 1 target
- optional stepper 2 target
- optional servo target

### What comes back from the board

Currently scaffolded in the telemetry payload model:

- board state
- fault bits
- watchdog state
- applied command sequence
- board timestamp
- actuator state placeholders
- IMU sample placeholders

### Why watchdog behavior influences protocol design

The embedded controller must be able to transition to a safe state if host commands stop arriving. That is why the host bridge now distinguishes:

- normal heartbeat traffic
- explicit disable commands
- explicit safe-stop frames
- stale-command watchdog behavior

## 5. One-Leg Bring-Up Plan

### Recommended order

1. Verify one real Ender 3 v4.2.2 board revision by physical inspection.
2. Confirm MCU, stepper driver arrangement, timer availability, servo-capable pin choice, and I2C access for two MPU6050 devices.
3. Keep the host-side binary protocol fixed while firmware is still simple.
4. Bring up one `serial_leg_bridge` instance over direct USB serial.
5. Validate enable, disable, and watchdog-triggered safe-stop behavior first.
6. Add servo output.
7. Add the first stepper path.
8. Add the second stepper path.
9. Add the first MPU6050.
10. Add the second MPU6050.
11. Add optional fusion only after raw telemetry is trusted.
12. Republish stable telemetry into ROS topics with clear fault semantics.

### Inference or engineering judgment

The current host code does not yet contain real stepper or servo targets from planning. That is the right time to stop and validate one board before inventing final actuator semantics.

## 6. Risks and Unknowns

### Validated from repo code

- The legacy Pi endpoint contains a real watchdog concept worth preserving.
- The current motion executor is incomplete and should not be treated as a stable API.
- The previous Pi bridge was tightly coupled to UDP JSON and one-leg assumptions.

### Likely but unverified hardware assumptions

- The Ender 3 v4.2.2 board may be suitable as a per-leg controller.
- The board may have enough timers and accessible pins for two steppers, one servo, and two IMUs.
- USB serial may be reliable enough for one-leg bring-up under expected update rates.

These are not validated from direct hardware inspection in this repo session.

### Engineering judgment

- Board revision variance can affect MCU details and pin availability.
- Timer allocation for steppers and servo output may become the real constraint.
- Power noise and grounding may complicate IMU quality and servo behavior.
- USB device naming should not be trusted without udev or equivalent bring-up discipline.
- Safe defaults should always prefer disable or safe-stop over holding stale commands.
