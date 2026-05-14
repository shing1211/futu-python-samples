# 73 — Multi-Asset Correlation Tracker

**Category**: Advanced Analytics / Real-Time

Subscribes to 10+ tickers in parallel, maintains rolling 60-bar return series, computes a live Pearson correlation matrix, and flags pairs whose correlation has spiked or collapsed.

## How It Works

1. User provides a ticker list (defaults to 10 HK blue-chips).
2. Subscribes to CUR_KLINE push for all tickers simultaneously.
3. Collects close prices and computes log-returns in rolling 60-bar windows.
4. Computes Pearson correlation matrix across all pairs (pure `math` — no numpy).
5. Compares current correlations to a 20-bar baseline window.
6. Flags pairs where correlation has shifted by more than ±0.3.
7. Prints formatted matrix every 30 seconds + real-time spike alerts.

## Usage

```bash
python3 main.py
python3 main.py --tickers HK.00700 HK.09988 HK.03690 US.TCEHY
python3 main.py --window 100 --min-bars 30
```

## Key Concepts Demonstrated

- Multi-ticker batch subscription via `subscribe(code_list=[...])`
- `CurKlineHandlerBase` push handler
- Pure-Python Pearson correlation (`math.sqrt`, `sum`)
- Rolling window via `collections.deque(maxlen=...)`
- Spike detection via baseline comparison

## Default Tickers

```
HK.00700  HK.09988  HK.03690  HK.02318  HK.00941
HK.01024  HK.02020  HK.09618  HK.03692  HK.01810
```