#include "firmware_app.hpp"

#include <stdint.h>

namespace {
class StubBoardSupport final : public BoardSupport {
public:
    uint32_t millis() const override {
        return milliseconds_;
    }

    void set_led_blink_state(bool enabled) override {
        led_enabled_ = enabled;
    }

    void set_led_blink_rate_khz(uint32_t rate_khz) override {
        led_rate_khz_ = rate_khz;
    }

    void set_servo_target(float degrees) override {
        servo_target_ = degrees;
    }

    void set_stepper_1_target(float target) override {
        stepper_1_target_ = target;
    }

    void set_stepper_2_target(float target) override {
        stepper_2_target_ = target;
    }

    ImuSample read_imu_1() override {
        return imu_1_;
    }

    ImuSample read_imu_2() override {
        return imu_2_;
    }

    void disable_outputs() override {
        servo_target_ = 0.0f;
        stepper_1_target_ = 0.0f;
        stepper_2_target_ = 0.0f;
    }

    void tick(uint32_t delta_ms) {
        milliseconds_ += delta_ms;
    }

private:
    mutable uint32_t milliseconds_ = 0;
    bool led_enabled_ = false;
    uint32_t led_rate_khz_ = 0;
    float servo_target_ = 0.0f;
    float stepper_1_target_ = 0.0f;
    float stepper_2_target_ = 0.0f;
    ImuSample imu_1_{};
    ImuSample imu_2_{};
};
}  // namespace

int main() {
    StubBoardSupport board_support;
    FirmwareApp app(board_support, 250);

    uint8_t rx_buffer[128]{};
    uint8_t tx_buffer[128]{};
    size_t tx_length = 0;

    while (true) {
        const size_t rx_length = 0;
        if (rx_length > 0) {
            app.process_frame(rx_buffer, rx_length, tx_buffer, &tx_length);
            (void)tx_buffer;
            (void)tx_length;
        }

        app.service_watchdog();
        board_support.tick(1);
    }

    return 0;
}
