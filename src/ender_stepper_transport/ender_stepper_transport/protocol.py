"""Pico <-> Ender compact binary protocol definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, IntFlag
import struct

from leg_transport import FrameCodec, FramedMessage


class EnderStepperMessageType(IntEnum):
    HEARTBEAT = 0x01
    STEPPER_COMMAND = 0x02
    STEPPER_STATUS = 0x10


class StepperMode(IntEnum):
    DISABLED = 0
    POSITION = 1
    HOLD = 2
    HOME_TO_LIMIT = 3


class StepperFault(IntFlag):
    NONE = 0
    WATCHDOG_EXPIRED = 1 << 0
    INVALID_COMMAND = 1 << 1
    DRIVER_FAULT = 1 << 2
    AXIS_1_STALL = 1 << 3
    AXIS_2_STALL = 1 << 4
    CRC_ERROR = 1 << 5


@dataclass(frozen=True)
class StepperAxisCommand:
    mode: StepperMode = StepperMode.DISABLED
    homing_direction: int = 0
    target_steps: int = 0
    max_step_rate_hz: int = 0


@dataclass(frozen=True)
class StepperCommand:
    enable: bool = False
    safe_stop: bool = True
    watchdog_timeout_ms: int = 250
    axis_1: StepperAxisCommand = StepperAxisCommand()
    axis_2: StepperAxisCommand = StepperAxisCommand()


@dataclass(frozen=True)
class StepperStatus:
    enabled: bool = False
    safe_stop: bool = True
    axis_1_state: StepperMode = StepperMode.DISABLED
    axis_2_state: StepperMode = StepperMode.DISABLED
    fault_bits: StepperFault = StepperFault.NONE
    applied_sequence: int = 0
    axis_1_position_steps: int = 0
    axis_2_position_steps: int = 0


class EnderStepperCodec:
    _GLOBAL_COMMAND_STRUCT = struct.Struct("<BBHH")
    _AXIS_COMMAND_STRUCT = struct.Struct("<BbHiI")
    _STATUS_STRUCT = struct.Struct("<BBBBIIii")

    def __init__(self) -> None:
        self._frame_codec = FrameCodec(b"\xC3\x3C", version=1)

    def encode_command(self, sequence: int, command: StepperCommand) -> bytes:
        payload = self._GLOBAL_COMMAND_STRUCT.pack(
            1 if command.enable else 0,
            1 if command.safe_stop else 0,
            int(command.watchdog_timeout_ms),
            0,
        )
        payload += self._pack_axis(command.axis_1)
        payload += self._pack_axis(command.axis_2)
        return self._frame_codec.encode(EnderStepperMessageType.STEPPER_COMMAND, sequence, payload)

    def decode_command(self, frame: bytes) -> tuple[int, StepperCommand]:
        message = self._require_type(self._frame_codec.decode(frame), EnderStepperMessageType.STEPPER_COMMAND)
        offset = 0
        enable, safe_stop, watchdog_timeout_ms, _ = self._GLOBAL_COMMAND_STRUCT.unpack_from(message.payload, offset)
        offset += self._GLOBAL_COMMAND_STRUCT.size
        axis_1 = self._unpack_axis(message.payload, offset)
        offset += self._AXIS_COMMAND_STRUCT.size
        axis_2 = self._unpack_axis(message.payload, offset)
        return message.sequence, StepperCommand(
            enable=bool(enable),
            safe_stop=bool(safe_stop),
            watchdog_timeout_ms=watchdog_timeout_ms,
            axis_1=axis_1,
            axis_2=axis_2,
        )

    def encode_status(self, sequence: int, status: StepperStatus) -> bytes:
        payload = self._STATUS_STRUCT.pack(
            1 if status.enabled else 0,
            1 if status.safe_stop else 0,
            int(status.axis_1_state),
            int(status.axis_2_state),
            int(status.fault_bits),
            int(status.applied_sequence),
            int(status.axis_1_position_steps),
            int(status.axis_2_position_steps),
        )
        return self._frame_codec.encode(EnderStepperMessageType.STEPPER_STATUS, sequence, payload)

    def decode_status(self, frame: bytes) -> tuple[int, StepperStatus]:
        message = self._require_type(self._frame_codec.decode(frame), EnderStepperMessageType.STEPPER_STATUS)
        enabled, safe_stop, axis_1_state, axis_2_state, fault_bits, applied_sequence, axis_1_position, axis_2_position = self._STATUS_STRUCT.unpack(message.payload)
        return message.sequence, StepperStatus(
            enabled=bool(enabled),
            safe_stop=bool(safe_stop),
            axis_1_state=StepperMode(axis_1_state),
            axis_2_state=StepperMode(axis_2_state),
            fault_bits=StepperFault(fault_bits),
            applied_sequence=applied_sequence,
            axis_1_position_steps=axis_1_position,
            axis_2_position_steps=axis_2_position,
        )

    def decode_frame(self, frame: bytes) -> FramedMessage:
        return self._frame_codec.decode(frame)

    def _pack_axis(self, axis: StepperAxisCommand) -> bytes:
        return self._AXIS_COMMAND_STRUCT.pack(
            int(axis.mode),
            int(axis.homing_direction),
            0,
            int(axis.target_steps),
            int(axis.max_step_rate_hz),
        )

    def _unpack_axis(self, payload: bytes, offset: int) -> StepperAxisCommand:
        mode, homing_direction, _, target_steps, max_step_rate_hz = self._AXIS_COMMAND_STRUCT.unpack_from(payload, offset)
        return StepperAxisCommand(
            mode=StepperMode(mode),
            homing_direction=homing_direction,
            target_steps=target_steps,
            max_step_rate_hz=max_step_rate_hz,
        )

    @staticmethod
    def _require_type(message: FramedMessage, expected: EnderStepperMessageType) -> FramedMessage:
        if message.message_type != int(expected):
            raise ValueError(f"expected message type {expected}, got {message.message_type}")
        return message
