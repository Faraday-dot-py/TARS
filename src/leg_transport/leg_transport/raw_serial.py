import os
import select
import termios
from typing import List, Optional


class RawSerialTransport:
    """Minimal POSIX raw serial transport for ASCII line-based traffic."""

    def __init__(self, device_path: str, baudrate: int) -> None:
        self._device_path = device_path
        self._baudrate = baudrate
        self._fd: Optional[int] = None
        self._rx_buffer = bytearray()

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
        self._rx_buffer.clear()

    def close(self) -> None:
        if self._fd is None:
            return
        os.close(self._fd)
        self._fd = None
        self._rx_buffer.clear()

    def write_line(self, text: str) -> None:
        if self._fd is None:
            raise RuntimeError("Serial transport is not open")
        os.write(self._fd, text.encode("utf-8") + b"\n")

    def read_lines(self, timeout_s: float = 0.0) -> List[str]:
        if self._fd is None:
            raise RuntimeError("Serial transport is not open")

        readable, _, _ = select.select([self._fd], [], [], timeout_s)
        if readable:
            chunk = os.read(self._fd, 4096)
            if chunk:
                self._rx_buffer.extend(chunk)

        lines: List[str] = []
        while True:
            newline_index = self._rx_buffer.find(b"\n")
            if newline_index < 0:
                break
            raw_line = self._rx_buffer[:newline_index]
            del self._rx_buffer[:newline_index + 1]
            lines.append(raw_line.rstrip(b"\r").decode("utf-8", errors="replace"))
        return lines



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
