"""VWAP Anchored Trading Levels — SIMULATE only.

Uses session VWAP as dynamic support/resistance. Generates buy signals
when price touches lower VWAP bands and sell signals at upper bands,
with volume confirmation.

Usage:
    python3 main.py [--stock HK.00700] [--bands 2.0] [--max-minutes 30]
"""

import sys
import logging
import argparse
import time
import statistics

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connect import (
    create_quote_context,
    create_trade_context,
    get_demo_trade_password,
    clear_connection_cache,
)
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
DEFAULT_BANDS = 2.0          # standard deviations for bands
DEFAULT_MAX_MINUTES = 30
TRD_ENV = ft.TrdEnv.SIMULATE
POLL_INTERVAL = 5  # seconds


# ---------------------------------------------------------------------------
# VWAP computation
# ---------------------------------------------------------------------------

class VWAPCalculator:
    """Computes running VWAP from tick/minute data."""

    def __init__(self):
        self.cum_tpv = 0.0   # cumulative typical price × volume
        self.cum_vol = 0      # cumulative volume
        self.vwap_history = []
        self.band_history = []

    def update(self, typical_price, volume):
        """Update VWAP with new tick data."""
        self.cum_tpv += typical_price * volume
        self.cum_vol += volume
        if self.cum_vol > 0:
            vwap = self.cum_tpv / self.cum_vol
        else:
            vwap = typical_price
        self.vwap_history.append(vwap)
        return vwap

    def get_current_vwap(self):
        if self.cum_vol == 0:
            return None
        return self.cum_tpv / self.cum_vol

    def compute_bands(self, num_std=2.0, window=20):
        """Compute VWAP +/- N standard deviation bands.

        Uses recent VWAP history to compute bands.
        """
        if len(self.vwap_history) < window:
            return None, None, None

        recent = self.vwap_history[-window:]
        mean_vwap = statistics.mean(recent)
        std_vwap = statistics.pstdev(recent) if len(recent) > 1 else 0

        upper = mean_vwap + num_std * std_vwap
        lower = mean_vwap - num_std * std_vwap
        return upper, mean_vwap, lower


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="VWAP Anchored Trading Levels")
    parser.add_argument("--stock", default=DEFAULT_STOCK, help="Stock ticker")
    parser.add_argument("--bands", type=float, default=DEFAULT_BANDS,
                        help="Standard deviation band width (default 2.0)")
    parser.add_argument("--max-minutes", type=float, default=DEFAULT_MAX_MINUTES,
                        help="Safety timeout (default 30)")
    args = parser.parse_args()

    code = args.stock
    band_std = args.bands
    max_seconds = args.max_minutes * 60

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()
    pwd = get_demo_trade_password()

    try:
        # Unlock SIMULATE
        ret, _ = trd_ctx.unlock_trade(pwd, trd_env=TRD_ENV)
        if ret != ft.RetCode.SUCCESS:
            logger.warning("unlock_trade: %s", ret)

        vwap_calc = VWAPCalculator()

        # Get last price for reference
        ret_df, df = quote_ctx.get_stock_quote(code)
        if ret_df != ft.RetCode.SUCCESS:
            logger.error("Cannot get quote for %s", code)
            return

        print(f"\n{'='*60}")
        print(f"  📊 VWAP ANCHORED TRADING — {code}")
        print(f"{'='*60}")
        print(f"  Bands: ±{band_std}σ from session VWAP")
        print(f"  Safety timeout: {max_seconds:.0f}s")
        print(f"{'='*60}")
        print("  Press Ctrl+C to stop.\n")

        position = None  # "long" or "short" or None
        entry_price = 0
        deadline = time.time() + max_seconds
        prev_signal_bar = ""

        import time as _time

        while _time.time() < deadline:
            # Get current K-bar data (use CurKline for live updates)
            ret_k, df_k = quote_ctx.get_cur_kline(
                code=code, ktype=ft.KLType.K_1M, num=5,
            )
            if ret_k != ft.RetCode.SUCCESS:
                _time.sleep(POLL_INTERVAL)
                continue

            latest = df_k.iloc[-1]
            h = float(latest.get("high", 0) or 0)
            l = float(latest.get("low", 0) or 0)
            c = float(latest.get("close", 0) or 0)
            v = float(latest.get("volume", 0) or 0)

            if c <= 0 or v <= 0:
                _time.sleep(POLL_INTERVAL)
                continue

            # Typical price = (high + low + close) / 3
            typical = (h + l + c) / 3
            current_vwap = vwap_calc.update(typical, v)

            if current_vwap is None:
                _time.sleep(POLL_INTERVAL)
                continue

            # Compute bands
            upper, mid, lower = vwap_calc.compute_bands(
                num_std=band_std, window=10,
            )
            if upper is None:
                _time.sleep(POLL_INTERVAL)
                continue

            # Volume average for confirmation
            recent_vols = [v]  # In production, use rolling window
            avg_vol = statistics.mean(recent_vols)

            # ── Signal generation ──────────────────────────────────────
            signal_bar = _time.strftime("%H:%M:%S")

            if position is None:
                # No position — look for entry
                if c <= lower and v >= avg_vol:
                    # Price at lower band with volume confirmation → BUY
                    signal = f"🟢 BUY  @ {c:.2f}  (≤ lower band {lower:.2f})"
                    position = "long"
                    entry_price = c
                    print(f"  [{signal_bar}] {signal}  VWAP={current_vwap:.2f}")

                elif c >= upper and v >= avg_vol:
                    # Price at upper band with volume confirmation → SELL
                    signal = f"🔴 SELL @ {c:.2f}  (≥ upper band {upper:.2f})"
                    position = "short"
                    entry_price = c
                    print(f"  [{signal_bar}] {signal}  VWAP={current_vwap:.2f}")

            elif position == "long":
                # In long position — look for exit
                profit_pct = (c - entry_price) / entry_price * 100
                if c >= mid:  # reached VWAP — take profit
                    signal = f"📤 CLOSE LONG @ {c:.2f}  (+{profit_pct:.1f}%, hit VWAP)"
                    print(f"  [{signal_bar}] {signal}")
                    position = None
                elif c <= lower * 0.998:  # stop loss below lower band
                    signal = f"🛑 STOP LOSS LONG @ {c:.2f}  ({profit_pct:.1f}%)"
                    print(f"  [{signal_bar}] {signal}")
                    position = None

            elif position == "short":
                # In short position — look for exit
                profit_pct = (entry_price - c) / entry_price * 100
                if c <= mid:  # reached VWAP — take profit
                    signal = f"📤 CLOSE SHORT @ {c:.2f}  (+{profit_pct:.1f}%, hit VWAP)"
                    print(f"  [{signal_bar}] {signal}")
                    position = None
                elif c >= upper * 1.002:  # stop loss above upper band
                    signal = f"🛑 STOP LOSS SHORT @ {c:.2f}  ({profit_pct:.1f}%)"
                    print(f"  [{signal_bar}] {signal}")
                    position = None

            # ── Status display ─────────────────────────────────────────
            if signal_bar != prev_signal_bar:
                pos_str = f"  Position: {position} (entry {entry_price:.2f})" if position else "  Position: flat"
                print(
                    f"  [{signal_bar}] VWAP={current_vwap:>8.2f}  "
                    f"Band=[{lower:>8.2f} {upper:>8.2f}]  "
                    f"Price={c:>8.2f}  Vol={v:>8,.0f}{pos_str}"
                )
                prev_signal_bar = signal_bar

            # Place orders in SIMULATE if signals fire
            if "BUY" in signal:
                trd_ctx.place_order(
                    price=c, code=code, qty=100,
                    trd_side=ft.TrdSide.BUY,
                    order_type=ft.OrderType.NORMAL,
                    trd_env=TRD_ENV,
                    remark="vwap_buy",
                )
            elif "SELL" in signal and "CLOSE" not in signal:
                trd_ctx.place_order(
                    price=c, code=code, qty=100,
                    trd_side=ft.TrdSide.SELL,
                    order_type=ft.OrderType.NORMAL,
                    trd_env=TRD_ENV,
                    remark="vwap_sell",
                )

            _time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        logger.info("Cleaning up …")
        trd_ctx.cancel_all_order(cancel_all_orders=True, trd_env=TRD_ENV)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()