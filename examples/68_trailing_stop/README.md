# 68 — Trailing Stop Execution

**Category**: Execution Strategy (SIMULATE)

Demonstrates a trailing stop-loss that follows the price favorably. When the price moves up, the stop tightens. When the price hits the stop, the position is exited.

## How It Works

1. Places a market buy order for `HK.00700` (or a code you specify).
2. Sets an initial stop at `entry_price × (1 − trail_pct)`.
3. Polls the latest price every 3 seconds:
   - If price rises, recalculates `new_stop = last_price × (1 − trail_pct)`.
   - If `new_stop` is meaningfully higher than the current stop, cancels the old stop and places a new one.
4. Exits when price ≤ stop, or after a configurable time limit.
5. `cancel_all_order` in `finally` — no orphaned orders.

## Usage

```bash
python3 main.py                         # defaults to HK.00700, 2 % trail, 5 min
python3 main.py HK.00700 --trail-pct 0.03 --max-minutes 10
```

## Key Concepts Demonstrated

- Dynamic order replacement (cancel → re-place)
- `OrderType.STOP` via the Futu SDK
- Position-fill detection via `order_list_query`
- SIMULATE-only with `cancel_all_order` cleanup
- Command-line arguments via `argparse`

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `code` | `HK.00700` | Stock ticker |
| `--trail-pct` | `0.02` | Trail width as fraction of price |
| `--max-minutes` | `5` | Safety timeout |