# 87 — Smart Watchlist with Price & Technical Alerts

**Category**: Screening / Real-Time Monitoring

Monitors a configurable watchlist for price-level and technical indicators,
firing alerts when conditions are met. Pure stdlib — no external deps.

## Alert Types

| Alert | Trigger | Cooldown |
|-------|---------|----------|
| **Price Above** | Price ≥ configured target | 60s |
| **Price Below** | Price ≤ configured target | 60s |
| **RSI Overbought** | RSI > 70 | 300s |
| **RSI Oversold** | RSI < 30 | 300s |
| **Bollinger Upper** | Price ≥ upper band | 300s |
| **Bollinger Lower** | Price ≤ lower band | 300s |

## Usage

```bash
python3 main.py                                    # defaults to 4 HK/US tickers, all alerts
python3 main.py --symbols HK.00700,HK.09988 --alert-price --alert-rsi --alert-bb
python3 main.py --config targets.json              # load price targets from JSON
```

## JSON Config Format

```json
{
  "HK.00700": {"above": 400.0, "below": 300.0},
  "US.TCEHY": {"above": 80.0, "below": 60.0}
}
```

## Key Concepts Demonstrated

- RSI computation via pure Python (Wilder smoothing)
- Bollinger Bands via `statistics` module
- Price target alerting with cooldown
- Periodic polling loop with configurable interval
- Clean terminal output with live status