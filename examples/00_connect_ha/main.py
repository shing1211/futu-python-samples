#!/usr/bin/env python3
"""Connect to FutuOpenD gateways with HA.

TCP probes all hosts in parallel, connects to fastest reachable one.
Per-host is_rsa flag controls encryption; auto-fallback retry on failure.

SDK truth: is_encrypt() returns SysConfig.IS_PROTO_ENCRYPT (global flag).
RSA is purely client-side opt-in — server-side RSA config only matters
if client also opts in. The localhost vs remote heuristic (RSA for remote,
no-RSA for localhost) works because remote OpenD instances typically have
RSA enabled while local ones typically don't.
"""

import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from futu import OpenQuoteContext, RET_OK, SysConfig
import sys

# Per-host config: (name, host, is_rsa)
# is_rsa=None  → auto: try RSA first, fallback to no-RSA on failure
# is_rsa=True  → RSA mode (remote servers with RSA enabled)
# is_rsa=False → no RSA (localhost, or remote with RSA off)
HOSTS = [
    ("futuopend-gw-01", "172.18.208.88", True),
    ("futuopend-gw-02", "172.20.208.88", True),
    # ("futuopend-local", "127.0.0.1", False),  # localhost fallback
]
PORT = 11111
RSA_KEY = "/etc/futu/keys/private_key.pem"
TCP_TIMEOUT = 3   # seconds per TCP probe
CONNECT_TIMEOUT = 8  # seconds per SDK connect attempt


def is_localhost(host):
    return host in ("127.0.0.1", "localhost")


def configure_rsa(enable: bool):
    """Set global RSA mode. Must be called BEFORE each connect."""
    SysConfig.enable_proto_encrypt(enable)
    if enable:
        SysConfig.set_init_rsa_file(RSA_KEY)


def tcp_connect(host, port, timeout=TCP_TIMEOUT):
    """Returns latency in ms for TCP connect, or None if unreachable."""
    t0 = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        return (time.time() - t0) * 1000
    except (socket.timeout, socket.error, OSError):
        return None


def try_connect(host, port, is_rsa: bool):
    """Attempt one connection with given RSA setting. Returns (ok, data_or_error, latency_ms)."""
    configure_rsa(enable=is_rsa)
    t0 = time.time()
    try:
        ctx = OpenQuoteContext(host=host, port=port)
        ret, data = ctx.get_global_state()
        ctx.close()
        return ret == RET_OK, data, (time.time() - t0) * 1000
    except Exception as e:
        return False, str(e), (time.time() - t0) * 1000


def connect_host(name, host, port, is_rsa: bool | None = None):
    """
    Connect to a single FutuOpenD host.

    is_rsa=True  → RSA mode only
    is_rsa=False → no-RSA mode only
    is_rsa=None  → try RSA first, on failure retry without RSA
    """
    rsa_mode = is_rsa if is_rsa is not None else True  # default to RSA for None

    ok, data, lat = try_connect(host, port, is_rsa=rsa_mode)

    if ok:
        return ok, data, lat

    # Fallback: if RSA failed, try without; or if no-RSA failed, try with
    if is_rsa is None:
        fallback_rsa = not rsa_mode
        label = f"RSA OFF → ON" if rsa_mode else f"RSA ON → OFF"
        ok, data, lat = try_connect(host, port, is_rsa=fallback_rsa)
        if ok:
            return ok, data, lat

    return ok, data, lat


def main():
    print(f"RSA key: {RSA_KEY}")
    print(f"TCP probing {len(HOSTS)} hosts ...\n")

    # Parallel TCP connect probe (fast, no SDK retry overhead)
    tcp_results = {}
    with ThreadPoolExecutor(max_workers=len(HOSTS)) as ex:
        futures = {ex.submit(tcp_connect, host, PORT): (name, host, is_rsa) for name, host, is_rsa in HOSTS}
        for future in as_completed(futures):
            name, host, is_rsa = futures[future]
            ms = future.result()
            tcp_results[host] = (ms, is_rsa)
            status = f"{ms:.0f}ms" if ms else "❌ unreachable"
            rsa_tag = {True: "[RSA]", None: "[RSA?]", False: "[noRSA]"}[is_rsa]
            print(f"  {rsa_tag} {name:20s} {host:16s}  {status}")

    reachable = {h: v for h, v in tcp_results.items() if v[0] is not None}
    if not reachable:
        print("\nNo reachable gateways.")
        sys.exit(1)

    # Sort by TCP latency
    sorted_hosts = sorted(reachable.items(), key=lambda x: x[1][0])
    fastest_host, (fastest_tcp, fastest_rsa) = sorted_hosts[0]
    print(f"\nFastest TCP: {next(n for n, h, _ in HOSTS if h == fastest_host)} ({fastest_host})")
    print("-" * 45)

    # Try each host in order; each host gets its own fallback retry
    for host, (tcp_lat, is_rsa) in sorted_hosts:
        name = next(n for n, h, _ in HOSTS if h == host)
        rsa_tag = {True: "[RSA]", None: "[RSA?]", False: "[noRSA]"}[is_rsa]
        print(f"{rsa_tag} Trying {name} ({host}) ...", end=" ", flush=True)

        ok, data, api_lat = connect_host(name, host, PORT, is_rsa=is_rsa)

        if ok:
            print(f"✅ ({api_lat:.0f}ms TCP {tcp_lat:.0f}ms)")
            print(f"   gateway     : {name}")
            print(f"   server_ver  : {data.get('server_ver', '?')}")
            print(f"   quote_login : {data.get('qot_logined', '?')}")
            print(f"   trade_login : {data.get('trd_logined', '?')}")
            print(f"   market_hk   : {data.get('market_hk', '?')}")
            print(f"   market_us   : {data.get('market_us', '?')}")
            print(f"   market_sh   : {data.get('market_sh', '?')}")
            print(f"   market_sz   : {data.get('market_sz', '?')}")
            return
        else:
            print(f"❌ {data}")


if __name__ == "__main__":
    main()
