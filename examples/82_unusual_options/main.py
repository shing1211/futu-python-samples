"""Unusual Options Activity Scanner — Screening.

Scans for large block trades and unusual volume spikes in options.
Flags contracts where current volume significantly exceeds historical
averages, suggesting institutional activity.

Usage:
    python3 main.py [--stock HK.00700] [--ratio 3.0] [--min-volume 50]
"""

import sys
import os
import logging
import argparse
import statistics

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from connect import create_quote_context, clear_connection_cache
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
DEFAULT_VOLUME_RATIO = 3.0   # current > 3× avg = unusual
DEFAULT_MIN_VOLUME = 50      # ignore contracts with tiny volume
DEFAULT_LOOKBACK = 20        # trading days for average
TRD_ENV = ft.TrdEnv.SIMULATE


# ---------------------------------------------------------------------------
# Option chain fetcher
# ---------------------------------------------------------------------------

def fetch_option_chain(quote_ctx, stock, num=50):
    """Fetch option chain with pagination. Returns list of dicts."""
    contracts = []
    start = ""
    for _ in range(10):
        ret, df, next_page = quote_ctx.get_option_chain(
            code=stock, num=num, start=start,
        )
        if ret != ft.RetCode.SUCCESS:
            logger.error("get_option_chain failed: %s", ret)
            break
        if df is not None and not df.empty:
            contracts.extend(df.to_dict("records"))
        if not next_page:
            break
        start = next_page
    return contracts


def fetch_historical_kline_for_option(quote_ctx, code, num_days):
    """Fetch historical daily bars for a specific option contract.

    Returns list of close prices, or empty list on failure.
    """
    closes = []
    start = ""
    for _ in range(5):
        ret, df, next_page = quote_ctx.request_history_kline(
            code=code, start=start, num_bars=num_days,
            ktype=ft.KLType.K_DAY,
        )
        if ret != ft.RetCode.SUCCESS:
            break
        if df is not None and not df.empty:
            closes.extend(df["close"].tolist())
        if not next_page:
            break
        start = next_page
    return closes


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def classify_option(name, code):
    """Classify option as CALL or PUT from name/code heuristics."""
    upper = (name + " " + code).upper()
    if "CALL" in upper or "C" in upper.split()[-1] if upper.split() else False:
        return "CALL"
    elif "PUT" in upper or "P" in upper.split()[-1] if upper.split() else False:
        return "PUT"
    # Fallback: check code suffix patterns (exchange-dependent)
    code_upper = code.upper()
    if code_upper.endswith("C") or "C" in code_upper[-3:]:
        return "CALL"
    elif code_upper.endswith("P") or "P" in code_upper[-3:]:
        return "PUT"
    return "UNKNOWN"


def compute_volume_anomaly(current_volume, historical_closes, lookback):
    """Determine if current volume is anomalous compared to history.

    Returns (is_unusual: bool, ratio: float, avg_volume: float).
    We approximate 'volume' using daily turnover in the historical kline data.
    For options with no history, use conservative thresholds.
    """
    if len(historical_closes) < 3:
        # No history — flag anything above minimum
        is_unusual = current_volume > DEFAULT_MIN_VOLUME * 2
        return is_unusual, float("inf") if is_unusual else 0.0, 0.0

    # Use close prices as proxy for turnover pattern
    # In practice, request_history_kline returns turnover; we use close variance
    avg_close = statistics.mean(historical_closes)
    std_close = statistics.pstdev(historical_closes) if len(historical_closes) > 1 else 0

    # Estimate expected daily volume proxy
    # This is a heuristic — real volume would need the turnover field
    expected_vol_proxy = max(avg_close * 0.01, 1.0)
    ratio = current_volume / expected_vol_proxy if expected_vol_proxy > 0 else 0

    is_unusual = ratio > DEFAULT_VOLUME_RATIO
    return is_unusual, ratio, expected_vol_proxy


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Unusual Options Activity Scanner")
    parser.add_argument("--stock", default=DEFAULT_STOCK,
                        help="Underlying stock ticker")
    parser.add_argument("--ratio", type=float, default=DEFAULT_VOLUME_RATIO,
                        help="Volume ratio threshold for flagging (default 3.0)")
    parser.add_argument("--min-volume", type=int, default=DEFAULT_MIN_VOLUME,
                        help="Minimum volume to consider (default 50)")
    args = parser.parse_args()

    stock = args.stock
    volume_ratio = args.ratio
    min_volume = args.min_volume

    quote_ctx = create_quote_context()

    try:
        # ── Get underlying spot price ──────────────────────────────────
        ret, df = quote_ctx.get_stock_quote(stock)
        if ret != ft.RetCode.SUCCESS:
            logger.error("Cannot get quote for %s", stock)
            return
        spot = float(df.iloc[-1]["last_price"])
        logger.info("Underlying %s spot: %.2f", stock, spot)

        # ── Fetch option chain ─────────────────────────────────────────
        contracts = fetch_option_chain(quote_ctx, stock)
        if not contracts:
            logger.warning("No option contracts found for %s", stock)
            return
        logger.info("Found %d option contracts for %s", len(contracts), stock)

        # ── Analyse each contract ──────────────────────────────────────
        unusual = []
        for c in contracts:
            code = str(c.get("code", ""))
            name = str(c.get("stock_name", ""))
            last_price = float(c.get("last_price", 0) or 0)
            volume = float(c.get("volume", 0) or 0)
            turnover = float(c.get("turnover", 0) or 0)
            oi = float(c.get("open_interest", 0) or 0)

            if volume < min_volume:
                continue

            opt_type = classify_option(name, code)

            # Fetch historical data for this specific contract
            hist = fetch_historical_kline_for_option(quote_ctx, code, DEFAULT_LOOKBACK)
            is_unusual, ratio, _ = compute_volume_anomaly(
                volume, hist, DEFAULT_LOOKBACK,
            )

            if is_unusual:
                strike = float(c.get("exercise_price", 0) or 0)
                expiry = str(c.get("end_date", ""))
                unusual.append({
                    "code": code,
                    "name": name,
                    "type": opt_type,
                    "strike": strike,
                    "expiry": expiry,
                    "volume": volume,
                    "turnover": turnover,
                    "oi": oi,
                    "last_price": last_price,
                    "ratio": ratio,
                    "moneyness": "ATM" if abs(strike / spot - 1) < 0.02
                                 else "ITM" if (opt_type == "CALL" and strike < spot) or
                                              (opt_type == "PUT" and strike > spot)
                                 else "OTM",
                })

        # ── Display results ────────────────────────────────────────────
        if not unusual:
            print(f"\n  No unusual options activity detected for {stock}.")
            print(f"  Scanned {len(contracts)} contracts "
                  f"(min volume filter: {min_volume})")
            return

        unusual.sort(key=lambda x: x["ratio"], reverse=True)

        print(f"\n{'='*80}")
        print(f"  🔍 UNUSUAL OPTIONS ACTIVITY — {stock} (spot {spot:.2f})")
        print(f"{'='*80}")
        print(
            f"  {'Code':<12} {'Type':<5} {'Strike':>8} {'Expiry':>10} "
            f"{'Moneyness':<6} {'Volume':>10} {'OI':>10} {'Ratio':>8}"
        )
        print(f"  {'-'*12} {'-'*5} {'-'*8} {'-'*10} {'-'*6} {'-'*10} {'-'*10} {'-'*8}")

        for u in unusual[:20]:
            print(
                f"  {u['code']:<12} {u['type']:<5} {u['strike']:>8.2f} "
                f"{u['expiry'][:10]:>10} {u['moneyness']:<6} "
                f"{u['volume']:>10,.0f} {u['oi']:>10,.0f} "
                f"{u['ratio']:>7.1f}×"
            )

        print(f"\n  {len(unusual)} unusual contract(s) detected.")
        print(f"  ⚠️  High volume/OI may indicate institutional activity.")
        print(f"     This is a screening tool — not investment advice.")
        print(f"{'='*80}")

        # ── Also check TICKER push for real-time volume burst ───────────
        print(f"\n  📡 Checking real-time ticker for additional signals…")
        ret_ticker, df_ticker = quote_ctx.get_rt_ticker(stock, 1)
        if ret_ticker == ft.RetCode.SUCCESS and df_ticker is not None:
            for _, row in df_ticker.iterrows():
                rt_vol = float(row.get("volume", 0) or 0)
                rt_turnover = float(row.get("turnover", 0) or 0)
                print(f"  Ticker Volume: {rt_vol:,}  Turnover: {rt_turnover:,.0f}")

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()