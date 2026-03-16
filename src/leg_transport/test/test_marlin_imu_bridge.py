from leg_transport.marlin_imu_protocol import accel_g_to_m_s2
from leg_transport.marlin_imu_protocol import build_imu_poll_command
from leg_transport.marlin_imu_protocol import gyro_dps_to_rad_s
from leg_transport.marlin_imu_protocol import parse_imu_line



def test_build_imu_poll_command() -> None:
    assert build_imu_poll_command() == "M776"



def test_parse_imu_line_returns_values() -> None:
    parsed = parse_imu_line(
        "TARS_IMU ax=0.10 ay=-0.20 az=0.98 gx=1.0 gy=2.0 gz=3.0 roll=4.0 pitch=5.0"
    )
    assert parsed is not None
    assert parsed["az"] == 0.98
    assert parsed["pitch"] == 5.0



def test_parse_imu_line_rejects_incomplete_payload() -> None:
    assert parse_imu_line("TARS_IMU ax=0.1 ay=0.2") is None



def test_unit_conversions() -> None:
    assert round(accel_g_to_m_s2(1.0), 5) == 9.80665
    assert round(gyro_dps_to_rad_s(180.0), 5) == 3.14159
