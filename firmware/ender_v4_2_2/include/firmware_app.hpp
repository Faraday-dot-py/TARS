#ifndef TARS_FIRMWARE_APP_HPP
#define TARS_FIRMWARE_APP_HPP

#include <stddef.h>
#include <stdint.h>

#include "tars_leg_protocol.h"

enum class BoardState : uint8_t {
    Boot = 0,
    Disabled = 1,
    Enabled = 2,
    SafeStop = 3,
    Fault = 4,
};

enum class WatchdogState : uint8_t {
    Idle = 0,
    Armed = 1,
    Tripped = 2,
};

struct MotionOutputs {
    float stepper_1_target = 0.0f;
    float stepper_2_target = 0.0f;
    float servo_target = 0.0f;
};

struct LedBlinkConfig {
    bool enabled = false;
    uint32_t rate_khz = 0;
};

struct ImuSample {
    float ax = 0.0f;
    float ay = 0.0f;
    float az = 0.0f;
};

struct FirmwareStatus {
    BoardState board_state = BoardState::Boot;
    WatchdogState watchdog_state = WatchdogState::Idle;
    uint8_t fault_bits = 0;
    uint8_t applied_sequence = 0;
    uint32_t last_host_time_ms = 0;
    uint32_t last_command_rx_ms = 0;
    uint8_t safe_stop_reason = 0;
};

class BoardSupport {
public:
    virtual ~BoardSupport() = default;
    virtual uint32_t millis() const = 0;
    virtual void set_led_blink_state(bool enabled) = 0;
    virtual void set_led_blink_rate_khz(uint32_t rate_khz) = 0;
    virtual void set_servo_target(float degrees) = 0;
    virtual void set_stepper_1_target(float target) = 0;
    virtual void set_stepper_2_target(float target) = 0;
    virtual ImuSample read_imu_1() = 0;
    virtual ImuSample read_imu_2() = 0;
    virtual void disable_outputs() = 0;
};

class FirmwareApp {
public:
    explicit FirmwareApp(BoardSupport& board_support, uint32_t watchdog_timeout_ms = 250);

    bool process_frame(const uint8_t* frame_bytes, size_t frame_length, uint8_t* reply_buffer, size_t* reply_length);
    void service_watchdog();
    bool build_telemetry(uint8_t sequence, uint8_t* reply_buffer, size_t* reply_length);

    const FirmwareStatus& status() const;
    const MotionOutputs& outputs() const;
    const LedBlinkConfig& led_blink() const;

private:
    bool decode_frame(const uint8_t* frame_bytes, size_t frame_length, tars_leg_frame_header_t* header, const uint8_t** payload) const;
    bool encode_frame(uint8_t message_type, uint8_t sequence, const uint8_t* payload, uint16_t payload_length, uint8_t* reply_buffer, size_t* reply_length) const;
    bool encode_ack(uint8_t sequence, uint8_t* reply_buffer, size_t* reply_length) const;
    bool encode_fault(uint8_t sequence, uint8_t fault_bits, uint8_t* reply_buffer, size_t* reply_length);
    void apply_motion_outputs();
    void apply_led_blink();
    void safe_stop(uint8_t reason_code, BoardState next_state);
    uint16_t crc16_ccitt_false(const uint8_t* data, size_t length) const;

    BoardSupport& board_support_;
    uint32_t watchdog_timeout_ms_;
    FirmwareStatus status_;
    MotionOutputs outputs_;
    LedBlinkConfig led_blink_;
};

#endif
