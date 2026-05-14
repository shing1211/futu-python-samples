# 77 — Iceberg Order Detector (Educational)

**Category**: Market Microstructure / Real-Time (Educational)

Monitors ORDER_BOOK push for patterns that suggest hidden "iceberg" orders —
large resting lots that repeatedly appear and partially fill. This is an
**educational heuristic exercise**, not production-grade detection.

## How It Works

1. Subscribes to ORDER_BOOK push for a target stock.
2. Tracks each price level's visible volume across updates.
3. Scores each level on four heuristics:
   - **Volume variance** — high coefficient of variation suggests hidden activity
   - **Roundness** — institutional sizes tend to be round lot multiples
   - **Persistence** — levels that survive many updates may be hiding depth
   - **Absolute size** — larger volumes are more interesting
4. Flags levels exceeding a configurable threshold (default 0.4).
5. Detects when large levels are consumed — possible iceberg exposure.

## ⚠️ Limitations

- Heuristic only — cannot prove an order is an iceberg
- No access to hidden order book data
- Thin markets produce unreliable signals
- For educational purposes only

## Usage

```bash
python3 main.py                         # defaults to HK.00700
python3 main.py --stock HK.00700 --threshold 0.4 --round-lot 100
```

## Key Concepts Demonstrated

- `OrderBookHandlerBase` push subscription
- Level-by-level order book tracking
- Volume analysis and variance computation
- Heuristic scoring system
- Educational market microstructure analysis

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock` | `HK.00700` | Stock ticker |
| `--threshold` | `0.4` | Iceberg score threshold (0–1) |
| `--round-lot` | `100` | Standard lot size for roundness detection |