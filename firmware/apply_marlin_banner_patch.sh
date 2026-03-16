#!/bin/bash
set -euo pipefail
cd /home/faraday/TARS/firmware/marlin_upstream
cp "/home/faraday/TARS/firmware/marlin_configurations/config/examples/Creality/Ender-3 V2/CrealityV422/MarlinUI/Configuration.h" Marlin/Configuration.h
cp "/home/faraday/TARS/firmware/marlin_configurations/config/examples/Creality/Ender-3 V2/CrealityV422/MarlinUI/Configuration_adv.h" Marlin/Configuration_adv.h
sed -i 's/#define STRING_CONFIG_H_AUTHOR.*/#define STRING_CONFIG_H_AUTHOR "(TARS, banner bringup)" \/\/ Who made the changes./' Marlin/Configuration.h
sed -i 's/#define CUSTOM_MACHINE_NAME .*/#define CUSTOM_MACHINE_NAME "TARS Banner Bringup"/' Marlin/Configuration.h
sed -i '/SERIAL_ECHOLNPGM("start");/a\  SERIAL_ECHOLNPGM("TARS_MARLIN_BANNER GD32F303RET6");' Marlin/src/MarlinCore.cpp
