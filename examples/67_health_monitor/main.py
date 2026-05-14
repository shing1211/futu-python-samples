#!/usr/bin/env python3
"""
67 — Connection Health Monitor

Watchdog that polls OpenD connection health metrics at regular intervals.
Logs latency, subscription quota, K-line quota, market status, and alerts
when thresholds are breached.

Useful for:
  - Verifying gateway stability before running a long-lived bot
  - Detecting silent connection degradation (latency creep)
  - Monitoring subscription quota exhaustion

SDK: OpenQuoteContext.get_delay_statistics()
               .get_global_state()
               .query_subscription()
               .get_history_kl_quota()
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 30
LATENCY_WARN_MS = 500
SUBS_WARN_PCT = 80
QUOTA_WARN_REMAIN = 10


class HealthMonitor:
    def __init__(self, ctx):
        self.ctx = ctx
        self.start_ts = time.time()
        self.latencies: list[float] = []
        self.alerts: list[str] = []

    @property
    def uptime(self) -> float:
        return time.time() - self.start_ts

    def poll(self):
        now = time.time()
        t = int(now - self.start_ts)

        latency = None
        try:
            ret, stats = self.ctx.get_delay_statistics()
            if ret == ft.RET_OK and isinstance(stats, dict):
                latency = float(stats.get("delay_ms", stats.get("avg_delay_ms", 0)))
                self.latencies.append(latency)
        except Exception:
            pass

        state = {}
        try:
            ret, data = self.ctx.get_global_state()
            if ret == ft.RET_OK and isinstance(data, dict):
                state = data
        except Exception:
            pass

        subs_used = subs_total = None
        try:
            ret, sub_data = self.ctx.query_subscription(is_all_conn=True)
            if ret == ft.RET_OK and isinstance(sub_data, dict):
                subs_used = sub_data.get("total_used", sub_data.get("used", 0))
                subs_total = sub_data.get("total", sub_data.get("quota", 0))
        except Exception:
            pass

        quota_used = quota_remain = None
        try:
            ret, quota_data = self.ctx.get_history_kl_quota(get_detail=False)
            if ret == ft.RET_OK:
                if isinstance(quota_data, tuple) and len(quota_data) >= 2:
                    quota_used, quota_remain = quota_data[0], quota_data[1]
                elif isinstance(quota_data, dict):
                    quota_used = quota_data.get("used_quota")
                    quota_remain = quota_data.get("remain_quota")
        except Exception:
            pass

        ver = state.get("server_ver", "?")
        hk = state.get("market_hk", "?")
        us = state.get("market_us", "?")
        sh = state.get("market_sh", "?")
        sz = state.get("market_sz", "?")

        parts = [f"[T+{t:04d}s]"]
        if latency is not None:
            parts.append(f"latency={latency:.0f}ms")
        else:
            parts.append("latency=N/A")
        parts.append(f"ver={ver}")
        if subs_used is not None and subs_total:
            parts.append(f"subs={subs_used}/{subs_total}")
        if quota_used is not None and quota_remain is not None:
            parts.append(f"klquota={quota_remain}")
        parts.append(f"hk={hk} us={us} sh={sh} sz={sz}")
        print("  " + " | ".join(parts))

        if latency is not None and latency > LATENCY_WARN_MS:
            msg = f"latency {latency:.0f}ms exceeds {LATENCY_WARN_MS}ms threshold"
            print(f"    ⚠ ALERT: {msg}")
            self.alerts.append(msg)

        if subs_used is not None and subs_total:
            pct = subs_used / subs_total * 100
            if pct > SUBS_WARN_PCT:
                msg = f"subs {pct:.0f}% used ({subs_used}/{subs_total})"
                print(f"    ⚠ ALERT: {msg}")
                self.alerts.append(msg)

        if quota_remain is not None and quota_remain < QUOTA_WARN_REMAIN:
            msg = f"K-line quota remaining {quota_remain} below {QUOTA_WARN_REMAIN}"
            print(f"    ⚠ ALERT: {msg}")
            self.alerts.append(msg)

    def summary(self):
        print()
        print("  " + "=" * 50)
        print("  FINAL SUMMARY")
        print("  " + "=" * 50)
        print(f"  Uptime: {self.uptime:.0f}s")
        if self.latencies:
            print(f"  Latency: min={min(self.latencies):.0f}ms "
                  f"max={max(self.latencies):.0f}ms "
                  f"avg={sum(self.latencies)/len(self.latencies):.0f}ms "
                  f"({len(self.latencies)} samples)")
        if self.alerts:
            print(f"  Alerts triggered: {len(self.alerts)}")
            for a in self.alerts:
                print(f"    - {a}")
        else:
            print("  No alerts — connection healthy")


def main():
    print("  === Connection Health Monitor ===")
    print(f"  Interval: {POLL_INTERVAL}s")
    print(f"  Thresholds: latency > {LATENCY_WARN_MS}ms, "
          f"subs > {SUBS_WARN_PCT}%, quota < {QUOTA_WARN_REMAIN}\n")

    ctx = create_quote_context()
    monitor = HealthMonitor(ctx)

    print(f"  [T+0000s] Connecting...\n")

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            monitor.poll()
    except KeyboardInterrupt:
        pass
    finally:
        monitor.summary()
        ctx.close()


if __name__ == "__main__":
    main()
