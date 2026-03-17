from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "leg_transport"))

from ender_stepper_transport import (
    EnderStepperCodec,
    StepperAxisCommand,
    StepperCommand,
    StepperFault,
    StepperMode,
    StepperStatus,
)


def test_stepper_command_round_trip_preserves_axis_targets() -> None:
    codec = EnderStepperCodec()
    frame = codec.encode_command(
        5,
        StepperCommand(
            enable=True,
            safe_stop=False,
            watchdog_timeout_ms=300,
            axis_1=StepperAxisCommand(mode=StepperMode.POSITION, target_steps=1200, max_step_rate_hz=8000),
            axis_2=StepperAxisCommand(mode=StepperMode.HOME_TO_LIMIT, homing_direction=-1, max_step_rate_hz=1500),
        ),
    )

    sequence, decoded = codec.decode_command(frame)
    assert sequence == 5
    assert decoded.enable is True
    assert decoded.safe_stop is False
    assert decoded.watchdog_timeout_ms == 300
    assert decoded.axis_1.target_steps == 1200
    assert decoded.axis_2.mode == StepperMode.HOME_TO_LIMIT
    assert decoded.axis_2.homing_direction == -1


def test_stepper_status_round_trip_preserves_fault_bits() -> None:
    codec = EnderStepperCodec()
    frame = codec.encode_status(
        8,
        StepperStatus(
            enabled=True,
            safe_stop=True,
            axis_1_state=StepperMode.HOLD,
            axis_2_state=StepperMode.POSITION,
            fault_bits=StepperFault.WATCHDOG_EXPIRED | StepperFault.DRIVER_FAULT,
            applied_sequence=7,
            axis_1_position_steps=44,
            axis_2_position_steps=-10,
        ),
    )

    sequence, decoded = codec.decode_status(frame)
    assert sequence == 8
    assert decoded.fault_bits == (StepperFault.WATCHDOG_EXPIRED | StepperFault.DRIVER_FAULT)
    assert decoded.axis_1_position_steps == 44
    assert decoded.axis_2_position_steps == -10
