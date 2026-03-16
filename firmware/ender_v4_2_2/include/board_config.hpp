#ifndef TARS_BOARD_CONFIG_HPP
#define TARS_BOARD_CONFIG_HPP

/*
 * Provisional board configuration for the first LED serial test.
 *
 * Validated from direct hardware inspection:
 * - MCU: GD32F303RET6
 *
 * Inference / engineering judgment:
 * - USART1 on PA9/PA10 is the host serial path used through the CH340 bridge.
 * - Flash image should target the Creality bootloader offset at 0x08007000.
 * - LED pin below is provisional and must be treated as unverified until a real blink is observed.
 */

#define TARS_PROVISIONAL_LED_GPIO_PORT 'C'
#define TARS_PROVISIONAL_LED_PIN 13
#define TARS_HOST_USART_BAUD 115200
#define TARS_FLASH_ORIGIN 0x08007000

#endif
