# 83 — Dividend & Corporate Action Tracker

**Category**: Screening / Reference

Tracks upcoming dividends, ex-dates, and corporate actions (rights issues, splits, buybacks) for a configurable watchlist.

## Usage

```bash
python3 main.py                                    # defaults to 5 HK/US tickers
python3 main.py --watchlist 'HK.00700,HK.00941,US.TCEHY' --days-ahead 60
```

## Key Concepts Demonstrated

- `get_market_snapshot` for dividend yield and basic info
- `get_code_change_history` for stock splits and rights issues
- Multi-stock screening with configurable watchlist
- Clean tabular output for corporate action overview