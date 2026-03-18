#ifndef TARS_PICO_LEG_CONTROLLER_CONTRACT_H
#define TARS_PICO_LEG_CONTROLLER_CONTRACT_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
  PICO_CAL_IDLE = 0,
  PICO_CAL_WAITING_FOR_ENABLE = 1,
  PICO_CAL_HOMING_STEPPER_1 = 2,
  PICO_CAL_HOMING_STEPPER_2 = 3,
  PICO_CAL_VERIFYING = 4,
  PICO_CAL_COMPLETE = 5,
  PICO_CAL_FAULT = 6,
} pico_calibration_state_t;

typedef struct {
  bool enabled;
  bool safe_stop;
  float servo_target_deg;
  float body_velocity_hint;
  float body_turn_rate_hint;
  uint8_t calibration_action;
  uint16_t command_ttl_ms;
} pico_wireless_command_t;

typedef struct {
  bool stepper_1_triggered;
  bool stepper_2_triggered;
} pico_limit_switch_state_t;

typedef struct {
  float accel_g[3];
  float gyro_dps[3];
} pico_imu_sample_t;

typedef struct {
  float quaternion_xyzw[4];
} pico_fused_orientation_t;

typedef struct {
  bool enabled;
  pico_calibration_state_t calibration_state;
  pico_limit_switch_state_t limit_switches;
  uint32_t fault_bits;
  uint32_t last_command_sequence;
  uint32_t last_stepper_sequence;
  float servo_position_deg;
  pico_fused_orientation_t fused_orientation;
} pico_leg_status_t;

#endif
