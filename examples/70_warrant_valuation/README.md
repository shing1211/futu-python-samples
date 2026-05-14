# 70 — Warrant Valuation Dashboard

**Category**: Analytics / Screening

Pulls all warrants for a given underlying via `get_warrant()`, computes intrinsic value, time value, and a simplified BSM implied vol. Ranks by mispricing.

## Usage

```bash
python3 main.py HK.00700
```

## Key Concepts Demonstrated

- `get_warrant()` 3-tuple `(df, has_more, total)` handling + pagination
- Pure-Python Black-Scholes via `math.erf` (reuses approach from 58)
- Intrinsic/time value decomposition
- Implied vol via Newton-Raphson back-solve
- Cross-asset analysis (warrants vs underlying spot)