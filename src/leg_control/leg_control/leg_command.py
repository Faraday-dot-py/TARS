import json
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class LegCommand:
    """Transport-agnostic leg command semantics produced on the Jetson."""

    leg_id: str
    sequence: int
    host_time_ns: int
    enabled: bool
    safe_stop: bool
    velocity_target: float = 0.0
    turn_rate_target: float = 0.0
    stepper_1_target: Optional[float] = None
    stepper_2_target: Optional[float] = None
    servo_target: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), sort_keys=True)

    @classmethod
    def from_json(cls, data: str) -> "LegCommand":
        return cls(**json.loads(data))
