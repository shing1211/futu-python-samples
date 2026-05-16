"""HA connection helper for Futu OpenD.

TCP-probes all configured hosts, connects to the fastest reachable one
with proper RSA configuration. Supports optional background health
monitoring with automatic failover and lifecycle hooks.

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

Health monitoring (optional):
    create_quote_context(health_monitor=True) starts a daemon thread
    that periodically pings the active gateway. If N consecutive
    heartbeats fail, it automatically fails over to the next-best host
    and fires lifecycle hooks.

    Hooks example:
        from connect import ConnectionHooks
        hooks = ConnectionHooks(
            on_connect=lambda h: print(f"Connected to {h['host']}"),
            on_failover=lambda o, n: print(f"Failover: {o['host']} -> {n['host']}"),
        )
        ctx = create_quote_context(hooks=hooks)
"""

import os
import socket
import time
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable
from dotenv import load_dotenv

_load_dotenv_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_load_dotenv_path)
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
                is_rsa = True
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
        result.append((host, port, False))

    return result


HOSTS = _parse_hosts()
PORT = 11111
RSA_KEY = _RSA_KEY
TCP_TIMEOUT = _TCP_TIMEOUT
DEMO_TRADE_PASSWORD = _TRADE_PWD

# ---------------------------------------------------------------------------
# Internal types — not part of the public API but usable via ConnectionHooks
# ---------------------------------------------------------------------------

@dataclass
class _HostInfo:
    host: str
    port: int
    is_rsa: bool
    tcp_latency: float | None = None
    api_latency: float | None = None
    success_count: int = 0
    failure_count: int = 0
    consecutive_failures: int = 0
    last_error: str | None = None


@dataclass
class ConnectionHooks:
    on_connect: Callable | None = None
    on_failover: Callable | None = None
    on_disconnect: Callable | None = None
    on_heartbeat: Callable | None = None


# ---------------------------------------------------------------------------
# Internal state (thread-safe via lock)
# ---------------------------------------------------------------------------

_connection_lock = threading.Lock()
_cached_probe_result: tuple | None = None
_cached_ranked_hosts: list[_HostInfo] = []
_health_thread: threading.Thread | None = None
_health_stop: threading.Event | None = None
_hooks: ConnectionHooks | None = None

# ---------------------------------------------------------------------------
# Low-level helpers (unchanged signatures)
# ---------------------------------------------------------------------------


def configure_rsa(enable: bool):
    logger.debug("configure_rsa: enable=%s, key=%s", enable, RSA_KEY)
    SysConfig.enable_proto_encrypt(enable)
    if enable:
        SysConfig.set_init_rsa_file(RSA_KEY)


def tcp_connect(host, port, timeout=TCP_TIMEOUT):
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


# ---------------------------------------------------------------------------
# Health monitoring and failover
# ---------------------------------------------------------------------------


def _stop_health_monitor():
    global _health_stop
    if _health_stop is not None:
        _health_stop.set()


def _health_monitor_loop(interval, max_failures):
    ctx = None
    while not _health_stop.wait(interval):
        with _connection_lock:
            if _cached_probe_result is None:
                continue
            info, actual_rsa = _cached_probe_result
            hosts = list(_cached_ranked_hosts)
            hooks = _hooks

        if ctx is None:
            configure_rsa(enable=actual_rsa)
            ctx = OpenQuoteContext(host=info["host"], port=info.get("port", PORT))

        try:
            ret, _ = ctx.get_global_state()
            if ret != RET_OK:
                raise RuntimeError(f"get_global_state returned {ret}")
            for hi in hosts:
                if hi.host == info["host"] and hi.port == info.get("port", PORT):
                    hi.success_count += 1
                    hi.consecutive_failures = 0
                    hi.last_error = None
                    break
            if hooks and hooks.on_heartbeat:
                hooks.on_heartbeat(info, None)
        except Exception as e:
            for hi in hosts:
                if hi.host == info["host"] and hi.port == info.get("port", PORT):
                    hi.failure_count += 1
                    hi.consecutive_failures += 1
                    hi.last_error = str(e)
                    break
            if hooks and hooks.on_heartbeat:
                hooks.on_heartbeat(info, str(e))
            logger.warning("Heartbeat failure #%d to %s:%s: %s",
                           next((hi.consecutive_failures for hi in hosts
                                 if hi.host == info["host"] and hi.port == info.get("port", PORT)), 0),
                           info["host"], info.get("port", PORT), e)

            if any(hi.consecutive_failures >= max_failures
                   for hi in hosts if hi.host == info["host"] and hi.port == info.get("port", PORT)):
                _trigger_failover(str(e))
                if ctx:
                    try:
                        ctx.close()
                    except Exception:
                        pass
                    ctx = None

    if ctx:
        try:
            ctx.close()
        except Exception:
            pass


def _start_health_monitor(interval=15.0, max_failures=3):
    global _health_thread, _health_stop
    if _health_thread is not None and _health_thread.is_alive():
        return
    _health_stop = threading.Event()
    _health_thread = threading.Thread(
        target=_health_monitor_loop,
        args=(interval, max_failures),
        daemon=True,
    )
    _health_thread.start()
    logger.debug("Health monitor started (interval=%.1fs, max_failures=%d)", interval, max_failures)


def _trigger_failover(error):
    global _cached_probe_result
    with _connection_lock:
        if _cached_probe_result is None:
            return
        old_info, _ = _cached_probe_result
        hooks = _hooks
        for hi in _cached_ranked_hosts:
            if hi.consecutive_failures < 3 and not (hi.host == old_info["host"] and hi.port == old_info.get("port", PORT)):
                new_info = {
                    "name": hi.host,
                    "host": hi.host,
                    "port": hi.port,
                    "tcp_ms": hi.tcp_latency,
                    "api_ms": hi.api_latency,
                    "server_ver": old_info.get("server_ver", "?"),
                    "quote_login": old_info.get("quote_login", "?"),
                    "trade_login": old_info.get("trade_login", "?"),
                    "market_hk": old_info.get("market_hk", "?"),
                    "market_us": old_info.get("market_us", "?"),
                    "market_sh": old_info.get("market_sh", "?"),
                    "market_sz": old_info.get("market_sz", "?"),
                }
                _cached_probe_result = (new_info, hi.is_rsa)
                logger.warning("Failover: %s:%s -> %s:%s (RSA=%s)",
                               old_info["host"], old_info.get("port", PORT),
                               hi.host, hi.port, hi.is_rsa)
                if hooks and hooks.on_failover:
                    hooks.on_failover(old_info, new_info)
                return

        logger.error("All hosts unreachable: %s", error)
        if hooks and hooks.on_disconnect:
            hooks.on_disconnect(old_info, error)


# ---------------------------------------------------------------------------
# Core HA connect (extended with retry + fallback chain)
# ---------------------------------------------------------------------------


def connect_opend(is_rsa: bool | None = None, *, retry_count=0, backoff_base=1.0):
    """
    TCP-probe all hosts, connect to fastest reachable one.

    is_rsa=True  → RSA mode only
    is_rsa=False → no-RSA mode only
    is_rsa=None  → auto: try RSA first, fallback without on failure
    retry_count  → number of retries on API connect failure (0 = no retry)
    backoff_base → seconds for exponential backoff: base * 2^attempt

    Returns (info_dict, actual_rsa, ranked_hosts).
    """
    logger.info("connect_opend: probing %d hosts (is_rsa=%s)", len(HOSTS), is_rsa)

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

    sorted_hosts = sorted(reachable.items(), key=lambda x: x[1][0])

    ranked_hosts = []
    for (h, p), (tcp_ms, rsa_flag) in sorted_hosts:
        ranked_hosts.append(_HostInfo(
            host=h, port=p, is_rsa=rsa_flag,
            tcp_latency=tcp_ms, api_latency=None,
        ))

    max_retries = 1 + retry_count

    for attempt in range(max_retries):
        for hi in ranked_hosts:
            host_rsa = is_rsa if is_rsa is not None else hi.is_rsa
            rsa_mode = host_rsa if host_rsa is not None else True
            ok, data, api_lat = try_connect(hi.host, hi.port, is_rsa=rsa_mode)
            actual_rsa = rsa_mode

            if not ok and is_rsa is None:
                fallback_rsa = not rsa_mode
                label = "RSA OFF→ON" if rsa_mode else "RSA ON→OFF"
                logger.debug("  Primary RSA failed for %s:%s, trying %s", hi.host, hi.port, label)
                ok, data, api_lat = try_connect(hi.host, hi.port, is_rsa=fallback_rsa)
                actual_rsa = fallback_rsa

            if ok:
                hi.api_latency = api_lat
                info = {
                    "name": hi.host,
                    "host": hi.host,
                    "port": hi.port,
                    "tcp_ms": hi.tcp_latency,
                    "api_ms": api_lat,
                    "server_ver": data.get("server_ver", "?"),
                    "quote_login": data.get("qot_logined", "?"),
                    "trade_login": data.get("trd_logined", "?"),
                    "market_hk": data.get("market_hk", "?"),
                    "market_us": data.get("market_us", "?"),
                    "market_sh": data.get("market_sh", "?"),
                    "market_sz": data.get("market_sz", "?"),
                }
                logger.info(
                    "  Connected to %s:%s (API %.1fms, RSA=%s)  server_ver=%s",
                    hi.host, hi.port, api_lat, actual_rsa,
                    data.get("server_ver", "?"),
                )
                return info, actual_rsa, ranked_hosts

            hi.last_error = str(data)
            hi.failure_count += 1
            logger.debug("  Failed %s:%s (RSA=%s): %s", hi.host, hi.port, actual_rsa, data)

        if attempt < max_retries - 1:
            delay = backoff_base * (2 ** attempt)
            logger.info("  All hosts failed, retrying in %.1fs (attempt %d/%d)",
                        delay, attempt + 1, max_retries)
            time.sleep(delay)

    raise RuntimeError("Failed to connect to any host")


# ---------------------------------------------------------------------------
# Cache management
# ---------------------------------------------------------------------------


def clear_connection_cache():
    global _cached_probe_result, _cached_ranked_hosts
    _stop_health_monitor()
    with _connection_lock:
        logger.debug("Clearing connection cache")
        _cached_probe_result = None
        _cached_ranked_hosts = []


# ---------------------------------------------------------------------------
# Public API: context factories
# ---------------------------------------------------------------------------


def create_quote_context(is_rsa: bool | None = None, *,
                         _use_cache=True,
                         health_monitor=False,
                         retry_count=0,
                         backoff_base=1.0,
                         hooks=None):
    global _cached_probe_result, _cached_ranked_hosts, _hooks
    if _use_cache and _cached_probe_result is not None:
        with _connection_lock:
            info, actual_rsa = _cached_probe_result
        configure_rsa(enable=actual_rsa)
        logger.info("create_quote_context: reusing cached connection to %s:%s",
                    info["host"], info["port"])
        ctx = OpenQuoteContext(host=info["host"], port=info.get("port", PORT))
        return ctx

    info, actual_rsa, ranked = connect_opend(
        is_rsa=is_rsa, retry_count=retry_count, backoff_base=backoff_base,
    )
    with _connection_lock:
        _cached_probe_result = (info, actual_rsa)
        _cached_ranked_hosts = ranked
        _hooks = hooks
    configure_rsa(enable=actual_rsa)
    logger.info("create_quote_context: new connection to %s:%s (RSA=%s)",
                info["host"], info["port"], actual_rsa)
    ctx = OpenQuoteContext(host=info["host"], port=info.get("port", PORT))

    if hooks and hooks.on_connect:
        hooks.on_connect(info)
    if health_monitor:
        _start_health_monitor()

    return ctx


def create_trade_context(is_rsa: bool | None = None, *,
                         _use_cache=True,
                         health_monitor=False,
                         retry_count=0,
                         backoff_base=1.0,
                         hooks=None,
                         **kwargs):
    from futu import OpenSecTradeContext
    global _cached_probe_result, _cached_ranked_hosts, _hooks
    if _use_cache and _cached_probe_result is not None:
        with _connection_lock:
            info, actual_rsa = _cached_probe_result
        configure_rsa(enable=actual_rsa)
        logger.info("create_trade_context: reusing cached connection to %s:%s (RSA=%s)",
                    info["host"], info["port"], actual_rsa)
        return OpenSecTradeContext(host=info["host"], port=info.get("port", PORT), **kwargs)

    info, actual_rsa, ranked = connect_opend(
        is_rsa=is_rsa, retry_count=retry_count, backoff_base=backoff_base,
    )
    with _connection_lock:
        _cached_probe_result = (info, actual_rsa)
        _cached_ranked_hosts = ranked
        _hooks = hooks
    configure_rsa(enable=actual_rsa)
    logger.info("create_trade_context: new connection to %s:%s (RSA=%s)",
                info["host"], info["port"], actual_rsa)
    ctx = OpenSecTradeContext(host=info["host"], port=info.get("port", PORT), **kwargs)

    if hooks and hooks.on_connect:
        hooks.on_connect(info)
    if health_monitor:
        _start_health_monitor()

    return ctx


def get_demo_trade_password():
    return DEMO_TRADE_PASSWORD
