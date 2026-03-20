import smbus2

class TCA9548A:
    def __init__(self, bus: int = 1, address: int = 0x70):
        self.bus = smbus2.SMBus(bus)
        self.address = address

    def select(self, channel: int):
        """Open one channel (0–7), close all others."""
        if not 0 <= channel <= 7:
            raise ValueError(f"Channel must be 0–7, got {channel}")
        self.bus.write_byte(self.address, 1 << channel)

    def close_all(self):
        """Disconnect all channels — good practice between reads."""
        self.bus.write_byte(self.address, 0x00)