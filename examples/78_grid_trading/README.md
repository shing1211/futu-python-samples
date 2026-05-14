# 78 — Grid Trading Bot

**Category**: Execution Strategy (SIMULATE)

Automated buy-low/sell-high within a defined price range. Places limit orders at evenly spaced grid levels and refills them when filled.

## How It Works

1. Fetches current price for the target stock.
2. Builds evenly spaced grid levels around the current price.
3. Places BUY orders below center, SELL orders above center.
4. Monitors fills — when an order fills, replaces it with an opposite-side order at the same level.
5. `cancel_all_order` in `finally`.

## Usage

```bash
python3 main.py                              # defaults: HK.00700, 10 grids, 10% range
python3 main.py HK.00700 --grids 10 --range-pct 0.15 --qty-per-grid 100
```

## Key Concepts Demonstrated

- Limit order placement and monitoring
- Dynamic order replacement on fill
- Grid-based market making strategy
- SIMULATE-only with proper cleanup

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock` | `HK.00700` | Stock ticker |
| `--grids` | `10` | Number of grid levels |
| `--range-pct` | `0.10` | Total price range as fraction |
| `--qty-per-grid` | `100` | Quantity per grid level |
| `--max-minutes` | `30` | Safety timeout |