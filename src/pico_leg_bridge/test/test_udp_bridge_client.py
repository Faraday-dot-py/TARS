from pathlib import Path
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from pico_leg_bridge.udp_bridge_client import UdpBridgeClient


def test_ping_and_marlin_info_succeed_against_udp_bridge() -> None:
    fake_socket = MagicMock()
    fake_socket.recvfrom.side_effect = [
        (b"PICO:PONG\n", ("127.0.0.1", 15120)),
        (b"FIRMWARE_NAME:Marlin 2.1.2\n", ("127.0.0.1", 15120)),
    ]
    fake_socket.__enter__.return_value = fake_socket

    with patch("socket.socket", return_value=fake_socket):
        client = UdpBridgeClient(host="127.0.0.1", port=15120, timeout_s=0.2)
        ping = client.ping()
        m115 = client.marlin_info()

    assert ping.success is True
    assert "PICO:PONG" in ping.response
    assert m115.success is True
    assert "FIRMWARE_NAME" in m115.response


def test_ping_reports_timeout() -> None:
    fake_socket = MagicMock()
    fake_socket.recvfrom.side_effect = TimeoutError()
    fake_socket.__enter__.return_value = fake_socket

    with patch("socket.socket", return_value=fake_socket):
        client = UdpBridgeClient(host="127.0.0.1", port=15120, timeout_s=0.05)
        result = client.ping()

    assert result.success is False
    assert "timeout" in result.error
