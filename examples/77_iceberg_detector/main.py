"""Iceberg Order Detector — Educational proxy for hidden order detection.

Monitors ORDER_BOOK push for repeated large resting lots that suggest
iceberg (hidden) orders. This is a heuristic exercise, not production-grade.

Usage:
    python3 main.py [--stock HK.00700] [--threshold 0.4] [--round-lot 100]
"""

import sys
import logging
import argparse
from collections import deque, defaultdict
import statistics

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
DEFAULT_THRESHOLD = 0.4    # iceberg score threshold (0–1)
DEFAULT_ROUND_LOT = 100    # standard lot size for HK stocks
DEFAULT_MAX_LEVELS = 20    # only track top N levels by volume
DEFAULT_HISTORY = 50       # history deque length per level

# ---------------------------------------------------------------------------
# Level tracker
# ---------------------------------------------------------------------------

class LevelTracker:
    """Tracks a single price level's volume history for iceberg detection."""

    def __init__(self, round_lot=100):
        self.visible_vol_history = deque(maxlen=DEFAULT_HISTORY)
        self.total_seen_vol = 0
        self.first_seen = None
        self.last_seen = None
        self.tick_count = 0
        self.round_lot = round_lot
        self.iceberg_score = 0.0

    def update(self, visible_vol, timestamp):
        self.visible_vol_history.append(visible_vol)
        self.total_seen_vol += visible_vol
        if self.first_seen is None:
            self.first_seen = timestamp
        self.last_seen = timestamp
        self.tick_count += 1

    def compute_score(self):
        """Compute iceberg confidence score (0–1)."""
        if len(self.visible_vol_history) < 3 or self.tick_count < 5:
            self.iceberg_score = 0
            return 0

        # 1. Volume variance — high variance on a resting level = suspicious
        try:
            vol_var = statistics.variance(self.visible_vol_history)
            vol_mean = statistics.mean(self.visible_vol_history)
        except statistics.StatisticsError:
            self.iceberg_score = 0
            return 0

        if vol_mean < 1:
            self.iceberg_score = 0
            return 0

        # Normalised coefficient of variation
        cv = (vol_var ** 0.5) / vol_mean

        # 2. Roundness — volume is suspiciously round (lot size multiples)
        latest = self.visible_vol_history[-1] if self.visible_vol_history else 0
        is_round = (latest % self.round_lot == 0 and latest % (self.round_lot * 5) == 0)

        # 3. Persistence — level lasts many updates without being fully consumed
        #    (tick_count is a rough proxy for how long it has persisted)
        persistence = min(1.0, self.tick_count / 50)

        # 4. Volume is significant (at least 5× round lot)
        size_factor = min(1.0, latest / (self.round_lot * 5))

        # Composite score (weighted)
        score = (
            0.35 * min(cv / 2.0, 1.0) +      # variance (high = suspicious)
            0.20 * float(is_round) +           # roundness (institutional size)
            0.25 * persistence +               # how long the level has persisted
            0.20 * size_factor                 # absolute size
        )
        self.iceberg_score = min(1.0, max(0.0, score))
        return self.iceberg_score


# ---------------------------------------------------------------------------
# Order Book Collector
# ---------------------------------------------------------------------------

class IcebergDetector(ft.OrderBookHandlerBase):
    """Detects potential iceberg orders from ORDER_BOOK push data."""

    def __init__(self, threshold=0.4, round_lot=100, max_levels=20):
        super().__init__()
        self.threshold = threshold
        self.round_lot = round_lot
        self.max_levels = max_levels
        self.levels = defaultdict(dict)  # price -> {'bid': LevelTracker, 'ask': LevelTracker}
        self.alerts = []  # recent alert messages
        self.max_alerts = 20
        self.prev_book = {'Bid': [], 'Ask': []}
        self.update_count = 0
        self.consumed = set()  # (side, price) that were fully consumed

    def on_recv_rsp(self, rsp_pb):
        ret, content = super().on_recv_rsp(rsp_pb)
        if ret != ft.RetCode.SUCCESS:
            return ret, content

        self.update_count += 1
        timestamp = self.update_count  # simple sequence as proxy

        bid = content.get("Bid", [])
        ask = content.get("Ask", [])

        self._process_side(bid, 'bid', timestamp)
        self._process_side(ask, 'ask', timestamp)

        self.prev_book = {'Bid': bid, 'Ask': ask}
        return ret, content

    def _process_side(self, levels, side, timestamp):
        """Process one side (Bid or Ask) of the order book."""
        # Sort by volume descending, take top N
        sorted_levels = sorted(levels, key=lambda l: l[1], reverse=True)[:self.max_levels]

        current_prices = set()
        for level in sorted_levels:
            if len(level) < 2:
                continue
            price = level[0]
            vol = level[1]
            current_prices.add((side, price))

            key = (side, price)
            if key not in self.levels:
                self.levels[key] = LevelTracker(round_lot=self.round_lot)

            tracker = self.levels[key]
            tracker.update(vol, timestamp)

            # Detect consumed levels (was there before, now much smaller)
            prev_vol = self._get_prev_vol(side, price)
            if prev_vol is not None and prev_vol > self.round_lot * 10:
                drop_pct = (prev_vol - vol) / prev_vol if prev_vol > 0 else 0
                if drop_pct > 0.7 and vol < self.round_lot * 2:
                    # Large drop — possible iceberg consumption revealed
                    msg = (
                        f"🔍 POTENTIAL ICEBERG CONSUMED: "
                        f"{side.upper()} {price:.2f} dropped {drop_pct:.0%} "
                        f"({prev_vol} → {vol}) — hidden volume may have been exposed"
                    )
                    self._add_alert(msg)

        # Clean up old levels
        stale = [k for k in self.levels if k not in current_prices]
        for k in stale:
            # Level disappeared — was it an iceberg?
            tracker = self.levels[k]
            if tracker.total_seen_vol > self.round_lot * 20:
                msg = (
                    f"🔍 LEVEL VANISHED: {k[0].upper()} {k[1]:.2f} "
                    f"(total seen: {tracker.total_seen_vol:,}) — possible iceberg fill"
                )
                self._add_alert(msg)
            del self.levels[k]

    def _get_prev_vol(self, side, price):
        """Get previous volume for a level from prior book snapshot."""
        for level in self.prev_book.get(side.capitalize()[:1].upper() + side[1:] if side == 'bid' else 'Ask', []):
            # Actually the prev_book keys are 'Bid'/'Ask'
            pass
        # Simpler: just check prev_book
        key_name = 'Bid' if side == 'bid' else 'Ask'
        for level in self.prev_book.get(key_name, []):
            if len(level) >= 2 and abs(level[0] - price) < 1e-8:
                return level[1]
        return None

    def _add_alert(self, msg):
        """Add an alert, keeping list bounded."""
        self.alerts.append(msg)
        if len(self.alerts) > self.max_alerts:
            self.alerts.pop(0)

    def get_top_iceberg_candidates(self, n=5):
        """Return top N price levels by iceberg score."""
        scored = []
        for (side, price), tracker in self.levels.items():
            score = tracker.compute_score()
            if score > self.threshold:
                latest_vol = tracker.visible_vol_history[-1] if tracker.visible_vol_history else 0
                scored.append({
                    'side': side.upper(),
                    'price': price,
                    'score': score,
                    'latest_vol': latest_vol,
                    'total_seen': tracker.total_seen_vol,
                    'ticks': tracker.tick_count,
                })
        scored.sort(key=lambda x: x['score'], reverse=True)
        return scored[:n]


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def display_candidates(candidates, update_count):
    """Print iceberg candidates in a formatted table."""
    if not candidates:
        return

    print(f"\n{'='*64}")
    print(f"  🧊 ICEBERG CANDIDATES (updates: {update_count})")
    print(f"{'='*64}")
    print(
        f"  {'Side':<5} {'Price':>10} {'Score':>7} {'Latest':>10} "
        f"{'Total Seen':>12} {'Ticks':>6}"
    )
    print(f"  {'-'*5} {'-'*10} {'-'*7} {'-'*10} {'-'*12} {'-'*6}")
    for c in candidates:
        bar_len = int(c['score'] * 20)
        bar = '█' * bar_len + '░' * (20 - bar_len)
        print(
            f"  {c['side']:<5} {c['price']:>10.2f} {c['score']:>6.2f} "
            f"{c['latest_vol']:>10,} {c['total_seen']:>12,} {c['ticks']:>6}  {bar}"
        )

    print(f"\n  ⚠️  These are heuristic indicators, not proof of iceberg orders.")
    print(f"     Score > 0.4 = elevated suspicion.")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Iceberg order detector (educational)")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Stock code")
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="Iceberg score threshold (0–1, default 0.4)")
    parser.add_argument("--round-lot", type=int, default=DEFAULT_ROUND_LOT,
                        help="Round lot size (default 100)")
    args = parser.parse_args()

    code = args.stock
    threshold = args.threshold
    round_lot = args.round_lot

    quote_ctx = create_quote_context()
    handler = IcebergDetector(threshold=threshold, round_lot=round_lot)

    try:
        ret, _ = quote_ctx.subscribe(
            code_list=[code],
            subtype_list=[ft.SubType.ORDER_BOOK],
            is_first_push=True,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("subscribe failed: %s", ret)
            return
        quote_ctx.set_handler(handler)
        logger.info("Iceberg detector listening on %s ORDER_BOOK …", code)
        print(f"\n  Monitoring {code} for iceberg-like order book patterns")
        print(f"  Threshold: {threshold}  Round lot: {round_lot}")
        print(f"  (Educational exercise — not production-grade)\n")

        import time as _time

        last_display = 0
        while True:
            _time.sleep(0.5)
            now = _time.time()

            # Display every 5 seconds or on alert
            if now - last_display >= 5 or handler.alerts:
                last_display = now
                candidates = handler.get_top_iceberg_candidates()
                display_candidates(candidates, handler.update_count)

                # Print any new alerts
                for alert in handler.alerts:
                    print(f"\n  {alert}")
                if handler.alerts:
                    handler.alerts.clear()

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()