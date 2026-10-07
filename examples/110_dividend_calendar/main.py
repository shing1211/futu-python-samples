import sys, time, logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

PORTFOLIO = ["HK.00005", "HK.00002", "HK.00066", "HK.00001", "HK.00003", "HK.00011"]


def safe_get_stock_price(ctx, code):
    try:
        ret, data = ctx.get_stock_quote([code])
        if ret == 0 and data is not None and not data.empty:
            return float(data.iloc[0].get("last_price", 0))
    except Exception:
        pass  # static-checks: allow-suppress -- safe_get_stock_price returns None on any failure by contract
    return None


def format_ts(ts):
    if ts and ts > 0:
        return time.strftime("%Y-%m-%d", time.gmtime(ts))
    return "—"


def main():
    parser = argparse.ArgumentParser(description="Dividend Capture Calendar")
    parser.add_argument("--codes", default=",".join(PORTFOLIO), help="Comma-separated stock codes")
    args = parser.parse_args()
    codes = [c.strip() for c in args.codes.split(",")]

    ctx = create_quote_context()

    try:
        events = []
        for code in codes:
            price = safe_get_stock_price(ctx, code)
            price_str = f"{price:.2f}" if price else "—"

            ret, data = ctx.get_corporate_actions_dividends(code)
            if ret == 0 and isinstance(data, dict):
                div_list = data.get("dividend_list", [])
                for d in div_list:
                    ex_date = d.get("ex_date", 0)
                    if isinstance(ex_date, str) and ex_date.isdigit():
                        ex_date = int(ex_date)
                    elif isinstance(ex_date, str):
                        ex_date = 0
                    if isinstance(ex_date, (int, float)) and ex_date > time.time():
                        amount = d.get("cash_dividend", d.get("dividend_amount", 0))
                        currency = d.get("currency", d.get("dividend_currency", "HKD"))
                        yield_pct = ""
                        if price and amount and float(amount) > 0:
                            annual = float(amount) * 4
                            yield_pct = f"{annual / price * 100:.1f}%"
                        events.append(("DIVIDEND", ex_date, code, f"{currency} {amount}", yield_pct, price_str))

            ret2, data2 = ctx.get_corporate_actions_buybacks(code)
            if ret2 == 0 and isinstance(data2, dict):
                hk_df = data2.get("hk_buy_back_list")
                if hk_df is not None and not hk_df.empty:
                    for _, row in hk_df.iterrows():
                        end_date = int(row.get("end_date", 0) or 0)
                        if end_date > time.time():
                            pct = row.get("percentage", 0) or 0
                            events.append(("BUYBACK", end_date, code, f"~{float(pct):.1f}%", str(row.get("buy_back_money", "—")), price_str))

            ret3, data3 = ctx.get_corporate_actions_stock_splits(code)
            if ret3 == 0 and isinstance(data3, dict):
                split_list = data3.get("split_list", [])
                for s in split_list:
                    ex_date = s.get("ex_date", 0)
                    if isinstance(ex_date, str) and ex_date.isdigit():
                        ex_date = int(ex_date)
                    elif isinstance(ex_date, str):
                        ex_date = 0
                    raw_rt = s.get("reform_type", 0) or 0
                    if isinstance(raw_rt, str):
                        reform_type = 1 if "合" in raw_rt else 0
                    else:
                        reform_type = int(raw_rt) if raw_rt else 0
                    raw_rate = s.get("rate", 0) or 0
                    if isinstance(raw_rate, str) and "→" in raw_rate:
                        rate_str = raw_rate.split("→")[-1].strip()
                        try:
                            rate = float(rate_str)
                        except ValueError:
                            rate = 0
                    else:
                        rate = float(raw_rate) if raw_rate else 0
                    label = "SPLIT" if reform_type == 0 else "REVERSE"
                    if isinstance(ex_date, (int, float)) and ex_date > time.time() and rate > 0:
                        rate_display = str(raw_rate) if isinstance(raw_rate, str) else f"{rate:.2f}:1"
                        events.append((label, ex_date, code, rate_display, "—", price_str))

        events.sort(key=lambda e: e[1])

        print(f"\n  === DIVIDEND CAPTURE CALENDAR ===\n")
        print(f"  {'Date':<14} {'Stock':<12} {'Event':<10} {'Amount':<14} {'Yield':<8} {'Price':<8}")
        print(f"  {'-'*14} {'-'*12} {'-'*10} {'-'*14} {'-'*8} {'-'*8}")
        for ev_type, ts, code, amount, yield_str, price_str in events:
            d = format_ts(ts)
            print(f"  {d:<14} {code:<12} {ev_type:<10} {str(amount):<14} {yield_str:<8} {price_str:<8}")

        if not events:
            print("  No upcoming corporate action events found.")

    finally:
        ctx.close()


if __name__ == "__main__":
    import argparse
    main()
