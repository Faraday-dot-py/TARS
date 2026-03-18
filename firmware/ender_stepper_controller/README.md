# Ender Stepper Controller

## Intent

- Validated from repo code: this firmware is the intended home for dual-stepper execution, watchdog safe-stop, and local status/fault telemetry.
- Validated from repo code: servo, IMU, Madgwick fusion, and limit switch ownership are intentionally excluded from this firmware contract.
- Validated from direct hardware inspection: none.

## Validation Goals

1. `M115` over the LCD header UART returns a recognizable firmware string.
2. `M17` enables the shared stepper driver output.
3. `G91` selects relative mode and `G90` selects absolute mode.
4. `G1 X200 Y200 R100` moves both axes together using raw step targets at an easy-to-see rate and only returns when the move finishes.
5. Compact commands like `S050100E` queue motion without using G-code.
6. `H10E`, `H01E`, and `H11E` home against stock X/Y endstop ports.
7. `Q0E`, `L0E`, and `B0E` return useful board status and pin mapping information.
8. Binary command frames matching `src/ender_stepper_transport` are accepted.
9. A watchdog timeout disables the shared enable line and reports a fault bit.

## Build

```bash
cd firmware/ender_stepper_controller
make
```

This produces:

- `build/tars_ender_stepper_controller.elf`
- `build/tars_ender_stepper_controller.bin`

Ready-to-flash artifact from this repo state:

- `build/tars_ender_stepper_controller_20260318_compact.bin`

## Current ASCII Validation Commands

- `M115`
- `M17`
- `M18`
- `M84`
- `M114`
- `G90`
- `G91`
- `G1 X<steps> Y<steps> R<steps_per_second>`
- `A1E` / `A0E` enable / disable
- `M0E` / `M1E` absolute / relative compact mode
- `R<rate>E` set compact move rate, fixed-width 3 digits
- `S<xxx><yyy>E` queue compact move for X and Y, fixed-width 3 digits each
- `H10E` / `H01E` / `H11E` home X / Y / both using stock endstop ports
- `Q0E` status query
- `L0E` limit switch query
- `B0E` board information query
- `Z10E` / `Z01E` / `Z11E` zero X / Y / both logical positions

Example:

```text
M17
G91
G1 X200 Y200 R100
M114
```

## Bench Validation

Validated from repo code:

- UART runs on the LCD header pins `PB10`/`PB11`.
- X step/dir use `PC2`/`PB9`.
- Y step/dir use `PB8`/`PB7`.
- X/Y endstop inputs use `PA5` / `PA6`.
- Shared enable uses `PC3` and is treated as active-low.

Validated from direct hardware inspection:

- none

Suggested first bench sequence:

1. Flash `build/tars_ender_stepper_controller_20260317.bin`.
2. Keep the LCD unplugged.
3. Wire the Pico bridge to LCD header UART:
   - Pico `GP4` -> Ender LCD pin 4 (`PB11 RX`)
   - Pico `GP5` <- Ender LCD pin 3 (`PB10 TX`)
   - Pico `GND` -> Ender LCD pin 9 (`GND`)
4. Power the Ender board normally and power the Pico from USB.
5. Send:

```text
A1E
Q0E
R120E
S050100E
Q0E
L0E
B0E
H11E
Q0E
A0E
```

Expected behavior:

- `A1E` returns `ok` and enables the shared driver output.
- `Q0E` returns current positions, targets, endstop state, enable/safe-stop/fault bits, rate, and axis states.
- `R120E` returns `ok` and sets the compact move rate to `120` steps per second.
- `S050100E` returns `ok` and queues X=`50`, Y=`100` in the current compact mode.
- `L0E` returns `XL:<0|1> YL:<0|1>`.
- `B0E` returns a board summary including the step, limit, and UART pin mapping.
- `H11E` returns `ok` and starts homing both axes toward the stock limit switches.
- `A0E` returns `ok` and disables the shared driver output.

## Binary Protocol

- Validated from repo code: the binary frame contract is defined by [protocol.py](/home/faraday/TARS/src/ender_stepper_transport/ender_stepper_transport/protocol.py).
- This firmware accepts:
  - heartbeat frames
  - stepper command frames
- This firmware emits:
  - stepper status frames
