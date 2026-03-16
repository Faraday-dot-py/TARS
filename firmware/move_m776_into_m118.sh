#!/bin/bash
set -euo pipefail
python3 - <<'PY'
from pathlib import Path
path = Path('/home/faraday/TARS/firmware/marlin_upstream/Marlin/src/gcode/host/M118.cpp')
text = path.read_text()
if '#include <Arduino.h>' not in text:
    text = text.replace('#include "../../core/serial.h"\n', '#include "../../core/serial.h"\n#include <Arduino.h>\n#include <math.h>\n')
marker = 'void GcodeSuite::M118() {'
if 'void GcodeSuite::M776() {' not in text:
    text += '''

namespace {

constexpr uint8_t TARS_IMU_SDA_PIN = PB0;
constexpr uint8_t TARS_IMU_SCL_PIN = PB1;
constexpr uint8_t TARS_IMU_ADDRESS = 0x68;
constexpr uint8_t TARS_IMU_REG_PWR_MGMT_1 = 0x6B;
constexpr uint8_t TARS_IMU_REG_WHO_AM_I = 0x75;
constexpr uint8_t TARS_IMU_REG_ACCEL_XOUT_H = 0x3B;

bool g_tars_imu_initialized = false;

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

void tars_line_release(const uint8_t pin) {
  pinMode(pin, INPUT);
}

void tars_line_low(const uint8_t pin) {
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
}

void tars_i2c_delay() {
  delayMicroseconds(5);
}

void tars_sda_release() { tars_line_release(TARS_IMU_SDA_PIN); }
void tars_sda_low() { tars_line_low(TARS_IMU_SDA_PIN); }
void tars_scl_release() { tars_line_release(TARS_IMU_SCL_PIN); }
void tars_scl_low() { tars_line_low(TARS_IMU_SCL_PIN); }

void tars_i2c_start() {
  tars_sda_release();
  tars_scl_release();
  tars_i2c_delay();
  tars_sda_low();
  tars_i2c_delay();
  tars_scl_low();
}

void tars_i2c_stop() {
  tars_sda_low();
  tars_i2c_delay();
  tars_scl_release();
  tars_i2c_delay();
  tars_sda_release();
  tars_i2c_delay();
}

bool tars_i2c_write_byte(const uint8_t value) {
  for (uint8_t bit = 0; bit < 8; ++bit) {
    if (value & (0x80u >> bit)) tars_sda_release();
    else tars_sda_low();
    tars_i2c_delay();
    tars_scl_release();
    tars_i2c_delay();
    tars_scl_low();
  }

  tars_sda_release();
  tars_i2c_delay();
  tars_scl_release();
  tars_i2c_delay();
  const bool ack = (digitalRead(TARS_IMU_SDA_PIN) == LOW);
  tars_scl_low();
  return ack;
}

uint8_t tars_i2c_read_byte(const bool ack) {
  uint8_t value = 0;
  tars_sda_release();
  for (uint8_t bit = 0; bit < 8; ++bit) {
    value <<= 1;
    tars_scl_release();
    tars_i2c_delay();
    if (digitalRead(TARS_IMU_SDA_PIN)) value |= 0x01u;
    tars_scl_low();
    tars_i2c_delay();
  }

  if (ack) tars_sda_low();
  else tars_sda_release();
  tars_i2c_delay();
  tars_scl_release();
  tars_i2c_delay();
  tars_scl_low();
  tars_sda_release();
  return value;
}

bool tars_imu_write_register(const uint8_t reg, const uint8_t value) {
  tars_i2c_start();
  if (!tars_i2c_write_byte(uint8_t(TARS_IMU_ADDRESS << 1))) { tars_i2c_stop(); return false; }
  if (!tars_i2c_write_byte(reg)) { tars_i2c_stop(); return false; }
  if (!tars_i2c_write_byte(value)) { tars_i2c_stop(); return false; }
  tars_i2c_stop();
  return true;
}

bool tars_imu_read_registers(const uint8_t reg, uint8_t *buffer, const uint8_t length) {
  tars_i2c_start();
  if (!tars_i2c_write_byte(uint8_t(TARS_IMU_ADDRESS << 1))) { tars_i2c_stop(); return false; }
  if (!tars_i2c_write_byte(reg)) { tars_i2c_stop(); return false; }
  tars_i2c_start();
  if (!tars_i2c_write_byte(uint8_t((TARS_IMU_ADDRESS << 1) | 0x01u))) { tars_i2c_stop(); return false; }
  for (uint8_t i = 0; i < length; ++i)
    buffer[i] = tars_i2c_read_byte(i + 1 < length);
  tars_i2c_stop();
  return true;
}

int16_t tars_be16(const uint8_t *data) {
  return int16_t((uint16_t(data[0]) << 8) | uint16_t(data[1]));
}

bool tars_imu_init() {
  if (g_tars_imu_initialized) return true;

  tars_sda_release();
  tars_scl_release();
  delay(10);

  if (!tars_imu_write_register(TARS_IMU_REG_PWR_MGMT_1, 0x00u))
    return false;

  delay(100);

  uint8_t who_am_i = 0;
  if (!tars_imu_read_registers(TARS_IMU_REG_WHO_AM_I, &who_am_i, 1))
    return false;

  if ((who_am_i & 0x7Eu) != 0x68u)
    return false;

  g_tars_imu_initialized = true;
  return true;
}

bool tars_imu_read_sample(TarsImuSample &sample) {
  if (!tars_imu_init()) return false;

  uint8_t raw[14] = {0};
  if (!tars_imu_read_registers(TARS_IMU_REG_ACCEL_XOUT_H, raw, sizeof(raw)))
    return false;

  const int16_t ax_raw = tars_be16(raw + 0);
  const int16_t ay_raw = tars_be16(raw + 2);
  const int16_t az_raw = tars_be16(raw + 4);
  const int16_t gx_raw = tars_be16(raw + 8);
  const int16_t gy_raw = tars_be16(raw + 10);
  const int16_t gz_raw = tars_be16(raw + 12);

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

} // namespace

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
'''
path.write_text(text)
PY
