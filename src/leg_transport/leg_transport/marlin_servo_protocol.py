from typing import Optional

SERVO_ACK_PREFIX = "TARS_SERVO_SET:"



def normalize_servo_angle(angle_deg: float) -> float:
    return max(0.0, min(180.0, float(angle_deg)))



def encode_servo_command(angle_deg: float, servo_index: int = 0) -> str:
    normalized = normalize_servo_angle(angle_deg)
    return f"M280 P{int(servo_index)} S{int(round(normalized))}"



def encode_servo_ack_command(angle_deg: float) -> str:
    normalized = normalize_servo_angle(angle_deg)
    return f"M118 {SERVO_ACK_PREFIX}{normalized:.1f}"



def extract_servo_ack_angle(line: str) -> Optional[float]:
    marker_index = line.find(SERVO_ACK_PREFIX)
    if marker_index < 0:
        return None
    payload = line[marker_index + len(SERVO_ACK_PREFIX):].strip()
    try:
        return float(payload)
    except ValueError:
        return None
