TARGET := tars_ender_stepper_controller
BUILD_DIR := build
ARCHIVE_ROOT := artifacts
BUILD_ID ?= $(shell date +%Y%m%d_%H%M%S)
ARCHIVE_DIR := $(ARCHIVE_ROOT)/$(BUILD_ID)
SHORT_ID := $(word 2,$(subst _, ,$(BUILD_ID)))
FLASH_BIN_NAME := FW$(SHORT_ID).bin
CC := arm-none-eabi-gcc
OBJCOPY := arm-none-eabi-objcopy
SIZE := arm-none-eabi-size

CFLAGS := -mcpu=cortex-m3 -mthumb -Os -ffreestanding -fdata-sections -ffunction-sections \
	-Wall -Wextra -Iinclude -DTARS_BUILD_ID=\"$(BUILD_ID)\" $(EXTRA_CFLAGS)
LDFLAGS := -T linker.ld -nostartfiles -Wl,--gc-sections

SOURCES := src/startup.c src/main.c
OBJECTS := $(SOURCES:src/%.c=$(BUILD_DIR)/%.o)
ELF := $(BUILD_DIR)/$(TARGET).elf
BIN := $(BUILD_DIR)/$(TARGET).bin
ARCHIVE_ELF := $(ARCHIVE_DIR)/$(TARGET)_$(BUILD_ID).elf
ARCHIVE_BIN := $(ARCHIVE_DIR)/$(TARGET)_$(BUILD_ID).bin
FLASH_BIN := $(ARCHIVE_DIR)/$(FLASH_BIN_NAME)
ARCHIVE_SHA := $(ARCHIVE_DIR)/SHA256SUMS.txt

.PHONY: all clean archive legacy

all: $(BIN) archive

legacy:
	$(MAKE) clean all BUILD_ID=$(BUILD_ID)_legacy EXTRA_CFLAGS='-DTARS_USE_TIM2_MICROS=0 -DTARS_STEP_PULSE_NOP_COUNT=1024'

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/%.o: src/%.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c $< -o $@

$(ELF): $(OBJECTS) linker.ld
	$(CC) $(CFLAGS) $(OBJECTS) $(LDFLAGS) -o $@
	$(SIZE) $@

$(BIN): $(ELF)
	$(OBJCOPY) -O binary $< $@

$(ARCHIVE_DIR):
	mkdir -p $(ARCHIVE_DIR)

$(ARCHIVE_ELF): $(ELF) | $(ARCHIVE_DIR)
	cp $< $@

$(ARCHIVE_BIN): $(BIN) | $(ARCHIVE_DIR)
	cp $< $@

$(FLASH_BIN): $(BIN) | $(ARCHIVE_DIR)
	cp $< $@

$(ARCHIVE_SHA): $(ARCHIVE_BIN) $(ARCHIVE_ELF) $(FLASH_BIN)
	sha256sum $(ARCHIVE_BIN) $(ARCHIVE_ELF) $(FLASH_BIN) > $@

archive: $(ARCHIVE_ELF) $(ARCHIVE_BIN) $(FLASH_BIN) $(ARCHIVE_SHA)
	@echo "Archived build to $(ARCHIVE_DIR)"
	@echo "Flash-ready image: $(FLASH_BIN)"

clean:
	rm -rf $(BUILD_DIR)
