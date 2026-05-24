import sys, logging, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

SCAN_LIST = ["US.GME", "US.AMC", "US.NVDA", "US.TSLA", "US.AAPL", "US.PLTR", "US.SNAP"]


def compute_squeeze_score(si_pct, days_to_cover, short_vol_pct, broker_conc):
    score = 0
    if si_pct > 40:
        score += 60
    elif si_pct > 20:
        score += 40
    elif si_pct > 10:
        score += 20

    if days_to_cover > 10:
        score += 25
    elif days_to_cover > 5:
        score += 15

    if short_vol_pct > 50:
        score += 25
    elif short_vol_pct > 30:
        score += 15

    if broker_conc > 0.6:
        score += 15
    elif broker_conc > 0.4:
        score += 8

    return min(score, 100)


def signal_label(score):
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "WATCH"
    return "LOW"


def main():
    parser = argparse.ArgumentParser(description="Short Squeeze Risk Scanner")
    parser.add_argument("--codes", default=",".join(SCAN_LIST), help="Comma-separated US stock codes")
    args = parser.parse_args()
    codes = [c.strip() for c in args.codes.split(",") if c.strip().startswith("US.")]

    ctx = create_quote_context()

    try:
        rows = []
        for code in codes:
            row = {"code": code, "si_pct": 0, "days_to_cover": 0, "short_vol_pct": 0, "broker_conc": 0, "score": 0}

            ret1, us_df, _ = ctx.get_short_interest(code)
            if ret1 == 0 and us_df is not None and not us_df.empty:
                latest = us_df.iloc[0]
                row["si_pct"] = float(latest.get("short_percent", 0))
                row["days_to_cover"] = float(latest.get("days_to_cover", 0))

            ret2, us_df2, _ = ctx.get_daily_short_volume(code)
            if ret2 == 0 and us_df2 is not None and not us_df2.empty:
                latest = us_df2.iloc[0]
                sv = float(latest.get("short_percent", 0))
                if sv > 0:
                    row["short_vol_pct"] = sv

            ret3, broker_df = ctx.get_top_ten_buy_sell_brokers(code)
            if ret3 == 0 and broker_df is not None and not broker_df.empty:
                top3 = broker_df.head(3)
                total_net = abs(broker_df["net_vol"]).sum()
                top3_net = abs(top3["net_vol"]).sum()
                if total_net > 0:
                    row["broker_conc"] = top3_net / total_net

            row["score"] = compute_squeeze_score(
                row["si_pct"], row["days_to_cover"], row["short_vol_pct"], row["broker_conc"],
            )
            rows.append(row)

        rows.sort(key=lambda r: r["score"], reverse=True)

        print(f"\n  === SHORT SQUEEZE RISK SCANNER ===\n")
        print(f"  {'Rank':<6} {'Stock':<12} {'SI%':<8} {'Days2Cover':<12} {'ShortVol%':<10} {'BrokerConc':<12} {'Score':<6} Signal")
        print(f"  {'-'*6} {'-'*12} {'-'*8} {'-'*12} {'-'*10} {'-'*12} {'-'*6} {'-'*8}")
        for i, r in enumerate(rows, 1):
            sig = signal_label(r["score"])
            print(f"  {i:<6} {r['code']:<12} {r['si_pct']:<8.1f} {r['days_to_cover']:<12.1f} {r['short_vol_pct']:<10.1f} {r['broker_conc']:<12.2f} {r['score']:<6} {sig}")

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
