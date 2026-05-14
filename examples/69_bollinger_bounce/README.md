# 69 — Bollinger Band Bounce

**Category**: Execution Strategy (SIMULATE)

Computes 20-period Bollinger Bands using pure `statistics` (no numpy). Enters a mean-reversion trade when price crosses ±2σ from the rolling mean.

## How It Works

1. Fetches historical daily K-lines via `request_history_kline` (handles pagination).
2. Computes rolling 20-period mean and standard deviation using `statistics.pstdev`.
3. Monitors the current (unfinished) bar via `get_cur_kline`.
4. **Long entry**: price drops below lower band (mean − 2σ).
5. **Exit target**: middle band (20-period mean).
6. **Stop**: upper band (mean + 2σ) — or opposite band breach.
7. All trades are SIMULATE. `cancel_all_order` in `finally`.

## Usage

```bash
python3 main.py                         # defaults to HK.00700, period=20, zscore=2.0
python3 main.py HK.00700 --period 50 --stdev 2.5
```

## Key Concepts Demonstrated

- Pure-Python Bollinger Bands via `statistics.pstdev`
- `request_history_kline` 3-tuple `(ret, df, next_page_token)` pagination
- `get_cur_kline` for real-time bar updates
- State machine: `IDLE → ENTERED → EXITING`
- SIMULATE-only with `cancel_all_order` cleanup

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `code` | `HK.00700` | Stock ticker |
| `--period` | `20` | Bollinger period |
| `--stdev` | `2.0` | Number of standard deviations for bands |
| `--max-minutes` | `10` | Safety timeout