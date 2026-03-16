from leg_transport.marlin_servo_protocol import SERVO_ACK_PREFIX
from leg_transport.marlin_servo_protocol import encode_servo_ack_command
from leg_transport.marlin_servo_protocol import encode_servo_command
from leg_transport.marlin_servo_protocol import extract_servo_ack_angle
from leg_transport.marlin_servo_protocol import normalize_servo_angle



def test_normalize_servo_angle_clamps_range() -> None:
    assert normalize_servo_angle(-5.0) == 0.0
    assert normalize_servo_angle(200.0) == 180.0



def test_encode_servo_command_rounds_to_integer_degrees() -> None:
    assert encode_servo_command(42.6, servo_index=0) == "M280 P0 S43"



def test_encode_servo_ack_command_contains_prefix() -> None:
    assert encode_servo_ack_command(90.0) == f"M118 {SERVO_ACK_PREFIX}90.0"



def test_extract_servo_ack_angle_returns_angle() -> None:
    assert extract_servo_ack_angle("echo:TARS_SERVO_SET:135.0") == 135.0



def test_extract_servo_ack_angle_returns_none_without_marker() -> None:
    assert extract_servo_ack_angle("ok") is None
