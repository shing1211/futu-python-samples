import sys, logging, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
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
    parser = argparse.ArgumentParser(description="Institutional Flow Tracker")
    parser.add_argument("--code", default="US.AAPL", help="Stock code")
    args = parser.parse_args()
    code = args.code

    ctx = create_quote_context()

    try:
        inst_df = safe_df(ctx.get_shareholders_institutional(code))
        detail_df = safe_df(ctx.get_shareholders_holder_detail(code))
        changes_df = safe_df(ctx.get_shareholders_holding_changes(code))
        broker_result = ctx.get_top_ten_buy_sell_brokers(code)
        broker_df = safe_df(broker_result)

        print(f"\n  === INSTITUTIONAL FLOW TRACKER: {code} ===\n")

        if inst_df is not None:
            latest = inst_df.iloc[-1] if len(inst_df) > 1 else inst_df.iloc[0]
            inst_qty = int(latest.get("institution_quantity", 0))
            inst_qty_chg = int(latest.get("institution_quantity_change", 0))
            holder_qty = int(latest.get("holder_quantity", 0))
            holder_qty_chg = int(latest.get("holder_quantity_change", 0))
            holder_pct = float(latest.get("holder_pct", 0))
            holder_pct_chg = float(latest.get("holder_pct_change", 0))
            period = latest.get("period_text", "")

            print(f"  Period: {period}")
            print(f"  {'Metric':<28} {'Value':<16} {'Change':<16}")
            print(f"  {'-'*28} {'-'*16} {'-'*16}")
            print(f"  {'Institution Quantity':<28} {inst_qty:<16,} {inst_qty_chg:<+,}")
            print(f"  {'Holder Count':<28} {holder_qty:<16,} {holder_qty_chg:<+,}")
            print(f"  {'Holder %':<28} {holder_pct:<16.2f} {holder_pct_chg:<+.2f}")
            print()

        if detail_df is not None:
            detail_df_sorted = detail_df.sort_values("holder_quantity", ascending=False)
            print(f"  TOP HOLDERS:")
            print(f"  {'Rank':<6} {'Holder Name':<28} {'Shares':<14} {'% Out':<8} {'Change':<12}")
            print(f"  {'-'*6} {'-'*28} {'-'*14} {'-'*8} {'-'*12}")
            for i, (_, row) in enumerate(detail_df_sorted.head(10).iterrows(), 1):
                name = row.get("name", "?")
                shares = int(row.get("holder_quantity", 0))
                ratio = float(row.get("holder_pct", 0))
                change = row.get("holder_quantity_change", 0)
                print(f"  {i:<6} {str(name):<28} {shares:<14,} {ratio:<7.2f}% {change:<+,}")
            print()

        if changes_df is not None:
            change_col = "share_change_num" if "share_change_num" in changes_df.columns else "holder_quantity_change"
            if "holder_type" in changes_df.columns:
                inst_changes = changes_df[changes_df["holder_type"].str.contains("institution|fund|bank", case=False, na=False)]
            else:
                inst_changes = changes_df
            if not inst_changes.empty:
                top_buy = inst_changes.nlargest(5, change_col)
                top_sell = inst_changes.nsmallest(5, change_col)
                print(f"  TOP ACCUMULATORS (net buy):")
                print(f"  {'Name':<28} {'Shares Changed':<16} {'Date':<14}")
                print(f"  {'-'*28} {'-'*16} {'-'*14}")
                for _, row in top_buy.iterrows():
                    print(f"  {str(row.get('name','?')):<28} {row.get(change_col,0):<+16,} {str(row.get('holding_date_str','')):<14}")
                print()
                print(f"  TOP DISTRIBUTORS (net sell):")
                print(f"  {'Name':<28} {'Shares Changed':<16} {'Date':<14}")
                print(f"  {'-'*28} {'-'*16} {'-'*14}")
                for _, row in top_sell.iterrows():
                    print(f"  {str(row.get('name','?')):<28} {row.get(change_col,0):<+,} {str(row.get('holding_date_str','')):<14}")
                print()

        if broker_df is not None:
            print(f"  BROKER FLOW (last period):")
            print(f"  {'Broker':<24} {'Net Vol':<12} {'Signal':<10}")
            print(f"  {'-'*24} {'-'*12} {'-'*10}")
            for _, row in broker_df.head(8).iterrows():
                broker = (row.get("broker_name", "") or "")[:22]
                net_vol = int(row.get("net_vol", 0))
                signal = "BUYING" if net_vol > 0 else ("SELLING" if net_vol < 0 else "NEUTRAL")
                print(f"  {broker:<24} {net_vol:<+12,} {signal:<10}")
            print()

        verdict = "INCONCLUSIVE"
        if inst_df is not None and broker_df is not None:
            inst_up = inst_qty_chg > 0
            broker_up = any(row.get("net_vol", 0) > 0 for _, row in broker_df.iterrows())
            broker_down = any(row.get("net_vol", 0) < 0 for _, row in broker_df.iterrows())
            if inst_up and broker_up:
                verdict = "STRONG ACCUMULATION"
            elif inst_up and broker_down:
                verdict = "MIXED — INSTITUTIONS BUYING, BROKERS SELLING"
            elif not inst_up and broker_up:
                verdict = "MIXED — INSTITUTIONS SELLING, BROKERS BUYING"
            elif not inst_up and broker_down:
                verdict = "STRONG DISTRIBUTION"
        elif inst_df is not None:
            verdict = "BULLISH ACCUMULATION" if inst_qty_chg > 0 else "BEARISH DISTRIBUTION"

        print(f"  VERDICT: {verdict}")

        if inst_df is None and detail_df is None:
            logger.warning("No institutional data available for %s", code)

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
