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


def main():
    parser = argparse.ArgumentParser(description="Valuation Heat Map")
    parser.add_argument("--code", default="HK.00700", help="Reference stock code")
    args = parser.parse_args()
    code = args.code

    ctx = create_quote_context()

    try:
        ret, val_data = ctx.get_valuation_detail(code)
        if ret != 0 or not isinstance(val_data, dict):
            logger.error("get_valuation_detail failed for %s", code)
            return

        trend = val_data.get("trend", {})
        current_val = trend.get("current_value", 0)
        avg_val = trend.get("average_value", 0)
        percentile = trend.get("valuation_percentile", 0)
        forward_val = trend.get("forward_value", 0)
        avg_minus_1s = trend.get("avg_minus_1_stddev", 0)
        avg_plus_1s = trend.get("avg_plus_1_stddev", 0)

        mkt_dist = val_data.get("market_distribution", {})
        total_stocks = mkt_dist.get("total", 0)
        ranking = mkt_dist.get("ranking", 0)
        mkt_avg = mkt_dist.get("average_value", 0)
        mkt_median = mkt_dist.get("median_value", 0)

        percentile_pct = percentile * 100 if percentile < 1 else percentile
        std_dev = avg_plus_1s - avg_val if avg_plus_1s > avg_val else 1
        z_score = (current_val - avg_val) / std_dev if std_dev > 0 else 0
        if z_score > 1.5:
            signal = "EXPENSIVE"
        elif z_score < -1.5:
            signal = "CHEAP"
        else:
            signal = "FAIR"

        print(f"\n  === VALUATION HEAT MAP: {code} ===\n")

        print(f"  Current PE:         {current_val:.2f}")
        print(f"  Forward PE:         {forward_val:.2f}" if forward_val else "")
        print(f"  3-Year Avg PE:      {avg_val:.2f}")
        print(f"  PE Range (1sd):      {avg_minus_1s:.2f} - {avg_plus_1s:.2f}")
        print()

        print(f"  Market Distribution (HK):")
        print(f"  Market Avg PE:      {mkt_avg:.2f}")
        print(f"  Market Median PE:   {mkt_median:.2f}")
        print(f"  Rank:               {ranking} / {total_stocks} (higher = more expensive)")
        print()

        sections = mkt_dist.get("sections", [])
        print(f"  {'PE Range':<18} {'Count':<8}")
        print(f"  {'-'*18} {'-'*8}")
        for s in sections:
            start = s.get("start", 0)
            end = s.get("end", None)
            count = s.get("number", 0)
            if end is None or (isinstance(end, (int, float)) and end == 0):
                rng = f"{start:.0f}+"
            else:
                rng = f"{start:.0f}-{float(end):.0f}"
            print(f"  {rng:<18} {count:<8}")
        print()

        print(f"\n  VERDICT: {code} trades at PE={current_val:.1f}, ")
        print(f"  which is in the {percentile_pct:.0f}th percentile ({signal}).")
        print(f"  Z-score vs 3-year mean: {z_score:.2f} (|z|<1.5 = fair, |z|>=1.5 = extreme)")
        if signal == "EXPENSIVE":
            print(f"  Suggestion: {code} is historically expensive. Wait for pullback towards {avg_val:.0f} PE.")
        elif signal == "CHEAP":
            print(f"  Suggestion: {code} is historically cheap. Consider accumulating while compressed.")
        else:
            print(f"  Suggestion: {code} is in fair value range. Monitor for breakout or breakdown.")

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
