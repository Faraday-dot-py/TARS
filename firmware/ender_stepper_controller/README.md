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
5. Binary command frames matching `src/ender_stepper_transport` are accepted.
6. A watchdog timeout disables the shared enable line and reports a fault bit.

## Build

```bash
cd firmware/ender_stepper_controller
make
```

This produces:

- `build/tars_ender_stepper_controller.elf`
- `build/tars_ender_stepper_controller.bin`

Ready-to-flash artifact from this repo state:

- `build/tars_ender_stepper_controller_20260317.bin`

## Current ASCII Validation Commands

- `M115`
- `M17`
- `M18`
- `M84`
- `M114`
- `G90`
- `G91`
- `G1 X<steps> Y<steps> R<steps_per_second>`

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
M115
M17
G91
G1 X200 Y200 R100
M114
M18
```

Expected behavior:

- `M115` returns a `TARS Ender Stepper Controller` firmware string.
- `M17` returns `ok` and enables the shared driver output.
- `G91` returns `ok`.
- `G1 X200 Y200 R100` returns `ok` only after the move finishes and both axes should step together if motors are attached.
- `M114` returns current and target raw step positions for `X` and `Y`.
- `M18` returns `ok` and disables the shared driver output.

## Binary Protocol

- Validated from repo code: the binary frame contract is defined by [protocol.py](/home/faraday/TARS/src/ender_stepper_transport/ender_stepper_transport/protocol.py).
- This firmware accepts:
  - heartbeat frames
  - stepper command frames
- This firmware emits:
  - stepper status frames
