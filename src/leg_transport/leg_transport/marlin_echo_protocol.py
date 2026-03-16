from typing import Optional

ECHO_PREFIX = "TARS_ECHO:"



def encode_marlin_echo_command(payload: str) -> str:
    safe_payload = payload.replace("\r", " ").replace("\n", " ").strip()
    return f"M118 {ECHO_PREFIX}{safe_payload}"



def extract_echo_payload(line: str) -> Optional[str]:
    marker_index = line.find(ECHO_PREFIX)
    if marker_index < 0:
        return None
    return line[marker_index + len(ECHO_PREFIX):].strip()
