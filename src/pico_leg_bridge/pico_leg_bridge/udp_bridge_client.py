"""Helpers for probing the temporary Pico UDP/UART bridge."""

from __future__ import annotations

from dataclasses import dataclass
import socket


@dataclass(frozen=True)
class ProbeResult:
    success: bool
    response: str
    error: str = ""


class UdpBridgeClient:
    """Small blocking client for the current Pico UDP bridge demo."""

    def __init__(self, host: str, port: int, timeout_s: float = 1.0) -> None:
        self._host = host
        self._port = int(port)
        self._timeout_s = float(timeout_s)

    def ping(self) -> ProbeResult:
        return self._exchange("PING", expected_substring="PICO:PONG")

    def marlin_info(self) -> ProbeResult:
        return self._exchange("M115", expected_substring="FIRMWARE_NAME")

    def _exchange(self, message: str, expected_substring: str) -> ProbeResult:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.settimeout(self._timeout_s)
                sock.sendto(message.encode("utf-8"), (self._host, self._port))
                data, _ = sock.recvfrom(2048)
        except TimeoutError:
            return ProbeResult(success=False, response="", error=f"timeout waiting for {message} response")
        except OSError as exc:
            return ProbeResult(success=False, response="", error=str(exc))

        response = data.decode("utf-8", errors="replace").strip()
        return ProbeResult(
            success=expected_substring in response,
            response=response,
            error="" if expected_substring in response else f"unexpected response to {message}: {response}",
        )
