import os
import select
import termios
from typing import Optional

from leg_transport.protocol import ProtocolFrame


class SerialLegTransport:
    """Minimal POSIX serial transport using only the standard library."""

    def __init__(self, device_path: str, baudrate: int) -> None:
        self._device_path = device_path
        self._baudrate = baudrate
        self._fd: Optional[int] = None

    @property
    def is_open(self) -> bool:
        return self._fd is not None

    def open(self) -> None:
        if self._fd is not None:
            return

        self._fd = os.open(self._device_path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attrs = termios.tcgetattr(self._fd)
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL
        attrs[3] = 0
        attrs[4] = _baudrate_to_termios(self._baudrate)
        attrs[5] = _baudrate_to_termios(self._baudrate)
        attrs[6][termios.VMIN] = 0
        attrs[6][termios.VTIME] = 0
        termios.tcsetattr(self._fd, termios.TCSANOW, attrs)

    def close(self) -> None:
        if self._fd is None:
            return
        os.close(self._fd)
        self._fd = None

    def send_frame(self, frame: ProtocolFrame) -> None:
        if self._fd is None:
            raise RuntimeError("Serial transport is not open")
        os.write(self._fd, frame.encode())

    def read_frame(self, timeout_s: float = 0.0) -> Optional[ProtocolFrame]:
        if self._fd is None:
            raise RuntimeError("Serial transport is not open")

        readable, _, _ = select.select([self._fd], [], [], timeout_s)
        if not readable:
            return None

        header = os.read(self._fd, 6)
        if len(header) < 6:
            return None

        payload_length = int.from_bytes(header[4:6], byteorder="little", signed=False)
        payload_and_crc = os.read(self._fd, payload_length + 2)
        if len(payload_and_crc) < payload_length + 2:
            return None

        return ProtocolFrame.decode(header + payload_and_crc)


def _baudrate_to_termios(baudrate: int) -> int:
    mapping = {
        9600: termios.B9600,
        19200: termios.B19200,
        38400: termios.B38400,
        57600: termios.B57600,
        115200: termios.B115200,
        230400: termios.B230400,
    }
    try:
        return mapping[baudrate]
    except KeyError as exc:
        raise ValueError(f"Unsupported baudrate: {baudrate}") from exc
