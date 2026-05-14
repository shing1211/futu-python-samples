# 75 — Futures Term Structure & Roll Yield

**Category**: Analytics / Screening

Dynamically discovers active futures contracts for an underlying, builds the term structure, computes annualised roll yield, and classifies contango/backwardation.

## How It Works

1. User provides a futures code stem (e.g., `HK.HHI` for Hang Seng Index Futures).
2. Dynamically discovers active contracts by iterating month codes.
3. Optionally enriches with expiry dates via `get_instrument_info`.
4. Renders an ASCII term structure chart showing prices across expiries.
5. Computes roll yield for each consecutive month pair:
   `roll_yield = (far_price - near_price) / near_price × (365 / days_to_expiry_diff)`
6. Classifies the curve: CONTANGO, BACKWARDATION, HUMPED, or IRREGULAR.

## Usage

```bash
python3 main.py HK.HHI     # Hang Seng Index Futures
python3 main.py HK.MHI     # MHI Futures
```

## Key Concepts Demonstrated

- Dynamic futures contract discovery via API (no hardcoded code lists)
- `get_market_snapshot` and `get_instrument_info` for contract metadata
- Annualised roll yield computation
- ASCII term structure visualization
- Pure stdlib — no external plotting libraries

## Roll Yield Interpretation

| Regime | Meaning |
|--------|---------|
| CONTANGO | Far month trades at premium (normal market) |
| BACKWARDATION | Far month trades at discount (supply tight) |
| HUMPED | Maximum or minimum in the middle of the curve |
| IRREGULAR | No clear shape |