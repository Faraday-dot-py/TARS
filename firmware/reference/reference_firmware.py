import struct
import time
from dataclasses import dataclass
from enum import IntEnum
from typing import Optional

SOF = 0xA5
PROTOCOL_VERSION = 1
HEADER_STRUCT = struct.Struct('<BBBBH')
CRC_STRUCT = struct.Struct('<H')


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


class BoardState(IntEnum):
    BOOT = 0
    DISABLED = 1
    ENABLED = 2
    SAFE_STOP = 3
    FAULT = 4


class WatchdogState(IntEnum):
    IDLE = 0
    ARMED = 1
    TRIPPED = 2


class SafeStopReason(IntEnum):
    NONE = 0
    DISABLED = 1
    WATCHDOG = 2
    FAULT = 3


@dataclass
class BoardOutputs:
    stepper_1_target: float = 0.0
    stepper_2_target: float = 0.0
    servo_target: float = 0.0


@dataclass
class BoardStatus:
    board_state: BoardState = BoardState.BOOT
    fault_bits: int = 0
    watchdog_state: WatchdogState = WatchdogState.IDLE
    applied_sequence: int = 0
    last_host_time_ms: int = 0
    last_command_rx_monotonic: float = 0.0
    safe_stop_reason: SafeStopReason = SafeStopReason.NONE


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
    def decode(cls, raw: bytes) -> 'ProtocolFrame':
        if len(raw) < HEADER_STRUCT.size + CRC_STRUCT.size:
            raise ValueError('frame too short')
        sof, version, message_type, sequence, payload_length = HEADER_STRUCT.unpack_from(raw, 0)
        if sof != SOF:
            raise ValueError('invalid sof')
        expected_size = HEADER_STRUCT.size + payload_length + CRC_STRUCT.size
        if len(raw) != expected_size:
            raise ValueError('frame length mismatch')
        payload = raw[HEADER_STRUCT.size:HEADER_STRUCT.size + payload_length]
        expected_crc = CRC_STRUCT.unpack_from(raw, HEADER_STRUCT.size + payload_length)[0]
        actual_crc = crc16_ccitt_false(raw[1:HEADER_STRUCT.size] + payload)
        if actual_crc != expected_crc:
            raise ValueError('crc mismatch')
        return cls(version, MessageType(message_type), sequence, payload)


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


class ReferenceLegFirmware:
    SET_ENABLE_STRUCT = struct.Struct('<?')
    SAFE_STOP_STRUCT = struct.Struct('<B')
    HEARTBEAT_STRUCT = struct.Struct('<I')
    SET_COMMAND_STRUCT = struct.Struct('<BIfff')
    TELEMETRY_STRUCT = struct.Struct('<BBBBIfffffffff')

    def __init__(self, watchdog_timeout_s: float = 0.25) -> None:
        self.watchdog_timeout_s = watchdog_timeout_s
        self.status = BoardStatus(board_state=BoardState.DISABLED)
        self.outputs = BoardOutputs()

    def process_frame(self, raw: bytes) -> Optional[bytes]:
        frame = ProtocolFrame.decode(raw)
        now = time.monotonic()

        if frame.message_type == MessageType.SET_ENABLE:
            (enabled,) = self.SET_ENABLE_STRUCT.unpack(frame.payload)
            self.status.applied_sequence = frame.sequence
            self.status.last_command_rx_monotonic = now
            self.status.watchdog_state = WatchdogState.ARMED
            self.status.safe_stop_reason = SafeStopReason.NONE if enabled else SafeStopReason.DISABLED
            self.status.board_state = BoardState.ENABLED if enabled else BoardState.DISABLED
            if not enabled:
                self._safe_stop(SafeStopReason.DISABLED)
            return self._encode_ack(frame.sequence)

        if frame.message_type == MessageType.SET_COMMAND:
            command_flags, host_time_ms, stepper_1_target, stepper_2_target, servo_target = self.SET_COMMAND_STRUCT.unpack(frame.payload)
            self.status.applied_sequence = frame.sequence
            self.status.last_host_time_ms = host_time_ms
            self.status.last_command_rx_monotonic = now
            self.status.watchdog_state = WatchdogState.ARMED
            if self.status.board_state != BoardState.ENABLED:
                return self._encode_fault(frame.sequence, fault_bits=0x01)
            if command_flags & 0x01:
                self.outputs.stepper_1_target = stepper_1_target
            if command_flags & 0x02:
                self.outputs.stepper_2_target = stepper_2_target
            if command_flags & 0x04:
                self.outputs.servo_target = servo_target
            return self._encode_ack(frame.sequence)

        if frame.message_type == MessageType.HEARTBEAT:
            (host_time_ms,) = self.HEARTBEAT_STRUCT.unpack(frame.payload)
            self.status.last_host_time_ms = host_time_ms
            self.status.last_command_rx_monotonic = now
            if self.status.board_state == BoardState.DISABLED:
                self.status.watchdog_state = WatchdogState.IDLE
            else:
                self.status.watchdog_state = WatchdogState.ARMED
            return self._encode_telemetry(frame.sequence)

        if frame.message_type == MessageType.SAFE_STOP:
            (reason_code,) = self.SAFE_STOP_STRUCT.unpack(frame.payload)
            self.status.applied_sequence = frame.sequence
            self._safe_stop(SafeStopReason(reason_code))
            return self._encode_ack(frame.sequence)

        return self._encode_fault(frame.sequence, fault_bits=0x80)

    def service_watchdog(self) -> None:
        if self.status.board_state not in (BoardState.ENABLED, BoardState.SAFE_STOP):
            return
        now = time.monotonic()
        age_s = now - self.status.last_command_rx_monotonic
        if age_s > self.watchdog_timeout_s:
            self.status.watchdog_state = WatchdogState.TRIPPED
            self._safe_stop(SafeStopReason.WATCHDOG)

    def _safe_stop(self, reason: SafeStopReason) -> None:
        self.outputs = BoardOutputs()
        self.status.board_state = BoardState.SAFE_STOP if reason != SafeStopReason.DISABLED else BoardState.DISABLED
        self.status.safe_stop_reason = reason

    def _encode_ack(self, sequence: int) -> bytes:
        return ProtocolFrame(PROTOCOL_VERSION, MessageType.ACK, sequence, b'').encode()

    def _encode_fault(self, sequence: int, fault_bits: int) -> bytes:
        self.status.board_state = BoardState.FAULT
        self.status.fault_bits |= fault_bits
        payload = bytes([self.status.fault_bits])
        return ProtocolFrame(PROTOCOL_VERSION, MessageType.FAULT, sequence, payload).encode()

    def _encode_telemetry(self, sequence: int) -> bytes:
        board_time_ms = int(time.monotonic() * 1000) & 0xFFFFFFFF
        payload = self.TELEMETRY_STRUCT.pack(
            int(self.status.board_state),
            self.status.fault_bits & 0xFF,
            int(self.status.watchdog_state),
            self.status.applied_sequence & 0xFF,
            board_time_ms,
            self.outputs.stepper_1_target,
            self.outputs.stepper_2_target,
            self.outputs.servo_target,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
            0.0,
        )
        return ProtocolFrame(PROTOCOL_VERSION, MessageType.TELEMETRY, sequence, payload).encode()
