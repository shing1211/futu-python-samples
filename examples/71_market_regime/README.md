# 71 — Market Regime Detector (ADX + Vol)

**Category**: Advanced Analytics / Real-Time

Computes ADX (Average Directional Index) and rolling volatility from live K-lines to classify the market regime: TRENDING, RANGING, or HIGH-VOL BREAKOUT.

## How It Works

1. Fetches historical daily K-lines via `request_history_kline` (handles pagination).
2. Computes ADX using Wilder smoothing (pure stdlib — no TA-Lib).
3. Computes rolling annualised realised volatility.
4. Subscribes to CUR_KLINE for real-time bar updates.
5. On each new bar: recomputes ADX + vol, classifies regime:
   - **TRENDING** — ADX > 25 and DI ratio > 1.3
   - **RANGING** — ADX < 20
   - **BREAKOUT** — vol > 2× median and ADX rising
6. Prints formatted regime label every 30 seconds.

## Usage

```bash
python3 main.py                         # defaults to HK.00700, ADX period=14
python3 main.py --stock HK.00700 --period 14 --window 100
```

## Key Concepts Demonstrated

- Wilder smoothing (standard ADX calculation)
- `CurKlineHandlerBase` push subscription
- Rolling volatility via `statistics.pstdev`
- State classification with hysteresis thresholds
- No numpy/pandas required

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock` | `HK.00700` | Stock ticker |
| `--period` | `14` | ADX period |
| `--window` | `100` | Rolling window for vol baseline |