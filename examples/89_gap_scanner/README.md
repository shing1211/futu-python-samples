# 89 — Gap Scanner (Pre-Market)

**Category**: Screening

Detects overnight gaps by comparing prior close vs current open across all stocks in selected markets.

## How It Works

1. Gets stock list for each selected market.
2. Fetches quotes in batches to find current open vs prior close.
3. Computes gap percentage: `(Open − Prior Close) / Prior Close × 100`.
4. Flags stocks where `|gap| ≥ threshold`.
5. Renders ranked table sorted by absolute gap size.

## Usage

```bash
python3 main.py                            # defaults: HK + US, 3% gap threshold
python3 main.py --markets HK US --gap-pct 5.0
```

## Key Concepts Demonstrated

- Multi-market stock enumeration via `get_stock_list`
- Batch quote fetching with `get_stock_quote`
- Gap percentage computation
- Volume confirmation flag
- Multi-market scanning with configurable thresholds

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--markets` | `HK US` | Markets to scan |
| `--gap-pct` | `3.0` | Minimum gap % to flag |