# carriage.py
# This is an update
from typing import Optional


class Carriage:
    """
    Placeholder carriage interface.

    Use this class from your main node as if it correctly drives either
    an active or fixed carriage, but do not implement hardware access here yet.
    """

    def __init__(self, kind: str) -> None:
        """
        kind: "active" or "fixed"
        """
        self.kind = kind

    def is_present(self) -> bool:
        """
        Return True if this carriage type exists on this node.
        Hardware-specific detection belongs here later.
        """
        raise NotImplementedError

    def set_goal_position(self, position: float) -> None:
        """
        Set the target position for the carriage.
        Units are up to you (meters, mm, steps), but be consistent.
        """
        raise NotImplementedError

    def update(self) -> None:
        """
        Periodic control update. Called by the stepper controller thread.
        """
        raise NotImplementedError

    def disable(self) -> None:
        """
        Immediately disable motion outputs for safety.
        """
        raise NotImplementedError