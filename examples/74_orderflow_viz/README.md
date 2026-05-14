# 74 — Order Flow Imbalance Visualizer

**Category**: Market Microstructure / Real-Time

Extends 56_order_flow_imbalance by rendering a live ASCII bar chart of net
bid/ask aggression in the terminal. Pure stdlib — no plotly/matplotlib.

## How It Works

1. Subscribes to ORDER_BOOK push for a single stock (default: HK.00700).
2. On each book update, sums bid volumes and ask volumes across all levels.
3. Computes imbalance ratio: `(bid_vol - ask_vol) / (bid_vol + ask_vol)`.
4. Maintains a rolling window of imbalance values.
5. Renders an ASCII chart showing the last 40 imbalance readings.
6. Updates throttled to configurable interval (default: 500ms).

## ASCII Chart Guide

```
  ▲ Current: +0.150
  Mean: +0.030  Min: -0.400  Max: +0.600

  ASK ◄················│████················ BID
  ░░░░░░░░░░░░░░░░░░░░░│░░░░░░░░░░░░░░░░░░░░░
  ░░░░░░░░░░░░░░░░░░░░░│░░░░░░░░░█░░░░░░░░░░░
  ░░░░░░░░░░░░░░░░░░█░░│░░░░░░░░░░░░░░░░░░░░░
  ░░░░░░░░░░░░░░░░░░░░░│░░░░░░░░░░░░░░░░░░░░░

  ▼ = ask-heavy (selling pressure)
  ▲ = bid-heavy (buying pressure)
```

## Usage

```bash
python3 main.py                         # defaults to HK.00700
python3 main.py --stock HK.00700 --window 100 --throttle 0.5
```

## Key Concepts Demonstrated

- `OrderBookHandlerBase` push subscription
- Real-time bid/ask aggregation across all levels
- Rolling window via `collections.deque(maxlen=...)`
- Terminal ASCII rendering with ANSI colors
- Throttled display updates

## Configuration

| Flag | Default | Description |
|------|---------|-------------|
| `--stock` | `HK.00700` | Stock ticker |
| `--window` | `100` | Rolling window size |
| `--throttle` | `0.5` | Min seconds between display refreshes |