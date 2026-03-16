from leg_transport.marlin_echo_protocol import ECHO_PREFIX
from leg_transport.marlin_echo_protocol import encode_marlin_echo_command
from leg_transport.marlin_echo_protocol import extract_echo_payload



def test_encode_marlin_echo_command_strips_newlines() -> None:
    command = encode_marlin_echo_command("hello\nworld")
    assert command == f"M118 {ECHO_PREFIX}hello world"



def test_extract_echo_payload_from_plain_echo_line() -> None:
    payload = extract_echo_payload("echo:TARS_ECHO:roundtrip-ok")
    assert payload == "roundtrip-ok"



def test_extract_echo_payload_from_status_line() -> None:
    payload = extract_echo_payload("Recv: TARS_ECHO:board says hi")
    assert payload == "board says hi"



def test_extract_echo_payload_returns_none_without_marker() -> None:
    assert extract_echo_payload("echo:SD card ok") is None
