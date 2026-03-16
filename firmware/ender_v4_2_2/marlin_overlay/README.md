# Marlin Overlay for Creality 4.2.2 GD32 Bring-Up

This folder is a repo-local overlay, not a full Marlin checkout.
It exists so TARS can track the board-specific customizations we want without vendoring a large upstream firmware tree into this repository yet.

## Intended usage

1. Obtain a Marlin source tree that matches the chosen configuration set.
2. Copy or merge the snippets from this overlay into that Marlin tree.
3. Build the `Creality 4.2.2 / GD32` target.
4. Flash the resulting `.bin` using the same SD-card workflow that has already been validated with stock firmware.

## First milestone

Do not jump straight to actuators.
The first custom milestone is only:

- boot a custom image
- emit a deterministic serial banner on the stock console path

## Overlay contents

- `platformio.ini.snippet`: target environment guidance
- `config/Configuration.h.banner_snippet`: minimal config intent for a serial-banner bring-up
- `config/Configuration_adv.h.banner_snippet`: additional serial/boot notes
- `patches/banner_hook_example.cpp`: example of the kind of runtime hook we want to add once the exact Marlin integration point is chosen

## Evidence discipline

Validated from repo code:

- this overlay is only a planning and implementation scaffold

Inference / engineering judgment:

- the exact Marlin files and hooks will depend on the chosen upstream version and board environment
- this overlay should be treated as a minimal, reviewable starting point rather than a drop-in finished firmware
