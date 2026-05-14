# 84 — VWAP Execution Analysis

**Category**: Execution Analysis (SIMULATE)

Compares your execution prices against Volume-Weighted Average Price (VWAP)
to measure execution quality. Computes slippage, timing cost, and shows a
time-bucketed visual breakdown.

## How It Works

1. Load trade fills from CSV files (or generate sample data with `--generate-sample`).
2. Compute VWAP = Σ(price × qty) / Σ(qty).
3. Calculate slippage per trade and aggregate cost impact.
4. Bucket trades by time window to identify optimal execution times.
5. Optionally run live VWAP analysis using real-time market data.

## Usage

```bash
python3 main.py --generate-sample                    # create sample CSVs
python3 main.py --buy-trades sample_buy.csv           # analyse buy fills
python3 main.py --buy-trades sample_buy.csv --sell-trades sample_sell.csv
python3 main.py --live --stock HK.00700               # live VWAP from market data
```

## Key Concepts Demonstrated

- VWAP computation from fill data
- Slippage analysis (per-trade and aggregate)
- Time-bucketed execution quality breakdown
- ASCII bar chart rendering (no dependencies)
- Live market data integration

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--buy-trades` | `None` | CSV file with buy fills |
| `--sell-trades` | `None` | CSV file with sell fills |
| `--generate-sample` | `False` | Create sample CSV files |
| `--stock` | `HK.00700` | Ticker for live mode |
| `--live` | `False` | Run live VWAP analysis |