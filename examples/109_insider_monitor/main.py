import sys, logging, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import pandas as pd
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def safe_df(result):
    if result is None:
        return None
    ret = result[0]
    if ret != 0:
        return None
    df = result[1]
    if df is None or df.empty:
        return None
    return df


def main():
    parser = argparse.ArgumentParser(description="Insider Activity Monitor")
    parser.add_argument("--code", default="US.AAPL", help="Stock code (US only)")
    args = parser.parse_args()
    code = args.code

    if not code.startswith("US."):
        logger.error("Insider data is only available for US stocks")
        sys.exit(1)

    ctx = create_quote_context()

    try:
        holder_df = safe_df(ctx.get_insider_holder_list(code))
        trade_df = safe_df(ctx.get_insider_trade_list(code))
        exec_df = safe_df(ctx.get_company_executives(code))

        print(f"\n  === INSIDER ACTIVITY MONITOR: {code} ===\n")

        if holder_df is not None:
            total = len(holder_df)
            bought = int(holder_df["insider_bought_count"].sum()) if "insider_bought_count" in holder_df.columns else 0
            sold = int(holder_df["insider_sold_count"].sum()) if "insider_sold_count" in holder_df.columns else 0
            net_ratio = (bought - sold) / total if total > 0 else 0
            print(f"  Total Insiders: {total}  |  Bought (30d): {bought}  |  Sold (30d): {sold}  |  Net Ratio: {net_ratio:+.2f}\n")

            if net_ratio > 0.3:
                print(f"  SIGNAL: BULLISH (insider buying outweighs selling)\n")
            elif net_ratio < -0.3:
                print(f"  SIGNAL: BEARISH (insider selling outweighs buying)\n")

            print(f"  {'Name':<22} {'Title':<20} {'Holdings':<10} {'Bought':<8} {'Sold':<8} {'Net':<8}")
            print(f"  {'-'*22} {'-'*20} {'-'*10} {'-'*8} {'-'*8} {'-'*8}")
            for _, row in holder_df.iterrows():
                name = row.get("name", "?")
                title = (row.get("title", "") or "")[:18]
                hq = int(row.get("holder_quantity", 0))
                ib = int(row.get("insider_bought_count", 0))
                iso = int(row.get("insider_sold_count", 0))
                net = ib - iso
                print(f"  {name:<22} {title:<20} {hq:<10} {ib:<8} {iso:<8} {net:<+8}")

        if trade_df is not None:
            print(f"\n  Recent Insider Trades:")
            print(f"  {'Name':<22} {'Shares':<10} {'Min Price':<12} {'Max Price':<12} {'Type':<12} {'Date':<14}")
            print(f"  {'-'*22} {'-'*10} {'-'*12} {'-'*12} {'-'*12} {'-'*14}")
            for _, row in trade_df.head(10).iterrows():
                name = row.get("name", "?")
                shares = int(row.get("trade_shares", 0))
                min_p = row.get("min_price", 0)
                max_p = row.get("max_price", 0)
                ttype = row.get("transaction_type", "?")
                date = str(row.get("min_trade_date_str", ""))
                print(f"  {name:<22} {shares:<10} {min_p:<12.2f} {max_p:<12.2f} {str(ttype):<12} {date:<14}")

        if exec_df is not None and not exec_df.empty:
            print(f"\n  Executive Roster:")
            print(f"  {'Name':<24} {'Position':<22} {'Age':<6} {'Tenure':<10}")
            print(f"  {'-'*24} {'-'*22} {'-'*6} {'-'*10}")
            for _, row in exec_df.head(8).iterrows():
                name = row.get("display_leader_name", row.get("leader_name", "?"))
                pos = (row.get("position_name", "") or "")[:20]
                age_val = row.get("leader_age", 0)
                if isinstance(age_val, float):
                    age = int(age_val) if not pd.isna(age_val) else 0
                else:
                    age = int(age_val) if age_val else 0
                print(f"  {name:<24} {pos:<22} {str(age) if age else '—':<6} {'—':<10}")

        if holder_df is None and trade_df is None:
            logger.warning("No insider data available for %s", code)

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
