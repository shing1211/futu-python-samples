# -*- coding: utf-8 -*-
"""MACD 量化交易策略示例

Demonstrates:
  - request_history_kline: fetch historical K-line data
  - talib.MACD: compute MACD indicator
  - get_market_snapshot: fetch current price + lot_size
  - accinfo_query: check buying power
  - position_list_query: check current holdings
  - place_order: buy/sell with proper lot sizing
  - Proper logging of all fields and signals
"""
import pandas as pd
import math
import datetime
import logging
import futu as ft
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class MACD:
    """
    A simple MACD cross strategy.

    Entry signal: short MA crosses above long MA (golden cross)
    Exit signal:  short MA crosses below long MA (death cross)

    All key values are logged at each step.
    """

    def __init__(self, stock, short_period, long_period, smooth_period, observation):
        self.stock = stock
        self.short_period = short_period
        self.long_period = long_period
        self.smooth_period = smooth_period
        self.observation = observation
        self.trade_env = ft.TrdEnv.SIMULATE
        self.quote_ctx, self.trade_ctx = self._setup_contexts()

    def _setup_contexts(self):
        logger.info("Setting up contexts...")
        quote_ctx = create_quote_context()
        trade_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.NONE)

        pwd = get_demo_trade_password()
        if self.trade_env == ft.TrdEnv.REAL:
            ret_code, ret_data = trade_ctx.unlock_trade(pwd)
            if ret_code != ft.RET_OK:
                raise RuntimeError(f"unlock_trade failed: {ret_data}")
            logger.info("Trade unlocked (REAL mode)")
        else:
            logger.info("Trade unlocked (SIMULATE mode — no password needed)")

        return quote_ctx, trade_ctx

    def close(self):
        logger.info("Closing contexts...")
        self.quote_ctx.close()
        self.trade_ctx.close()

    def handle_data(self):
        """Main strategy logic — fetch data, compute MACD, place orders."""
        logger.info("=== MACD Strategy ===")
        logger.info("Stock: %s | short=%d long=%d smooth=%d observation=%d",
                    self.stock, self.short_period, self.long_period,
                    self.smooth_period, self.observation)

        # ── Fetch historical K-line ──────────────────────────────────
        today = datetime.datetime.today()
        pre_day = (today - datetime.timedelta(days=self.observation)).strftime('%Y-%m-%d')
        end_dt = today.strftime('%Y-%m-%d')

        logger.info("Fetching history kline: %s to %s", pre_day, end_dt)
        ret_code, prices, page_req_key = self.quote_ctx.request_history_kline(
            self.stock, start=pre_day, end=end_dt,
        )
        if ret_code != ft.RET_OK:
            logger.error("request_history_kline failed: %s", prices)
            return

        logger.info("Received %d bars (columns: %s)", len(prices), list(prices.columns))
        if prices.empty or len(prices) < self.long_period + self.smooth_period:
            logger.error("Not enough kline data (%d bars) for MACD (need %d)",
                         len(prices), self.long_period + self.smooth_period)
            return
        logger.info("Date range: %s to %s", prices['time_key'].min(), prices['time_key'].max())
        logger.info("Close price sample: %s", prices['close'].tail(5).tolist())

        # ── Compute MACD ─────────────────────────────────────────────
        def macd(close, fast=12, slow=26, signal=9):
            ema_fast = close.ewm(span=fast, adjust=False).mean()
            ema_slow = close.ewm(span=slow, adjust=False).mean()
            macd_line = ema_fast - ema_slow
            macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
            macd_hist = macd_line - macd_signal
            return macd_line, macd_signal, macd_hist

        close_arr = prices['close']
        macd_line, signal, hist = macd(close_arr, self.short_period, self.long_period, self.smooth_period)

        latest_macd = macd_line.iloc[-1]
        latest_signal = signal.iloc[-1]
        prev_macd = macd_line.iloc[-2]
        prev_signal = signal.iloc[-2]

        logger.info(
            "MACD: macd=%.4f signal=%.4f hist=%.4f | prev: macd=%.4f signal=%.4f",
            latest_macd, latest_signal, hist[-1], prev_macd, prev_signal,
        )

        # ── Get current positions ─────────────────────────────────────
        logger.info("\n--- Portfolio Check ---")
        ret_code, pos_data = self.trade_ctx.position_list_query(trd_env=self.trade_env)
        if ret_code != ft.RET_OK:
            logger.error("position_list_query failed: %s", pos_data)
            return

        if pos_data.empty:
            logger.info("No positions held")
            has_position = False
            cur_qty = 0
        else:
            logger.info("Positions (%d rows): columns=%s", len(pos_data), list(pos_data.columns))
            pos_info = pos_data.set_index('code')
            if self.stock in pos_info.index:
                cur_qty = int(pos_info.loc[self.stock, 'qty'])
                has_position = True
                logger.info("  Holding %s: qty=%d", self.stock, cur_qty)
            else:
                logger.info("  Not holding %s", self.stock)
                has_position = False
                cur_qty = 0

        # ── Sell Signal: MACD crosses below signal ───────────────────
        if latest_macd < latest_signal and prev_macd > prev_signal:
            logger.info("\n>>> SELL SIGNAL (death cross) — MACD crossed below signal")

            if has_position and cur_qty > 0:
                ret_code, snapshot = self.quote_ctx.get_market_snapshot([self.stock])
                if ret_code != ft.RET_OK:
                    logger.error("get_market_snapshot failed: %s", snapshot)
                    return

                cur_price = snapshot['last_price'][0]
                lot_size = snapshot['lot_size'][0]
                logger.info("  Current price: %.2f | lot_size: %d", cur_price, lot_size)

                ret_code, ret_data = self.trade_ctx.place_order(
                    price=cur_price,
                    qty=cur_qty,
                    code=self.stock,
                    trd_side=ft.TrdSide.SELL,
                    order_type=ft.OrderType.NORMAL,
                    trd_env=self.trade_env,
                )
                if ret_code == ft.RET_OK:
                    logger.info("SELL ORDER PLACED: code=%s price=%.2f qty=%d order_id=%s",
                                self.stock, cur_price, cur_qty, ret_data.get("order_id", "N/A"))
                else:
                    logger.error("SELL ORDER FAILED: %s", ret_data)
            else:
                logger.info("  No position to sell")

        # ── Buy Signal: MACD crosses above signal ────────────────────
        elif latest_macd > latest_signal and prev_macd < prev_signal:
            logger.info("\n>>> BUY SIGNAL (golden cross) — MACD crossed above signal")

            ret_code, acc_info = self.trade_ctx.accinfo_query(trd_env=self.trade_env)
            if ret_code != ft.RET_OK:
                logger.error("accinfo_query failed: %s", acc_info)
                return

            logger.info("Account info columns: %s", list(acc_info.columns))
            buying_power = acc_info['power'][0]
            logger.info("  Buying power: %.2f", buying_power)

            ret_code, snapshot = self.quote_ctx.get_market_snapshot([self.stock])
            if ret_code != ft.RET_OK:
                logger.error("get_market_snapshot failed: %s", snapshot)
                return

            cur_price = snapshot['last_price'][0]
            lot_size = snapshot['lot_size'][0]
            logger.info("  Current price: %.2f | lot_size: %d", cur_price, lot_size)

            qty = int(math.floor(buying_power / cur_price))
            qty = (qty // lot_size) * lot_size
            logger.info("  Calculated qty: %d (buying_power=%.2f / price=%.2f)", qty, buying_power, cur_price)

            if qty < lot_size:
                logger.info("  qty < lot_size, skipping buy")
                return

            ret_code, ret_data = self.trade_ctx.place_order(
                price=cur_price,
                qty=qty,
                code=self.stock,
                trd_side=ft.TrdSide.BUY,
                order_type=ft.OrderType.NORMAL,
                trd_env=self.trade_env,
            )
            if ret_code == ft.RET_OK:
                logger.info("BUY ORDER PLACED: code=%s price=%.2f qty=%d order_id=%s",
                            self.stock, cur_price, qty, ret_data.get("order_id", "N/A"))
            else:
                logger.error("BUY ORDER FAILED: %s", ret_data)
        else:
            logger.info("\n>>> No signal (MACD=%.4f, Signal=%.4f) — holding%s",
                        latest_macd, latest_signal,
                        f" {cur_qty} shares" if has_position else "")


if __name__ == "__main__":
    SHORT_PERIOD = 12
    LONG_PERIOD = 26
    SMOOTH_PERIOD = 9
    OBSERVATION = 100
    STOCK = "HK.00700"

    strategy = MACD(STOCK, SHORT_PERIOD, LONG_PERIOD, SMOOTH_PERIOD, OBSERVATION)
    try:
        strategy.handle_data()
    finally:
        strategy.close()

    logger.info("Done.")