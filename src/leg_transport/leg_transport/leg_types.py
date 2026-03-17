"""Transport-agnostic leg command and telemetry models."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum, IntFlag


class CalibrationAction(IntEnum):
    NONE = 0
    STARTUP_HOME = 1
    CLEAR_FAULTS = 2
    ABORT = 3


class CalibrationState(IntEnum):
    UNKNOWN = 0
    IDLE = 1
    WAITING_FOR_ENABLE = 2
    HOMING_STEPPER_1 = 3
    HOMING_STEPPER_2 = 4
    VERIFYING = 5
    COMPLETE = 6
    FAULT = 7


class LegFault(IntFlag):
    NONE = 0
    STALE_COMMAND = 1 << 0
    SAFE_STOP_ACTIVE = 1 << 1
    WIRELESS_LINK_LOSS = 1 << 2
    ENDER_LINK_LOSS = 1 << 3
    IMU_SAMPLE_TIMEOUT = 1 << 4
    IMU_FUSION_FAULT = 1 << 5
    LIMIT_SWITCH_FAULT = 1 << 6
    CALIBRATION_FAULT = 1 << 7
    STEPPER_DRIVER_FAULT = 1 << 8


@dataclass(frozen=True)
class Vector3Sample:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass(frozen=True)
class ImuSample:
    accel_g: Vector3Sample = field(default_factory=Vector3Sample)
    gyro_dps: Vector3Sample = field(default_factory=Vector3Sample)


@dataclass(frozen=True)
class FusedOrientation:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0


@dataclass(frozen=True)
class LimitSwitchState:
    stepper_1_triggered: bool = False
    stepper_2_triggered: bool = False

    def to_bits(self) -> int:
        return (1 if self.stepper_1_triggered else 0) | ((1 if self.stepper_2_triggered else 0) << 1)

    @classmethod
    def from_bits(cls, bits: int) -> "LimitSwitchState":
        return cls(
            stepper_1_triggered=bool(bits & 0x01),
            stepper_2_triggered=bool(bits & 0x02),
        )


@dataclass(frozen=True)
class WireCommand:
    leg_id: str
    enable: bool = False
    safe_stop: bool = True
    servo_target_deg: float = 90.0
    body_velocity_hint: float = 0.0
    body_turn_rate_hint: float = 0.0
    calibration_action: CalibrationAction = CalibrationAction.NONE
    command_ttl_ms: int = 250


@dataclass(frozen=True)
class LegTelemetry:
    leg_id: str
    enabled: bool = False
    calibration_state: CalibrationState = CalibrationState.UNKNOWN
    limit_switches: LimitSwitchState = field(default_factory=LimitSwitchState)
    fault_bits: LegFault = LegFault.NONE
    servo_position_deg: float = 0.0
    fused_orientation: FusedOrientation = field(default_factory=FusedOrientation)
    last_command_sequence: int = 0
    last_stepper_sequence: int = 0
