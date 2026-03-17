"""Pure-Python bridge state handling for Jetson <-> Pico communication."""

from __future__ import annotations

import time

from leg_transport import (
    CalibrationAction,
    CommandLease,
    FusedOrientation,
    ImuSample,
    LegFault,
    LegTelemetry,
    WireCommand,
)

from .protocol import Heartbeat, JetsonPicoCodec, JetsonPicoMessageType


class PicoLegBridgeRuntime:
    """Owns the bridge command state and telemetry freshness."""

    def __init__(
        self,
        leg_id: str,
        telemetry_timeout_s: float = 0.5,
        monotonic=None,
    ) -> None:
        self.leg_id = leg_id
        self._codec = JetsonPicoCodec()
        self._monotonic = monotonic or time.monotonic
        self._telemetry_lease = CommandLease(monotonic=self._monotonic)
        self._telemetry_timeout_s = telemetry_timeout_s
        self._next_command_sequence = 1
        self._next_heartbeat_sequence = 1
        self._command = WireCommand(leg_id=leg_id)
        self.telemetry = LegTelemetry(leg_id=leg_id, fault_bits=LegFault.WIRELESS_LINK_LOSS)
        self.last_orientation = FusedOrientation()
        self.last_imu_samples: dict[int, ImuSample] = {}

    def set_enable(self, enabled: bool) -> None:
        self._command = WireCommand(
            leg_id=self.leg_id,
            enable=bool(enabled),
            safe_stop=self._command.safe_stop,
            servo_target_deg=self._command.servo_target_deg,
            body_velocity_hint=self._command.body_velocity_hint,
            body_turn_rate_hint=self._command.body_turn_rate_hint,
            calibration_action=self._command.calibration_action,
            command_ttl_ms=self._command.command_ttl_ms,
        )

    def set_safe_stop(self, safe_stop: bool) -> None:
        self._command = WireCommand(
            leg_id=self.leg_id,
            enable=self._command.enable,
            safe_stop=bool(safe_stop),
            servo_target_deg=self._command.servo_target_deg,
            body_velocity_hint=self._command.body_velocity_hint,
            body_turn_rate_hint=self._command.body_turn_rate_hint,
            calibration_action=self._command.calibration_action,
            command_ttl_ms=self._command.command_ttl_ms,
        )

    def set_servo_target(self, servo_target_deg: float) -> None:
        self._command = WireCommand(
            leg_id=self.leg_id,
            enable=self._command.enable,
            safe_stop=self._command.safe_stop,
            servo_target_deg=float(servo_target_deg),
            body_velocity_hint=self._command.body_velocity_hint,
            body_turn_rate_hint=self._command.body_turn_rate_hint,
            calibration_action=self._command.calibration_action,
            command_ttl_ms=self._command.command_ttl_ms,
        )

    def set_motion_hints(self, velocity: float | None = None, turn_rate: float | None = None) -> None:
        self._command = WireCommand(
            leg_id=self.leg_id,
            enable=self._command.enable,
            safe_stop=self._command.safe_stop,
            servo_target_deg=self._command.servo_target_deg,
            body_velocity_hint=self._command.body_velocity_hint if velocity is None else float(velocity),
            body_turn_rate_hint=self._command.body_turn_rate_hint if turn_rate is None else float(turn_rate),
            calibration_action=self._command.calibration_action,
            command_ttl_ms=self._command.command_ttl_ms,
        )

    def set_calibration_action(self, action: CalibrationAction) -> None:
        self._command = WireCommand(
            leg_id=self.leg_id,
            enable=self._command.enable,
            safe_stop=self._command.safe_stop,
            servo_target_deg=self._command.servo_target_deg,
            body_velocity_hint=self._command.body_velocity_hint,
            body_turn_rate_hint=self._command.body_turn_rate_hint,
            calibration_action=CalibrationAction(action),
            command_ttl_ms=self._command.command_ttl_ms,
        )

    def build_command_frame(self) -> tuple[int, bytes]:
        sequence = self._next_command_sequence
        self._next_command_sequence += 1
        return sequence, self._codec.encode_command(sequence, self._command)

    def build_heartbeat_frame(self, uptime_ms: int) -> tuple[int, bytes]:
        sequence = self._next_heartbeat_sequence
        self._next_heartbeat_sequence += 1
        heartbeat = Heartbeat(uptime_ms=uptime_ms, last_command_sequence=self.telemetry.last_command_sequence)
        return sequence, self._codec.encode_heartbeat(sequence, heartbeat)

    def accept_frame(self, frame: bytes) -> str:
        message = self._codec.decode_frame(frame)
        if message.message_type == int(JetsonPicoMessageType.LEG_STATE):
            _, telemetry = self._codec.decode_state(frame, leg_id=self.leg_id)
            fault_bits = LegFault(int(telemetry.fault_bits)) & ~LegFault.WIRELESS_LINK_LOSS
            self.telemetry = LegTelemetry(
                leg_id=self.leg_id,
                enabled=telemetry.enabled,
                calibration_state=telemetry.calibration_state,
                limit_switches=telemetry.limit_switches,
                fault_bits=fault_bits,
                servo_position_deg=telemetry.servo_position_deg,
                fused_orientation=self.last_orientation,
                last_command_sequence=telemetry.last_command_sequence,
                last_stepper_sequence=telemetry.last_stepper_sequence,
            )
            self._telemetry_lease.renew(self._telemetry_timeout_s)
            return "state"

        if message.message_type == int(JetsonPicoMessageType.FUSED_ORIENTATION):
            _, orientation = self._codec.decode_orientation(frame)
            self.last_orientation = orientation
            self.telemetry = LegTelemetry(
                leg_id=self.telemetry.leg_id,
                enabled=self.telemetry.enabled,
                calibration_state=self.telemetry.calibration_state,
                limit_switches=self.telemetry.limit_switches,
                fault_bits=self.telemetry.fault_bits,
                servo_position_deg=self.telemetry.servo_position_deg,
                fused_orientation=orientation,
                last_command_sequence=self.telemetry.last_command_sequence,
                last_stepper_sequence=self.telemetry.last_stepper_sequence,
            )
            self._telemetry_lease.renew(self._telemetry_timeout_s)
            return "orientation"

        if message.message_type == int(JetsonPicoMessageType.IMU_SAMPLE):
            _, indexed_sample = self._codec.decode_imu_sample(frame)
            self.last_imu_samples[indexed_sample.index] = indexed_sample.sample
            self._telemetry_lease.renew(self._telemetry_timeout_s)
            return "imu"

        if message.message_type == int(JetsonPicoMessageType.HEARTBEAT):
            self._telemetry_lease.renew(self._telemetry_timeout_s)
            return "heartbeat"

        raise ValueError(f"unsupported message type {message.message_type}")

    def refresh_faults(self) -> LegTelemetry:
        if self._telemetry_lease.expired():
            self.telemetry = LegTelemetry(
                leg_id=self.telemetry.leg_id,
                enabled=False,
                calibration_state=self.telemetry.calibration_state,
                limit_switches=self.telemetry.limit_switches,
                fault_bits=LegFault(int(self.telemetry.fault_bits)) | LegFault.WIRELESS_LINK_LOSS,
                servo_position_deg=self.telemetry.servo_position_deg,
                fused_orientation=self.last_orientation,
                last_command_sequence=self.telemetry.last_command_sequence,
                last_stepper_sequence=self.telemetry.last_stepper_sequence,
            )
        return self.telemetry
