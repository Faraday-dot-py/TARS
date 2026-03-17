"""ROS 2 node that confirms Jetson <-> Pico <-> Ender bridge connectivity."""

from __future__ import annotations

import time

import rclpy
from rclpy.node import Node
from std_msgs.msg import Bool, String

from .udp_bridge_client import UdpBridgeClient


class PicoEnderConnectionProbeNode(Node):
    """Periodically probes the current Pico bridge and Ender serial responder."""

    def __init__(self) -> None:
        super().__init__("pico_ender_connection_probe")

        self.declare_parameter("pico_host", "192.168.4.1")
        self.declare_parameter("command_port", 15120)
        self.declare_parameter("probe_period_s", 2.0)
        self.declare_parameter("response_timeout_s", 1.0)

        self._client = UdpBridgeClient(
            host=str(self.get_parameter("pico_host").value),
            port=int(self.get_parameter("command_port").value),
            timeout_s=float(self.get_parameter("response_timeout_s").value),
        )

        self._pico_pub = self.create_publisher(Bool, "probe/pico_connected", 10)
        self._ender_pub = self.create_publisher(Bool, "probe/ender_connected", 10)
        self._pico_response_pub = self.create_publisher(String, "probe/pico_response", 10)
        self._ender_response_pub = self.create_publisher(String, "probe/ender_response", 10)
        self._summary_pub = self.create_publisher(String, "probe/summary", 10)

        probe_period_s = float(self.get_parameter("probe_period_s").value)
        self.create_timer(probe_period_s, self._run_probe)

        self.get_logger().info(
            "Probing Pico bridge at "
            f"{self.get_parameter('pico_host').value}:{self.get_parameter('command_port').value}"
        )

    def _run_probe(self) -> None:
        started = time.monotonic()
        pico_result = self._client.ping()
        ender_result = self._client.marlin_info() if pico_result.success else None

        self._publish_bool(self._pico_pub, pico_result.success)
        self._publish_text(self._pico_response_pub, pico_result.response or pico_result.error)

        ender_success = bool(ender_result and ender_result.success)
        self._publish_bool(self._ender_pub, ender_success)
        self._publish_text(
            self._ender_response_pub,
            ""
            if ender_result is None
            else (ender_result.response or ender_result.error),
        )

        elapsed_ms = int((time.monotonic() - started) * 1000.0)
        if pico_result.success and ender_success:
            summary = (
                f"OK: Jetson reached Pico and Ender responded to M115 in {elapsed_ms} ms. "
                f"Ender said: {ender_result.response}"
            )
            self.get_logger().info(summary)
        elif pico_result.success:
            summary = (
                "PARTIAL: Pico responded to PING but Ender did not answer M115. "
                f"Detail: {ender_result.error if ender_result else 'probe not run'}"
            )
            self.get_logger().warning(summary)
        else:
            summary = f"DOWN: Pico did not answer PING. Detail: {pico_result.error}"
            self.get_logger().warning(summary)

        self._publish_text(self._summary_pub, summary)

    @staticmethod
    def _publish_bool(publisher, value: bool) -> None:
        msg = Bool()
        msg.data = bool(value)
        publisher.publish(msg)

    @staticmethod
    def _publish_text(publisher, value: str) -> None:
        msg = String()
        msg.data = value
        publisher.publish(msg)


def main(args=None) -> None:
    rclpy.init(args=args)
    node = PicoEnderConnectionProbeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()
