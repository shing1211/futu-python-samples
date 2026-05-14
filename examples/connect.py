"""HA connection helper for Futu OpenD.

Provides connect_opend() which TCP-probes all configured hosts,
connects to the fastest reachable one with proper RSA configuration.

Usage:
    from connect import create_quote_context
    quote_ctx = create_quote_context()
    # ... use context ...
    quote_ctx.close()

Configuration via environment variables:
    FUTU_ADDR         - Single host fallback (host:port, default 127.0.0.1:11111)
    FUTU_OPEND_HOSTS  - Comma-separated host list with RSA flags (host:port:is_rsa,...)
                        Example: "127.0.0.1:11111:False,172.18.208.88:11111:True"
    FUTU_RSA_KEY      - Path to RSA private key (default /etc/futu/keys/private_key.pem)
    FUTU_TCP_TIMEOUT  - TCP probe timeout in seconds (default 3)
    FUTU_TRADE_PWD    - Demo trade unlock password (default 123456 for SIMULATE)

Connection caching:
    create_quote_context() and create_trade_context() share a cached
    TCP probe result so that both contexts connect to the same gateway
    without redundant probing. Call clear_connection_cache() to reset.
"""

import os
import socket
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Load .env from the repo root (parent of examples/)
_dotenv_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_dotenv_path)
from concurrent.futures import ThreadPoolExecutor, as_completed
from futu import OpenQuoteContext, RET_OK, SysConfig

logger = logging.getLogger("connect")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
_FUTU_ADDR = os.environ.get("FUTU_ADDR", "127.0.0.1:11111")
_RSA_KEY = os.environ.get("FUTU_RSA_KEY", "/etc/futu/keys/private_key.pem")
_TCP_TIMEOUT = float(os.environ.get("FUTU_TCP_TIMEOUT", "3"))
_TRADE_PWD = os.environ.get("FUTU_TRADE_PWD", "123456")


def _parse_hosts():
    """Parse FUTU_OPEND_HOSTS env var into HOSTS list.

    Format: host:port:is_rsa[,host:port:is_rsa,...]
    Example: "172.18.208.88:11111:True,172.20.208.88:11111:True"

    If FUTU_OPEND_HOSTS is unset, falls back to FUTU_ADDR (single host, no RSA).
    If both are unset, defaults to localhost.
    """
    env_hosts = os.environ.get("FUTU_OPEND_HOSTS", "").strip()
    result = []

    if env_hosts:
        for entry in env_hosts.split(","):
            parts = entry.strip().split(":")
            if len(parts) == 3:
                host, port_str, rsa_str = parts
                is_rsa = rsa_str.lower() == "true"
            elif len(parts) == 2:
                host, port_str = parts
                is_rsa = True  # remote hosts default to RSA
            else:
                host = parts[0]
                port_str = "11111"
                is_rsa = True
            try:
                port = int(port_str)
            except ValueError:
                port = 11111
            result.append((host, port, is_rsa))
    else:
        # Fallback to FUTU_ADDR
        addr = _FUTU_ADDR
        if ":" in addr:
            host, port_str = addr.rsplit(":", 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 11111
        else:
            host = addr
            port = 11111
        result.append((host, port, False))  # localhost assumed no RSA

    return result


HOSTS = _parse_hosts()
PORT = 11111
RSA_KEY = _RSA_KEY
TCP_TIMEOUT = _TCP_TIMEOUT

# Demo password (for SIMULATE trade only — real accounts use proper auth)
DEMO_TRADE_PASSWORD = _TRADE_PWD

# -- Connection cache: avoid redundant TCP probes when creating both
#    quote and trade contexts in the same session.
_cached_probe_result: tuple | None = None  # (info_dict, actual_rsa)


def configure_rsa(enable: bool):
    """Set global RSA mode. Must be called BEFORE each connect."""
    logger.debug("configure_rsa: enable=%s, key=%s", enable, RSA_KEY)
    SysConfig.enable_proto_encrypt(enable)
    if enable:
        SysConfig.set_init_rsa_file(RSA_KEY)


def tcp_connect(host, port, timeout=TCP_TIMEOUT):
    """Returns latency in ms for TCP connect, or None if unreachable."""
    t0 = time.time()
    try:
        sock = socket.create_connection((host, port), timeout=timeout)
        sock.close()
        latency = (time.time() - t0) * 1000
        logger.debug("tcp_connect %s:%s -> %.1fms", host, port, latency)
        return latency
    except (socket.timeout, socket.error, OSError) as e:
        logger.debug("tcp_connect %s:%s -> failed: %s", host, port, e)
        return None


def try_connect(host, port, is_rsa: bool):
    """Attempt one connection with given RSA setting. Returns (ok, data_or_error, latency_ms)."""
    configure_rsa(enable=is_rsa)
    t0 = time.time()
    ctx = None
    try:
        ctx = OpenQuoteContext(host=host, port=port)
        ret, data = ctx.get_global_state()
        latency = (time.time() - t0) * 1000
        logger.debug("try_connect %s:%s RSA=%s -> OK (%.1fms)", host, port, is_rsa, latency)
        return ret == RET_OK, data, latency
    except Exception as e:
        latency = (time.time() - t0) * 1000
        logger.debug("try_connect %s:%s RSA=%s -> FAIL: %s", host, port, is_rsa, e)
        return False, str(e), latency
    finally:
        if ctx is not None:
            ctx.close()


def connect_opend(is_rsa: bool | None = None):
    """
    TCP-probe all hosts, connect to fastest reachable one.

    is_rsa=True  → RSA mode only
    is_rsa=False → no-RSA mode only
    is_rsa=None  → auto: try RSA first, fallback without on failure

    Returns (info_dict, actual_rsa) where actual_rsa is the bool RSA setting
    that succeeded, and info_dict has keys:
        name, host, tcp_ms, api_ms, server_ver, quote_login, trade_login,
        market_hk, market_us, market_sh, market_sz
    """
    logger.info("connect_opend: probing %d hosts (is_rsa=%s)", len(HOSTS), is_rsa)

    # Parallel TCP probe
    tcp_results = {}
    with ThreadPoolExecutor(max_workers=len(HOSTS)) as ex:
        futures = {ex.submit(tcp_connect, h, p): (h, p, r) for h, p, r in HOSTS}
        for future in as_completed(futures):
            host, port, rsa = futures[future]
            ms = future.result()
            tcp_results[(host, port)] = (ms, rsa)
            status = f"{ms:.0f}ms" if ms is not None else "unreachable"
            logger.debug("  TCP probe %s:%s -> %s", host, port, status)

    reachable = {h: v for h, v in tcp_results.items() if v[0] is not None}
    if not reachable:
        raise RuntimeError("No reachable OpenD gateways")

    # Sort by TCP latency
    sorted_hosts = sorted(reachable.items(), key=lambda x: x[1][0])
    fastest_host, (fastest_tcp, fastest_rsa) = sorted_hosts[0]
    logger.info("  Fastest host: %s:%s (TCP %.1fms)", fastest_host[0], fastest_host[1], fastest_tcp)

    # Use per-host is_rsa if not overridden
    host_rsa = is_rsa if is_rsa is not None else fastest_rsa

    # Try with primary RSA mode, then fallback
    rsa_mode = host_rsa if host_rsa is not None else True
    ok, data, api_lat = try_connect(fastest_host[0], fastest_host[1], is_rsa=rsa_mode)
    actual_rsa = rsa_mode

    if not ok and is_rsa is None:
        fallback_rsa = not rsa_mode
        label = "RSA OFF→ON" if rsa_mode else "RSA ON→OFF"
        logger.info("  Primary RSA failed, trying %s", label)
        ok, data, api_lat = try_connect(fastest_host[0], fastest_host[1], is_rsa=fallback_rsa)
        actual_rsa = fallback_rsa

    if not ok:
        logger.error("  All connection attempts failed to %s:%s", fastest_host[0], fastest_host[1])
        raise RuntimeError(f"Failed to connect to {fastest_host[0]}:{fastest_host[1]}: {data}")

    logger.info(
        "  Connected to %s:%s (API %.1fms, RSA=%s)  server_ver=%s",
        fastest_host[0], fastest_host[1], api_lat, actual_rsa,
        data.get("server_ver", "?"),
    )

    return {
        "name": fastest_host[0],
        "host": fastest_host[0],
        "port": fastest_host[1],
        "tcp_ms": fastest_tcp,
        "api_ms": api_lat,
        "server_ver": data.get("server_ver", "?"),
        "quote_login": data.get("qot_logined", "?"),
        "trade_login": data.get("trd_logined", "?"),
        "market_hk": data.get("market_hk", "?"),
        "market_us": data.get("market_us", "?"),
        "market_sh": data.get("market_sh", "?"),
        "market_sz": data.get("market_sz", "?"),
    }, actual_rsa


def clear_connection_cache():
    """Clear the cached probe result so the next create_quote_context /
    create_trade_context call will re-probe all gateways."""
    global _cached_probe_result
    logger.debug("Clearing connection cache")
    _cached_probe_result = None


def create_quote_context(is_rsa: bool | None = None, *, _use_cache=True):
    """
    Create and return a connected OpenQuoteContext using HA gateway selection.
    Call .close() on the context when done.

    is_rsa: override RSA setting (None = per-host config, auto-fallback)
    _use_cache: if True (default), reuse a prior TCP probe result when both
                quote and trade contexts are needed in the same session.
    """
    global _cached_probe_result
    if _use_cache and _cached_probe_result is not None:
        info, actual_rsa = _cached_probe_result
        configure_rsa(enable=actual_rsa)
        logger.info("create_quote_context: reusing cached connection to %s:%s", info["host"], info["port"])
        ctx = OpenQuoteContext(host=info["host"], port=info.get("port", PORT))
        return ctx

    info, actual_rsa = connect_opend(is_rsa=is_rsa)
    _cached_probe_result = (info, actual_rsa)
    configure_rsa(enable=actual_rsa)
    logger.info("create_quote_context: new connection to %s:%s (RSA=%s)", info["host"], info["port"], actual_rsa)
    return OpenQuoteContext(host=info["host"], port=info.get("port", PORT))


def create_trade_context(is_rsa: bool | None = None, *, _use_cache=True, **kwargs):
    """
    Create and return a connected trade context (OpenSecTradeContext) using
    the same HA gateway as create_quote_context(). Call .close() when done.

    is_rsa: override RSA setting (None = per-host config, auto-fallback)
    _use_cache: if True (default), reuse a prior TCP probe result when both
                quote and trade contexts are needed in the same session.
    kwargs: passed through to OpenSecTradeContext (e.g. filter_trdmarket, security_firm)
    """
    from futu import OpenSecTradeContext
    global _cached_probe_result
    if _use_cache and _cached_probe_result is not None:
        info, actual_rsa = _cached_probe_result
        configure_rsa(enable=actual_rsa)
        logger.info("create_trade_context: reusing cached connection to %s:%s (RSA=%s)", info["host"], info["port"], actual_rsa)
        return OpenSecTradeContext(host=info["host"], port=info.get("port", PORT), **kwargs)

    info, actual_rsa = connect_opend(is_rsa=is_rsa)
    _cached_probe_result = (info, actual_rsa)
    configure_rsa(enable=actual_rsa)
    logger.info("create_trade_context: new connection to %s:%s (RSA=%s)", info["host"], info["port"], actual_rsa)
    return OpenSecTradeContext(host=info["host"], port=info.get("port", PORT), **kwargs)


def get_demo_trade_password():
    """Return the demo SIMULATE trade password. Configure via FUTU_TRADE_PWD env var."""
    return DEMO_TRADE_PASSWORD