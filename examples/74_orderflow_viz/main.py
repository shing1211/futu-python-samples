"""Order Flow Imbalance Visualizer — Real-time ASCII chart.

Extends 56_order_flow_imbalance by rendering a live terminal bar chart
of net bid/ask aggression using pure stdlib.

Usage:
    python3 main.py [--stock HK.00700] [--window 100] [--throttle 0.5]
"""

import sys
import os
import logging
import argparse
import time
from collections import deque
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
DEFAULT_WINDOW = 100
DEFAULT_THROTTLE = 0.5  # seconds between display refreshes

# ---------------------------------------------------------------------------
# Order Book Collector
# ---------------------------------------------------------------------------

class OrderBookCollector(ft.OrderBookHandlerBase):
    """Collects order book snapshots and computes imbalance."""

    def __init__(self, window=100):
        super().__init__()
        self.imbalance_history = deque(maxlen=window)
        self.last_book_time = 0
        self.update_count = 0

    def on_recv_rsp(self, rsp_pb):
        ret, content = super().on_recv_rsp(rsp_pb)
        if ret != ft.RetCode.SUCCESS:
            return ret, content

        self.update_count += 1
        bid = content.get("Bid", [])
        ask = content.get("Ask", [])

        # Sum volumes across all levels
        total_bid = sum(level[1] for level in bid if len(level) >= 2)
        total_ask = sum(level[1] for level in ask if len(level) >= 2)

        total = total_bid + total_ask
        if total > 0:
            imbalance = (total_bid - total_ask) / total  # range [-1, 1]
        else:
            imbalance = 0.0

        self.imbalance_history.append(imbalance)
        self.last_book_time = time.time()

        return ret, content  # return to base class


# ---------------------------------------------------------------------------
# ASCII Rendering
# ---------------------------------------------------------------------------

BAR_WIDTH = 20  # characters each side of center

def render_chart(imbalance_history):
    """Render an ASCII imbalance chart with stats."""
    if not imbalance_history:
        print("  [no data yet]")
        return

    vals = list(imbalance_history)
    current = vals[-1]
    mean = statistics.mean(vals)
    mn = min(vals)
    mx = max(vals)

    # Build bar
    bar = ""
    for val in vals[-40:]:  # show last 40 points
        clamped = max(-1.0, min(1.0, val))
        pos = int((clamped + 1.0) * BAR_WIDTH / 2)  # 0..2*BAR_WIDTH
        line = ['.'] * (BAR_WIDTH * 2 + 1)
        line[BAR_WIDTH] = '|'  # center
        idx = min(max(0, pos), BAR_WIDTH * 2)
        if idx == BAR_WIDTH:
            line[idx] = '█'
        elif idx < BAR_WIDTH:
            line[idx] = '█'
        else:
            line[idx] = '█'
        bar += ''.join(line) + '\n'

    # Current indicator
    arrow = "▼" if current < 0 else "▲" if current > 0 else "="
    color_start = "\033[91m" if current < 0 else "\033[92m"  # red/green
    color_end = "\033[0m"

    print(f"\n  {color_start}{arrow} Current: {current:+.3f}{color_end}")
    print(f"  Mean: {mean:+.3f}  Min: {mn:+.3f}  Max: {mx:+.3f}  N: {len(vals)}")
    print(f"  {'ASK ◄' + '·' * BAR_WIDTH + '│' + '·' * BAR_WIDTH + '► BID'}")
    # Print reversed so newest is at bottom
    lines = bar.strip().split('\n')
    for line in reversed(lines[-20:]):  # show last 20 bars
        print(f"  {line}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Order Flow Imbalance Visualizer")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Stock code")
    parser.add_argument("--window", type=int, default=DEFAULT_WINDOW,
                        help="Rolling window size (default 100)")
    parser.add_argument("--throttle", type=float, default=DEFAULT_THROTTLE,
                        help="Min seconds between display refreshes (default 0.5)")
    args = parser.parse_args()

    code = args.stock
    window = args.window
    throttle = args.throttle

    quote_ctx = create_quote_context()

    try:
        # Subscribe to order book
        handler = OrderBookCollector(window=window)
        ret, _ = quote_ctx.subscribe(
            code_list=[code],
            subtype_list=[ft.SubType.ORDER_BOOK],
            is_first_push=True,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("subscribe failed: %s", ret)
            return
        quote_ctx.set_handler(handler)
        logger.info("Subscribed to ORDER_BOOK for %s", code)

        print("\n" + "=" * 60)
        print(f"  ORDER FLOW IMBALANCE — {code}")
        print(f"  Window={window}  Throttle={throttle}s")
        print("=" * 60)
        print("  Bid-heavy ██ (left) | Ask-heavy ██ (right)")
        print("  Press Ctrl+C to exit\n")

        last_display = 0
        while True:
            time.sleep(0.1)  # fast loop, throttle display
            now = time.time()
            if now - last_display < throttle:
                continue
            if handler.update_count == 0:
                continue

            last_display = now
            render_chart(handler.imbalance_history)
            print(f"  Updates: {handler.update_count}", end='\r')

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()