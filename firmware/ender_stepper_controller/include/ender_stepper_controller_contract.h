#ifndef TARS_ENDER_STEPPER_CONTROLLER_CONTRACT_H
#define TARS_ENDER_STEPPER_CONTROLLER_CONTRACT_H

#include <stdbool.h>
#include <stdint.h>

typedef enum {
  ENDER_STEPPER_DISABLED = 0,
  ENDER_STEPPER_POSITION = 1,
  ENDER_STEPPER_HOLD = 2,
  ENDER_STEPPER_HOME_TO_LIMIT = 3,
} ender_stepper_mode_t;

typedef struct {
  ender_stepper_mode_t mode;
  int8_t homing_direction;
  int32_t target_steps;
  uint32_t max_step_rate_hz;
} ender_stepper_axis_command_t;

typedef struct {
  bool enabled;
  bool safe_stop;
  uint16_t watchdog_timeout_ms;
  ender_stepper_axis_command_t axis_1;
  ender_stepper_axis_command_t axis_2;
} ender_stepper_command_t;

typedef struct {
  bool enabled;
  bool safe_stop;
  uint8_t axis_1_state;
  uint8_t axis_2_state;
  uint32_t fault_bits;
  uint32_t applied_sequence;
  int32_t axis_1_position_steps;
  int32_t axis_2_position_steps;
} ender_stepper_status_t;

#endif
