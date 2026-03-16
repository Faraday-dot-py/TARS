from leg_transport.marlin_imu_protocol import parse_imu_line
from leg_transport.marlin_servo_protocol import extract_servo_ack_angle


def test_combined_bridge_can_parse_servo_ack_lines() -> None:
    assert extract_servo_ack_angle("echo:TARS_SERVO_SET:45.0") == 45.0



def test_combined_bridge_can_parse_imu_lines() -> None:
    parsed = parse_imu_line(
        "TARS_IMU ax=0.00 ay=0.10 az=0.99 gx=1.0 gy=2.0 gz=3.0 roll=5.0 pitch=-6.0"
    )
    assert parsed is not None
    assert parsed["roll"] == 5.0
