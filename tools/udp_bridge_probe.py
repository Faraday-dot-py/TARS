#!/usr/bin/env python3
"""Send a UDP line to the Pico W bridge and print replies."""

from __future__ import annotations

import argparse
import socket
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("message", nargs="?", default="PING", help="UDP payload to send")
    parser.add_argument("--host", default="192.168.4.1", help="Pico W IP address")
    parser.add_argument("--port", type=int, default=15120, help="UDP port")
    parser.add_argument("--timeout", type=float, default=2.0, help="Response timeout in seconds")
    args = parser.parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(args.timeout)
    sock.sendto(args.message.encode("utf-8"), (args.host, args.port))

    try:
        while True:
            data, addr = sock.recvfrom(2048)
            sys.stdout.write(f"{addr[0]}:{addr[1]} {data.decode('utf-8', errors='replace')}")
    except socket.timeout:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
