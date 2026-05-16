"""Candlestick Pattern Scanner — Pure Python pattern recognition.

Scans the latest N bars for classic candlestick patterns. Uses ticker/CurKline
push for real-time bar completion detection. No ML, no external deps.

Patterns: Doji, Hammer, Shooting Star, Bullish/Bearish Engulfing,
          Morning/Evening Star, Three White Soldiers/Black Crows.

Usage:
    python3 main.py [--stock HK.00700] [--lookback 30]
"""

import sys
import logging
import argparse
from collections import deque

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connect import create_quote_context, clear_connection_cache
import futu as ft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DEFAULT_STOCK = "HK.00700"
DEFAULT_LOOKBACK = 30
COOLDOWN_BARS = 5  # suppress duplicate pattern alerts for N bars
TRD_ENV = ft.TrdEnv.SIMULATE


# ---------------------------------------------------------------------------
# Bar helper
# ---------------------------------------------------------------------------

def body_size(bar):
    return abs(bar["close"] - bar["open"])


def upper_shadow(bar):
    return bar["high"] - max(bar["open"], bar["close"])


def lower_shadow(bar):
    return min(bar["open"], bar["close"]) - bar["low"]


def bar_range(bar):
    return bar["high"] - bar["low"]


def is_bullish(bar):
    return bar["close"] >= bar["open"]


def is_bearish(bar):
    return bar["close"] < bar["open"]


# ---------------------------------------------------------------------------
# Pattern detectors
# Each returns (detected: bool, confidence: float, direction: str or None)
# ---------------------------------------------------------------------------

def detect_doji(window, idx):
    """Bar at idx is a doji: tiny body relative to range."""
    bar = window[idx]
    br = bar_range(bar)
    if br < 1e-8:
        return False, 0, None
    ratio = body_size(bar) / br
    if ratio < 0.1:
        # Direction from shadow bias
        if upper_shadow(bar) > lower_shadow(bar):
            return True, min(1.0, 0.6 + (1 - ratio) * 0.4), "bearish"
        else:
            return True, min(1.0, 0.6 + (1 - ratio) * 0.4), "bullish"
    return False, 0, None


def detect_hammer(window, idx):
    """Hammer / hanging man: small body at top, long lower shadow."""
    bar = window[idx]
    br = bar_range(bar)
    bs = body_size(bar)
    ls = lower_shadow(bar)
    us = upper_shadow(bar)
    if br < 1e-8 or bs < 1e-8:
        return False, 0, None
    if ls >= 2 * bs and us <= bs * 0.5:
        conf = min(1.0, 0.5 + ls / br * 0.3)
        direction = "bullish" if idx > len(window) // 2 else "neutral"
        return True, conf, direction
    return False, 0, None


def detect_shooting_star(window, idx):
    """Shooting star: small body at bottom, long upper shadow."""
    bar = window[idx]
    br = bar_range(bar)
    bs = body_size(bar)
    us = upper_shadow(bar)
    ls = lower_shadow(bar)
    if br < 1e-8 or bs < 1e-8:
        return False, 0, None
    if us >= 2 * bs and ls <= bs * 0.5:
        conf = min(1.0, 0.5 + us / br * 0.3)
        return True, conf, "bearish"
    return False, 0, None


def detect_bullish_engulfing(window, idx):
    """Two-bar: second green body engulfs first red body."""
    if idx < 1:
        return False, 0, None
    prev, curr = window[idx - 1], window[idx]
    if not is_bearish(prev) or not is_bullish(curr):
        return False, 0, None
    if curr["open"] <= prev["close"] and curr["close"] >= prev["open"]:
        conf = min(1.0, 0.6 + body_size(curr) / max(bar_range(prev), 1e-8) * 0.4)
        return True, conf, "bullish"
    return False, 0, None


def detect_bearish_engulfing(window, idx):
    """Two-bar: second red body engulfs first green body."""
    if idx < 1:
        return False, 0, None
    prev, curr = window[idx - 1], window[idx]
    if not is_bullish(prev) or not is_bearish(curr):
        return False, 0, None
    if curr["open"] >= prev["close"] and curr["close"] <= prev["open"]:
        conf = min(1.0, 0.6 + body_size(curr) / max(bar_range(prev), 1e-8) * 0.4)
        return True, conf, "bearish"
    return False, 0, None


def detect_morning_star(window, idx):
    """Three-bar: long red, small body, long green (bullish reversal)."""
    if idx < 2:
        return False, 0, None
    b1, b2, b3 = window[idx - 2], window[idx - 1], window[idx]
    if not is_bearish(b1) or not is_bullish(b3):
        return False, 0, None
    body1 = body_size(b1)
    body2 = body_size(b2)
    body3 = body_size(b3)
    if body2 > body1 * 0.5 or body2 > body3 * 0.5:
        return False, 0, None  # middle bar should be small
    if b3["close"] > (b1["open"] + b1["close"]) / 2:
        conf = min(1.0, 0.55 + body3 / max(body1, 1e-8) * 0.3)
        return True, conf, "bullish"
    return False, 0, None


def detect_evening_star(window, idx):
    """Three-bar: long green, small body, long red (bearish reversal)."""
    if idx < 2:
        return False, 0, None
    b1, b2, b3 = window[idx - 2], window[idx - 1], window[idx]
    if not is_bullish(b1) or not is_bearish(b3):
        return False, 0, None
    body1 = body_size(b1)
    body2 = body_size(b2)
    body3 = body_size(b3)
    if body2 > body1 * 0.5 or body2 > body3 * 0.5:
        return False, 0, None
    if b3["close"] < (b1["open"] + b1["close"]) / 2:
        conf = min(1.0, 0.55 + body3 / max(body1, 1e-8) * 0.3)
        return True, conf, "bearish"
    return False, 0, None


def detect_three_white_soldiers(window, idx):
    """Three consecutive long bullish candles, each opening within prior body."""
    if idx < 2:
        return False, 0, None
    b1, b2, b3 = window[idx - 2], window[idx - 1], window[idx]
    if not (is_bullish(b1) and is_bullish(b2) and is_bullish(b3)):
        return False, 0, None
    br1, br2, br3 = body_size(b1), body_size(b2), body_size(b3)
    avg_br = (br1 + br2 + br3) / 3
    if avg_br < 1e-8:
        return False, 0, None
    # Each open should be within prior body
    ok1 = b2["open"] >= min(b1["open"], b1["close"]) and b2["open"] <= max(b1["open"], b1["close"])
    ok2 = b3["open"] >= min(b2["open"], b2["close"]) and b3["open"] <= max(b2["open"], b2["close"])
    # Bodies should be roughly similar size (at least 60% of avg)
    size_ok = all(br > avg_br * 0.6 for br in [br1, br2, br3])
    if ok1 and ok2 and size_ok:
        conf = min(1.0, 0.6 + avg_br / bar_range(b3) * 0.4) if bar_range(b3) > 0 else 0.6
        return True, conf, "bullish"
    return False, 0, None


def detect_three_black_crows(window, idx):
    """Mirror of Three White Soldiers."""
    if idx < 2:
        return False, 0, None
    b1, b2, b3 = window[idx - 2], window[idx - 1], window[idx]
    if not (is_bearish(b1) and is_bearish(b2) and is_bearish(b3)):
        return False, 0, None
    br1, br2, br3 = body_size(b1), body_size(b2), body_size(b3)
    avg_br = (br1 + br2 + br3) / 3
    if avg_br < 1e-8:
        return False, 0, None
    ok1 = b2["open"] >= min(b1["open"], b1["close"]) and b2["open"] <= max(b1["open"], b1["close"])
    ok2 = b3["open"] >= min(b2["open"], b2["close"]) and b3["open"] <= max(b2["open"], b2["close"])
    size_ok = all(br > avg_br * 0.6 for br in [br1, br2, br3])
    if ok1 and ok2 and size_ok:
        conf = min(1.0, 0.6 + avg_br / bar_range(b3) * 0.4) if bar_range(b3) > 0 else 0.6
        return True, conf, "bearish"
    return False, 0, None


# All detectors
ALL_DETECTORS = [
    ("Doji", detect_doji),
    ("Hammer", detect_hammer),
    ("Shooting Star", detect_shooting_star),
    ("Bullish Engulfing", detect_bullish_engulfing),
    ("Bearish Engulfing", detect_bearish_engulfing),
    ("Morning Star", detect_morning_star),
    ("Evening Star", detect_evening_star),
    ("Three White Soldiers", detect_three_white_soldiers),
    ("Three Black Crows", detect_three_black_crows),
]

# Emoji map
PATTERN_EMOJI = {
    "Doji": "⚖️", "Hammer": "🔨", "Shooting Star": "🌠",
    "Bullish Engulfing": "🟢", "Bearish Engulfing": "🔴",
    "Morning Star": "🌅", "Evening Star": "🌆",
    "Three White Soldiers": "📈", "Three Black Crows": "📉",
}

# Direction emoji
DIR_EMOJI = {"bullish": "🟢", "bearish": "🔴", "neutral": "⚪"}


# ---------------------------------------------------------------------------
# Confidence scoring with trend + volume confirmation
# ---------------------------------------------------------------------------

def trend_direction(window, lookback=10):
    """Simple trend via linear slope of last N closes."""
    closes = [w["close"] for w in window][-lookback:]
    if len(closes) < 2:
        return 0
    n = len(closes)
    x_mean = (n - 1) / 2
    y_mean = sum(closes) / n
    num = sum((i - x_mean) * (c - y_mean) for i, c in enumerate(closes))
    den = sum((i - x_mean) ** 2 for i in range(n))
    if den < 1e-15:
        return 0
    return num / den  # positive = uptrend


def compute_confidence(pattern_conf, direction, window):
    """Adjust confidence with trend alignment + volume heuristics."""
    trend = trend_direction(window)
    trend_bonus = 0
    if direction == "bullish" and trend > 0:
        trend_bonus = min(0.15, trend * 5)
    elif direction == "bearish" and trend < 0:
        trend_bonus = min(0.15, abs(trend) * 5)

    # Slight penalty if trend contradicts pattern
    trend_penalty = 0
    if direction == "bullish" and trend < -0.01:
        trend_penalty = 0.1
    elif direction == "bearish" and trend > 0.01:
        trend_penalty = 0.1

    raw = pattern_conf + trend_bonus - trend_penalty
    return max(0.0, min(1.0, raw))


# ---------------------------------------------------------------------------
# Collector
# ---------------------------------------------------------------------------

class BarCollector(ft.CurKlineHandlerBase):
    """Collects K-lines via push subscription."""

    def __init__(self, maxlen=200):
        super().__init__()
        self.bars = deque(maxlen=maxlen)

    def on_recv_rsp(self, rsp_pb):
        ret, content = super().on_recv_rsp(rsp_pb)
        if ret != ft.RetCode.SUCCESS:
            return ret, content
        close = float(content.get("close", 0))
        high = float(content.get("high", 0))
        low = float(content.get("low", 0))
        self.bars.append({"open": float(content.get("open", close)),
                          "close": close, "high": high, "low": low})
        return ret, content


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def fetch_initial_bars(quote_ctx, code, num):
    """Fetch historical K-lines for warmup."""
    bars = []
    next_token = ""
    while len(bars) < num:
        need = num - len(bars)
        ret, df, next_token = quote_ctx.request_history_kline(
            code=code, start=next_token, num_bars=min(need, 50),
            ktype=ft.KLType.K_DAY,
        )
        if ret != ft.RetCode.SUCCESS:
            break
        if df is not None and not df.empty:
            for _, row in df.iterrows():
                bars.append({
                    "open": float(row["open"]),
                    "close": float(row["close"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                })
        if not next_token:
            break
    return bars


def main():
    parser = argparse.ArgumentParser(description="Candlestick pattern scanner")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Stock code")
    parser.add_argument("--lookback", type=int, default=DEFAULT_LOOKBACK,
                        help="History bars for pattern context (default 30)")
    args = parser.parse_args()

    code = args.stock
    lookback = args.lookback

    # Cooldown tracker per pattern
    last_alert_bar = {name: -COOLDOWN_BARS for name, _ in ALL_DETECTORS}

    quote_ctx = create_quote_context()

    try:
        # ── Bootstrap ──────────────────────────────────────────────────
        logger.info("Fetching %d historical bars for %s …", lookback, code)
        hist = fetch_initial_bars(quote_ctx, code, lookback)
        logger.info("Loaded %d bars.", len(hist))

        window = deque(hist, maxlen=lookback + 10)

        # ── Subscribe to live bars ─────────────────────────────────────
        handler = BarCollector()
        ret, _ = quote_ctx.subscribe(
            code_list=[code],
            subtype_list=[ft.SubType.CUR_KLINE],
            is_first_push=True,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("subscribe failed: %s", ret)
            return
        quote_ctx.set_handler(handler)
        logger.info("Subscribed to CUR_KLINE for %s", code)

        print("\n" + "=" * 60)
        print(f"  🕯️  CANDLESTICK PATTERN SCANNER — {code}")
        print(f"  Lookback={lookback}  Patterns={len(ALL_DETECTORS)}")
        print("=" * 60)
        print("  Patterns: " + ", ".join(n for n, _ in ALL_DETECTORS))
        print(f"  Cooldown: {COOLDOWN_BARS} bars between repeated alerts\n")

        bar_number = len(hist)

        import time as _time

        while True:
            _time.sleep(5)

            # Merge historical + live
            live = list(handler.bars)
            while len(window) < len(hist) + len(live):
                window.append({"open": 0, "close": 0, "high": 0, "low": 0})
            for i, b in enumerate(live):
                if i < len(window):
                    window[i + len(hist)] = b
                else:
                    window.append(b)
            # Trim
            while len(window) > lookback + 10:
                window.popleft()

            if len(window) < 3:
                print(f"  Warming up … {len(window)}/3 bars")
                continue

            new_bars = len(live) - bar_number + len(hist)
            if new_bars <= 0:
                continue
            bar_number = len(live) + len(hist)

            # Run all detectors on the latest bar
            idx = len(window) - 1
            print(f"\n[{_time.strftime('%H:%M:%S')}] Bar {bar_number}  "
                  f"O={window[idx]['open']:.2f} H={window[idx]['high']:.2f} "
                  f"L={window[idx]['low']:.2f} C={window[idx]['close']:.2f}")

            for name, detector in ALL_DETECTORS:
                if bar_number - last_alert_bar[name] < COOLDOWN_BARS:
                    continue
                detected, conf, direction = detector(window, idx)
                if detected and conf > 0:
                    conf = compute_confidence(conf, direction, window)
                    emoji = PATTERN_EMOJI.get(name, "❓")
                    dir_emoji = DIR_EMOJI.get(direction, "")
                    print(f"  {emoji} {name:<24} conf={conf:.0%} {dir_emoji} "
                          f"(direction: {direction})")
                    last_alert_bar[name] = bar_number

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()