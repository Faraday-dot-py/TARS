from leg_transport.protocol import ConfigKey
from leg_transport.protocol import HeartbeatPayload
from leg_transport.protocol import MessageType
from leg_transport.protocol import ProtocolFrame
from leg_transport.protocol import SetCommandPayload
from leg_transport.protocol import SetConfigPayload
from leg_transport.protocol import SetEnablePayload
from leg_transport.protocol import crc16_ccitt_false


def test_crc16_ccitt_false_known_vector():
    assert crc16_ccitt_false(b"123456789") == 0x29B1


def test_protocol_frame_round_trip():
    frame = ProtocolFrame(
        version=1,
        message_type=MessageType.SET_ENABLE,
        sequence=7,
        payload=SetEnablePayload(enabled=True).encode(),
    )

    encoded = frame.encode()
    decoded = ProtocolFrame.decode(encoded)

    assert decoded == frame


def test_set_command_payload_flags():
    payload = SetCommandPayload.from_optional_targets(
        host_time_ms=42,
        stepper_1_target=1.5,
        stepper_2_target=None,
        servo_target=90.0,
    )

    encoded = payload.encode()

    assert payload.command_flags == 0b101
    assert len(encoded) == SetCommandPayload.STRUCT.size


def test_set_config_payload_encodes_led_rate():
    payload = SetConfigPayload(
        config_key=ConfigKey.LED_BLINK_RATE_KHZ,
        value_u32=2,
    ).encode()

    assert payload == SetConfigPayload.STRUCT.pack(int(ConfigKey.LED_BLINK_RATE_KHZ), 2)


def test_heartbeat_payload_size():
    assert len(HeartbeatPayload(host_time_ms=1234).encode()) == HeartbeatPayload.STRUCT.size
