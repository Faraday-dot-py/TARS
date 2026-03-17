"""Generic binary frame encoding and decoding."""

from __future__ import annotations

from dataclasses import dataclass
import struct

from .crc import crc16_ccitt


@dataclass(frozen=True)
class FramedMessage:
    version: int
    message_type: int
    sequence: int
    payload: bytes


class FrameError(ValueError):
    """Raised when a frame fails validation."""


class FrameCodec:
    """Codec for compact embedded-friendly frames with CRC16."""

    _HEADER_STRUCT = struct.Struct("<2sBBIH")
    _CRC_STRUCT = struct.Struct("<H")

    def __init__(self, start_of_frame: bytes, version: int = 1) -> None:
        if len(start_of_frame) != 2:
            raise ValueError("start_of_frame must be exactly 2 bytes")
        self._start_of_frame = start_of_frame
        self._version = int(version)

    @property
    def version(self) -> int:
        return self._version

    def encode(self, message_type: int, sequence: int, payload: bytes) -> bytes:
        if not 0 <= int(message_type) <= 0xFF:
            raise ValueError("message_type must fit in uint8")
        if not 0 <= int(sequence) <= 0xFFFFFFFF:
            raise ValueError("sequence must fit in uint32")
        if len(payload) > 0xFFFF:
            raise ValueError("payload is too large for uint16 length")

        header = self._HEADER_STRUCT.pack(
            self._start_of_frame,
            self._version,
            int(message_type),
            int(sequence),
            len(payload),
        )
        crc_input = header[2:] + payload
        crc = self._CRC_STRUCT.pack(crc16_ccitt(crc_input))
        return header + payload + crc

    def decode(self, frame: bytes) -> FramedMessage:
        minimum_size = self._HEADER_STRUCT.size + self._CRC_STRUCT.size
        if len(frame) < minimum_size:
            raise FrameError("frame is shorter than the minimum header + CRC")

        sof, version, message_type, sequence, payload_length = self._HEADER_STRUCT.unpack_from(frame, 0)
        if sof != self._start_of_frame:
            raise FrameError("unexpected start-of-frame marker")
        if version != self._version:
            raise FrameError(f"unsupported frame version {version}")

        expected_size = minimum_size + payload_length
        if len(frame) != expected_size:
            raise FrameError("frame length does not match payload length")

        payload_start = self._HEADER_STRUCT.size
        payload_end = payload_start + payload_length
        payload = frame[payload_start:payload_end]
        expected_crc = self._CRC_STRUCT.unpack_from(frame, payload_end)[0]
        actual_crc = crc16_ccitt(frame[2:payload_end])
        if actual_crc != expected_crc:
            raise FrameError("CRC mismatch")

        return FramedMessage(
            version=version,
            message_type=message_type,
            sequence=sequence,
            payload=payload,
        )
