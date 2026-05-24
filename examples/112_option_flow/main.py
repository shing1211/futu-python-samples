import sys, logging, argparse
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def build_screen_request():
    req = ft.OptionScreenRequest([ft.OptMarketCategory.US_STOCK])
    req.add_option_filter(ft.OptIndicator.VOLUME, lower=50)
    req.add_option_filter(ft.OptIndicator.OPEN_INTEREST, lower=200)
    req.add_sort(ft.OptIndicator.IMPLIED_VOLATILITY, desc=False)
    req.add_option_retrieve(ft.OptIndicator.IMPLIED_VOLATILITY)
    req.add_option_retrieve(ft.OptIndicator.HISTORY_VOLATILITY)
    req.add_option_retrieve(ft.OptIndicator.DELTA)
    req.add_option_retrieve(ft.OptIndicator.GAMMA)
    req.add_option_retrieve(ft.OptIndicator.VOLUME)
    req.add_option_retrieve(ft.OptIndicator.OPEN_INTEREST)
    req.add_option_retrieve(ft.OptIndicator.PREMIUM)
    req.add_option_retrieve(ft.OptIndicator.IV_HV_RATIO)
    req.add_option_retrieve(ft.OptIndicator.ITM_PROBABILITY)
    req.add_option_retrieve(ft.OptIndicator.STRIKE_PRICE)
    req.add_option_retrieve(ft.OptIndicator.LEFT_DAY)
    req.add_option_retrieve(ft.OptIndicator.OPTION_TYPE)
    req.add_option_retrieve(ft.OptIndicator.CHANGE_RATIO)
    req.add_underlying_retrieve(ft.OptUnderlyingIndicator.STOCK_PRICE)
    req.page_from = 0
    req.page_count = 50
    return req


def compute_flow_score(row):
    score = 0
    iv_hv = row.get("iv_hv_ratio", 0)
    if 0.8 <= iv_hv <= 1.2:
        score += 30
    itm_prob = row.get("itm_probability", 0)
    if itm_prob > 40:
        score += 30
    elif itm_prob > 20:
        score += 15
    vol = row.get("volume", 0)
    oi = row.get("open_interest", 1)
    vol_oi = vol / oi if oi > 0 else 0
    if vol_oi > 0.5:
        score += 20
    elif vol_oi > 0.2:
        score += 10
    premium = row.get("premium", 999)
    if premium < 2.0:
        score += 20
    elif premium < 5.0:
        score += 10
    return min(score, 100)


def main():
    parser = argparse.ArgumentParser(description="Option Flow Screener")
    parser.add_argument("--market", default="US", help="Option market category")
    args = parser.parse_args()

    ctx = create_quote_context()

    try:
        req = build_screen_request()
        ret, data = ctx.get_option_screen(req)
        if ret != 0:
            logger.error("get_option_screen failed: %s", data)
            return

        last_page, all_count, df = data
        logger.info("Option screen: total=%d, last_page=%s", all_count, last_page)

        if df is None or df.empty:
            print("  No options matched the screen criteria.")
            return

        drill_codes = []
        rows = []
        for _, row in df.head(20).iterrows():
            code = str(row.get("code", "?"))
            parts = code.split(".")
            ticker = "?"
            if len(parts) > 1:
                code_body = parts[1]
                alpha = ""
                for ch in code_body:
                    if ch.isalpha():
                        alpha += ch
                    else:
                        break
                if len(alpha) >= 1:
                    ticker = alpha
            underlying = ticker

            option_type = "CALL" if row.get("option_type", 0) == 1 else "PUT"
            strike = row.get("strike_price", 0)
            expiry_days = int(row.get("left_day", 0))
            def safe_float(v, default=0.0):
                try:
                    return float(v)
                except (ValueError, TypeError):
                    return default
            iv = safe_float(row.get("implied_volatility", 0))
            hv = safe_float(row.get("history_volatility", 0))
            iv_hv = safe_float(row.get("iv_hv_ratio", 0))
            delta = safe_float(row.get("delta", 0))
            gamma = safe_float(row.get("gamma", 0))
            premium = safe_float(row.get("premium", 0))
            itm_prob = safe_float(row.get("itm_probability", 0))
            volume = safe_float(row.get("volume", 0))
            oi = safe_float(row.get("open_interest", 1))
            vol_oi = volume / oi if oi > 0 else 0

            flow_score = compute_flow_score({
                "iv_hv_ratio": iv_hv, "itm_probability": itm_prob,
                "volume": volume, "open_interest": oi, "premium": premium,
            })

            rows.append({
                "code": code, "underlying": underlying, "type": option_type,
                "strike": strike, "expiry_days": expiry_days,
                "iv": iv, "hv": hv, "iv_hv": iv_hv,
                "delta": delta, "gamma": gamma, "premium": premium,
                "itm_prob": itm_prob, "vol_oi": vol_oi, "score": flow_score,
            })
            if len(drill_codes) < 5:
                drill_codes.append(code)

        print(f"\n  === OPTION FLOW SCREENER (top 20 of {all_count}) ===\n")
        print(f"  {'#':<4} {'Underlying':<14} {'Strike':<8} {'Type':<6} {'Expiry(d)':<10} {'IV':<8} {'IV/HV':<8} {'ExProb':<8} {'Vol/OI':<8} {'Score':<6}")
        print(f"  {'-'*4} {'-'*14} {'-'*8} {'-'*6} {'-'*10} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*6}")
        for i, r in enumerate(rows[:20], 1):
            print(f"  {i:<4} {r['underlying']:<14} {r['strike']:<8.0f} {r['type']:<6} {r['expiry_days']:<10} {r['iv']:<7.1f}% {r['iv_hv']:<7.2f} {r['itm_prob']:<7.1f}% {r['vol_oi']:<7.2f} {r['score']:<6}")

        print(f"\n  DRILLDOWN — Top {len(drill_codes)} options:\n")
        for opt_code in drill_codes:
            print(f"  --- {opt_code} ---")

            ret_v, vol_df = ctx.get_option_volatility(opt_code)
            if ret_v == 0 and vol_df is not None and not vol_df.empty:
                latest = vol_df.iloc[-1]
                iv_v = float(latest.get("implied_volatility", 0)) * 100
                hv_v = float(latest.get("history_volatility", 0)) * 100
                vp = float(latest.get("volatility_premium", 0)) * 100
                print(f"  IV={iv_v:.1f}%  HV={hv_v:.1f}%  VolPremium={vp:.1f}%")
            else:
                print(f"  Volatility data: N/A")

            ret_e, ex_df = ctx.get_option_exercise_probability(opt_code)
            if ret_e == 0 and ex_df is not None and not ex_df.empty:
                latest = ex_df.iloc[-1]
                sp = float(latest.get("security_price", 0))
                sprob = float(latest.get("strike_probability", 0)) * 100
                print(f"  Underlying Price: {sp:.2f}  ExProb: {sprob:.1f}%")
            else:
                print(f"  Exercise probability: N/A")
            print()

    finally:
        ctx.close()


if __name__ == "__main__":
    main()
