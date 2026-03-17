from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from leg_transport import CommandLease


def test_command_lease_expires_after_deadline() -> None:
    now = 100.0

    def monotonic() -> float:
        return now

    lease = CommandLease(monotonic=monotonic)
    lease.renew(0.5)
    assert lease.expired() is False

    now = 100.6
    assert lease.expired() is True
