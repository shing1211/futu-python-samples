# -*- coding: utf-8 -*-
"""
股票卖出函数示例 (simple_sell / smart_sell)

Demonstrates:
  - simple_sell: place sell order at fixed price
  - smart_sell: read order book, sell at best bid price
  - get_market_snapshot: fetch lot_size for position rounding
  - get_order_book: read current bid queue
  - place_order: buy/sell with proper lot sizing
  - Proper logging throughout
"""
from time import sleep
import logging
import futu as ft
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def simple_sell(quote_ctx, trade_ctx, stock_code, trade_price, volume,
                trade_env, order_type=ft.OrderType.NORMAL):
    """
    简单卖出函数。取到股票每手的股数后，就下单卖出。

    Steps:
      1. get_market_snapshot -> lot_size
      2. Round volume to nearest lot
      3. place_order (SELL)
      4. Log full response
    """
    logger.info("simple_sell: code=%s price=%.2f volume=%d", stock_code, trade_price, volume)

    lot_size = 0
    for attempt in range(5):
        sleep(1)
        ret, data = quote_ctx.get_market_snapshot([stock_code])
        if ret != ft.RET_OK:
            logger.warning("get_market_snapshot failed (attempt %d/5): %s", attempt + 1, data)
            continue

        lot_size = data.iloc[0]['lot_size']
        logger.info("  lot_size=%d", lot_size)
        if lot_size <= 0:
            logger.error("Invalid lot_size=%d for %s", lot_size, stock_code)
            return None

        break
    else:
        logger.error("get_market_snapshot failed after 5 attempts")
        return None

    qty = int(volume // lot_size) * lot_size
    if qty == 0:
        logger.error("Volume %d is less than one lot (%d) — cannot sell", volume, lot_size)
        return None
    logger.info("  adjusted qty to %d (rounded to lot=%d)", qty, lot_size)

    ret, data = trade_ctx.place_order(
        price=trade_price,
        qty=qty,
        code=stock_code,
        trd_side=ft.TrdSide.SELL,
        trd_env=trade_env,
        order_type=order_type,
    )
    if ret != ft.RET_OK:
        logger.error("simple_sell place_order failed: %s", data)
        return None

    logger.info("simple_sell SUCCESS: order_id=%s", data.get("order_id", "N/A"))
    logger.info("  Full response: %s", data)
    return data


def smart_sell(quote_ctx, trade_ctx, stock_code, volume,
               trade_env, order_type=ft.OrderType.NORMAL):
    """
    智能卖出函数。取到股票每手的股数，以及摆盘数据后，就以买一价下单卖出。

    Steps:
      1. get_market_snapshot -> lot_size
      2. get_order_book -> best bid price
      3. Round qty to lot
      4. place_order at bid price
      5. Log full response
    """
    logger.info("smart_sell: code=%s volume=%d", stock_code, volume)

    lot_size = 0
    for attempt in range(5):
        ret, data = quote_ctx.get_market_snapshot([stock_code])
        lot_size = data.iloc[0]['lot_size'] if ret == ft.RET_OK else 0
        if ret != ft.RET_OK:
            logger.warning("get_market_snapshot failed (attempt %d/5): %s", attempt + 1, data)
            continue
        if lot_size <= 0:
            logger.error("Invalid lot_size=%d for %s", lot_size, stock_code)
            return None
        break
    else:
        logger.error("get_market_snapshot failed after 5 attempts")
        return None

    qty = int(volume // lot_size) * lot_size
    if qty == 0:
        logger.error("Volume %d is less than one lot (%d) — cannot sell", volume, lot_size)
        return None
    logger.info("  adjusted qty=%d (lot=%d)", qty, lot_size)

    ret, data = quote_ctx.get_order_book(stock_code)
    if ret != ft.RET_OK:
        logger.error("get_order_book failed: %s", data)
        return None

    bid_price = data['Bid'][0][0]
    logger.info("  best bid price=%.2f", bid_price)

    ret, data = trade_ctx.place_order(
        price=bid_price,
        qty=qty,
        code=stock_code,
        trd_side=ft.TrdSide.SELL,
        trd_env=trade_env,
        order_type=order_type,
    )
    if ret != ft.RET_OK:
        logger.error("smart_sell place_order failed: %s", data)
        return None

    logger.info("smart_sell SUCCESS: order_id=%s price=%.2f qty=%d",
                data.get("order_id", "N/A"), bid_price, qty)
    logger.info("  Full response: %s", data)
    return data


if __name__ == "__main__":
    code = 'HK.00700'
    trd_env = ft.TrdEnv.SIMULATE
    order_type = ft.OrderType.NORMAL
    logger.info("=== Stock Sell Demo ===")
    logger.info("Stock: %s | TradeEnv: %s", code, trd_env)

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        quote_ctx.subscribe(code, ft.SubType.ORDER_BOOK)
        logger.info("Subscribed to ORDER_BOOK for %s", code)

        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret == ft.RET_OK:
            logger.info("unlock_trade: OK")
        else:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)

        logger.info("\n--- simple_sell at fixed price ---")
        simple_sell(quote_ctx, trd_ctx, code, 280.0, 100, trd_env, order_type)

        logger.info("\n--- smart_sell at best bid ---")
        smart_sell(quote_ctx, trd_ctx, code, 100, trd_env, order_type)

    finally:
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")