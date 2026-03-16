CC := arm-none-eabi-gcc
OBJCOPY := arm-none-eabi-objcopy
CFLAGS := -mcpu=cortex-m4 -mthumb -ffreestanding -fdata-sections -ffunction-sections -Os -Wall -Wextra -Iinclude
LDFLAGS := -nostdlib -Wl,--gc-sections -Wl,-Map,build/tars_led_test.map -T embedded/linker_gd32f303ret6.ld

BUILD_DIR := build
TARGET_ELF := $(BUILD_DIR)/tars_led_test.elf
TARGET_BIN := $(BUILD_DIR)/tars_led_test.bin

SRCS := embedded/main_gd32f303ret6.c embedded/startup_gd32f303ret6.s
OBJS := $(BUILD_DIR)/main_gd32f303ret6.o $(BUILD_DIR)/startup_gd32f303ret6.o

all: $(TARGET_BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/main_gd32f303ret6.o: embedded/main_gd32f303ret6.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/startup_gd32f303ret6.o: embedded/startup_gd32f303ret6.s | $(BUILD_DIR)
	$(CC) -mcpu=cortex-m4 -mthumb -c $< -o $@

$(TARGET_ELF): $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) $(LDFLAGS) -lgcc -o $@

$(TARGET_BIN): $(TARGET_ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)

.PHONY: all clean
