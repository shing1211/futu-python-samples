# 91 — Sector Rotation Scanner

**Category**: Screening / Analytics

Ranks all sector/industry plates by relative strength using RSI and price
momentum. Identifies leading and lagging sectors for rotation signals.

## How It Works

1. Fetches all plates for the selected market.
2. For each plate, fetches constituent stocks and computes aggregate RSI.
3. Ranks plates from oversold (RSI < 30) to overbought (RSI > 70).
4. Shows top gainers and losers within each plate.
5. Highlights rotation candidates (low RSI sectors with upward momentum).

## Usage

```bash
python3 main.py                              # defaults to HK market
python3 main.py --market HK --rsi-period 14
```

## Key Concepts Demonstrated

- `get_plate_list` and `get_plate_stock` for sector enumeration
- Pure-Python RSI computation via Wilder smoothing
- Multi-stock batch processing
- Sector ranking by relative strength
- Top mover identification within sectors

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--market` | `HK` | Market code: HK, US, SH, SZ |
| `--rsi-period` | `14` | RSI calculation period |
| `--lookback` | `30` | K-line lookback for RSI |