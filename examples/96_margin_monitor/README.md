# 96 — Margin Utilization Monitor

**Category**: Risk Management (SIMULATE)

Tracks real-time margin usage across positions, alerts on margin call proximity,
and computes liquidation prices.

## How It Works

1. Fetches current positions via `position_list_query`.
2. Gets live prices via `get_stock_quote`.
3. Queries trading info via `acctradinginfo_query` for margin ratios and lot sizes.
4. Computes utilization = margin_required / total_equity.
5. Estimates liquidation price based on maintenance margin assumptions.
6. Renders color-coded utilization bars (green < 50%, yellow < 80%, red ≥ 80%).
7. Polls continuously until interrupted.

## Usage

```bash
python3 main.py                              # defaults: HK.00700, US.TCEHY, HK.00005
python3 main.py --symbols HK.00700,US.TCEHY --margin-threshold 0.75
```

## Key Concepts Demonstrated

- `position_list_query` for live holdings
- `accinfo_query` for account equity
- `acctradinginfo_query` for margin parameters
- Liquidation price estimation
- Color-coded terminal output with ANSI escapes
- Continuous monitoring with configurable polling interval

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--symbols` | `HK.00700,US.TCEHY,HK.00005` | Monitored tickers |
| `--margin-threshold` | `0.80` | Alert threshold (80% default) |