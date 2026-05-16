#!/usr/bin/env python3
"""
98 — HA Connection Diagnostics

Interactive tool that demonstrates health monitoring, auto-failover,
and lifecycle hooks. Shows ranked host list, real-time heartbeats,
failover detection, and connection statistics.

Usage:
    python3 examples/98_ha_diagnostics/main.py

    While running, try killing your primary OpenD gateway to see
    auto-failover in action. The health monitor will detect the
    disconnection and fire on_failover / on_disconnect hooks.

SDK: connect.py (ConnectionHooks, create_quote_context, health_monitor)
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connect import (
    create_quote_context,
    clear_connection_cache,
    ConnectionHooks,
    HOSTS,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s: %(message)s",
)
logger = logging.getLogger(__name__)


def make_hooks():
    """Create lifecycle hooks for this diagnostic session."""
    heartbeat_count = 0
    failover_count = 0

    def on_connect(info):
        print(f"  [HOOK] Connected to {info['host']}:{info['port']}  "
              f"server={info.get('server_ver', '?')}  "
              f"RSA={info.get('api_ms', '?'):.0f}ms")

    def on_heartbeat(info, error):
        nonlocal heartbeat_count
        heartbeat_count += 1
        status = "OK" if error is None else f"FAIL: {error}"
        print(f"  [HOOK] Heartbeat #{heartbeat_count} -> "
              f"{info['host']}:{info.get('port', 11111)}  {status}")

    def on_failover(old, new):
        nonlocal failover_count
        failover_count += 1
        print(f"  [HOOK] ⚠ FAILOVER #{failover_count}: "
              f"{old['host']}:{old.get('port', 11111)} -> "
              f"{new['host']}:{new.get('port', 11111)}")

    def on_disconnect(info, error):
        print(f"  [HOOK] ⚠ DISCONNECTED from "
              f"{info['host']}:{info.get('port', 11111)}: {error}")

    return ConnectionHooks(
        on_connect=on_connect,
        on_heartbeat=on_heartbeat,
        on_failover=on_failover,
        on_disconnect=on_disconnect,
    ), lambda: (heartbeat_count, failover_count)


def print_banner():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║     HA Connection Diagnostics                ║")
    print("  ║     Health Monitor + Auto-Failover           ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()

    print("  Configured hosts:")
    for host, port, is_rsa in HOSTS:
        rsa_label = "RSA" if is_rsa else "noRSA"
        print(f"    {host}:{port} ({rsa_label})")
    print()


def run_diagnostics(duration=120, heartbeat_interval=15, max_failures=3):
    """
    Connect with health monitoring and collect statistics.

    Args:
        duration: how long to monitor (seconds)
        heartbeat_interval: seconds between health pings
        max_failures: consecutive failures before failover
    """
    hooks, get_counts = make_hooks()

    print(f"  Connecting with health monitoring...")
    print(f"    heartbeat_interval={heartbeat_interval}s")
    print(f"    max_failures={max_failures}")
    print()

    ctx = create_quote_context(
        health_monitor=True,
        hooks=hooks,
    )

    info = {
        "host": None,
        "port": None,
    }
    try:
        ret, gs = ctx.get_global_state()
        if ret == 0:
            print(f"  Connected. Gateway info:")
            for k in ("server_ver", "qot_logined", "trd_logined",
                      "market_hk", "market_us", "market_sh", "market_sz"):
                print(f"    {k}: {gs.get(k, '?')}")
        print()

        deadline = time.time() + duration
        tick = 0
        while time.time() < deadline:
            remaining = int(deadline - time.time())
            tick += 1

            try:
                ret, quote = ctx.get_stock_quote("HK.00700")
                if ret == 0 and quote is not None and not quote.empty:
                    last = quote.iloc[-1].get("last_price", "?")
                    print(f"  [{remaining:03d}s] Quote: "
                          f"HK.00700 = {last}")
                else:
                    print(f"  [{remaining:03d}s] Quote: "
                          f"HK.00700 = N/A (ret={ret})")
            except Exception as e:
                print(f"  [{remaining:03d}s] Quote FAILED: {e}")

            for _ in range(min(heartbeat_interval, remaining)):
                time.sleep(1)
                remaining -= 1
                if remaining <= 0:
                    break

        hb, fo = get_counts()
        print()
        print(f"  ── Session Summary ──")
        print(f"    Duration:     {duration}s")
        print(f"    Heartbeats:   {hb}")
        print(f"    Failovers:    {fo}")

    except KeyboardInterrupt:
        hb, fo = get_counts()
        print()
        print(f"  Stopped by user.")
        print(f"    Heartbeats:   {hb}")
        print(f"    Failovers:    {fo}")
    finally:
        ctx.close()
        clear_connection_cache()
        print("  Connection closed.")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="HA Connection Diagnostics",
    )
    parser.add_argument(
        "--duration", type=int, default=120,
        help="Monitoring duration in seconds (default: 120)",
    )
    parser.add_argument(
        "--interval", type=int, default=15,
        help="Heartbeat interval in seconds (default: 15)",
    )
    parser.add_argument(
        "--max-failures", type=int, default=3,
        help="Consecutive failures before failover (default: 3)",
    )
    args = parser.parse_args()

    print_banner()
    run_diagnostics(
        duration=args.duration,
        heartbeat_interval=args.interval,
        max_failures=args.max_failures,
    )
