# 81 — Portfolio Rebalancing Bot

**Category**: Risk Management (SIMULATE)

Compares current portfolio allocation against target weights and places trades to bring the portfolio back in line. Runs continuously with configurable check intervals.

## How It Works

1. Fetches current positions via `position_list_query`.
2. Gets live prices via `get_stock_quote` for each target.
3. Computes current weights vs target weights.
4. If any position drifts beyond threshold, places market orders to rebalance.
5. Loops indefinitely until interrupted.
6. SIMULATE only. `cancel_all_order` in `finally`.

## Usage

```bash
python3 main.py
python3 main.py --targets '{"HK.00700":0.5,"US.TCEHY":0.3,"HK.00005":0.2}' --interval 120
```

## Key Concepts Demonstrated

- `position_list_query` for live portfolio data
- `accinfo_query` for account equity
- Multi-asset rebalancing logic
- JSON config for target weights
- Periodic execution loop
- SIMULATE-only with proper cleanup

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--targets` | `{"HK.00700":0.4,"US.TCEHY":0.3,"HK.00005":0.3}` | Target weights (JSON) |
| `--threshold` | `0.05` | Rebalance when drift > 5% |
| `--interval` | `60` | Check interval in seconds |