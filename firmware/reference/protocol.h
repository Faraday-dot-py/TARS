#ifndef TARS_LEG_PROTOCOL_H
#define TARS_LEG_PROTOCOL_H

#include <stdint.h>

#define TARS_LEG_SOF 0xA5
#define TARS_LEG_PROTOCOL_VERSION 1

#define TARS_MSG_SET_COMMAND 1
#define TARS_MSG_SET_ENABLE 2
#define TARS_MSG_SET_CONFIG 3
#define TARS_MSG_PING 4
#define TARS_MSG_TELEMETRY 5
#define TARS_MSG_FAULT 6
#define TARS_MSG_ACK 7
#define TARS_MSG_HEARTBEAT 8
#define TARS_MSG_SAFE_STOP 9

#define TARS_CMD_FLAG_STEPPER_1 (1u << 0)
#define TARS_CMD_FLAG_STEPPER_2 (1u << 1)
#define TARS_CMD_FLAG_SERVO     (1u << 2)

#define TARS_SAFE_STOP_DISABLED 1
#define TARS_SAFE_STOP_WATCHDOG 2
#define TARS_SAFE_STOP_FAULT    3

#pragma pack(push, 1)
typedef struct {
    uint8_t sof;
    uint8_t version;
    uint8_t message_type;
    uint8_t sequence;
    uint16_t payload_length;
} tars_leg_frame_header_t;

typedef struct {
    uint8_t enabled;
} tars_leg_set_enable_payload_t;

typedef struct {
    uint8_t reason_code;
} tars_leg_safe_stop_payload_t;

typedef struct {
    uint32_t host_time_ms;
} tars_leg_heartbeat_payload_t;

typedef struct {
    uint8_t command_flags;
    uint32_t host_time_ms;
    float stepper_1_target;
    float stepper_2_target;
    float servo_target;
} tars_leg_set_command_payload_t;

typedef struct {
    uint8_t board_state;
    uint8_t fault_bits;
    uint8_t watchdog_state;
    uint8_t applied_sequence;
    uint32_t board_time_ms;
    float stepper_1_position;
    float stepper_2_position;
    float servo_position;
    float imu_1_ax;
    float imu_1_ay;
    float imu_1_az;
    float imu_2_ax;
    float imu_2_ay;
    float imu_2_az;
} tars_leg_telemetry_payload_t;
#pragma pack(pop)

#endif
