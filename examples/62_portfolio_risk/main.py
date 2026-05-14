#!/usr/bin/env python3
"""
62 — Portfolio Risk Monitor

Poll positions, compute aggregate risk metrics, and alert when thresholds
are breached. No order placement — pure monitoring.

Risk metrics:
  - Concentration % per position
  - Leverage ratio
  - Buying power used
  - Unrealized P&L %
  - Margin utilization
  - Number of positions

SDK: OpenSecTradeContext.position_list_query()
               .accinfo_query()
               .get_margin_ratio()
    OpenQuoteContext.get_stock_quote()
"""

import sys
import time
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context, create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

POLL_INTERVAL = 30
CONCENTRATION_WARN = 15.0
LEVERAGE_WARN = 2.0
BP_USED_WARN = 80.0
UNREALIZED_LOSS_WARN = -10.0
MARGIN_WARN = 70.0


def main():
    print("  === Portfolio Risk Monitor ===\n")
    print(f"  Interval: {POLL_INTERVAL}s")
    print(f"  Thresholds: concentration > {CONCENTRATION_WARN}%, "
          f"leverage > {LEVERAGE_WARN}x, "
          f"BP used > {BP_USED_WARN}%, "
          f"unrealized P&L < {UNREALIZED_LOSS_WARN}%, "
          f"margin > {MARGIN_WARN}%\n")

    quote_ctx = create_quote_context()
    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        ret, data = trd_ctx.unlock_trade(get_demo_trade_password())
        if ret != ft.RET_OK:
            print(f"  unlock_trade failed: {data}")
            return

        print(f"  {'='*70}")

        while True:
            ret, acc = trd_ctx.accinfo_query(trd_env=ft.TrdEnv.SIMULATE)
            total_equity = 0.0
            buying_power = 0.0
            if ret == ft.RET_OK and acc is not None and not acc.empty:
                total_equity = float(acc.iloc[0].get("total_assets",
                                    acc.iloc[0].get("power", 0)))
                buying_power = float(acc.iloc[0].get("power",
                               acc.iloc[0].get("available_funds", 0)))

            ret, positions = trd_ctx.position_list_query(trd_env=ft.TrdEnv.SIMULATE)
            alerts = []
            pos_rows = []

            if ret == ft.RET_OK and positions is not None and not positions.empty:
                codes = positions["code"].tolist()
                ret2, quotes = quote_ctx.get_stock_quote(codes) if codes else (0, None)
                quote_map = {}
                if ret2 == 0 and quotes is not None and not quotes.empty:
                    for _, r in quotes.iterrows():
                        quote_map[str(r.get("code", ""))] = float(r.get("last_price", 0))

                for _, row in positions.iterrows():
                    code = str(row.get("code", ""))
                    qty = float(row.get("qty", 0))
                    cost = float(row.get("cost_price", 0))
                    mkt_val = float(row.get("market_val", row.get("pl_ratio", 0)))
                    cur_price = quote_map.get(code, cost)
                    pos_value = qty * cur_price
                    cost_value = qty * cost
                    pnl_pct = ((cur_price - cost) / cost * 100) if cost else 0
                    weight = (pos_value / total_equity * 100) if total_equity else 0

                    pos_rows.append({
                        "code": code,
                        "qty": qty,
                        "cost": cost,
                        "price": cur_price,
                        "value": pos_value,
                        "pnl_pct": pnl_pct,
                        "weight_pct": weight,
                    })

                    if weight > CONCENTRATION_WARN:
                        alerts.append(f"CONCENTRATION: {code} at {weight:.1f}% "
                                      f"(>{CONCENTRATION_WARN:.0f}%)")

            total_position_value = sum(r["value"] for r in pos_rows)
            leverage = total_position_value / total_equity if total_equity else 0
            bp_used = ((total_equity - buying_power) / total_equity * 100) if total_equity else 0

            if leverage > LEVERAGE_WARN:
                alerts.append(f"LEVERAGE: {leverage:.2f}x (>{LEVERAGE_WARN:.1f}x)")
            if bp_used > BP_USED_WARN:
                alerts.append(f"BUYING POWER USED: {bp_used:.0f}% (>{BP_USED_WARN:.0f}%)")

            total_pnl_pct = sum(r["pnl_pct"] * r["value"] for r in pos_rows)
            total_pnl_pct = total_pnl_pct / total_position_value if total_position_value else 0
            if total_pnl_pct < UNREALIZED_LOSS_WARN:
                alerts.append(f"UNREALIZED P&L: {total_pnl_pct:+.1f}% "
                              f"(<{UNREALIZED_LOSS_WARN:.0f}%)")

            ret3, margin_data = trd_ctx.get_margin_ratio(code_list=[])
            if ret3 == ft.RET_OK and margin_data is not None and not margin_data.empty:
                margin_used = float(margin_data.iloc[0].get("margin_ratio", 0)) * 100
                if margin_used > MARGIN_WARN:
                    alerts.append(f"MARGIN: {margin_used:.0f}% (>{MARGIN_WARN:.0f}%)")
            else:
                margin_used = 0.0

            print(f"\n  [{time.strftime('%H:%M:%S')}]")
            print(f"  {'Code':<12} {'Qty':>8} {'Cost':>10} {'Price':>10} "
                  f"{'Value':>12} {'P&L%':>8} {'Weight':>8}")
            print(f"  {'-'*12} {'-'*8} {'-'*10} {'-'*10} "
                  f"{'-'*12} {'-'*8} {'-'*8}")

            for r in pos_rows:
                print(f"  {r['code']:<12} {r['qty']:>8.0f} {r['cost']:>10.2f} "
                      f"{r['price']:>10.2f} {r['value']:>12,.0f} "
                      f"{r['pnl_pct']:>+7.1f}% {r['weight_pct']:>7.1f}%")

            if not pos_rows:
                print(f"  (no positions)")

            print(f"\n  {'Total Equity:':<20} {total_equity:>12,.2f}")
            print(f"  {'Buying Power:':<20} {buying_power:>12,.2f}")
            print(f"  {'Leverage:':<20} {leverage:>12.2f}x")
            print(f"  {'BP Used:':<20} {bp_used:>11.1f}%")
            print(f"  {'Unrealized P&L:':<20} {total_pnl_pct:>+11.1f}%")
            print(f"  {'Margin Used:':<20} {margin_used:>11.1f}%")
            print(f"  {'Positions:':<20} {len(pos_rows):>12}")

            if alerts:
                print(f"\n  {'⚠' * 5} ALERTS {'⚠' * 5}")
                for a in alerts:
                    print(f"  ⚠ {a}")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        pass
    finally:
        quote_ctx.close()
        trd_ctx.close()
        print("\n  Done.")


if __name__ == "__main__":
    main()
