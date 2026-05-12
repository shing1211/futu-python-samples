"""HA connection helper for Futu OpenD.

Provides connect_opend() which TCP-probes all configured hosts,
connects to the fastest reachable one with proper RSA configuration.

Usage:
    from connect import create_quote_context
    quote_ctx = create_quote_context()
    # ... use context ...
    quote_ctx.close()
"""

import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from futu import OpenQuoteContext, RET_OK, SysConfig
import sys

# Per-host config: (name, host, is_rsa)
# is_rsa=True  → RSA encryption (remote servers with RSA enabled)
# is_rsa=False → no RSA (localhost, or remote with RSA off)
# is_rsa=None  → auto: try RSA first, fallback to no-RSA on failure
HOSTS = [
    ("futuopend-gw-01", "172.18.208.88", True),
    ("futuopend-gw-02", "172.20.208.88", True),
    # ("futuopend-local", "127.0.0.1", False),  # localhost fallback
]
PORT = 11111
RSA_KEY = "/etc/futu/keys/private_key.pem"
TCP_TIMEOUT = 3   # seconds per TCP probe


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


def connect_opend(is_rsa: bool | None = None):
    """
    TCP-probe all hosts, connect to fastest reachable one.

    is_rsa=True  → RSA mode only
    is_rsa=False → no-RSA mode only
    is_rsa=None  → auto: try RSA first, fallback without on failure

    Returns (ctx, info_dict) where info_dict has keys:
        name, host, tcp_ms, api_ms, server_ver, quote_login, trade_login,
        market_hk, market_us, market_sh, market_sz
    """
    # Parallel TCP probe
    tcp_results = {}
    with ThreadPoolExecutor(max_workers=len(HOSTS)) as ex:
        futures = {ex.submit(tcp_connect, h, PORT): (n, h, r) for n, h, r in HOSTS}
        for future in as_completed(futures):
            name, host, rsa = futures[future]
            ms = future.result()
            tcp_results[host] = (ms, rsa)

    reachable = {h: v for h, v in tcp_results.items() if v[0] is not None}
    if not reachable:
        raise RuntimeError("No reachable OpenD gateways")

    # Sort by TCP latency
    sorted_hosts = sorted(reachable.items(), key=lambda x: x[1][0])
    fastest_host, (fastest_tcp, fastest_rsa) = sorted_hosts[0]

    # Use per-host is_rsa if not overridden
    host_rsa = is_rsa if is_rsa is not None else fastest_rsa

    # Try with primary RSA mode, then fallback
    rsa_mode = host_rsa if host_rsa is not None else True
    ok, data, api_lat = try_connect(fastest_host, PORT, is_rsa=rsa_mode)

    if not ok and is_rsa is None:
        fallback_rsa = not rsa_mode
        ok, data, api_lat = try_connect(fastest_host, PORT, is_rsa=fallback_rsa)

    if not ok:
        raise RuntimeError(f"Failed to connect to {fastest_host}: {data}")

    return {
        "name": fastest_host,
        "host": fastest_host,
        "tcp_ms": fastest_tcp,
        "api_ms": api_lat,
        "server_ver": data.get("server_ver", "?"),
        "quote_login": data.get("qot_logined", "?"),
        "trade_login": data.get("trd_logined", "?"),
        "market_hk": data.get("market_hk", "?"),
        "market_us": data.get("market_us", "?"),
        "market_sh": data.get("market_sh", "?"),
        "market_sz": data.get("market_sz", "?"),
    }


def create_quote_context(is_rsa: bool | None = None):
    """
    Create and return a connected OpenQuoteContext using HA gateway selection.
    Call .close() on the context when done.

    is_rsa: override RSA setting (None = per-host config, auto-fallback)
    """
    info = connect_opend(is_rsa=is_rsa)
    configure_rsa(enable=False)  # reset to plain for subsequent contexts
    return OpenQuoteContext(host=info["host"], port=PORT)


def create_trade_context(is_rsa: bool | None = None, **kwargs):
    """
    Create and return a connected trade context (OpenSecTradeContext) using
    the same HA gateway as create_quote_context(). Call .close() when done.

    is_rsa: override RSA setting (None = per-host config, auto-fallback)
    kwargs: passed through to OpenSecTradeContext (e.g. filter_trdmarket, security_firm)
    """
    from futu import OpenSecTradeContext
    info = connect_opend(is_rsa=is_rsa)
    configure_rsa(enable=False)
    return OpenSecTradeContext(host=info["host"], port=PORT, **kwargs)
