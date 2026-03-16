#include <stddef.h>
#include <stdint.h>

#define REG32(addr) (*(volatile uint32_t *)(addr))

#define RCU_BASE             0x40021000u
#define GPIOA_BASE           0x40010800u
#define GPIOB_BASE           0x40010C00u
#define GPIOC_BASE           0x40011000u
#define USART1_BASE          0x40013800u
#define USART2_BASE          0x40004400u
#define USART3_BASE          0x40004800u
#define UART4_BASE           0x40004C00u

#define RCU_APB1EN           REG32(RCU_BASE + 0x1Cu)
#define RCU_APB2EN           REG32(RCU_BASE + 0x18u)
#define GPIOA_CTL0           REG32(GPIOA_BASE + 0x00u)
#define GPIOA_CTL1           REG32(GPIOA_BASE + 0x04u)
#define GPIOB_CTL1           REG32(GPIOB_BASE + 0x04u)
#define GPIOC_CTL1           REG32(GPIOC_BASE + 0x04u)

#define RCU_APB2EN_AFEN      (1u << 0)
#define RCU_APB2EN_PAEN      (1u << 2)
#define RCU_APB2EN_PBEN      (1u << 3)
#define RCU_APB2EN_PCEN      (1u << 4)
#define RCU_APB2EN_USART1EN  (1u << 14)
#define RCU_APB1EN_USART2EN  (1u << 17)
#define RCU_APB1EN_USART3EN  (1u << 18)
#define RCU_APB1EN_UART4EN   (1u << 19)

#define USART_STAT_TBE       (1u << 7)
#define USART_CTL0_UEN       (1u << 13)
#define USART_CTL0_TEN       (1u << 3)
#define USART_CTL0_REN       (1u << 2)

struct UartPort {
    volatile uint32_t *stat;
    volatile uint32_t *data;
    volatile uint32_t *baud;
    volatile uint32_t *ctl0;
    volatile uint32_t *ctl1;
    volatile uint32_t *ctl2;
};

static struct UartPort g_ports[] = {
    {
        (volatile uint32_t *)(USART1_BASE + 0x00u),
        (volatile uint32_t *)(USART1_BASE + 0x04u),
        (volatile uint32_t *)(USART1_BASE + 0x08u),
        (volatile uint32_t *)(USART1_BASE + 0x0Cu),
        (volatile uint32_t *)(USART1_BASE + 0x10u),
        (volatile uint32_t *)(USART1_BASE + 0x14u),
    },
    {
        (volatile uint32_t *)(USART2_BASE + 0x00u),
        (volatile uint32_t *)(USART2_BASE + 0x04u),
        (volatile uint32_t *)(USART2_BASE + 0x08u),
        (volatile uint32_t *)(USART2_BASE + 0x0Cu),
        (volatile uint32_t *)(USART2_BASE + 0x10u),
        (volatile uint32_t *)(USART2_BASE + 0x14u),
    },
    {
        (volatile uint32_t *)(USART3_BASE + 0x00u),
        (volatile uint32_t *)(USART3_BASE + 0x04u),
        (volatile uint32_t *)(USART3_BASE + 0x08u),
        (volatile uint32_t *)(USART3_BASE + 0x0Cu),
        (volatile uint32_t *)(USART3_BASE + 0x10u),
        (volatile uint32_t *)(USART3_BASE + 0x14u),
    },
    {
        (volatile uint32_t *)(UART4_BASE + 0x00u),
        (volatile uint32_t *)(UART4_BASE + 0x04u),
        (volatile uint32_t *)(UART4_BASE + 0x08u),
        (volatile uint32_t *)(UART4_BASE + 0x0Cu),
        (volatile uint32_t *)(UART4_BASE + 0x10u),
        (volatile uint32_t *)(UART4_BASE + 0x14u),
    },
};

void SysTick_Handler(void) {
}

static void delay_cycles(volatile uint32_t cycles) {
    while (cycles-- != 0u) {
        __asm__ volatile ("nop");
    }
}

static void configure_tx_rx_pins(void) {
    RCU_APB2EN |= RCU_APB2EN_AFEN | RCU_APB2EN_PAEN | RCU_APB2EN_PBEN | RCU_APB2EN_PCEN;

    GPIOA_CTL1 &= ~(0xFu << 4);
    GPIOA_CTL1 |=  (0xBu << 4);
    GPIOA_CTL1 &= ~(0xFu << 8);
    GPIOA_CTL1 |=  (0x4u << 8);

    GPIOA_CTL0 &= ~(0xFu << 8);
    GPIOA_CTL0 |=  (0xBu << 8);
    GPIOA_CTL0 &= ~(0xFu << 12);
    GPIOA_CTL0 |=  (0x4u << 12);

    GPIOB_CTL1 &= ~(0xFu << 8);
    GPIOB_CTL1 |=  (0xBu << 8);
    GPIOB_CTL1 &= ~(0xFu << 12);
    GPIOB_CTL1 |=  (0x4u << 12);

    GPIOC_CTL1 &= ~(0xFu << 12);
    GPIOC_CTL1 |=  (0xBu << 12);
    GPIOC_CTL1 &= ~(0xFu << 8);
    GPIOC_CTL1 |=  (0x4u << 8);
}

static void init_ports(void) {
    size_t i = 0u;

    RCU_APB2EN |= RCU_APB2EN_USART1EN;
    RCU_APB1EN |= RCU_APB1EN_USART2EN | RCU_APB1EN_USART3EN | RCU_APB1EN_UART4EN;

    for (i = 0u; i < (sizeof(g_ports) / sizeof(g_ports[0])); ++i) {
        *(g_ports[i].baud) = 625u;
        *(g_ports[i].ctl0) = USART_CTL0_UEN | USART_CTL0_TEN | USART_CTL0_REN;
        *(g_ports[i].ctl1) = 0u;
        *(g_ports[i].ctl2) = 0u;
    }
}

static void write_byte(struct UartPort *port, uint8_t byte) {
    while ((*(port->stat) & USART_STAT_TBE) == 0u) {
    }
    *(port->data) = byte;
}

static void write_cstr_all(const char *text) {
    size_t i = 0u;

    while (*text != '\0') {
        for (i = 0u; i < (sizeof(g_ports) / sizeof(g_ports[0])); ++i) {
            write_byte(&g_ports[i], (uint8_t)(*text));
        }
        ++text;
    }
}

int main(void) {
    configure_tx_rx_pins();
    init_ports();

    while (1) {
        write_cstr_all("TARS_UART_SCAN GD32F303RET6\\r\\n");
        delay_cycles(1200000u);
    }
}
