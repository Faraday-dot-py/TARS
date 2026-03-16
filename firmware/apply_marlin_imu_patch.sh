#!/bin/bash
set -euo pipefail
cd /home/faraday/TARS/firmware/marlin_upstream

cat > Marlin/src/feature/tars_mpu6050.h <<'EOF'
#pragma once

#include "../inc/MarlinConfig.h"

struct TarsImuSample {
  float ax_g;
  float ay_g;
  float az_g;
  float gx_dps;
  float gy_dps;
  float gz_dps;
  float roll_deg;
  float pitch_deg;
};

bool tars_imu_read_sample(TarsImuSample &sample);
EOF

cat > Marlin/src/feature/tars_mpu6050.cpp <<'EOF'
#include "../inc/MarlinConfig.h"
#include "tars_mpu6050.h"

#include <Arduino.h>
#include <math.h>

namespace {

constexpr uint8_t IMU_SDA_PIN = PB0;
constexpr uint8_t IMU_SCL_PIN = PB1;
constexpr uint8_t IMU_ADDRESS = 0x68;
constexpr uint8_t IMU_REG_PWR_MGMT_1 = 0x6B;
constexpr uint8_t IMU_REG_WHO_AM_I = 0x75;
constexpr uint8_t IMU_REG_ACCEL_XOUT_H = 0x3B;

bool g_imu_initialized = false;

void line_release(const uint8_t pin) {
  pinMode(pin, INPUT);
}

void line_low(const uint8_t pin) {
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
}

void i2c_delay() {
  delayMicroseconds(5);
}

void sda_release() { line_release(IMU_SDA_PIN); }
void sda_low() { line_low(IMU_SDA_PIN); }
void scl_release() { line_release(IMU_SCL_PIN); }
void scl_low() { line_low(IMU_SCL_PIN); }

void i2c_start() {
  sda_release();
  scl_release();
  i2c_delay();
  sda_low();
  i2c_delay();
  scl_low();
}

void i2c_stop() {
  sda_low();
  i2c_delay();
  scl_release();
  i2c_delay();
  sda_release();
  i2c_delay();
}

bool i2c_write_byte(const uint8_t value) {
  for (uint8_t bit = 0; bit < 8; ++bit) {
    if (value & (0x80u >> bit)) sda_release();
    else sda_low();
    i2c_delay();
    scl_release();
    i2c_delay();
    scl_low();
  }

  sda_release();
  i2c_delay();
  scl_release();
  i2c_delay();
  const bool ack = (digitalRead(IMU_SDA_PIN) == LOW);
  scl_low();
  return ack;
}

uint8_t i2c_read_byte(const bool ack) {
  uint8_t value = 0;
  sda_release();

  for (uint8_t bit = 0; bit < 8; ++bit) {
    value <<= 1;
    scl_release();
    i2c_delay();
    if (digitalRead(IMU_SDA_PIN)) value |= 0x01u;
    scl_low();
    i2c_delay();
  }

  if (ack) sda_low();
  else sda_release();
  i2c_delay();
  scl_release();
  i2c_delay();
  scl_low();
  sda_release();
  return value;
}

bool imu_write_register(const uint8_t reg, const uint8_t value) {
  i2c_start();
  if (!i2c_write_byte(uint8_t(IMU_ADDRESS << 1))) { i2c_stop(); return false; }
  if (!i2c_write_byte(reg)) { i2c_stop(); return false; }
  if (!i2c_write_byte(value)) { i2c_stop(); return false; }
  i2c_stop();
  return true;
}

bool imu_read_registers(const uint8_t reg, uint8_t *buffer, const uint8_t length) {
  i2c_start();
  if (!i2c_write_byte(uint8_t(IMU_ADDRESS << 1))) { i2c_stop(); return false; }
  if (!i2c_write_byte(reg)) { i2c_stop(); return false; }
  i2c_start();
  if (!i2c_write_byte(uint8_t((IMU_ADDRESS << 1) | 0x01u))) { i2c_stop(); return false; }
  for (uint8_t i = 0; i < length; ++i)
    buffer[i] = i2c_read_byte(i + 1 < length);
  i2c_stop();
  return true;
}

int16_t be16(const uint8_t *data) {
  return int16_t((uint16_t(data[0]) << 8) | uint16_t(data[1]));
}

bool imu_init() {
  if (g_imu_initialized) return true;

  sda_release();
  scl_release();
  delay(10);

  if (!imu_write_register(IMU_REG_PWR_MGMT_1, 0x00u))
    return false;

  delay(100);

  uint8_t who_am_i = 0;
  if (!imu_read_registers(IMU_REG_WHO_AM_I, &who_am_i, 1))
    return false;

  if ((who_am_i & 0x7Eu) != 0x68u)
    return false;

  g_imu_initialized = true;
  return true;
}

} // namespace

bool tars_imu_read_sample(TarsImuSample &sample) {
  if (!imu_init()) return false;

  uint8_t raw[14] = {0};
  if (!imu_read_registers(IMU_REG_ACCEL_XOUT_H, raw, sizeof(raw)))
    return false;

  const int16_t ax_raw = be16(raw + 0);
  const int16_t ay_raw = be16(raw + 2);
  const int16_t az_raw = be16(raw + 4);
  const int16_t gx_raw = be16(raw + 8);
  const int16_t gy_raw = be16(raw + 10);
  const int16_t gz_raw = be16(raw + 12);

  sample.ax_g = float(ax_raw) / 16384.0f;
  sample.ay_g = float(ay_raw) / 16384.0f;
  sample.az_g = float(az_raw) / 16384.0f;
  sample.gx_dps = float(gx_raw) / 131.0f;
  sample.gy_dps = float(gy_raw) / 131.0f;
  sample.gz_dps = float(gz_raw) / 131.0f;
  sample.roll_deg = atan2f(sample.ay_g, sample.az_g) * 57.2957795f;
  sample.pitch_deg = atan2f(-sample.ax_g, sqrtf(sample.ay_g * sample.ay_g + sample.az_g * sample.az_g)) * 57.2957795f;
  return true;
}
EOF

cat > Marlin/src/gcode/control/M776.cpp <<'EOF'
#include "../../inc/MarlinConfig.h"

#include "../gcode.h"
#include "../../feature/tars_mpu6050.h"

void GcodeSuite::M776() {
  TarsImuSample sample;
  if (!tars_imu_read_sample(sample)) {
    SERIAL_ECHOLNPGM("TARS_IMU_ERROR");
    return;
  }

  SERIAL_ECHOPGM("TARS_IMU ");
  SERIAL_ECHOPAIR("ax=", sample.ax_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("ay=", sample.ay_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("az=", sample.az_g); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("gx=", sample.gx_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("gy=", sample.gy_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("gz=", sample.gz_dps); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("roll=", sample.roll_deg); SERIAL_CHAR(' ');
  SERIAL_ECHOPAIR("pitch=", sample.pitch_deg);
  SERIAL_EOL();
}
EOF

python3 - <<'PY'
from pathlib import Path

root = Path('/home/faraday/TARS/firmware/marlin_upstream/Marlin/src/gcode')
gcode_h = root / 'gcode.h'
text = gcode_h.read_text()
needle = "      static void M282();\n    #endif\n  #endif\n"
replacement = "      static void M282();\n    #endif\n  #endif\n\n  static void M776();\n"
if 'static void M776();' not in text:
    text = text.replace(needle, replacement)
gcode_h.write_text(text)

gcode_cpp = root / 'gcode.cpp'
text = gcode_cpp.read_text()
needle = "      #if HAS_SOUND\n        case 300: M300(); break;                                  // M300: Play beep tone\n      #endif\n"
replacement = "      case 776: M776(); break;                                  // M776: Sample custom TARS MPU6050\n\n      #if HAS_SOUND\n        case 300: M300(); break;                                  // M300: Play beep tone\n      #endif\n"
if 'case 776: M776(); break;' not in text:
    text = text.replace(needle, replacement)
gcode_cpp.write_text(text)
PY
