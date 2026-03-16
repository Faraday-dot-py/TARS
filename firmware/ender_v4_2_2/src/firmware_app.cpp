#include "firmware_app.hpp"

#include <string.h>

namespace {
constexpr uint8_t kFaultProtocolError = 0x01;
constexpr uint8_t kFaultDisabledCommand = 0x02;
constexpr uint8_t kFaultUnsupportedMessage = 0x04;
constexpr uint8_t kFaultUnsupportedConfig = 0x08;
constexpr size_t kHeaderSize = sizeof(tars_leg_frame_header_t);
constexpr size_t kCrcSize = sizeof(uint16_t);
}  // namespace

FirmwareApp::FirmwareApp(BoardSupport& board_support, uint32_t watchdog_timeout_ms)
    : board_support_(board_support), watchdog_timeout_ms_(watchdog_timeout_ms) {
    status_.board_state = BoardState::Disabled;
}

bool FirmwareApp::process_frame(const uint8_t* frame_bytes, size_t frame_length, uint8_t* reply_buffer, size_t* reply_length) {
    tars_leg_frame_header_t header{};
    const uint8_t* payload = nullptr;
    if (!decode_frame(frame_bytes, frame_length, &header, &payload)) {
        return encode_fault(0, kFaultProtocolError, reply_buffer, reply_length);
    }

    status_.applied_sequence = header.sequence;
    status_.last_command_rx_ms = board_support_.millis();

    switch (header.message_type) {
        case TARS_MSG_SET_ENABLE: {
            if (header.payload_length != sizeof(tars_leg_set_enable_payload_t)) {
                return encode_fault(header.sequence, kFaultProtocolError, reply_buffer, reply_length);
            }
            const auto* enable = reinterpret_cast<const tars_leg_set_enable_payload_t*>(payload);
            if (enable->enabled) {
                status_.board_state = BoardState::Enabled;
                status_.watchdog_state = WatchdogState::Armed;
                status_.safe_stop_reason = 0;
            } else {
                safe_stop(TARS_SAFE_STOP_DISABLED, BoardState::Disabled);
            }
            return encode_ack(header.sequence, reply_buffer, reply_length);
        }
        case TARS_MSG_SET_CONFIG: {
            if (header.payload_length != sizeof(tars_leg_set_config_payload_t)) {
                return encode_fault(header.sequence, kFaultProtocolError, reply_buffer, reply_length);
            }
            const auto* config = reinterpret_cast<const tars_leg_set_config_payload_t*>(payload);
            switch (config->config_key) {
                case TARS_CFG_LED_BLINK_STATE:
                    led_blink_.enabled = (config->value_u32 != 0u);
                    apply_led_blink();
                    return encode_ack(header.sequence, reply_buffer, reply_length);
                case TARS_CFG_LED_BLINK_RATE_KHZ:
                    led_blink_.rate_khz = config->value_u32;
                    apply_led_blink();
                    return encode_ack(header.sequence, reply_buffer, reply_length);
                default:
                    return encode_fault(header.sequence, kFaultUnsupportedConfig, reply_buffer, reply_length);
            }
        }
        case TARS_MSG_SET_COMMAND: {
            if (header.payload_length != sizeof(tars_leg_set_command_payload_t)) {
                return encode_fault(header.sequence, kFaultProtocolError, reply_buffer, reply_length);
            }
            if (status_.board_state != BoardState::Enabled) {
                return encode_fault(header.sequence, kFaultDisabledCommand, reply_buffer, reply_length);
            }
            const auto* command = reinterpret_cast<const tars_leg_set_command_payload_t*>(payload);
            status_.last_host_time_ms = command->host_time_ms;
            status_.watchdog_state = WatchdogState::Armed;
            if ((command->command_flags & TARS_CMD_FLAG_STEPPER_1) != 0u) {
                outputs_.stepper_1_target = command->stepper_1_target;
            }
            if ((command->command_flags & TARS_CMD_FLAG_STEPPER_2) != 0u) {
                outputs_.stepper_2_target = command->stepper_2_target;
            }
            if ((command->command_flags & TARS_CMD_FLAG_SERVO) != 0u) {
                outputs_.servo_target = command->servo_target;
            }
            apply_motion_outputs();
            return encode_ack(header.sequence, reply_buffer, reply_length);
        }
        case TARS_MSG_HEARTBEAT: {
            if (header.payload_length != sizeof(tars_leg_heartbeat_payload_t)) {
                return encode_fault(header.sequence, kFaultProtocolError, reply_buffer, reply_length);
            }
            const auto* heartbeat = reinterpret_cast<const tars_leg_heartbeat_payload_t*>(payload);
            status_.last_host_time_ms = heartbeat->host_time_ms;
            if (status_.board_state == BoardState::Enabled) {
                status_.watchdog_state = WatchdogState::Armed;
            }
            return build_telemetry(header.sequence, reply_buffer, reply_length);
        }
        case TARS_MSG_SAFE_STOP: {
            if (header.payload_length != sizeof(tars_leg_safe_stop_payload_t)) {
                return encode_fault(header.sequence, kFaultProtocolError, reply_buffer, reply_length);
            }
            const auto* safe_stop_payload = reinterpret_cast<const tars_leg_safe_stop_payload_t*>(payload);
            safe_stop(safe_stop_payload->reason_code, BoardState::SafeStop);
            return encode_ack(header.sequence, reply_buffer, reply_length);
        }
        default:
            return encode_fault(header.sequence, kFaultUnsupportedMessage, reply_buffer, reply_length);
    }
}

void FirmwareApp::service_watchdog() {
    if (status_.board_state != BoardState::Enabled) {
        return;
    }

    const uint32_t now_ms = board_support_.millis();
    if ((now_ms - status_.last_command_rx_ms) > watchdog_timeout_ms_) {
        status_.watchdog_state = WatchdogState::Tripped;
        safe_stop(TARS_SAFE_STOP_WATCHDOG, BoardState::SafeStop);
    }
}

bool FirmwareApp::build_telemetry(uint8_t sequence, uint8_t* reply_buffer, size_t* reply_length) {
    tars_leg_telemetry_payload_t telemetry{};
    telemetry.board_state = static_cast<uint8_t>(status_.board_state);
    telemetry.fault_bits = status_.fault_bits;
    telemetry.watchdog_state = static_cast<uint8_t>(status_.watchdog_state);
    telemetry.applied_sequence = status_.applied_sequence;
    telemetry.board_time_ms = board_support_.millis();
    telemetry.stepper_1_position = outputs_.stepper_1_target;
    telemetry.stepper_2_position = outputs_.stepper_2_target;
    telemetry.servo_position = outputs_.servo_target;

    const ImuSample imu_1 = board_support_.read_imu_1();
    const ImuSample imu_2 = board_support_.read_imu_2();
    telemetry.imu_1_ax = imu_1.ax;
    telemetry.imu_1_ay = imu_1.ay;
    telemetry.imu_1_az = imu_1.az;
    telemetry.imu_2_ax = imu_2.ax;
    telemetry.imu_2_ay = imu_2.ay;
    telemetry.imu_2_az = imu_2.az;

    return encode_frame(TARS_MSG_TELEMETRY, sequence, reinterpret_cast<const uint8_t*>(&telemetry), sizeof(telemetry), reply_buffer, reply_length);
}

const FirmwareStatus& FirmwareApp::status() const {
    return status_;
}

const MotionOutputs& FirmwareApp::outputs() const {
    return outputs_;
}

const LedBlinkConfig& FirmwareApp::led_blink() const {
    return led_blink_;
}

bool FirmwareApp::decode_frame(const uint8_t* frame_bytes, size_t frame_length, tars_leg_frame_header_t* header, const uint8_t** payload) const {
    if (frame_length < (kHeaderSize + kCrcSize)) {
        return false;
    }
    memcpy(header, frame_bytes, kHeaderSize);
    if (header->sof != TARS_LEG_SOF || header->version != TARS_LEG_PROTOCOL_VERSION) {
        return false;
    }
    const size_t expected_length = kHeaderSize + header->payload_length + kCrcSize;
    if (frame_length != expected_length) {
        return false;
    }
    *payload = frame_bytes + kHeaderSize;
    const uint16_t expected_crc = crc16_ccitt_false(frame_bytes + 1, (kHeaderSize - 1) + header->payload_length);
    uint16_t received_crc = 0;
    memcpy(&received_crc, frame_bytes + kHeaderSize + header->payload_length, kCrcSize);
    return expected_crc == received_crc;
}

bool FirmwareApp::encode_frame(uint8_t message_type, uint8_t sequence, const uint8_t* payload, uint16_t payload_length, uint8_t* reply_buffer, size_t* reply_length) const {
    if (reply_buffer == nullptr || reply_length == nullptr) {
        return false;
    }
    tars_leg_frame_header_t header{};
    header.sof = TARS_LEG_SOF;
    header.version = TARS_LEG_PROTOCOL_VERSION;
    header.message_type = message_type;
    header.sequence = sequence;
    header.payload_length = payload_length;

    memcpy(reply_buffer, &header, sizeof(header));
    if (payload_length > 0 && payload != nullptr) {
        memcpy(reply_buffer + sizeof(header), payload, payload_length);
    }
    const uint16_t crc = crc16_ccitt_false(reply_buffer + 1, (sizeof(header) - 1) + payload_length);
    memcpy(reply_buffer + sizeof(header) + payload_length, &crc, sizeof(crc));
    *reply_length = sizeof(header) + payload_length + sizeof(crc);
    return true;
}

bool FirmwareApp::encode_ack(uint8_t sequence, uint8_t* reply_buffer, size_t* reply_length) const {
    return encode_frame(TARS_MSG_ACK, sequence, nullptr, 0, reply_buffer, reply_length);
}

bool FirmwareApp::encode_fault(uint8_t sequence, uint8_t fault_bits, uint8_t* reply_buffer, size_t* reply_length) {
    status_.board_state = BoardState::Fault;
    status_.fault_bits |= fault_bits;
    return encode_frame(TARS_MSG_FAULT, sequence, &status_.fault_bits, sizeof(status_.fault_bits), reply_buffer, reply_length);
}

void FirmwareApp::apply_motion_outputs() {
    board_support_.set_servo_target(outputs_.servo_target);
    board_support_.set_stepper_1_target(outputs_.stepper_1_target);
    board_support_.set_stepper_2_target(outputs_.stepper_2_target);
}

void FirmwareApp::apply_led_blink() {
    board_support_.set_led_blink_state(led_blink_.enabled);
    board_support_.set_led_blink_rate_khz(led_blink_.rate_khz);
}

void FirmwareApp::safe_stop(uint8_t reason_code, BoardState next_state) {
    outputs_ = MotionOutputs{};
    status_.safe_stop_reason = reason_code;
    status_.board_state = next_state;
    board_support_.disable_outputs();
}

uint16_t FirmwareApp::crc16_ccitt_false(const uint8_t* data, size_t length) const {
    uint16_t crc = 0xFFFFu;
    for (size_t i = 0; i < length; ++i) {
        crc ^= static_cast<uint16_t>(data[i]) << 8;
        for (uint8_t bit = 0; bit < 8; ++bit) {
            if ((crc & 0x8000u) != 0u) {
                crc = static_cast<uint16_t>((crc << 1) ^ 0x1021u);
            } else {
                crc = static_cast<uint16_t>(crc << 1);
            }
        }
    }
    return crc;
}
