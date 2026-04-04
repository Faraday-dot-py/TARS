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
8. `T0E` / `T1E` disable / enable the periodic ASCII UART telemetry stream.
9. Binary command frames matching `src/ender_stepper_transport` are accepted.
10. A watchdog timeout disables the shared enable line and reports a fault bit.

## Firmware Toolchain

Validated from repo code:

- This firmware is a bare-metal Cortex-M3 build, not PlatformIO, not STM32Cube, and not Marlin.
- The build is driven by [`Makefile`](/home/faraday/TARS/firmware/ender_stepper_controller/Makefile).
- The compiler toolchain is `arm-none-eabi-gcc` plus `arm-none-eabi-objcopy` and `arm-none-eabi-size`.
- The link step uses [`linker.ld`](/home/faraday/TARS/firmware/ender_stepper_controller/linker.ld).
- Reset and vector-table setup live in [`startup.c`](/home/faraday/TARS/firmware/ender_stepper_controller/src/startup.c).
- Application logic lives in [`main.c`](/home/faraday/TARS/firmware/ender_stepper_controller/src/main.c).

Build flow:

1. `make` compiles `src/startup.c` and `src/main.c` into `build/*.o`.
2. The objects are linked into `build/tars_ender_stepper_controller.elf`.
3. `arm-none-eabi-objcopy` converts that ELF into `build/tars_ender_stepper_controller.bin`.
4. The build is archived into `artifacts/<build_id>/`.
5. The same `.bin` is copied to a short flash-ready alias `FW<short_id>.bin` for Creality SD flashing.
6. `SHA256SUMS.txt` is generated for the archived outputs.

Build metadata:

- `BUILD_ID` defaults to the current timestamp in `YYYYMMDD_HHMMSS` form.
- That `BUILD_ID` is compiled into the firmware as `TARS_BUILD_ID`.
- The firmware prints that build ID in the startup banner and board-info response.

Important targets:

- `make` builds the current/default firmware path.
- `make legacy BUILD_ID=<id>` rebuilds with the legacy timing flags:
  - `-DTARS_USE_TIM2_MICROS=0`
  - `-DTARS_STEP_PULSE_NOP_COUNT=1024`

Practical push guidance:

- Source of truth to commit is the firmware source and build files:
  - [`Makefile`](/home/faraday/TARS/firmware/ender_stepper_controller/Makefile)
  - [`linker.ld`](/home/faraday/TARS/firmware/ender_stepper_controller/linker.ld)
  - [`startup.c`](/home/faraday/TARS/firmware/ender_stepper_controller/src/startup.c)
  - [`main.c`](/home/faraday/TARS/firmware/ender_stepper_controller/src/main.c)
  - [`ender_stepper_controller_contract.h`](/home/faraday/TARS/firmware/ender_stepper_controller/include/ender_stepper_controller_contract.h)
- `build/` is transient.
- `artifacts/` preserves flash history; keep or ignore it based on how you want to manage release binaries in the firmware repo.

```bash
cd firmware/ender_stepper_controller
make
```

This produces:

- `build/tars_ender_stepper_controller.elf`
- `build/tars_ender_stepper_controller.bin`
- `artifacts/<build_id>/tars_ender_stepper_controller_<build_id>.elf`
- `artifacts/<build_id>/tars_ender_stepper_controller_<build_id>.bin`
- `artifacts/<build_id>/FW<short_id>.bin`
- `artifacts/<build_id>/SHA256SUMS.txt`

Each `make` run now:

- injects a unique build ID into the startup banner and board info
- archives the build into a new `artifacts/<build_id>/` folder so older builds are preserved
- creates a short flash-ready filename `FW<short_id>.bin` for Creality SD flashing

Most recent archived flash artifact in this repo worktree:

- [`FWtelemetry.bin`](/home/faraday/TARS/firmware/ender_stepper_controller/artifacts/20260324_telemetry_toggle/FWtelemetry.bin)

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
- `R<rate>E` set compact move rate with variable-length digits, e.g. `R5000E`
- `S<x>,<y>E` queue compact move for X and Y using a separator-based frame
- `H10E` / `H01E` / `H11E` home X / Y / both using stock endstop ports
- `Q0E` status query
- `L0E` limit switch query
- `B0E` board information query
- `T0E` / `T1E` disable / enable periodic ASCII telemetry
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

1. Flash the short archived image for the build you want to test, for example [`FWtelemetry.bin`](/home/faraday/TARS/firmware/ender_stepper_controller/artifacts/20260324_telemetry_toggle/FWtelemetry.bin).
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
S50,100E
Q0E
L0E
B0E
T0E
T1E
H11E
Q0E
A0E
```

Expected behavior:

- `A1E` returns `ok` and enables the shared driver output.
- `Q0E` returns current positions, targets, endstop state, enable/safe-stop/fault bits, rate, and axis states.
- `R120E` returns `ok` and sets the compact move rate to `120` steps per second.
- changing `R...E` while an axis is already in `POSITION` mode updates that active move immediately
- `S50,100E` returns `ok` and queues X=`50`, Y=`100` in the current compact mode.
- `L0E` returns `XL:<0|1> YL:<0|1>`.
- `B0E` returns a board summary including the step, limit, and UART pin mapping.
- `T0E` returns `ok` and stops the periodic `T,...` carriage telemetry stream.
- `T1E` returns `ok` and resumes the periodic `T,...` carriage telemetry stream.
- `H11E` returns `ok` and starts homing both axes toward the stock limit switches.
- `A0E` returns `ok` and disables the shared driver output.

Continuous telemetry:

- The Ender now streams a carriage telemetry line roughly every `50 ms` over UART when not in binary-protocol mode.
- Send `T0E` to stop this stream and `T1E` to turn it back on.
- Format:

```text
T,<x_pos>,<x_target>,<y_pos>,<y_target>,<enabled>,<safe_stop>,<fault_bits>,<x_limit>,<y_limit>,<rate_hz>,<mode>,<x_state>,<y_state>
```

## Binary Protocol

- Validated from repo code: the binary frame contract is defined by [protocol.py](/home/faraday/TARS/src/ender_stepper_transport/ender_stepper_transport/protocol.py).
- This firmware accepts:
  - heartbeat frames
  - stepper command frames
- This firmware emits:
  - stepper status frames
