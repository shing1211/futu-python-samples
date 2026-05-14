"""Margin Utilization Monitor — SIMULATE only.

Tracks real-time margin usage across SIMULATE positions, alerts on
margin call proximity, and computes liquidation prices.

Usage:
    python3 main.py [--symbols 'HK.00700,US.TCEHY'] [--margin-threshold 0.8]
"""

import sys
import os
import logging
import argparse
import time

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
DEFAULT_SYMBOLS = ["HK.00700", "US.TCEHY", "HK.00005"]
DEFAULT_MARGIN_THRESHOLD = 0.80  # alert when 80% utilized
POLL_INTERVAL = 10  # seconds
TRD_ENV = ft.TrdEnv.SIMULATE


# ---------------------------------------------------------------------------
# Margin helpers
# ---------------------------------------------------------------------------

def get_margin_info(trd_ctx, quote_ctx, symbols):
    """Gather margin info for each symbol in the portfolio.

    Returns dict per symbol with position, margin required, available,
    utilization, and liquidation price.
    """
    # Current positions
    positions = {}
    ret_pos, df_pos = trd_ctx.position_list_query(trd_env=TRD_ENV)
    if ret_pos == ft.RetCode.SUCCESS and df_pos is not None and not df_pos.empty:
        for _, row in df_pos.iterrows():
            code = row.get("code", "")
            qty = float(row.get("qty", 0) or 0)
            if code in symbols and qty > 0:
                positions[code] = {
                    "qty": int(qty),
                    "cost_price": float(row.get("cost_price", 0) or 0),
                    "market_val": float(row.get("market_val", 0) or 0),
                    "profit_loss": float(row.get("profit_loss", 0) or 0),
                }

    # Live prices
    prices = {}
    for code in symbols:
        ret, df = quote_ctx.get_stock_quote(code)
        if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
            prices[code] = float(df.iloc[-1]["last_price"])

    # Trading info (margin ratios, lot sizes)
    margin_info = {}
    for code in symbols:
        if code not in positions:
            continue
        ret_ti, df_ti = trd_ctx.acctradinginfo_query(
            code, trd_env=TRD_ENV,
        )
        lot_size = 100  # default
        margin_ratio = 1.0  # 100% margin required
        if ret_ti == ft.RetCode.SUCCESS and df_ti is not None and not df_ti.empty:
            lot_size = float(df_ti.iloc[-1].get("lot_size", 100) or 100)
            # margin_ratio may be in the response
            for col in df_ti.columns:
                if "margin" in col.lower() or "initial" in col.lower():
                    try:
                        margin_ratio = float(df_ti.iloc[-1][col]) / 100
                        break
                    except (ValueError, TypeError):
                        pass

        pos = positions[code]
        current_price = prices.get(code, pos.get("cost_price", 0))
        market_value = current_price * pos["qty"]
        margin_required = market_value * margin_ratio

        # Approximate liquidation price (simplified)
        # Liquidation when equity = maintenance margin (typically ~30-50%)
        maintenance_margin = 0.30  # assume 30%
        if pos["qty"] > 0:
            entry_price = pos.get("cost_price", 0) / pos["qty"] if pos["qty"] > 0 else 0
            # For longs: liq_price = entry_price × (1 - (1 - maintenance) / margin_ratio)
            if margin_ratio > 0:
                liq_pct = 1 - (1 - maintenance_margin) / margin_ratio
                liq_price = entry_price * (1 - liq_pct) if liq_pct > 0 else 0
            else:
                liq_price = 0
        else:
            liq_price = 0

        margin_info[code] = {
            "qty": pos["qty"],
            "entry_price": positions[code]["cost_price"] / pos["qty"] if pos["qty"] > 0 else 0,
            "current_price": current_price,
            "market_value": market_value,
            "margin_required": margin_required,
            "margin_ratio": margin_ratio,
            "lot_size": int(lot_size),
            "liquidation_price": liq_price,
            "unrealized_pnl": pos["profit_loss"],
        }

    return margin_info


def get_account_equity(trd_ctx):
    """Get total account equity and available margin."""
    ret, df = trd_ctx.accinfo_query(trd_env=TRD_ENV)
    if ret != ft.RetCode.SUCCESS or df is None or df.empty:
        return None, None, None

    row = df.iloc[-1]
    total_assets = float(row.get("total_assets", 0) or 0)
    cash = float(row.get("cash", 0) or 0)
    frozen_cash = float(row.get("frozen_cash", 0) or 0)

    return total_assets, cash, frozen_cash


def format_margin_bar(utilization, width=30):
    """Format a margin utilization bar."""
    filled = int(utilization * width)
    filled = min(filled, width)
    if utilization < 0.5:
        color = "\033[92m"  # green
    elif utilization < 0.8:
        color = "\033[93m"  # yellow
    else:
        color = "\033[91m"  # red
    reset = "\033[0m"
    bar = f"{color}{'█' * filled}{'░' * (width - filled)}{reset}"
    return bar


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Margin Utilization Monitor")
    parser.add_argument("--symbols", default=",".join(DEFAULT_SYMBOLS),
                        help="Comma-separated stock symbols")
    parser.add_argument("--margin-threshold", type=float,
                        default=DEFAULT_MARGIN_THRESHOLD,
                        help="Alert when utilization exceeds this (default 0.80)")
    args = parser.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    threshold = args.margin_threshold

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context()
    pwd = get_demo_trade_password()

    try:
        # Unlock SIMULATE
        ret, _ = trd_ctx.unlock_trade(pwd, trd_env=TRD_ENV)
        if ret != ft.RetCode.SUCCESS:
            logger.warning("unlock_trade returned %s (may be already unlocked)", ret)

        print(f"\n{'='*64}")
        print(f"  💰 MARGIN UTILIZATION MONITOR")
        print(f"  Symbols: {', '.join(symbols)}")
        print(f"  Alert threshold: {threshold:.0%}")
        print(f"  Poll interval: {POLL_INTERVAL}s")
        print(f"{'='*64}")
        print("  Press Ctrl+C to stop.\n")

        while True:
            # Account equity
            total_eq, cash, frozen = get_account_equity(trd_ctx)
            margin_used_total = 0

            print(f"\r  ── Account ──", end="")
            if total_eq is not None:
                print(
                    f"  Equity: ${total_eq:>12,.2f}  "
                    f"Cash: ${cash:>12,.2f}  Frozen: ${frozen:>12,.2f}",
                    end="",
                )
            print()

            # Per-symbol margin
            margin_info = get_margin_info(trd_ctx, quote_ctx, symbols)

            if not margin_info:
                print("  No open positions. Waiting …")
                time.sleep(POLL_INTERVAL)
                continue

            for code in sorted(margin_info.keys()):
                info = margin_info[code]

                total_margin = info["market_value"]
                req_margin = info["margin_required"]
                # Utilization based on market value vs equity
                if total_eq and total_eq > 0:
                    util = total_margin / total_eq
                else:
                    util = 0

                bar = format_margin_bar(util)
                alert = " ⚠️ MARGIN ALERT" if util > threshold else ""

                pnl = info["unrealized_pnl"]
                pnl_str = f"${pnl:>+10,.2f}"
                liq = info["liquidation_price"]
                liq_str = f"${liq:>10,.2f}" if liq > 0 else "N/A"

                print(
                    f"  {code:<12} "
                    f"Qty: {info['qty']:>6,}  "
                    f"@ ${info['current_price']:>8.2f}  "
                    f"Value: ${info['market_value']:>12,.2f}  "
                    f"Margin: ${req_margin:>10,.2f}  "
                    f"Util: {util:>6.1%}  {bar}{alert}  "
                    f"P&L: {pnl_str}  "
                    f"Liq: {liq_str}"
                )

                margin_used_total += req_margin

            # Aggregate utilization
            if total_eq and total_eq > 0:
                total_util = margin_used_total / total_eq
                total_bar = format_margin_bar(total_util)
                print(f"\n  Total Margin Used: ${margin_used_total:>12,.2f}  "
                      f"({total_util:>6.1%}) {total_bar}")

            time.sleep(POLL_INTERVAL)

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