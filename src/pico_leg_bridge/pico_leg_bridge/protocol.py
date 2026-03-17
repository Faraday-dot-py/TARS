"""Jetson <-> Pico W protocol definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import struct

from leg_transport import (
    CalibrationAction,
    CalibrationState,
    FrameCodec,
    FramedMessage,
    FusedOrientation,
    ImuSample,
    LegFault,
    LegTelemetry,
    LimitSwitchState,
    Vector3Sample,
    WireCommand,
)


class JetsonPicoMessageType(IntEnum):
    HEARTBEAT = 0x01
    LEG_COMMAND = 0x02
    LEG_STATE = 0x10
    IMU_SAMPLE = 0x11
    FUSED_ORIENTATION = 0x12


@dataclass(frozen=True)
class Heartbeat:
    uptime_ms: int
    last_command_sequence: int


@dataclass(frozen=True)
class IndexedImuSample:
    index: int
    sample: ImuSample


class JetsonPicoCodec:
    _COMMAND_STRUCT = struct.Struct("<BBBBfffH")
    _STATE_STRUCT = struct.Struct("<BBBBIIIf")
    _HEARTBEAT_STRUCT = struct.Struct("<II")
    _IMU_STRUCT = struct.Struct("<Bxxffffff")
    _ORIENTATION_STRUCT = struct.Struct("<ffff")

    def __init__(self) -> None:
        self._frame_codec = FrameCodec(b"\xA5\x5A", version=1)

    def encode_command(self, sequence: int, command: WireCommand) -> bytes:
        payload = self._COMMAND_STRUCT.pack(
            1 if command.enable else 0,
            1 if command.safe_stop else 0,
            int(command.calibration_action),
            0,
            float(command.servo_target_deg),
            float(command.body_velocity_hint),
            float(command.body_turn_rate_hint),
            int(command.command_ttl_ms),
        )
        return self._frame_codec.encode(JetsonPicoMessageType.LEG_COMMAND, sequence, payload)

    def decode_command(self, frame: bytes, leg_id: str = "") -> tuple[int, WireCommand]:
        message = self._require_type(self._frame_codec.decode(frame), JetsonPicoMessageType.LEG_COMMAND)
        enable, safe_stop, calibration_action, _, servo_target_deg, velocity_hint, turn_rate_hint, ttl_ms = self._COMMAND_STRUCT.unpack(message.payload)
        return message.sequence, WireCommand(
            leg_id=leg_id,
            enable=bool(enable),
            safe_stop=bool(safe_stop),
            servo_target_deg=servo_target_deg,
            body_velocity_hint=velocity_hint,
            body_turn_rate_hint=turn_rate_hint,
            calibration_action=CalibrationAction(calibration_action),
            command_ttl_ms=ttl_ms,
        )

    def encode_state(self, sequence: int, telemetry: LegTelemetry) -> bytes:
        payload = self._STATE_STRUCT.pack(
            1 if telemetry.enabled else 0,
            int(telemetry.calibration_state),
            telemetry.limit_switches.to_bits(),
            0,
            int(telemetry.fault_bits),
            int(telemetry.last_command_sequence),
            int(telemetry.last_stepper_sequence),
            float(telemetry.servo_position_deg),
        )
        return self._frame_codec.encode(JetsonPicoMessageType.LEG_STATE, sequence, payload)

    def decode_state(self, frame: bytes, leg_id: str = "") -> tuple[int, LegTelemetry]:
        message = self._require_type(self._frame_codec.decode(frame), JetsonPicoMessageType.LEG_STATE)
        enabled, calibration_state, limit_bits, _, fault_bits, last_command_sequence, last_stepper_sequence, servo_position_deg = self._STATE_STRUCT.unpack(message.payload)
        return message.sequence, LegTelemetry(
            leg_id=leg_id,
            enabled=bool(enabled),
            calibration_state=CalibrationState(calibration_state),
            limit_switches=LimitSwitchState.from_bits(limit_bits),
            fault_bits=LegFault(fault_bits),
            servo_position_deg=servo_position_deg,
            last_command_sequence=last_command_sequence,
            last_stepper_sequence=last_stepper_sequence,
        )

    def encode_heartbeat(self, sequence: int, heartbeat: Heartbeat) -> bytes:
        payload = self._HEARTBEAT_STRUCT.pack(int(heartbeat.uptime_ms), int(heartbeat.last_command_sequence))
        return self._frame_codec.encode(JetsonPicoMessageType.HEARTBEAT, sequence, payload)

    def decode_heartbeat(self, frame: bytes) -> tuple[int, Heartbeat]:
        message = self._require_type(self._frame_codec.decode(frame), JetsonPicoMessageType.HEARTBEAT)
        uptime_ms, last_command_sequence = self._HEARTBEAT_STRUCT.unpack(message.payload)
        return message.sequence, Heartbeat(uptime_ms=uptime_ms, last_command_sequence=last_command_sequence)

    def encode_imu_sample(self, sequence: int, sample: IndexedImuSample) -> bytes:
        payload = self._IMU_STRUCT.pack(
            int(sample.index),
            float(sample.sample.accel_g.x),
            float(sample.sample.accel_g.y),
            float(sample.sample.accel_g.z),
            float(sample.sample.gyro_dps.x),
            float(sample.sample.gyro_dps.y),
            float(sample.sample.gyro_dps.z),
        )
        return self._frame_codec.encode(JetsonPicoMessageType.IMU_SAMPLE, sequence, payload)

    def decode_imu_sample(self, frame: bytes) -> tuple[int, IndexedImuSample]:
        message = self._require_type(self._frame_codec.decode(frame), JetsonPicoMessageType.IMU_SAMPLE)
        index, ax, ay, az, gx, gy, gz = self._IMU_STRUCT.unpack(message.payload)
        return message.sequence, IndexedImuSample(
            index=index,
            sample=ImuSample(
                accel_g=Vector3Sample(ax, ay, az),
                gyro_dps=Vector3Sample(gx, gy, gz),
            ),
        )

    def encode_orientation(self, sequence: int, orientation: FusedOrientation) -> bytes:
        payload = self._ORIENTATION_STRUCT.pack(
            float(orientation.x),
            float(orientation.y),
            float(orientation.z),
            float(orientation.w),
        )
        return self._frame_codec.encode(JetsonPicoMessageType.FUSED_ORIENTATION, sequence, payload)

    def decode_orientation(self, frame: bytes) -> tuple[int, FusedOrientation]:
        message = self._require_type(self._frame_codec.decode(frame), JetsonPicoMessageType.FUSED_ORIENTATION)
        return message.sequence, FusedOrientation(*self._ORIENTATION_STRUCT.unpack(message.payload))

    def decode_frame(self, frame: bytes) -> FramedMessage:
        return self._frame_codec.decode(frame)

    @staticmethod
    def _require_type(message: FramedMessage, expected: JetsonPicoMessageType) -> FramedMessage:
        if message.message_type != int(expected):
            raise ValueError(f"expected message type {expected}, got {message.message_type}")
        return message
