#!/bin/bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
path = Path('/home/faraday/TARS/firmware/marlin_upstream/Marlin/src/gcode/host/M118.cpp')
text = path.read_text()
old = '''  SERIAL_ECHOPGM("TARS_IMU ");
  SERIAL_ECHOPAIR("ax=", sample.ax_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("ay=", sample.ay_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("az=", sample.az_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("gx=", sample.gx_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("gy=", sample.gy_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("gz=", sample.gz_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("roll=", sample.roll_deg); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("pitch=", sample.pitch_deg);
'''
new = '''  SERIAL_ECHOPGM("TARS_IMU ");
  SERIAL_ECHOPGM("ax="); SERIAL_ECHO(sample.ax_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPGM("ay="); SERIAL_ECHO(sample.ay_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPGM("az="); SERIAL_ECHO(sample.az_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPGM("gx="); SERIAL_ECHO(sample.gx_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPGM("gy="); SERIAL_ECHO(sample.gy_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPGM("gz="); SERIAL_ECHO(sample.gz_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPGM("roll="); SERIAL_ECHO(sample.roll_deg); SERIAL_CHAR(' ');
  SERIAL_ECHOPGM("pitch="); SERIAL_ECHO(sample.pitch_deg);
'''
text = text.replace(old, new)
path.write_text(text)
PY
