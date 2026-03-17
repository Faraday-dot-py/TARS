from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "leg_transport"))

from leg_transport import LegFault, LegTelemetry
from pico_leg_bridge.bridge_runtime import PicoLegBridgeRuntime
from pico_leg_bridge.protocol import JetsonPicoCodec


def test_runtime_marks_wireless_fault_when_telemetry_goes_stale() -> None:
    now = 0.0

    def monotonic() -> float:
        return now

    runtime = PicoLegBridgeRuntime("L0", telemetry_timeout_s=0.2, monotonic=monotonic)
    assert runtime.refresh_faults().fault_bits & LegFault.WIRELESS_LINK_LOSS

    codec = JetsonPicoCodec()
    frame = codec.encode_state(1, LegTelemetry(leg_id="L0", enabled=True))
    runtime.accept_frame(frame)
    assert not (runtime.refresh_faults().fault_bits & LegFault.WIRELESS_LINK_LOSS)

    now = 0.3
    assert runtime.refresh_faults().fault_bits & LegFault.WIRELESS_LINK_LOSS
