TARGET := tars_ender_stepper_controller
BUILD_DIR := build
CC := arm-none-eabi-gcc
OBJCOPY := arm-none-eabi-objcopy
SIZE := arm-none-eabi-size

CFLAGS := -mcpu=cortex-m3 -mthumb -Os -ffreestanding -fdata-sections -ffunction-sections \
	-Wall -Wextra -Iinclude
LDFLAGS := -T linker.ld -nostartfiles -Wl,--gc-sections

SOURCES := src/startup.c src/main.c
OBJECTS := $(SOURCES:src/%.c=$(BUILD_DIR)/%.o)
ELF := $(BUILD_DIR)/$(TARGET).elf
BIN := $(BUILD_DIR)/$(TARGET).bin

.PHONY: all clean

all: $(BIN)

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: src/%.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(ELF): $(OBJECTS) linker.ld
	$(CC) $(CFLAGS) $(OBJECTS) $(LDFLAGS) -o $@
	$(SIZE) $@

$(BIN): $(ELF)
	$(OBJCOPY) -O binary $< $@

clean:
	rm -rf $(BUILD_DIR)
