# 67 — Connection Health Monitor

Watchdog that polls OpenD connection health metrics at regular intervals: latency, subscription usage, K-line quota, market states. Alerts when thresholds are breached.

**SDK APIs used:** `get_delay_statistics()`, `get_global_state()`, `query_subscription()`, `get_history_kl_quota()`

**Risk:** None — read-only, lightweight polling.

```bash
python3 examples/67_health_monitor/main.py
```
