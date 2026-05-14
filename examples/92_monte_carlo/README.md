# 92 — Monte Carlo Portfolio Simulator

**Category**: Risk Analysis

Runs 10,000 simulated portfolio paths using historical return distributions.
Outputs probability of loss, VaR, and expected range — pure stdlib, no numpy.

## How It Works

1. Fetches daily K-lines for each portfolio asset (default 1 year).
2. Computes daily log-returns and fits a historical distribution.
3. Runs 10,000 Monte Carlo simulations over N days (default 30).
4. Aggregates results: mean, median, VaR (95%/99%), probability of loss.
5. Renders an ASCII histogram of final portfolio value distribution.

## Usage

```bash
python3 main.py --symbols 'HK.00700,US.TCEHY,HK.00005' --days 30 --simulations 10000
```

## Key Concepts Demonstrated

- Historical return extraction via `request_history_kline`
- Portfolio return simulation via bootstrapping
- Value at Risk (VaR) computation
- Percentile analysis (1st, 5th, 25th, 50th, 75th, 90th, 95th, 99th)
- ASCII histogram rendering
- Inverse-volatility weighting (or equal-weight flag)

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--symbols` | `HK.00700,US.TCEHY,HK.00005` | Portfolio tickers |
| `--days` | `30` | Projection horizon |
| `--simulations` | `10000` | Number of Monte Carlo paths |
| `--history` | `252` | Lookback period for returns |
| `--equal-weight` | `False` | Use equal weights instead of inverse-vol |