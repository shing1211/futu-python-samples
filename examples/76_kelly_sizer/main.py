"""Kelly Criterion Position Sizer — SIMULATE only.

Analyzes historical trade results from the SIMULATE account, computes the
Kelly optimal fraction, and sizes the next order accordingly.

Usage:
    python3 main.py <stock_code> [--fraction 0.5] [--max-pct 0.25]
"""

import sys
import os
import logging
import argparse
import math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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
DEFAULT_FRACTION = 0.5     # half-Kelly by default
DEFAULT_MAX_PCT = 0.25     # cap at 25 % of equity (quarter-Kelly)
TRD_ENV = ft.TrdEnv.SIMULATE

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_trade_history(trd_ctx, num_days=30):
    """Fetch historical order/deal records for SIMULATE account.

    Returns a list of dicts with keys: code, trd_side, order_status,
    fill_qty, avg_price, create_time.
    """
    ret, orders = trd_ctx.history_order_list_query(
        trd_env=TRD_ENV,
        start="",
        num=100,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.warning("history_order_list_query failed: %s", ret)
        return []

    deals = []
    for _, row in orders.iterrows():
        if row.get("order_status") in (
            ft.OrderStatus.FILLED_ALL,
            ft.OrderStatus.FILLED_PART,
        ):
            deals.append({
                "code": row.get("code", ""),
                "trd_side": row.get("trd_side", ""),
                "order_status": row.get("order_status", ""),
                "fill_qty": float(row.get("fill_qty", 0) or 0),
                "avg_price": float(row.get("avg_price", 0) or 0),
                "create_time": row.get("create_time", ""),
            })
    return deals


def compute_kelly(deals):
    """Compute Kelly fraction from a list of completed trades.

    Returns dict with p, q, b, kelly_full, kelly_half, kelly_quarter.
    Returns None if insufficient data.
    """
    if len(deals) < 5:
        return None

    # Group by stock, compute P&L per trade
    trade_pnls = []
    # Simple approach: for each filled order, we need entry and exit.
    # Since we have flat deal records, we approximate:
    #   - BUY deals: negative P&L placeholder (we need sell to compute)
    #   - SELL deals: positive means profit
    #
    # For SIMULATE we pair consecutive BUY/SELL of same code as round trips.

    # Build per-stock queue of buys
    from collections import defaultdict, deque
    buy_queue = defaultdict(deque)  # code -> deque of (qty, price)
    round_trips = []  # list of (pnl_pct, pnl_abs)

    sorted_deals = sorted(deals, key=lambda d: d.get("create_time", ""))

    for d in sorted_deals:
        code = d["code"]
        side = d["trd_side"]
        qty = d["fill_qty"]
        price = d["avg_price"]

        if side == ft.TrdSide.BUY:
            buy_queue[code].append((qty, price))
        elif side == ft.TrdSide.SELL:
            # Match against buys (FIFO)
            remaining = qty
            while remaining > 0 and buy_queue[code]:
                buy_qty, buy_price = buy_queue[code][0]
                matched = min(remaining, buy_qty)
                pnl_pct = (price - buy_price) / buy_price if buy_price > 0 else 0
                pnl_abs = pnl_pct * matched * buy_price
                round_trips.append({
                    "pnl_pct": pnl_pct,
                    "pnl_abs": pnl_abs,
                    "qty": matched,
                })
                remaining -= matched
                if matched == buy_qty:
                    buy_queue[code].popleft()
                else:
                    buy_queue[code][0] = (buy_qty - matched, buy_price)

    if len(round_trips) < 5:
        logger.info("Only %d round-trip(s) found — need ≥ 5 for Kelly.", len(round_trips))
        return None

    wins = [t for t in round_trips if t["pnl_abs"] > 0]
    losses = [t for t in round_trips if t["pnl_abs"] <= 0]

    n = len(round_trips)
    p = len(wins) / n
    q = 1.0 - p

    avg_win = sum(t["pnl_abs"] for t in wins) / len(wins) if wins else 0
    avg_loss = abs(sum(t["pnl_abs"] for t in losses) / len(losses)) if losses else 1e-10

    # Win/loss ratio
    b = avg_win / avg_loss if avg_loss > 0 else 0

    # Kelly: f* = (p * b - q) / b
    # Laplace smoothing if p == 0 or p == 1
    p_smooth = (len(wins) + 1) / (n + 2)
    q_smooth = 1.0 - p_smooth
    b_adj = avg_win / avg_loss if avg_loss > 0 else 1.0

    kelly_full = (p_smooth * b_adj - q_smooth) / b_adj if b_adj > 0 else -1

    return {
        "n_trades": n,
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": p,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "wr_ratio": b,
        "kelly_full": kelly_full,
        "kelly_half": kelly_full / 2,
        "kelly_quarter": kelly_full / 4,
        "round_trips": round_trips,
    }

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Kelly Criterion position sizer")
    parser.add_argument("code", nargs="?", default=DEFAULT_STOCK,
                        help="Stock ticker (default HK.00700)")
    parser.add_argument("--fraction", type=float, default=DEFAULT_FRACTION,
                        help="Kelly fraction to use (default 0.5 = half-Kelly)")
    parser.add_argument("--max-pct", type=float, default=DEFAULT_MAX_PCT,
                        help="Max equity fraction to risk (default 0.25 = quarter-Kelly cap)")
    args = parser.parse_args()

    code = args.code
    kelly_fraction = args.fraction
    max_pct = args.max_pct

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()
    pwd = get_demo_trade_password()

    try:
        # ── Unlock SIMULATE account ────────────────────────────────────
        ret, _ = trd_ctx.unlock_trade(pwd, trd_env=TRD_ENV)
        if ret != ft.RetCode.SUCCESS:
            logger.error("unlock_trade failed: %s", ret)
            return
        logger.info("SIMULATE account unlocked.")

        # ── Run Kelly analysis ─────────────────────────────────────────
        logger.info("Analysing trade history …")
        deals = get_trade_history(trd_ctx)
        if not deals:
            logger.warning("No historical trades found. "
                           "Run some SIMULATE trades first (e.g. examples 04/06), then retry.")
            return

        logger.info("Found %d filled order(s).", len(deals))
        result = compute_kelly(deals)

        if result is None:
            logger.warning("Insufficient round-trip data for Kelly calculation. "
                           "Need ≥ 5 paired BUY/SELL trades.")
            # Fall back: just show account info
            ret_acc, acc = trd_ctx.accinfo_query(trd_env=TRD_ENV)
            if ret_acc == ft.RetCode.SUCCESS:
                logger.info("Account total assets: %.2f", acc.iloc[-1].get("total_assets", 0))
            return

        # ── Display results ────────────────────────────────────────────
        print("\n" + "=" * 56)
        print(f"  KELLY CRITERION ANALYSIS — {code}")
        print("=" * 56)
        print(f"  Round trips analysed : {result['n_trades']}")
        print(f"  Wins / Losses        : {result['wins']} / {result['losses']}")
        print(f"  Win rate             : {result['win_rate']:.1%}")
        print(f"  Avg win              : ${result['avg_win']:.2f}")
        print(f"  Avg loss             : ${result['avg_loss']:.2f}")
        print(f"  Win/Loss ratio (b)   : {result['wr_ratio']:.3f}")
        print("-" * 56)
        print(f"  Kelly (full)         : {result['kelly_full']:.1%}")
        print(f"  Kelly (half)         : {result['kelly_half']:.1%}")
        print(f"  Kelly (quarter)      : {result['kelly_quarter']:.1%}")
        print("-" * 56)

        # ── Negative Kelly? ────────────────────────────────────────────
        if result["kelly_full"] <= 0:
            print("  ⚠️  NO EDGE DETECTED — Kelly ≤ 0. Do not trade.")
            print("=" * 56 + "\n")
            return

        # ── Position sizing ────────────────────────────────────────────
        chosen_kelly = result["kelly_full"] * kelly_fraction
        chosen_kelly = min(chosen_kelly, max_pct)  # cap

        ret_acc, acc = trd_ctx.accinfo_query(trd_env=TRD_ENV)
        if ret_acc != ft.RetCode.SUCCESS:
            logger.error("accinfo_query failed: %s", ret_acc)
            return

        equity = float(acc.iloc[-1].get("total_assets", 0))
        risk_amount = equity * chosen_kelly

        last_price = get_last_price(quote_ctx, code)
        if last_price is None:
            return

        # ATR-based stop (10-period ATR, daily)
        stop_distance_pct = 0.02  # 2 % stop as default
        risk_per_share = last_price * stop_distance_pct
        if risk_per_share < 0.01:
            risk_per_share = 0.01

        shares = int(risk_amount / risk_per_share)
        max_shares = int(equity * max_pct / last_price)

        print(f"  Equity               : ${equity:,.2f}")
        print(f"  Chosen Kelly fraction : {chosen_kelly:.1%}")
        print(f"  Risk amount           : ${risk_amount:,.2f}")
        print(f"  Risk per share        : ${risk_per_share:.4f}")
        print(f"  Max shares (cap)      : {max_shares}")
        print(f"  Kelly-sized shares    : {shares}")
        print(f"  At price              : ${last_price:.2f}")
        print("=" * 56)

        if shares <= 0:
            print("  ⚠️  Kelly size rounds to 0 shares — position too small.")
        else:
            final_shares = min(shares, max_shares)
            print(f"\n  → Ready to BUY {final_shares} shares of {code} "
                  f"@ ${last_price:.2f}")

            resp = input("  Place order? (y/N): ").strip().lower()
            if resp == "y":
                order_id = place_market_order(trd_ctx, code, ft.TrdSide.BUY, final_shares)
                if order_id:
                    logger.info("Kelly-sized order placed: %s", order_id)
                else:
                    logger.error("Order placement failed.")
            else:
                logger.info("Skipped — no order placed.")

    finally:
        logger.info("Cleaning up …")
        trd_ctx.cancel_all_order(cancel_all_orders=True, trd_env=TRD_ENV)
        quote_ctx.close()
        trd_ctx.close()
        logger.info("Done.")


def get_last_price(quote_ctx, code):
    ret, df = quote_ctx.get_stock_quote(code)
    if ret != ft.RetCode.SUCCESS:
        logger.error("get_stock_quote failed: %s", ret)
        return None
    return df.iloc[-1]["last_price"]


def place_market_order(trd_ctx, code, direction, qty):
    ret, order_id = trd_ctx.place_order(
        price=0,
        code=code,
        qty=qty,
        trd_side=direction,
        order_type=ft.OrderType.NORMAL,
        trd_env=TRD_ENV,
    )
    if ret != ft.RetCode.SUCCESS:
        logger.error("place_order failed: %s", ret)
        return None
    return order_id


if __name__ == "__main__":
    main()