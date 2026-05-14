# 94 — Earnings Surprise Analyzer

**Category**: Event-Driven Screening

Compares actual vs estimated EPS from financial reports. Flags post-earnings
unusual activity and provides options IV context.

## How It Works

1. Fetches financial reports via `get_financial_report` or `get_income_statement`.
2. Compares reported EPS vs estimated (based on prior quarters).
3. Computes surprise percentage and classifies as Beat/Miss/In-line.
4. Checks post-earnings K-lines for volume spikes and gaps.
5. Displays nearest ATM option for IV context.

## Usage

```bash
python3 main.py --codes HK.00700,US.TCEHY   # specific stocks
python3 main.py --market HK                   # scan entire market
```

## Key Concepts Demonstrated

- `get_financial_report` / `get_income_statement` for earnings data
- EPS surprise computation
- Post-earnings price action analysis
- Volume spike and gap detection
- Options chain overview for IV context

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--market` | `HK` | Market to scan |
| `--surprise-threshold` | `10` | Min earnings surprise % to flag |
| `--codes` | `None` | Specific stock codes (comma-separated) |