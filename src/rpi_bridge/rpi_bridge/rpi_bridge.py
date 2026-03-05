#!/usr/bin/env python3
import json
import socket
import threading
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Vector3
from std_msgs.msg import Bool
from std_msgs.msg import Float32MultiArray
from std_msgs.msg import Float32

# Hard-coded network config
ZERO_IP = "10.42.0.47"       # set to your Pi Zero W IP
ZERO_CMD_PORT = 15120          # Zero listens here for commands

JETSON_BIND_IP = "0.0.0.0"
JETSON_TELEM_PORT = 15121      # Jetson listens here for telemetry

LEG_ID = 1

def monotonic_s() -> float:
    return time.monotonic()

class RpiBridge(Node):
    def __init__(self):
        super().__init__("leg_bridge_leg1")

        # ROS interfaces
        # Command message: Float32MultiArray: [enable, hip, knee, ankle]
        # self.cmd_sub = self.create_subscription(
        #     Float32MultiArray,
        #     "/leg_1/cmd",
        #     self.on_cmd,
        #     10
        # )

        self.ila_goal_sub = self.create_subscription(
            Float32,
            "/leg_1/ila_goal",
            self.on_ila_goal,
            10
        )

        self.gyro_pub = self.create_publisher(Vector3, "/leg_1/gyro", 10)
        self.enabled_pub = self.create_publisher(Bool, "/leg_1/enabled", 10)

        # UDP sockets
        self.tx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        self.rx_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.rx_sock.bind((JETSON_BIND_IP, JETSON_TELEM_PORT))

        self.cmd_seq = 0

        # Start telemetry receive thread
        self.rx_thread = threading.Thread(target=self.rx_loop, daemon=True)
        self.rx_thread.start()

        self.get_logger().info(f"Sending commands to {ZERO_IP}:{ZERO_CMD_PORT}")
        self.get_logger().info(f"Listening telemetry on {JETSON_BIND_IP}:{JETSON_TELEM_PORT}")

    def _send_pkt(self, data):
        pkt = {
            "type": "cmd",
            "leg_id": LEG_ID,
            "seq": self.cmd_seq,
            "t_monotonic": monotonic_s(),
        }
        
        # Dict update in place union operator
        pkt |= data

        self.cmd_seq += 1

        payload = json.dumps(pkt).encode("utf-8")
        self.tx_sock.sendto(payload, (ZERO_IP, ZERO_CMD_PORT))

    def on_ila_goal(self, msg: dict):
        data = float(msg.data)

        print(data)

        self._send_pkt({"ila_goal": str(data)})
        

    def rx_loop(self):
        while rclpy.ok():
            try:
                data, _addr = self.rx_sock.recvfrom(4096)
            except Exception:
                continue

            try:
                msg = json.loads(data.decode("utf-8"))
            except Exception:
                continue

            if msg.get("type") != "telem":
                continue
            if int(msg.get("leg_id", -1)) != LEG_ID:
                continue

            gyro = msg.get("gyro", {})
            gx = float(gyro.get("gx", 0.0))
            gy = float(gyro.get("gy", 0.0))
            gz = float(gyro.get("gz", 0.0))

            v = Vector3()
            v.x = gx
            v.y = gy
            v.z = gz
            self.gyro_pub.publish(v)

            en = Bool()
            en.data = bool(msg.get("enabled", False))
            self.enabled_pub.publish(en)

            # self.get_logger().info(
            #     f"telem seq={msg.get('seq')} enabled={msg.get('enabled')} gyro={msg.get('gyro')}"
            # )

def main():
    rclpy.init()
    node = RpiBridge()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
