"""Portfolio Rebalancing Bot — SIMULATE only.

Compares current portfolio allocation against target weights and places
trades to bring the portfolio back in line. Supports configurable rebalance
threshold and frequency.

Usage:
    python3 main.py [--targets '{"HK.00700":0.4,"US.TCEHY":0.3,"HK.00005":0.3}']
                    [--threshold 0.05] [--interval 60]
"""

import sys
import os
import logging
import argparse
import json
import time

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
DEFAULT_TARGETS = {"HK.00700": 0.4, "US.TCEHY": 0.3, "HK.00005": 0.3}
DEFAULT_THRESHOLD = 0.05    # rebalance when drift > 5 %
DEFAULT_INTERVAL = 60       # check every 60 seconds
TRD_ENV = ft.TrdEnv.SIMULATE

# ---------------------------------------------------------------------------
# Portfolio helpers
# ---------------------------------------------------------------------------

def get_portfolio(trd_ctx, quote_ctx, target_codes):
    """Return current holdings + market values for target codes.

    Returns dict: {code: {"shares": int, "market_value": float,
                          "weight": float, "price": float}}
    """
    # Current positions
    positions = {}
    ret_pos, df_pos = trd_ctx.position_list_query(trd_env=TRD_ENV)
    if ret_pos == ft.RetCode.SUCCESS and df_pos is not None and not df_pos.empty:
        for _, row in df_pos.iterrows():
            code = row.get("code", "")
            qty = float(row.get("qty", 0) or 0)
            if code in target_codes and qty > 0:
                positions[code] = {"shares": int(qty)}

    # Current prices
    prices = {}
    for code in target_codes:
        ret, df = quote_ctx.get_stock_quote(code)
        if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
            prices[code] = float(df.iloc[-1]["last_price"])

    # Compute market values
    result = {}
    total_value = 0
    for code in target_codes:
        shares = positions.get(code, {}).get("shares", 0)
        price = prices.get(code, 0)
        mv = shares * price
        result[code] = {"shares": shares, "price": price, "market_value": mv}
        total_value += mv

    # Weights
    for code in result:
        result[code]["weight"] = (
            result[code]["market_value"] / total_value if total_value > 0 else 0
        )

    return result, total_value


def compute_rebalance_orders(portfolio, targets, total_value):
    """Compute trades needed to move portfolio toward target weights.

    Returns list of (code, side, qty) or empty list if no rebalance needed.
    """
    trades = []
    for code, target_weight in targets.items():
        if code not in portfolio:
            portfolio[code] = {"shares": 0, "price": 0, "weight": 0}

        current_weight = portfolio[code]["weight"]
        drift = current_weight - target_weight
        price = portfolio[code]["price"]

        if price <= 0:
            continue

        # Dollar amount to trade
        delta_dollar = -drift * total_value
        shares = int(abs(delta_dollar) / price)

        if shares == 0:
            continue

        # Only trade if drift exceeds threshold
        if abs(drift) >= 0.01:  # 1 % minimum to avoid noise
            if delta_dollar > 0:
                trades.append((code, ft.TrdSide.BUY, shares))
            else:
                trades.append((code, ft.TrdSide.SELL, shares))

    return trades


def place_rebalance(trd_ctx, trades):
    """Place rebalance orders. Returns filled order IDs."""
    order_ids = []
    for code, side, qty in trades:
        ret, order_id = trd_ctx.place_order(
            price=0, code=code, qty=qty,
            trd_side=side, order_type=ft.OrderType.NORMAL,
            trd_env=TRD_ENV,
            remark="rebalance",
        )
        if ret == ft.RetCode.SUCCESS:
            order_ids.append(order_id)
            logger.info("  %s %d %s", side.name, qty, code)
        else:
            logger.error("  Failed to %s %d %s: %s", side.name, qty, code, ret)
    return order_ids


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Portfolio rebalancing bot")
    parser.add_argument(
        "--targets",
        default=json.dumps(DEFAULT_TARGETS),
        help='JSON of {code: weight}, e.g. \'{"HK.00700":0.5,"US.TCEHY":0.5}\'',
    )
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD,
                        help="Rebalance when drift exceeds this (default 0.05)")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL,
                        help="Check interval in seconds (default 60)")
    args = parser.parse_args()

    targets = json.loads(args.targets)
    threshold = args.threshold
    interval = args.interval

    # Validate targets sum to ~1.0
    total_w = sum(targets.values())
    if abs(total_w - 1.0) > 0.01:
        logger.warning("Target weights sum to %.2f (expected 1.0). Normalising.", total_w)
        targets = {k: v / total_w for k, v in targets.items()}

    assert all(w > 0 for w in targets.values()), "All target weights must be > 0"

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()

    try:
        logger.info("Portfolio Rebalancing Bot started.")
        logger.info("Targets: %s", targets)
        logger.info("Threshold: %.1f%%  Interval: %ds", threshold * 100, interval)

        cycle = 0
        while True:
            cycle += 1
            print(f"\n--- Cycle {cycle} [{time.strftime('%H:%M:%S')}] ---")

            portfolio, total_value = get_portfolio(trd_ctx, quote_ctx, list(targets.keys()))

            # Print current state
            print(f"  Total value: ${total_value:,.2f}")
            for code in sorted(targets.keys()):
                info = portfolio.get(code, {})
                current_w = info.get("weight", 0)
                target_w = targets[code]
                drift = current_w - target_w
                status = "✓" if abs(drift) < threshold else "✗ REBALANCE"
                print(
                    f"  {code:<12} shares={info.get('shares',0):>6}  "
                    f"value=${info.get('market_value',0):>12,.2f}  "
                    f"weight={current_w:>6.1%}  target={target_w:>6.1%}  "
                    f"drift={drift:>+6.1%}  {status}"
                )

            # Compute and place trades
            trades = compute_rebalance_orders(portfolio, targets, total_value)
            if trades:
                print(f"\n  Placing {len(trades)} rebalance trade(s):")
                order_ids = place_rebalance(trd_ctx, trades)
                logger.info("  %d / %d orders placed.", len(order_ids), len(trades))
            else:
                print("  ✓ Portfolio within threshold — no trades needed.")

            # Wait for next cycle
            print(f"\n  Sleeping {interval}s … (Ctrl+C to stop)")
            time.sleep(interval)

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