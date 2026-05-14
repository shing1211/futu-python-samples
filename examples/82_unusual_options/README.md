# 82 — Unusual Options Activity Scanner

**Category**: Screening

Scans options chains for large block trades and unusual volume spikes,
flagging contracts where current volume significantly exceeds historical
averages — suggesting institutional activity.

## How It Works

1. Fetches the full option chain for a given underlying via `get_option_chain`.
2. For each contract above a minimum volume threshold:
   - Fetches historical K-lines via `request_history_kline`
   - Computes a volume ratio (current vs historical average)
   - Classifies moneyness (ATM/ITM/OTM)
3. Flags contracts exceeding the volume ratio threshold.
4. Also checks real-time ticker for additional volume context.

## Usage

```bash
python3 main.py                              # defaults to HK.00700
python3 main.py --stock HK.00700 --ratio 3.0 --min-volume 50
```

## Key Concepts Demonstrated

- `get_option_chain` with pagination across all expiry/ strike/ type combos
- Historical volume comparison per contract
- Moneyness classification
- Real-time ticker cross-reference
- Pure stdlib — no external analysis libraries

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock` | `HK.00700` | Underlying stock ticker |
| `--ratio` | `3.0` | Volume ratio to flag as unusual |
| `--min-volume` | `50` | Minimum volume to consider |