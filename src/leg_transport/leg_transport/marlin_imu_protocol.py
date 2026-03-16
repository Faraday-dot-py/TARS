import math
from typing import Dict, Optional

IMU_LINE_PREFIX = "TARS_IMU"



def build_imu_poll_command() -> str:
    return "M776"



def parse_imu_line(line: str) -> Optional[Dict[str, float]]:
    if not line.startswith(IMU_LINE_PREFIX + " "):
        return None

    parts = line.split()
    values: Dict[str, float] = {}
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, raw_value = part.split("=", 1)
        try:
            values[key] = float(raw_value)
        except ValueError:
            return None

    required = {"ax", "ay", "az", "gx", "gy", "gz", "roll", "pitch"}
    if not required.issubset(values.keys()):
        return None
    return values



def accel_g_to_m_s2(value_g: float) -> float:
    return float(value_g) * 9.80665



def gyro_dps_to_rad_s(value_dps: float) -> float:
    return float(value_dps) * math.pi / 180.0
