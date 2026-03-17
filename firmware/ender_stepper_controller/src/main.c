#include "ender_stepper_controller_contract.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

typedef struct {
  volatile uint32_t CRL;
  volatile uint32_t CRH;
  volatile uint32_t IDR;
  volatile uint32_t ODR;
  volatile uint32_t BSRR;
  volatile uint32_t BRR;
  volatile uint32_t LCKR;
} gpio_regs_t;

typedef struct {
  volatile uint32_t SR;
  volatile uint32_t DR;
  volatile uint32_t BRR;
  volatile uint32_t CR1;
  volatile uint32_t CR2;
  volatile uint32_t CR3;
  volatile uint32_t GTPR;
} usart_regs_t;

typedef struct {
  volatile uint32_t CR;
  volatile uint32_t CFGR;
  volatile uint32_t CIR;
  volatile uint32_t APB2RSTR;
  volatile uint32_t APB1RSTR;
  volatile uint32_t AHBENR;
  volatile uint32_t APB2ENR;
  volatile uint32_t APB1ENR;
  volatile uint32_t BDCR;
  volatile uint32_t CSR;
} rcc_regs_t;

#define RCC_BASE_ADDR 0x40021000u
#define GPIOA_BASE_ADDR 0x40010800u
#define GPIOB_BASE_ADDR 0x40010C00u
#define GPIOC_BASE_ADDR 0x40011000u
#define AFIO_BASE_ADDR 0x40010000u
#define USART3_BASE_ADDR 0x40004800u
#define FLASH_ACR_ADDR 0x40022000u

#define RCC ((rcc_regs_t *)RCC_BASE_ADDR)
#define GPIOA ((gpio_regs_t *)GPIOA_BASE_ADDR)
#define GPIOB ((gpio_regs_t *)GPIOB_BASE_ADDR)
#define GPIOC ((gpio_regs_t *)GPIOC_BASE_ADDR)
#define AFIO_MAPR (*(volatile uint32_t *)(AFIO_BASE_ADDR + 0x04u))
#define USART3 ((usart_regs_t *)USART3_BASE_ADDR)
#define FLASH_ACR (*(volatile uint32_t *)(FLASH_ACR_ADDR + 0x00u))

#define RCC_APB2ENR_AFIOEN (1u << 0)
#define RCC_APB2ENR_IOPAEN (1u << 2)
#define RCC_APB2ENR_IOPBEN (1u << 3)
#define RCC_APB2ENR_IOPCEN (1u << 4)
#define RCC_APB1ENR_USART3EN (1u << 18)
#define RCC_CR_HSION (1u << 0)
#define RCC_CR_HSIRDY (1u << 1)
#define RCC_CR_HSEON (1u << 16)
#define RCC_CR_HSERDY (1u << 17)
#define RCC_CR_PLLON (1u << 24)
#define RCC_CR_PLLRDY (1u << 25)
#define RCC_CFGR_SW_MASK (0x3u << 0)
#define RCC_CFGR_SW_HSI (0x0u << 0)
#define RCC_CFGR_SW_PLL (0x2u << 0)
#define RCC_CFGR_SWS_MASK (0x3u << 2)
#define RCC_CFGR_SWS_PLL (0x2u << 2)
#define RCC_CFGR_HPRE_DIV1 (0x0u << 4)
#define RCC_CFGR_PPRE1_DIV2 (0x4u << 8)
#define RCC_CFGR_PPRE2_DIV1 (0x0u << 11)
#define RCC_CFGR_PLLSRC_HSE (1u << 16)
#define RCC_CFGR_PLLMULL9 (0x7u << 18)
#define FLASH_ACR_LATENCY_2 (0x2u << 0)
#define FLASH_ACR_PRFTBE (1u << 4)

#define USART_SR_RXNE (1u << 5)
#define USART_SR_TXE (1u << 7)
#define USART_CR1_UE (1u << 13)
#define USART_CR1_TE (1u << 3)
#define USART_CR1_RE (1u << 2)

#define PIN_MASK(pin) (1u << (pin))

#define X_STEP_PIN 2u
#define X_DIR_PIN 9u
#define Y_STEP_PIN 8u
#define Y_DIR_PIN 7u
#define XY_ENABLE_PIN 3u
#define UART_TX_PIN 10u
#define UART_RX_PIN 11u

#define FRAME_SOF_0 0xC3u
#define FRAME_SOF_1 0x3Cu
#define FRAME_VERSION 1u
#define MSG_HEARTBEAT 0x01u
#define MSG_COMMAND 0x02u
#define MSG_STATUS 0x10u

#define FAULT_WATCHDOG_EXPIRED (1u << 0)
#define FAULT_INVALID_COMMAND (1u << 1)
#define FAULT_DRIVER_FAULT (1u << 2)
#define FAULT_AXIS_1_STALL (1u << 3)
#define FAULT_AXIS_2_STALL (1u << 4)
#define FAULT_CRC_ERROR (1u << 5)

#define STEP_PULSE_NOP_COUNT 1024u
#define ASCII_LINE_MAX 96u
#define BINARY_FRAME_MAX 64u
#define STATUS_PERIOD_MS 100u
#define DEFAULT_RATE_HZ 400u
#define ASCII_WATCHDOG_TIMEOUT_MS 5000u

typedef struct {
  gpio_regs_t *step_port;
  uint8_t step_pin;
  gpio_regs_t *dir_port;
  uint8_t dir_pin;
  int32_t position_steps;
  int32_t target_steps;
  uint32_t step_interval_us;
  uint32_t last_step_time_us;
  ender_stepper_mode_t mode;
} axis_state_t;

typedef struct {
  bool outputs_enabled;
  bool safe_stop;
  bool relative_mode;
  bool binary_streaming_active;
  uint32_t last_command_ms;
  uint32_t last_status_ms;
  uint32_t last_sequence;
  uint32_t fault_bits;
  ender_stepper_command_t latest_command;
  ender_stepper_status_t latest_status;
  axis_state_t axis_1;
  axis_state_t axis_2;
} controller_state_t;

static void controller_refresh_watchdog(void);
static void controller_step_axis(axis_state_t *axis);
static void controller_run_until_idle_or_timeout(uint32_t timeout_ms);

static volatile uint32_t g_systick_ms = 0;
static volatile uint32_t g_systick_us = 0;
static uint32_t g_system_clock_hz = 8000000u;
static uint32_t g_apb1_clock_hz = 8000000u;
static controller_state_t g_controller;
static char g_ascii_line[ASCII_LINE_MAX];
static uint8_t g_ascii_line_len = 0;
static uint8_t g_binary_frame[BINARY_FRAME_MAX];
static uint8_t g_binary_frame_len = 0;
static bool g_binary_sync = false;

void SysTick_Handler(void) {
  g_systick_ms += 1u;
  g_systick_us += 1000u;
}

static uint32_t millis_now(void) {
  return g_systick_ms;
}

static uint32_t micros_now(void) {
  return g_systick_us;
}

static void busy_nop_delay(uint32_t count) {
  while (count-- > 0u) {
    __asm__ volatile("nop");
  }
}

static void gpio_config_output(gpio_regs_t *port, uint8_t pin) {
  volatile uint32_t *config = pin < 8u ? &port->CRL : &port->CRH;
  const uint8_t shift = (uint8_t)((pin & 0x7u) * 4u);
  uint32_t value = *config;
  value &= ~(0xFu << shift);
  value |= (0x2u << shift);  // 2MHz push-pull output
  *config = value;
}

static void gpio_config_input_floating(gpio_regs_t *port, uint8_t pin) {
  volatile uint32_t *config = pin < 8u ? &port->CRL : &port->CRH;
  const uint8_t shift = (uint8_t)((pin & 0x7u) * 4u);
  uint32_t value = *config;
  value &= ~(0xFu << shift);
  value |= (0x4u << shift);  // floating input
  *config = value;
}

static void gpio_config_alt_pushpull(gpio_regs_t *port, uint8_t pin) {
  volatile uint32_t *config = pin < 8u ? &port->CRL : &port->CRH;
  const uint8_t shift = (uint8_t)((pin & 0x7u) * 4u);
  uint32_t value = *config;
  value &= ~(0xFu << shift);
  value |= (0xBu << shift);  // 50MHz alt push-pull
  *config = value;
}

static void gpio_write(gpio_regs_t *port, uint8_t pin, bool high) {
  if (high) {
    port->BSRR = PIN_MASK(pin);
  } else {
    port->BRR = PIN_MASK(pin);
  }
}

static void uart3_write_byte(uint8_t value) {
  while ((USART3->SR & USART_SR_TXE) == 0u) {
  }
  USART3->DR = value;
}

static void uart3_write_text(const char *text) {
  while (*text != '\0') {
    uart3_write_byte((uint8_t)(*text));
    ++text;
  }
}

static void uart3_write_u32(uint32_t value) {
  char buffer[11];
  uint8_t index = 0;

  if (value == 0u) {
    uart3_write_byte('0');
    return;
  }

  while (value > 0u && index < sizeof(buffer)) {
    buffer[index++] = (char)('0' + (value % 10u));
    value /= 10u;
  }

  while (index > 0u) {
    uart3_write_byte((uint8_t)buffer[--index]);
  }
}

static void uart3_write_i32(int32_t value) {
  if (value < 0) {
    uart3_write_byte('-');
    uart3_write_u32((uint32_t)(-value));
  } else {
    uart3_write_u32((uint32_t)value);
  }
}

static void uart3_write_line(const char *text) {
  uart3_write_text(text);
  uart3_write_text("\r\n");
}

static uint16_t crc16_ccitt(const uint8_t *data, uint16_t length) {
  uint16_t crc = 0xFFFFu;
  for (uint16_t i = 0; i < length; ++i) {
    crc ^= (uint16_t)data[i] << 8;
    for (uint8_t bit = 0; bit < 8u; ++bit) {
      if ((crc & 0x8000u) != 0u) {
        crc = (uint16_t)((crc << 1) ^ 0x1021u);
      } else {
        crc <<= 1;
      }
    }
  }
  return crc;
}

static uint16_t read_u16_le(const uint8_t *data) {
  return (uint16_t)data[0] | ((uint16_t)data[1] << 8);
}

static uint32_t read_u32_le(const uint8_t *data) {
  return (uint32_t)data[0]
      | ((uint32_t)data[1] << 8)
      | ((uint32_t)data[2] << 16)
      | ((uint32_t)data[3] << 24);
}

static int32_t read_i32_le(const uint8_t *data) {
  return (int32_t)read_u32_le(data);
}

static void write_u16_le(uint8_t *dst, uint16_t value) {
  dst[0] = (uint8_t)(value & 0xFFu);
  dst[1] = (uint8_t)((value >> 8) & 0xFFu);
}

static void write_u32_le(uint8_t *dst, uint32_t value) {
  dst[0] = (uint8_t)(value & 0xFFu);
  dst[1] = (uint8_t)((value >> 8) & 0xFFu);
  dst[2] = (uint8_t)((value >> 16) & 0xFFu);
  dst[3] = (uint8_t)((value >> 24) & 0xFFu);
}

static void write_i32_le(uint8_t *dst, int32_t value) {
  write_u32_le(dst, (uint32_t)value);
}

static void axis_apply_command(axis_state_t *axis, const ender_stepper_axis_command_t *command) {
  axis->mode = command->mode;
  axis->target_steps = command->target_steps;
  if (command->max_step_rate_hz > 0u) {
    axis->step_interval_us = 1000000u / command->max_step_rate_hz;
    if (axis->step_interval_us == 0u) {
      axis->step_interval_us = 1u;
    }
  } else {
    axis->step_interval_us = 1000000u / DEFAULT_RATE_HZ;
  }
}

static void controller_publish_status_binary(void) {
  uint8_t payload[20];
  uint8_t frame[32];
  uint16_t payload_len = sizeof(payload);
  uint16_t crc;

  g_controller.latest_status.enabled = g_controller.outputs_enabled;
  g_controller.latest_status.safe_stop = g_controller.safe_stop;
  g_controller.latest_status.axis_1_state = (uint8_t)g_controller.axis_1.mode;
  g_controller.latest_status.axis_2_state = (uint8_t)g_controller.axis_2.mode;
  g_controller.latest_status.fault_bits = g_controller.fault_bits;
  g_controller.latest_status.applied_sequence = g_controller.last_sequence;
  g_controller.latest_status.axis_1_position_steps = g_controller.axis_1.position_steps;
  g_controller.latest_status.axis_2_position_steps = g_controller.axis_2.position_steps;

  payload[0] = g_controller.latest_status.enabled ? 1u : 0u;
  payload[1] = g_controller.latest_status.safe_stop ? 1u : 0u;
  payload[2] = g_controller.latest_status.axis_1_state;
  payload[3] = g_controller.latest_status.axis_2_state;
  write_u32_le(&payload[4], g_controller.latest_status.fault_bits);
  write_u32_le(&payload[8], g_controller.latest_status.applied_sequence);
  write_i32_le(&payload[12], g_controller.latest_status.axis_1_position_steps);
  write_i32_le(&payload[16], g_controller.latest_status.axis_2_position_steps);

  frame[0] = FRAME_SOF_0;
  frame[1] = FRAME_SOF_1;
  frame[2] = FRAME_VERSION;
  frame[3] = MSG_STATUS;
  write_u32_le(&frame[4], g_controller.last_sequence);
  write_u16_le(&frame[8], payload_len);

  for (uint16_t i = 0; i < payload_len; ++i) {
    frame[10u + i] = payload[i];
  }

  crc = crc16_ccitt(&frame[2], (uint16_t)(8u + payload_len));
  write_u16_le(&frame[10u + payload_len], crc);

  for (uint16_t i = 0; i < (uint16_t)(12u + payload_len); ++i) {
    uart3_write_byte(frame[i]);
  }
}

static void controller_publish_status_text(void) {
  uart3_write_text("X:");
  uart3_write_i32(g_controller.axis_1.position_steps);
  uart3_write_text(" XT:");
  uart3_write_i32(g_controller.axis_1.target_steps);
  uart3_write_text(" Y:");
  uart3_write_i32(g_controller.axis_2.position_steps);
  uart3_write_text(" YT:");
  uart3_write_i32(g_controller.axis_2.target_steps);
  uart3_write_text(" ENABLED:");
  uart3_write_u32(g_controller.outputs_enabled ? 1u : 0u);
  uart3_write_text(" SAFE_STOP:");
  uart3_write_u32(g_controller.safe_stop ? 1u : 0u);
  uart3_write_text(" FAULT:");
  uart3_write_u32(g_controller.fault_bits);
  uart3_write_text("\r\n");
}

static void controller_enable_outputs(bool enabled) {
  g_controller.outputs_enabled = enabled;
  g_controller.safe_stop = !enabled;
  gpio_write(GPIOC, XY_ENABLE_PIN, !enabled);  // shared enable is active-low
}

static void controller_mark_ascii_activity(void) {
  g_controller.binary_streaming_active = false;
  g_controller.last_command_ms = millis_now();
  g_controller.latest_command.watchdog_timeout_ms = ASCII_WATCHDOG_TIMEOUT_MS;
}

static int32_t parse_signed_value(const char *line, char key, bool *found) {
  const char *cursor = line;
  *found = false;

  while (*cursor != '\0') {
    if (*cursor == key) {
      int sign = 1;
      int32_t value = 0;
      cursor++;
      if (*cursor == '-') {
        sign = -1;
        cursor++;
      }
      while (*cursor >= '0' && *cursor <= '9') {
        value = (value * 10) + (int32_t)(*cursor - '0');
        cursor++;
      }
      *found = true;
      return value * sign;
    }
    cursor++;
  }

  return 0;
}

static void controller_apply_move(int32_t x_value, bool has_x, int32_t y_value, bool has_y, uint32_t rate_hz) {
  if (has_x) {
    if (g_controller.relative_mode) {
      g_controller.axis_1.target_steps = g_controller.axis_1.position_steps + x_value;
    } else {
      g_controller.axis_1.target_steps = x_value;
    }
    g_controller.axis_1.mode = ENDER_STEPPER_POSITION;
    g_controller.axis_1.step_interval_us = rate_hz > 0u ? (1000000u / rate_hz) : (1000000u / DEFAULT_RATE_HZ);
  }

  if (has_y) {
    if (g_controller.relative_mode) {
      g_controller.axis_2.target_steps = g_controller.axis_2.position_steps + y_value;
    } else {
      g_controller.axis_2.target_steps = y_value;
    }
    g_controller.axis_2.mode = ENDER_STEPPER_POSITION;
    g_controller.axis_2.step_interval_us = rate_hz > 0u ? (1000000u / rate_hz) : (1000000u / DEFAULT_RATE_HZ);
  }
}

static void controller_process_ascii_command(const char *line) {
  if (line[0] == '\0') {
    return;
  }

  if (line[0] == 'M' && line[1] == '1' && line[2] == '1' && line[3] == '5' && line[4] == '\0') {
    controller_mark_ascii_activity();
    uart3_write_line("FIRMWARE_NAME:TARS Ender Stepper Controller MACHINE_TYPE:TARS Ender Stepper Controller");
    return;
  }

  if (line[0] == 'M' && line[1] == '1' && line[2] == '7' && line[3] == '\0') {
    controller_mark_ascii_activity();
    g_controller.fault_bits &= ~FAULT_WATCHDOG_EXPIRED;
    controller_enable_outputs(true);
    uart3_write_line("ok");
    return;
  }

  if (line[0] == 'M' && ((line[1] == '1' && line[2] == '8') || (line[1] == '8' && line[2] == '4')) && line[3] == '\0') {
    controller_mark_ascii_activity();
    controller_enable_outputs(false);
    uart3_write_line("ok");
    return;
  }

  if (line[0] == 'G' && line[1] == '9' && line[2] == '0' && line[3] == '\0') {
    controller_mark_ascii_activity();
    g_controller.relative_mode = false;
    uart3_write_line("ok");
    return;
  }

  if (line[0] == 'G' && line[1] == '9' && line[2] == '1' && line[3] == '\0') {
    controller_mark_ascii_activity();
    g_controller.relative_mode = true;
    uart3_write_line("ok");
    return;
  }

  if (line[0] == 'M' && line[1] == '1' && line[2] == '1' && line[3] == '4' && line[4] == '\0') {
    controller_mark_ascii_activity();
    controller_publish_status_text();
    return;
  }

  if (line[0] == 'G' && line[1] == '1') {
    bool has_x = false;
    bool has_y = false;
    bool has_r = false;
    int32_t x_value = parse_signed_value(line, 'X', &has_x);
    int32_t y_value = parse_signed_value(line, 'Y', &has_y);
    int32_t rate_value = parse_signed_value(line, 'R', &has_r);
    uint32_t rate_hz = has_r && rate_value > 0 ? (uint32_t)rate_value : DEFAULT_RATE_HZ;

    if (!g_controller.outputs_enabled) {
      uart3_write_line("error:motors_disabled");
      return;
    }

    controller_mark_ascii_activity();
    controller_apply_move(x_value, has_x, y_value, has_y, rate_hz);
    controller_run_until_idle_or_timeout(10000u);
    if (g_controller.safe_stop || g_controller.fault_bits != 0u) {
      uart3_write_line("error:move_incomplete");
    } else {
      uart3_write_line("ok");
    }
    return;
  }

  uart3_write_line("error:unknown_command");
}

static void controller_process_binary_frame(const uint8_t *frame, uint16_t frame_length) {
  if (frame_length < 12u) {
    return;
  }

  if (frame[0] != FRAME_SOF_0 || frame[1] != FRAME_SOF_1 || frame[2] != FRAME_VERSION) {
    return;
  }

  const uint8_t message_type = frame[3];
  const uint32_t sequence = read_u32_le(&frame[4]);
  const uint16_t payload_len = read_u16_le(&frame[8]);

  if ((uint16_t)(12u + payload_len) != frame_length) {
    g_controller.fault_bits |= FAULT_INVALID_COMMAND;
    return;
  }

  const uint16_t expected_crc = read_u16_le(&frame[10u + payload_len]);
  const uint16_t actual_crc = crc16_ccitt(&frame[2], (uint16_t)(8u + payload_len));
  if (expected_crc != actual_crc) {
    g_controller.fault_bits |= FAULT_CRC_ERROR;
    return;
  }

  if (message_type == MSG_HEARTBEAT) {
    g_controller.binary_streaming_active = true;
    g_controller.last_command_ms = millis_now();
    g_controller.last_sequence = sequence;
    return;
  }

  if (message_type != MSG_COMMAND || payload_len != 30u) {
    g_controller.fault_bits |= FAULT_INVALID_COMMAND;
    return;
  }

  const uint8_t *payload = &frame[10];
  g_controller.latest_command.enabled = payload[0] != 0u;
  g_controller.latest_command.safe_stop = payload[1] != 0u;
  g_controller.latest_command.watchdog_timeout_ms = read_u16_le(&payload[2]);
  g_controller.latest_command.axis_1.mode = (ender_stepper_mode_t)payload[6];
  g_controller.latest_command.axis_1.homing_direction = (int8_t)payload[7];
  g_controller.latest_command.axis_1.target_steps = read_i32_le(&payload[10]);
  g_controller.latest_command.axis_1.max_step_rate_hz = read_u32_le(&payload[14]);
  g_controller.latest_command.axis_2.mode = (ender_stepper_mode_t)payload[18];
  g_controller.latest_command.axis_2.homing_direction = (int8_t)payload[19];
  g_controller.latest_command.axis_2.target_steps = read_i32_le(&payload[22]);
  g_controller.latest_command.axis_2.max_step_rate_hz = read_u32_le(&payload[26]);

  g_controller.last_command_ms = millis_now();
  g_controller.last_sequence = sequence;
  g_controller.binary_streaming_active = true;
  g_controller.safe_stop = g_controller.latest_command.safe_stop;
  controller_enable_outputs(g_controller.latest_command.enabled && !g_controller.latest_command.safe_stop);
  axis_apply_command(&g_controller.axis_1, &g_controller.latest_command.axis_1);
  axis_apply_command(&g_controller.axis_2, &g_controller.latest_command.axis_2);
}

static void controller_pulse_step(axis_state_t *axis) {
  gpio_write(axis->step_port, axis->step_pin, true);
  busy_nop_delay(STEP_PULSE_NOP_COUNT);
  gpio_write(axis->step_port, axis->step_pin, false);
}

static void controller_step_axis(axis_state_t *axis) {
  if (!g_controller.outputs_enabled || g_controller.safe_stop) {
    return;
  }

  if (axis->mode == ENDER_STEPPER_DISABLED || axis->mode == ENDER_STEPPER_HOLD) {
    return;
  }

  if (axis->position_steps == axis->target_steps) {
    if (axis->mode == ENDER_STEPPER_POSITION) {
      axis->mode = ENDER_STEPPER_HOLD;
    }
    return;
  }

  const uint32_t now_us = micros_now();
  if ((now_us - axis->last_step_time_us) < axis->step_interval_us) {
    return;
  }

  const bool direction_positive = axis->target_steps > axis->position_steps;
  gpio_write(axis->dir_port, axis->dir_pin, direction_positive);
  controller_pulse_step(axis);
  axis->position_steps += direction_positive ? 1 : -1;
  axis->last_step_time_us = now_us;
}

static bool controller_axes_idle(void) {
  return g_controller.axis_1.position_steps == g_controller.axis_1.target_steps
      && g_controller.axis_2.position_steps == g_controller.axis_2.target_steps;
}

static void controller_run_until_idle_or_timeout(uint32_t timeout_ms) {
  const uint32_t start = millis_now();

  while (!controller_axes_idle()) {
    controller_refresh_watchdog();
    controller_step_axis(&g_controller.axis_1);
    controller_step_axis(&g_controller.axis_2);

    if (g_controller.safe_stop || g_controller.fault_bits != 0u) {
      break;
    }

    if ((millis_now() - start) > timeout_ms) {
      g_controller.fault_bits |= FAULT_INVALID_COMMAND;
      break;
    }
  }
}

static void controller_refresh_watchdog(void) {
  if (!g_controller.binary_streaming_active) {
    return;
  }

  const uint16_t timeout_ms = g_controller.latest_command.watchdog_timeout_ms > 0u
      ? g_controller.latest_command.watchdog_timeout_ms
      : 250u;

  if ((millis_now() - g_controller.last_command_ms) > timeout_ms) {
    g_controller.safe_stop = true;
    g_controller.outputs_enabled = false;
    g_controller.fault_bits |= FAULT_WATCHDOG_EXPIRED;
    gpio_write(GPIOC, XY_ENABLE_PIN, true);
  }
}

static void controller_poll_uart(void) {
  while ((USART3->SR & USART_SR_RXNE) != 0u) {
    const uint8_t value = (uint8_t)(USART3->DR & 0xFFu);

    if (g_binary_sync || value == FRAME_SOF_0) {
      if (!g_binary_sync) {
        g_binary_sync = true;
        g_binary_frame_len = 0u;
      }

      if (g_binary_frame_len < BINARY_FRAME_MAX) {
        g_binary_frame[g_binary_frame_len++] = value;
      } else {
        g_binary_sync = false;
        g_binary_frame_len = 0u;
      }

      if (g_binary_frame_len >= 10u) {
        const uint16_t payload_len = read_u16_le(&g_binary_frame[8]);
        const uint16_t total_len = (uint16_t)(12u + payload_len);
        if (payload_len > (BINARY_FRAME_MAX - 12u)) {
          g_binary_sync = false;
          g_binary_frame_len = 0u;
          g_controller.fault_bits |= FAULT_INVALID_COMMAND;
        } else if (g_binary_frame_len == total_len) {
          controller_process_binary_frame(g_binary_frame, total_len);
          if (g_controller.binary_streaming_active) {
            controller_publish_status_binary();
          }
          g_binary_sync = false;
          g_binary_frame_len = 0u;
        }
      }

      continue;
    }

    if (value == '\r') {
      continue;
    }

    if (value == '\n') {
      g_ascii_line[g_ascii_line_len] = '\0';
      controller_process_ascii_command(g_ascii_line);
      g_ascii_line_len = 0u;
      continue;
    }

    if (g_ascii_line_len + 1u < ASCII_LINE_MAX) {
      g_ascii_line[g_ascii_line_len++] = (char)value;
    } else {
      g_ascii_line_len = 0u;
    }
  }
}

static void controller_publish_periodic_status(void) {
  const uint32_t now = millis_now();
  if (g_controller.binary_streaming_active && (now - g_controller.last_status_ms) >= STATUS_PERIOD_MS) {
    controller_publish_status_binary();
    g_controller.last_status_ms = now;
  }
}

static void clock_init(void) {
  RCC->CR |= RCC_CR_HSION;
  while ((RCC->CR & RCC_CR_HSIRDY) == 0u) {
  }

  RCC->CR |= RCC_CR_HSEON;
  for (uint32_t wait = 0; wait < 500000u; ++wait) {
    if ((RCC->CR & RCC_CR_HSERDY) != 0u) {
      FLASH_ACR = FLASH_ACR_PRFTBE | FLASH_ACR_LATENCY_2;
      RCC->CFGR = RCC_CFGR_HPRE_DIV1
          | RCC_CFGR_PPRE1_DIV2
          | RCC_CFGR_PPRE2_DIV1
          | RCC_CFGR_PLLSRC_HSE
          | RCC_CFGR_PLLMULL9;
      RCC->CR |= RCC_CR_PLLON;
      while ((RCC->CR & RCC_CR_PLLRDY) == 0u) {
      }
      RCC->CFGR = (RCC->CFGR & ~RCC_CFGR_SW_MASK) | RCC_CFGR_SW_PLL;
      while ((RCC->CFGR & RCC_CFGR_SWS_MASK) != RCC_CFGR_SWS_PLL) {
      }
      g_system_clock_hz = 72000000u;
      g_apb1_clock_hz = 36000000u;
      break;
    }
  }

  RCC->APB2ENR |= RCC_APB2ENR_AFIOEN | RCC_APB2ENR_IOPAEN | RCC_APB2ENR_IOPBEN | RCC_APB2ENR_IOPCEN;
  RCC->APB1ENR |= RCC_APB1ENR_USART3EN;
  AFIO_MAPR |= (1u << 26);  // disable JTAG, keep SWD
}

static void gpio_init(void) {
  gpio_config_output(GPIOC, X_STEP_PIN);
  gpio_config_output(GPIOB, X_DIR_PIN);
  gpio_config_output(GPIOB, Y_STEP_PIN);
  gpio_config_output(GPIOB, Y_DIR_PIN);
  gpio_config_output(GPIOC, XY_ENABLE_PIN);
  gpio_config_alt_pushpull(GPIOB, UART_TX_PIN);
  gpio_config_input_floating(GPIOB, UART_RX_PIN);

  gpio_write(GPIOC, X_STEP_PIN, false);
  gpio_write(GPIOB, Y_STEP_PIN, false);
  gpio_write(GPIOC, XY_ENABLE_PIN, true);
}

static void systick_init(void) {
  *(volatile uint32_t *)0xE000E014u = (g_system_clock_hz / 1000u) - 1u;
  *(volatile uint32_t *)0xE000E018u = 0u;
  *(volatile uint32_t *)0xE000E010u = 7u;
}

static void uart3_init(void) {
  USART3->BRR = (g_apb1_clock_hz + 57600u) / 115200u;
  USART3->CR1 = USART_CR1_UE | USART_CR1_TE | USART_CR1_RE;
}

static void controller_init(void) {
  g_controller.axis_1.step_port = GPIOC;
  g_controller.axis_1.step_pin = X_STEP_PIN;
  g_controller.axis_1.dir_port = GPIOB;
  g_controller.axis_1.dir_pin = X_DIR_PIN;
  g_controller.axis_1.step_interval_us = 1000000u / DEFAULT_RATE_HZ;
  g_controller.axis_1.mode = ENDER_STEPPER_HOLD;

  g_controller.axis_2.step_port = GPIOB;
  g_controller.axis_2.step_pin = Y_STEP_PIN;
  g_controller.axis_2.dir_port = GPIOB;
  g_controller.axis_2.dir_pin = Y_DIR_PIN;
  g_controller.axis_2.step_interval_us = 1000000u / DEFAULT_RATE_HZ;
  g_controller.axis_2.mode = ENDER_STEPPER_HOLD;

  g_controller.latest_command.watchdog_timeout_ms = ASCII_WATCHDOG_TIMEOUT_MS;
  g_controller.last_command_ms = millis_now();
  g_controller.last_status_ms = millis_now();
}

int main(void) {
  clock_init();
  gpio_init();
  systick_init();
  uart3_init();
  controller_init();

  uart3_write_line("TARS_ENDER_STEPPER_READY");

  while (true) {
    controller_poll_uart();
    controller_refresh_watchdog();
    controller_step_axis(&g_controller.axis_1);
    controller_step_axis(&g_controller.axis_2);
    controller_publish_periodic_status();
  }
}
