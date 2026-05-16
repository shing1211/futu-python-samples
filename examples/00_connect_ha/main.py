#!/usr/bin/env python3
"""
00 — HA Gateway Selection Demo

TCP probes all configured OpenD hosts in parallel, connects to the fastest.
Demonstrates the full HA algorithm with health monitoring and auto-failover.

This standalone version shows how connect.py works internally. For normal
usage, import from `connect` instead:
    from connect import create_quote_context, ConnectionHooks

Usage:
    python3 examples/00_connect_ha/main.py

Configuration (environment variables override hardcoded defaults):
    FUTU_OPEND_HOSTS  - comma-separated host:port:is_rsa entries
    FUTU_ADDR         - single host fallback
    FUTU_RSA_KEY      - path to RSA private key
    FUTU_TCP_TIMEOUT  - TCP probe timeout in seconds
"""
import os
import socket
import time
import logging
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from futu import OpenQuoteContext, RET_OK, SysConfig
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (mirrors connect.py but standalone for teaching)
# ---------------------------------------------------------------------------
_FUTU_OPEND_HOSTS = os.environ.get("FUTU_OPEND_HOSTS", "").strip()
_FUTU_ADDR = os.environ.get("FUTU_ADDR", "127.0.0.1:11111")
_FUTU_RSA_KEY = os.environ.get("FUTU_RSA_KEY", "/etc/futu/keys/private_key.pem")
_FUTU_TCP_TIMEOUT = float(os.environ.get("FUTU_TCP_TIMEOUT", "3"))


def _parse_hosts():
    if _FUTU_OPEND_HOSTS:
        result = []
        for entry in _FUTU_OPEND_HOSTS.split(","):
            parts = entry.strip().split(":")
            host = parts[0]
            port = int(parts[1]) if len(parts) > 1 else 11111
            is_rsa = parts[2].lower() == "true" if len(parts) > 2 else True
            result.append((host, port, is_rsa))
        return result
    addr = _FUTU_ADDR
    host, port_str = (addr.rsplit(":", 1) if ":" in addr else (addr, "11111"))
    return [(host, int(port_str), False)]


HOSTS = _parse_hosts()
PORT = 11111
RSA_KEY = _FUTU_RSA_KEY
TCP_TIMEOUT = _FUTU_TCP_TIMEOUT


def configure_rsa(enable: bool):
    logger.debug("configure_rsa: enable=%s key=%s", enable, RSA_KEY)
    SysConfig.enable_proto_encrypt(enable)
    if enable:
        SysConfig.set_init_rsa_file(RSA_KEY)


def tcp_connect(host, port, timeout=TCP_TIMEOUT):
    t0 = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        ms = (time.time() - t0) * 1000
        logger.debug("tcp_connect %s:%s -> %.1fms", host, port, ms)
        return ms
    except Exception as e:
        logger.debug("tcp_connect %s:%s -> failed: %s", host, port, e)
        return None


def try_connect(host, port, is_rsa: bool):
    configure_rsa(enable=is_rsa)
    t0 = time.time()
    try:
        ctx = OpenQuoteContext(host=host, port=port)
        ret, data = ctx.get_global_state()
        ctx.close()
        ms = (time.time() - t0) * 1000
        logger.debug("try_connect %s:%s RSA=%s -> OK (%.1fms)", host, port, is_rsa, ms)
        return ret == RET_OK, data, ms
    except Exception as e:
        ms = (time.time() - t0) * 1000
        logger.debug("try_connect %s:%s RSA=%s -> FAIL: %s", host, port, is_rsa, e)
        return False, str(e), ms


def connect_host(name, host, port, is_rsa):
    rsa_mode = is_rsa if is_rsa is not None else True
    ok, data, lat = try_connect(host, port, is_rsa=rsa_mode)
    if ok:
        logger.debug("connect_host [%s] %s:%s OK (%.1fms RSA=%s)", name, host, port, lat, rsa_mode)
        return ok, data, lat
    if is_rsa is None:
        fallback = not rsa_mode
        label = "RSA OFF→ON" if rsa_mode else "RSA ON→OFF"
        logger.info("  Primary failed, trying %s", label)
        ok, data, lat = try_connect(host, port, is_rsa=fallback)
        if ok:
            return ok, data, lat
    return ok, data, lat


def main():
    logger.info("=== HA Gateway Selection + Health Demo ===\n")
    logger.info("RSA key: %s", RSA_KEY)
    logger.info("TCP probing %d hosts (timeout=%.1fs)...\n", len(HOSTS), TCP_TIMEOUT)
    for host, port, is_rsa in HOSTS:
        logger.info("  host=%s:%s is_rsa=%s", host, port, is_rsa)

    # ── Step 1: Parallel TCP probe ──
    tcp_results = {}
    with ThreadPoolExecutor(max_workers=len(HOSTS)) as ex:
        futures = {ex.submit(tcp_connect, h, p): (h, p, r) for h, p, r in HOSTS}
        for future in as_completed(futures):
            host, port, is_rsa = futures[future]
            ms = future.result()
            tcp_results[(host, port)] = (ms, is_rsa)
            status = f"{ms:.0f}ms" if ms is not None else "unreachable"
            rsa_tag = {True: "[RSA]", False: "[noRSA]"}[is_rsa]
            logger.info("  TCP %s %s:%s -> %s", rsa_tag, host, port, status)

    reachable = {h: v for h, v in tcp_results.items() if v[0] is not None}
    if not reachable:
        logger.error("No reachable gateways!")
        raise SystemExit(1)

    sorted_hosts = sorted(reachable.items(), key=lambda x: x[1][0])
    fastest, (fastest_tcp, fastest_rsa) = sorted_hosts[0]
    logger.info("\nFastest: %s:%s (TCP %.1fms)\n", fastest[0], fastest[1], fastest_tcp)

    # ── Step 2: API connect with fallback chain ──
    ok, data, api_lat = connect_host(
        fastest[0], fastest[0], fastest[1], fastest_rsa
    )
    if not ok:
        logger.error("All connection attempts failed: %s", data)
        raise SystemExit(1)

    logger.info("Connected to %s:%s", fastest[0], fastest[1])
    logger.info("   API latency:  %.1fms", api_lat)
    logger.info("   server_ver:  %s", data.get("server_ver", "?"))
    logger.info("   quote_login: %s", data.get("qot_logined", "?"))
    logger.info("   trade_login: %s", data.get("trd_logined", "?"))
    logger.info("   market_hk:   %s", data.get("market_hk", "?"))
    logger.info("   market_us:   %s", data.get("market_us", "?"))
    logger.info("   market_sh:   %s", data.get("market_sh", "?"))
    logger.info("   market_sz:   %s", data.get("market_sz", "?"))

    # ── Step 3: Health monitoring (3 heartbeats at 5s intervals) ──
    logger.info("\nStarting health monitor (5s interval, 3 samples)...\n")
    ctx = OpenQuoteContext(host=fastest[0], port=fastest[1])
    try:
        for i in range(3):
            time.sleep(5)
            try:
                ret, gs = ctx.get_global_state()
                ok_str = "OK" if ret == RET_OK else "FAIL"
                ver = gs.get("server_ver", "?")
                logger.info("  Heartbeat #%d -> %s  server_ver=%s", i + 1, ok_str, ver)
            except Exception as e:
                logger.info("  Heartbeat #%d -> FAIL: %s", i + 1, e)
    finally:
        ctx.close()

    logger.info("\nDone. Run other examples to use the full SDK.")
    logger.info("For auto-failover with health monitoring, use:")
    logger.info("  from connect import create_quote_context, ConnectionHooks")
    logger.info("  ctx = create_quote_context(health_monitor=True)")


if __name__ == "__main__":
    main()