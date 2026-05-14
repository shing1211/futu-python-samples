# 90 — AH Premium/Discount Tracker

**Category**: Cross-Market Analytics

Compares A-share vs H-share prices for dual-listed companies. Computes the
premium/discount ratio in real time after FX conversion.

## How It Works

1. Pairs A-share codes with their H-share dual-listing counterparts.
2. Fetches live quotes for both sides of each pair.
3. Converts A-share price to HKD using approximate FX rate.
4. Computes premium: `(A_HKD / H_price) - 1`.
5. Fetches 30-day historical premiums for trend context.
6. Renders ASCII premium trend chart.

## Usage

```bash
python3 main.py                          # defaults to 5 AH pairs
python3 main.py --pairs 10               # show more pairs
```

## Key Concepts Demonstrated

- Cross-market dual-listing comparison
- FX-adjusted price comparison
- Historical premium/discount trend
- ASCII sparkline rendering
- Multi-market quote fetching

## Default Pairs

| A-Share | H-Share | Company |
|---------|---------|---------|
| SH.600519 | HK.08592 | Kweichow Moutai |
| SH.601318 | HK.02358 | Ping An Insurance |
| SH.601398 | HK.01398 | ICBC |
| SH.601988 | HK.04613 | Bank of China |
| SH.600276 | HK.06186 | Hengrui Medicine |

Note: FX rate is approximate (1 CNY ≈ 1.088 HKD). For production, use a live FX feed.