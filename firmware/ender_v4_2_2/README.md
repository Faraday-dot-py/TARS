# Ender 3 v4.2.2 Firmware Project Scaffold

This directory now has two distinct purposes:

- preserve the current host-facing protocol and bring-up notes inside this repo
- define a Marlin-oriented firmware integration path for the connected `GD32F303RET6` Creality `4.2.2` board

## Why this pivot exists

Validated from direct hardware behavior:

- stock Creality firmware flashes successfully on the connected board
- the bootloader launches applications from `0x08007000`
- stock firmware emits serial output on the CH340 path at `115200`

Validated from repo code:

- the host-side transport and protocol scaffolding exist in this repo
- the earlier bare-metal images were useful for proving flash acceptance, but they have not yet proven runtime console control

Engineering judgment:

- the next custom-firmware attempts should follow the same class of build/runtime assumptions as Marlin rather than continuing as a hand-rolled bare-metal image
- the first custom milestone remains intentionally small: print a deterministic serial banner on the known-good console path

## Current subpaths

- `embedded/`: earlier bare-metal bring-up experiments kept as reference only
- `include/` and `src/`: host-facing protocol/state-machine scaffold for later embedded integration
- `marlin_overlay/`: repo-local files intended to be layered onto a checked-out Marlin tree
- `docs/hardware_task_plan.md`: ordered real-world task plan

## Marlin-oriented approach

The intended flow is:

1. obtain a matching Marlin source tree separately
2. layer the files in `marlin_overlay/` onto that tree
3. build the Creality GD32 `4.2.2` target with PlatformIO / Auto Build Marlin
4. flash the produced firmware image using the same SD-card workflow that already works with stock firmware
5. observe only the banner milestone first, then move to Servo, IMU, and Stepper in order

## Evidence status

Validated from direct hardware inspection:

- MCU: `GD32F303RET6`
- bootloader accepts SD-card firmware updates
- stock serial console exists at `115200`

Not yet validated from hardware:

- exact Marlin environment string that boots cleanly on this exact board revision
- exact custom serial banner path inside a successful custom image
- actuator and sensor pin mappings for the intended leg-control hardware

## Important constraint

This scaffold does not claim the connected board already runs custom TARS firmware.
It makes the next implementation step more realistic and reviewable by aligning the build strategy with how Creality/Marlin-class firmware is normally produced for this board family.
