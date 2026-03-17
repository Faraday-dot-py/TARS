"""CRC helpers for compact framed transport links."""


def crc16_ccitt(data: bytes, seed: int = 0xFFFF) -> int:
    """Return the CRC-16/CCITT-FALSE checksum for *data*."""
    crc = seed
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc
