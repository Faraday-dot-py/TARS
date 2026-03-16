import struct
from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar, Optional


SOF = 0xA5
PROTOCOL_VERSION = 1
HEADER_STRUCT = struct.Struct("<BBBBH")
CRC_STRUCT = struct.Struct("<H")


class MessageType(IntEnum):
    SET_COMMAND = 1
    SET_ENABLE = 2
    SET_CONFIG = 3
    PING = 4
    TELEMETRY = 5
    FAULT = 6
    ACK = 7
    HEARTBEAT = 8
    SAFE_STOP = 9


class CommandField(IntEnum):
    STEPPER_1 = 1 << 0
    STEPPER_2 = 1 << 1
    SERVO = 1 << 2


class ConfigKey(IntEnum):
    LED_BLINK_STATE = 1
    LED_BLINK_RATE_KHZ = 2


@dataclass(frozen=True)
class ProtocolFrame:
    version: int
    message_type: MessageType
    sequence: int
    payload: bytes

    def encode(self) -> bytes:
        header = HEADER_STRUCT.pack(
            SOF,
            self.version,
            int(self.message_type),
            self.sequence & 0xFF,
            len(self.payload),
        )
        crc = crc16_ccitt_false(header[1:] + self.payload)
        return header + self.payload + CRC_STRUCT.pack(crc)

    @classmethod
    def decode(cls, data: bytes) -> "ProtocolFrame":
        min_size = HEADER_STRUCT.size + CRC_STRUCT.size
        if len(data) < min_size:
            raise ValueError("Frame too short")

        sof, version, message_type, sequence, payload_length = HEADER_STRUCT.unpack_from(data, 0)
        if sof != SOF:
            raise ValueError("Invalid start-of-frame marker")

        expected_size = HEADER_STRUCT.size + payload_length + CRC_STRUCT.size
        if len(data) != expected_size:
            raise ValueError("Frame length mismatch")

        payload = data[HEADER_STRUCT.size:HEADER_STRUCT.size + payload_length]
        expected_crc = CRC_STRUCT.unpack_from(data, HEADER_STRUCT.size + payload_length)[0]
        actual_crc = crc16_ccitt_false(data[1:HEADER_STRUCT.size] + payload)
        if actual_crc != expected_crc:
            raise ValueError("CRC mismatch")

        return cls(
            version=version,
            message_type=MessageType(message_type),
            sequence=sequence,
            payload=payload,
        )


def crc16_ccitt_false(data: bytes) -> int:
    crc = 0xFFFF
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


@dataclass(frozen=True)
class SetEnablePayload:
    enabled: bool

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<?")

    def encode(self) -> bytes:
        return self.STRUCT.pack(self.enabled)


@dataclass(frozen=True)
class SafeStopPayload:
    reason_code: int

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<B")

    def encode(self) -> bytes:
        return self.STRUCT.pack(self.reason_code & 0xFF)


@dataclass(frozen=True)
class HeartbeatPayload:
    host_time_ms: int

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<I")

    def encode(self) -> bytes:
        return self.STRUCT.pack(self.host_time_ms & 0xFFFFFFFF)


@dataclass(frozen=True)
class SetConfigPayload:
    config_key: int
    value_u32: int

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<BI")

    def encode(self) -> bytes:
        return self.STRUCT.pack(self.config_key & 0xFF, self.value_u32 & 0xFFFFFFFF)


@dataclass(frozen=True)
class SetCommandPayload:
    command_flags: int
    host_time_ms: int
    stepper_1_target: float
    stepper_2_target: float
    servo_target: float

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<BIfff")

    def encode(self) -> bytes:
        return self.STRUCT.pack(
            self.command_flags & 0xFF,
            self.host_time_ms & 0xFFFFFFFF,
            float(self.stepper_1_target),
            float(self.stepper_2_target),
            float(self.servo_target),
        )

    @classmethod
    def from_optional_targets(
        cls,
        host_time_ms: int,
        stepper_1_target: Optional[float],
        stepper_2_target: Optional[float],
        servo_target: Optional[float],
    ) -> "SetCommandPayload":
        flags = 0
        if stepper_1_target is not None:
            flags |= CommandField.STEPPER_1
        if stepper_2_target is not None:
            flags |= CommandField.STEPPER_2
        if servo_target is not None:
            flags |= CommandField.SERVO

        return cls(
            command_flags=flags,
            host_time_ms=host_time_ms,
            stepper_1_target=stepper_1_target if stepper_1_target is not None else 0.0,
            stepper_2_target=stepper_2_target if stepper_2_target is not None else 0.0,
            servo_target=servo_target if servo_target is not None else 0.0,
        )


@dataclass(frozen=True)
class TelemetryPayload:
    board_state: int
    fault_bits: int
    watchdog_state: int
    applied_sequence: int
    board_time_ms: int
    stepper_1_position: float
    stepper_2_position: float
    servo_position: float
    imu_1_ax: float
    imu_1_ay: float
    imu_1_az: float
    imu_2_ax: float
    imu_2_ay: float
    imu_2_az: float

    STRUCT: ClassVar[struct.Struct] = struct.Struct("<BBBBIfffffffff")

    @classmethod
    def decode(cls, payload: bytes) -> "TelemetryPayload":
        return cls(*cls.STRUCT.unpack(payload))
