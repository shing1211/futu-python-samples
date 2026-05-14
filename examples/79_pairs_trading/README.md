# 79 — Pairs Trading (Cointegration)

**Category**: Execution Strategy (SIMULATE)

Uses Engle-Granger cointegration to find a mean-reverting spread between two correlated stocks. Trades the spread when it diverges beyond ±2σ.

## How It Works

1. Fetches daily K-lines for both stocks (default: HK.00700 vs US.TCEHY).
2. Runs OLS regression to determine hedge ratio: `A = α + β × B + ε`.
3. Performs ADF test on residuals to check stationarity.
4. Monitors live spread via quote push; enters trade when z-score > threshold.
5. Exits when spread mean-reverts to within ±0.3σ.6. SIMULATE only. `cancel_all_order` in `finally`.

## Usage

```bash
python3 main.py                                    # defaults: HK.00700 vs US.TCEHY
python3 main.py --stock-a HK.00700 --stock-b HK.09988 --lookback 60
```

## Key Concepts Demonstrated

- OLS regression (pure Python)
- ADF stationarity test (simplified Dickey-Fuller)
- Hedge ratio calculation
- Z-score mean-reversion entry/exit
- SIMULATE-only with paired long/short legs

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock-a` | `HK.00700` | First stock |
| `--stock-b` | `US.TCEHY` | Second stock |
| `--lookback` | `60` | History window for cointegration |
| `--zscore` | `2.0` | Entry threshold |
| `--max-minutes` | `30` | Safety timeout |