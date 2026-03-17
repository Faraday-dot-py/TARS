from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "leg_transport"))

from leg_transport import CalibrationAction, LegFault, LegTelemetry, LimitSwitchState, WireCommand
from pico_leg_bridge.protocol import JetsonPicoCodec


def test_command_round_trip_preserves_calibration_and_watchdog_fields() -> None:
    codec = JetsonPicoCodec()
    frame = codec.encode_command(
        9,
        WireCommand(
            leg_id="L1",
            enable=True,
            safe_stop=False,
            servo_target_deg=123.0,
            body_velocity_hint=0.4,
            body_turn_rate_hint=-0.2,
            calibration_action=CalibrationAction.STARTUP_HOME,
            command_ttl_ms=180,
        ),
    )

    sequence, decoded = codec.decode_command(frame, leg_id="L1")
    assert sequence == 9
    assert decoded.enable is True
    assert decoded.safe_stop is False
    assert decoded.servo_target_deg == 123.0
    assert decoded.calibration_action == CalibrationAction.STARTUP_HOME
    assert decoded.command_ttl_ms == 180


def test_state_round_trip_preserves_faults_and_sequences() -> None:
    codec = JetsonPicoCodec()
    frame = codec.encode_state(
        12,
        LegTelemetry(
            leg_id="L2",
            enabled=True,
            limit_switches=LimitSwitchState(True, True),
            fault_bits=LegFault.CALIBRATION_FAULT | LegFault.ENDER_LINK_LOSS,
            servo_position_deg=75.0,
            last_command_sequence=11,
            last_stepper_sequence=7,
        ),
    )

    sequence, decoded = codec.decode_state(frame, leg_id="L2")
    assert sequence == 12
    assert decoded.enabled is True
    assert decoded.limit_switches == LimitSwitchState(True, True)
    assert decoded.fault_bits == (LegFault.CALIBRATION_FAULT | LegFault.ENDER_LINK_LOSS)
    assert decoded.last_command_sequence == 11
    assert decoded.last_stepper_sequence == 7
