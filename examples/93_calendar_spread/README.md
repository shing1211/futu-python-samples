# 93 — Options Calendar Spread Builder

**Category**: Execution Strategy (SIMULATE)

Constructs calendar spreads by finding options at the same strike with
different expiries. Computes theoretical edge from vol differential and
time decay.

## How It Works

1. Fetches the full option chain via `get_option_chain`.
2. Groups contracts by (strike, call/put type).
3. For each group with multiple expiries, compares implied vols.
4. Ranks opportunities by annualised edge from vol spread.
5. Offers interactive execution: sell near-term, buy longer-term.

## Usage

```bash
python3 main.py --stock HK.00700
python3 main.py --stock HK.00700 --strike-offset 0.02
```

## Key Concepts Demonstrated

- `get_option_chain` with pagination
- Black-Scholes implied vol via Newton-Raphson
- Calendar spread opportunity identification
- Interactive trade execution on SIMULATE
- Multi-leg order placement

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock` | `HK.00700` | Underlying stock |
| `--strike-offset` | `0.0` | Strike offset from ATM (as fraction) |
| `--max-minutes` | `10` | Safety timeout |