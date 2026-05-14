# 85 — Options Volatility Skew Scanner

**Category**: Screening / Analytics

Scans option chains to compute implied volatility across strikes and expiries,
identifying mispriced options and displaying the vol surface.

## How It Works

1. Fetches the full option chain via `get_option_chain` with pagination.
2. Classifies each contract as CALL or PUT via name/code heuristics.
3. Computes implied vol via Newton-Raphson back-solve using Black-Scholes.
4. Groups results by expiry and displays skew tables.
5. Highlights the vol smile bottom and overall skew spread.

## Usage

```bash
python3 main.py                         # defaults to HK.00700
python3 main.py --stock HK.00700 --min-oi 100
```

## Key Concepts Demonstrated

- `get_option_chain` with pagination
- Black-Scholes implied vol via Newton-Raphson (pure `math.erf`)
- Moneyness classification (ATM/OTM/ITM)
- Vol skew visualization via formatted tables
- Pure stdlib — no numpy/scipy