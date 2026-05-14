# 88 — Stop-Loss / Take-Profit Engine

**Category**: Execution Strategy (SIMULATE)

Dual SL/TP framework with configurable risk-reward, partial exits, and trailing activation.

## How It Works

1. Places a market buy order for the target stock.
2. On fill, sets a stop-loss below entry and a take-profit above entry.
3. **TP1** (partial exit): Closes a configurable fraction (default 50%) at the TP price.
4. **TP2** (trail): Remaining shares trail with a tighter stop near breakeven.
5. If SL triggers first, the TP order is cancelled.

## Usage

```bash
python3 main.py                              # defaults: HK.00700, 1:2 R/R, 50% partial
python3 main.py --stock HK.00700 --risk-reward 3.0 --partial-exit 0.3
```

## Key Concepts Demonstrated

- Market entry + SL/TP order placement
- Partial position exit with remaining trailing
- Order status monitoring via `order_list_query`
- Dynamic stop replacement (cancel old, place new)
- SIMULATE enforcement with `cancel_all_order` cleanup

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock` | `HK.00700` | Stock ticker |
| `--risk-reward` | `2.0` | TP distance = RR × SL distance |
| `--partial-exit` | `0.5` | Fraction closed at TP1 |
| `--max-minutes` | `15` | Safety timeout |