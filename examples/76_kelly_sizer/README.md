# 76 — Kelly Criterion Position Sizer

**Category**: Risk Management (SIMULATE)

Analyzes historical SIMULATE trade results, computes the Kelly optimal fraction,
and sizes your next order accordingly. Includes half-Kelly and quarter-Kelly
options for more conservative sizing.

## Kelly Formula

```
f* = (p × b − q) / b

where:
  p  = win rate (wins / total trades)
  q  = loss rate (1 − p)
  b  = win/loss ratio (avg win ÷ avg loss)
  f* = fraction of capital to risk
```

## How It Works

1. Fetches historical order/fill records from the SIMULATE account.
2. Pairs consecutive BUY/SELL trades to compute round-trip P&L.
3. Calculates win rate, average win, average loss, and win/loss ratio.
4. Computes Kelly fraction (full, half, quarter).
5. Applies a 25% equity cap (quarter-Kelly) for safety.
6. Computes max shares based on a 2% ATR-based stop distance.
7. Prompts for confirmation before placing the order.

## Usage

```bash
python3 main.py                         # defaults to HK.00700
python3 main.py HK.00700 --fraction 0.5 --max-pct 0.25
```

Note: Run some SIMULATE trades first (e.g., examples 04 or 06) so there's
history to analyse.

## Key Concepts Demonstrated

- `history_order_list_query` for trade analysis
- Kelly Criterion with Laplace smoothing for small samples
- Half-Kelly / quarter-Kelly for risk reduction
- ATR-based stop distance for position sizing
- SIMULATE-only with `cancel_all_order` cleanup

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `code` | `HK.00700` | Stock ticker |
| `--fraction` | `0.5` | Kelly multiplier (0.5 = half-Kelly) |
| `--max-pct` | `0.25` | Max equity fraction to risk (25% cap) |