#!/bin/bash
set -euo pipefail
cd /home/faraday/TARS/firmware/marlin_upstream
latest_bin=$(ls -1t .pio/build/STM32F103RE_creality/*.bin | sed -n '1p')
cp "$latest_bin" /home/faraday/TARS/firmware/ender_v4_2_2/build/tars_marlin_imu_20260314.bin
strings .pio/build/STM32F103RE_creality/firmware.elf | grep 'TARS_MARLIN_IMU_READY PB0_PB1'
strings .pio/build/STM32F103RE_creality/firmware.elf | grep 'TARS_IMU '
ls -l /home/faraday/TARS/firmware/ender_v4_2_2/build/tars_marlin_imu_20260314.bin
