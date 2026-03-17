from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from leg_transport import LimitSwitchState


def test_limit_switch_bits_round_trip() -> None:
    state = LimitSwitchState(stepper_1_triggered=True, stepper_2_triggered=False)
    assert state.to_bits() == 0x01
    assert LimitSwitchState.from_bits(state.to_bits()) == state
