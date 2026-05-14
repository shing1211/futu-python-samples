# 72 — Candlestick Pattern Scanner

**Category**: Technical Analysis / Screening

Pure-Python recognition of 9 classic candlestick patterns on live K-line data. No ML, no external deps — just geometry and heuristics.

## Patterns Detected

| Pattern | Bars | Signal |
|---------|------|--------|
| ⚖️ Doji | 1 | Indecision (bias from shadow direction) |
| 🔨 Hammer | 1 | Bullish reversal (after downtrend) |
| 🌠 Shooting Star | 1 | Bearish reversal (after uptrend) |
| 🟢 Bullish Engulfing | 2 | Strong bullish reversal |
| 🔴 Bearish Engulfing | 2 | Strong bearish reversal |
| 🌅 Morning Star | 3 | Bullish reversal |
| 🌆 Evening Star | 3 | Bearish reversal |
| 📈 Three White Soldiers | 3 | Bullish continuation |
| 📉 Three Black Crows | 3 | Bearish continuation |

## How It Works

1. Fetches historical K-lines via `request_history_kline` for warmup.
2. Subscribes to CUR_KLINE push for real-time bar completion.
3. On each new bar, runs all 9 pattern detectors on the trailing window.
4. Confidence scoring combines pattern strictness + trend alignment + volume.
5. Cooldown timer prevents duplicate alerts (configurable, default 5 bars).

## Confidence Scoring

- **Base**: Pattern geometric strictness (0–1)
- **Trend bonus**: +0.15 max if pattern aligns with rolling slope
- **Trend penalty**: −0.10 if pattern contradicts trend
- Final confidence clamped to [0%, 100%]

## Usage

```bash
python3 main.py                         # defaults to HK.00700
python3 main.py --stock HK.00700 --lookback 30
```

## Key Concepts Demonstrated

- 9 pattern detectors as pure functions
- `CurKlineHandlerBase` push subscription
- Confidence scoring with trend confirmation
- Cooldown-based alert deduplication
- Pure stdlib (no TA-Lib, no sklearn)