import sys, logging, argparse, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def extract_eps(data):
    if not isinstance(data, dict):
        return None
    stmts = data.get("income_statement", data.get("financial_statement_list", []))
    if not stmts:
        return None
    stmt = stmts[0] if isinstance(stmts, list) else stmts
    if isinstance(stmt, dict):
        eps = stmt.get("eps", stmt.get("basic_eps", 0))
        revenue = stmt.get("revenue", stmt.get("total_revenue", 0))
        net_profit = stmt.get("net_profit", stmt.get("netProfit", 0))
        return {"eps": float(eps), "revenue": float(revenue), "net_profit": float(net_profit)}
    return None


def extract_consensus(data):
    if not isinstance(data, dict):
        return None
    consensus = data.get("analyst_consensus", data.get("consensus_list", []))
    if isinstance(consensus, list) and consensus:
        c = consensus[0] if isinstance(consensus[0], dict) else {}
        eps_est = c.get("current_eps_estimate", c.get("eps_estimate", 0))
        target = c.get("current_target_price", c.get("target_price", 0))
        return {"eps_estimate": float(eps_est), "target_price": float(target)}
    return None


def compute_surprise_score(actual_eps, consensus_eps, price_move_pct, iv_crush_pct):
    surprise_bps = 0
    if consensus_eps and consensus_eps != 0:
        surprise_bps = (actual_eps - consensus_eps) / abs(consensus_eps) * 10000
    elif actual_eps:
        surprise_bps = actual_eps * 100

    reaction = abs(price_move_pct)
    vol_impact = abs(iv_crush_pct)

    raw = 0.4 * min(abs(surprise_bps) / 2000, 1) + 0.3 * min(reaction / 10, 1) + 0.3 * min(vol_impact / 30, 1)
    return min(raw * 100, 100), surprise_bps


def main():
    parser = argparse.ArgumentParser(description="Earnings Surprise Dashboard")
    parser.add_argument("--code", default="US.NVDA", help="Stock code")
    args = parser.parse_args()
    code = args.code

    ctx = create_quote_context()

    try:
        eps_data = extract_eps(ctx.get_financials_statements(code, 0, 0)[1]) if ctx.get_financials_statements(code, 0, 0)[0] == 0 else None
        consensus_data = extract_consensus(ctx.get_research_analyst_consensus(code)[1]) if ctx.get_research_analyst_consensus(code)[0] == 0 else None

        price_move_df = None
        ret1, pm = ctx.get_financials_earnings_price_move(code)
        if ret1 == 0 and pm is not None and not pm.empty:
            price_move_df = pm

        price_hist_df = None
        ret2, ph = ctx.get_financials_earnings_price_history(code)
        if ret2 == 0 and ph is not None and not ph.empty:
            price_hist_df = ph

        print(f"\n  === EARNINGS SURPRISE DASHBOARD: {code} ===\n")

        actual_eps = eps_data["eps"] if eps_data else None
        consensus_eps = consensus_data["eps_estimate"] if consensus_data else None
        print(f"  Latest EPS:         {actual_eps or 'N/A'}")
        print(f"  Consensus Estimate: {consensus_eps or 'N/A'}")
        if actual_eps and consensus_eps and consensus_eps != 0:
            surprise_bps = (actual_eps - consensus_eps) / abs(consensus_eps) * 10000
            print(f"  Surprise (bps):     {surprise_bps:+.0f}")
        print()

        if price_hist_df is not None and not price_hist_df.empty:
            print(f"  {'Period':<12} {'Fiscal Yr':<10} {'Pub Type':<10} {'IV Crush':<10} {'Vol Ratio':<10}")
            print(f"  {'-'*12} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
            for _, row in price_hist_df.iterrows():
                iv_crush = row.get("option_iv_crush", 0)
                if isinstance(iv_crush, float) and abs(iv_crush) > 0.001:
                    crush_display = iv_crush if iv_crush > 1 else iv_crush * 100
                    print(f"  {str(row.get('period_text','')):<12} {str(row.get('fiscal_year','')):<10} {str(row.get('pub_type','')):<10} {crush_display:<9.1f}% {str(row.get('predict_vola_ratio_newest','')):<10}")

        if price_move_df is not None and not price_move_df.empty:
            print(f"\n  {'Day Offset':<12} {'Close':<10} {'Change%':<10}")
            print(f"  {'-'*12} {'-'*10} {'-'*10}")
            for _, row in price_move_df.iterrows():
                offset = row.get("day_offset", 0)
                close = row.get("close_price", 0)
                last_close = row.get("last_close_price", 0)
                change_pct = (close - last_close) / last_close * 100 if last_close and last_close != 0 else 0
                print(f"  {offset:<12} {close:<10.2f} {change_pct:<+9.2f}%")

        if price_hist_df is not None and price_move_df is not None:
            iv_crush_val = 0
            if not price_hist_df.empty:
                raw_crush = float(price_hist_df.iloc[0].get("option_iv_crush", 0))
                iv_crush_val = raw_crush if raw_crush > 1 else raw_crush * 100
            max_move = 0
            if not price_move_df.empty:
                for _, row in price_move_df.iterrows():
                    c, lc = row.get("close_price", 0), row.get("last_close_price", 0)
                    if lc and lc != 0:
                        max_move = max(max_move, abs((c - lc) / lc * 100))
            score, surprise_bps = compute_surprise_score(actual_eps or 0, consensus_eps or 0, max_move, iv_crush_val)
            grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "D"
            print(f"\n  COMPOSITE SURPRISE SCORE: {score:.0f}/100  GRADE: {grade}")

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
