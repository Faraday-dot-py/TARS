from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from leg_transport import FrameCodec, FrameError


def test_frame_round_trip_preserves_message() -> None:
    codec = FrameCodec(b"\xA5\x5A", version=1)

    frame = codec.encode(message_type=2, sequence=42, payload=b"\x01\x02\x03")
    decoded = codec.decode(frame)

    assert decoded.version == 1
    assert decoded.message_type == 2
    assert decoded.sequence == 42
    assert decoded.payload == b"\x01\x02\x03"


def test_frame_decode_rejects_crc_mismatch() -> None:
    codec = FrameCodec(b"\xC3\x3C", version=1)
    frame = bytearray(codec.encode(message_type=7, sequence=3, payload=b"payload"))
    frame[-1] ^= 0xFF

    with pytest.raises(FrameError):
        codec.decode(bytes(frame))
