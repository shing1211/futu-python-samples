"""Smart Watchlist with Price & Technical Alerts.

Monitors a configurable watchlist for price-level and technical indicators,
firing alerts when conditions are met. Pure stdlib — no external deps.

Usage:
    python3 main.py [--symbols 'HK.00700,HK.09988'] --alert-price --alert-rsi
"""

import sys
import logging
import argparse
import time
import json
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
DEFAULT_SYMBOLS = ["HK.00700", "HK.09988", "HK.03690", "US.TCEHY"]
POLL_INTERVAL = 10  # seconds


# ---------------------------------------------------------------------------
# Technical indicators (pure stdlib)
# ---------------------------------------------------------------------------

def compute_rsa(closes, period=14):
    """Relative Strength Index (RSI)."""
    if len(closes) < period + 1:
        return None
    gains = []
    losses = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        if delta > 0:
            gains.append(delta)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(delta))

    if len(gains) < period:
        return None

    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def compute_macd(closes, fast=12, slow=26, signal=9):
    """MACD line, signal line, histogram."""
    if len(closes) < slow:
        return None, None, None

    def ema(data, period):
        k = 2 / (period + 1)
        ema_val = data[0]
        for val in data[1:]:
            ema_val = val * k + ema_val * (1 - k)
        return ema_val

    fast_ema = ema(closes, fast)
    slow_ema = ema(closes, slow)
    macd_line = fast_ema - slow_ema
    # Signal line needs MACD history for proper EMA, approximate with last values
    return macd_line, None, macd_line  # simplified


def compute_bollinger(closes, period=20, stdev_mult=2.0):
    """Bollinger Bands. Returns (upper, middle, lower) or Nones."""
    if len(closes) < period:
        return None, None, None
    recent = closes[-period:]
    import statistics
    middle = statistics.mean(recent)
    std = statistics.pstdev(recent)
    if std < 1e-8:
        return middle, middle, middle
    return middle + stdev_mult * std, middle, middle - stdev_mult * std


# ---------------------------------------------------------------------------
# Alert conditions
# ---------------------------------------------------------------------------

class AlertEngine:
    def __init__(self):
        self.price_history = {}  # {symbol: deque of prices}
        self.alerts_fired = []
        self.alert_cooldown = {}  # {(symbol, alert_type): last_fire_time}
        self.price_targets = {}   # {symbol: {"above": price, "below": price}}

    def update_prices(self, symbol, price):
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=200)
        self.price_history[symbol].append(price)

    def set_price_target(self, symbol, above=None, below=None):
        self.price_targets[symbol] = {"above": above, "below": below}

    def check_alerts(self, symbol, current_price):
        """Evaluate all alert conditions. Returns list of alert messages."""
        alerts = []
        now = time.time()

        # Price target alerts
        targets = self.price_targets.get(symbol, {})
        if targets.get("above") and current_price >= targets["above"]:
            key = (symbol, "price_above")
            if now - self.alert_cooldown.get(key, 0) > 60:  # 1 min cooldown
                msg = f"🔔 {symbol} hit ABOVE target: {current_price:.2f} >= {targets['above']:.2f}"
                alerts.append(msg)
                self.alert_cooldown[key] = now

        if targets.get("below") and current_price <= targets["below"]:
            key = (symbol, "price_below")
            if now - self.alert_cooldown.get(key, 0) > 60:
                msg = f"🔔 {symbol} hit BELOW target: {current_price:.2f} <= {targets['below']:.2f}"
                alerts.append(msg)
                self.alert_cooldown[key] = now

        # RSI alerts
        prices = list(self.price_history.get(symbol, []))
        rsi = compute_rsa(prices)
        if rsi is not None:
            key = (symbol, "rsi_overbought")
            if rsi > 70 and now - self.alert_cooldown.get(key, 0) > 300:
                msg = f"⚠️ {symbol} RSI overbought: {rsi:.1f}"
                alerts.append(msg)
                self.alert_cooldown[key] = now

            key = (symbol, "rsi_oversold")
            if rsi < 30 and now - self.alert_cooldown.get(key, 0) > 300:
                msg = f"🔔 {symbol} RSI oversold: {rsi:.1f}"
                alerts.append(msg)
                self.alert_cooldown[key] = now

        # Bollinger Band alerts
        upper, mid, lower = compute_bollinger(prices)
        if upper is not None:
            if current_price >= upper:
                key = (symbol, "bb_upper")
                if now - self.alert_cooldown.get(key, 0) > 300:
                    msg = f"⚠️ {symbol} broke upper Bollinger Band: {current_price:.2f} >= {upper:.2f}"
                    alerts.append(msg)
                    self.alert_cooldown[key] = now
            elif current_price <= lower:
                key = (symbol, "bb_lower")
                if now - self.alert_cooldown.get(key, 0) > 300:
                    msg = f"🔔 {symbol} broke lower Bollinger Band: {current_price:.2f} <= {lower:.2f}"
                    alerts.append(msg)
                    self.alert_cooldown[key] = now

        return alerts


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Smart Watchlist with Price & Technical Alerts")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated symbol list")
    parser.add_argument("--alert-price", action="store_true",
                        help="Enable price target alerts")
    parser.add_argument("--alert-rsi", action="store_true",
                        help="Enable RSI overbought/oversold alerts")
    parser.add_argument("--alert-bb", action="store_true",
                        help="Enable Bollinger Band break alerts")
    parser.add_argument("--config", default=None,
                        help="JSON config file with price targets")
    parser.add_argument("--interval", type=int, default=POLL_INTERVAL,
                        help="Poll interval in seconds (default 10)")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    engine = AlertEngine()

    # Load config if provided
    if args.config:
        with open(args.config) as f:
            config = json.load(f)
            for sym, targets in config.items():
                engine.set_price_target(sym, **targets)
    else:
        # Default: alert on 5 % moves for each symbol
        for sym in symbols:
            engine.set_price_target(sym, above=None, below=None)

    # If no alert flags set, enable all
    if not (args.alert_price or args.alert_rsi or args.alert_bb):
        args.alert_price = args.alert_rsi = args.alert_bb = True

    quote_ctx = create_quote_context()

    try:
        print(f"\n{'='*60}")
        print(f"  📋 SMART WATCHLIST")
        print(f"  Symbols: {', '.join(symbols)}")
        print(f"  Alerts: price={'ON' if args.alert_price else 'OFF'}  "
              f"rsi={'ON' if args.alert_rsi else 'OFF'}  "
              f"bb={'ON' if args.alert_bb else 'OFF'}")
        print(f"  Poll interval: {args.interval}s")
        print(f"{'='*60}")
        print("  Press Ctrl+C to stop.\n")

        alert_log = []

        while True:
            for sym in symbols:
                ret, df = quote_ctx.get_stock_quote(sym)
                if ret != ft.RetCode.SUCCESS:
                    continue
                price = float(df.iloc[-1]["last_price"])
                engine.update_prices(sym, price)

                # Check alerts
                new_alerts = engine.check_alerts(sym, price)
                for alert in new_alerts:
                    print(f"  {time.strftime('%H:%M:%S')}  {alert}")
                    alert_log.append(alert)

                # Status line
                rsi = compute_rsa(list(engine.price_history.get(sym, [])))
                rsi_str = f"  RSI={rsi:.1f}" if rsi else ""
                print(f"  [{time.strftime('%H:%M:%S')}] {sym:<12} {price:>10.2f}{rsi_str}")

            time.sleep(args.interval)

    except KeyboardInterrupt:
        logger.info("Stopped by user.")
        if alert_log:
            print(f"\n  {len(alert_log)} alert(s) fired this session.")
    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()