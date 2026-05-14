# 97 — VWAP Anchored Trading Levels

**Category**: Execution Strategy (SIMULATE)

Uses session VWAP as dynamic support/resistance. Generates buy signals when
price touches lower VWAP bands and sell signals at upper bands, with volume
confirmation.

## How It Works

1. Computes running VWAP from 1-minute K-line data using typical price.
2. Calculates VWAP bands at ±N standard deviations (default 2σ).
3. Generates signals:
   - **BUY**: price touches lower band with volume confirmation
   - **SELL**: price touches upper band with volume confirmation
   - **CLOSE**: price returns to VWAP (take profit)
4. Places SIMULATE orders on signal triggers.

## Usage

```bash
python3 main.py                              # defaults to HK.00700, ±2σ bands
python3 main.py --stock HK.00700 --bands 1.5 --max-minutes 30
```

## Key Concepts Demonstrated

- Running VWAP computation from tick data
- Standard deviation band calculation
- Signal generation with volume confirmation
- Session-based trading (resets daily)
- SIMULATE order placement with proper cleanup

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock` | `HK.00700` | Stock ticker |
| `--bands` | `2.0` | Standard deviation band width |
| `--max-minutes` | `30` | Safety timeout |