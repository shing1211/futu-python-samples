# 86 — Market Breadth Dashboard

**Category**: Screening / Analytics

Tracks market breadth indicators across multiple markets: advancing/declining
issues, new highs/lows, volume distribution, and sector participation.

## How It Works

1. Fetches the full stock list for each selected market.
2. Pulls quotes in batches to classify each stock as advancing/declining/unchanged.
3. Computes breadth indicators: Adv/Dec ratio, McClellan Oscillator, volume distribution.
4. Displays sector-level breakdown within each market.

## Usage

```bash
python3 main.py                              # defaults to HK,US
python3 main.py --markets HK,US,SH,SZ
```

## Key Concepts Demonstrated

- `get_stock_list` and `get_stock_quote` batch processing
- Market breadth computation (pure stdlib)
- McClellan Oscillator approximation
- ASCII bar chart rendering
- Multi-market screening