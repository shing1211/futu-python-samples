"""Option Analytics — get_option_volatility, get_option_exercise_probability, get_option_screen.

Demonstrates three option-related SDK APIs:
  - get_option_volatility(code)
  - get_option_exercise_probability(code)
  - get_option_screen(code, filter_list)

Usage:
    python3 main.py [--code US.AAPL260616C200000] [--underlying US.AAPL]
"""
import sys
import logging
import argparse

from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from connect import create_quote_context
import futu as ft

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Option Analytics")
    parser.add_argument("--code", default="US.AAPL260616C200000", help="Option contract code")
    parser.add_argument("--underlying", default="US.AAPL", help="Underlying stock code")
    args = parser.parse_args()

    quote_ctx = create_quote_context()
    try:
        logger.info("=== Option Volatility for %s ===", args.code)
        try:
            ret, df = quote_ctx.get_option_volatility(args.code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                cols = [c for c in ["timestamp_str", "implied_volatility", "history_volatility", "volatility_premium"] if c in df.columns]
                if cols:
                    print(df[cols].to_string(index=False))
                else:
                    print(df.to_string(index=False))
            else:
                logger.warning("No option volatility: %s", df)
        except Exception as e:
            logger.warning("Option volatility failed: %s", e)

        logger.info("=== Option Exercise Probability for %s ===", args.code)
        try:
            ret, df = quote_ctx.get_option_exercise_probability(args.code)
            if ret == ft.RetCode.SUCCESS and df is not None and not df.empty:
                print(df.to_string(index=False))
            else:
                logger.warning("No exercise probability: %s", df)
        except Exception as e:
            logger.warning("Exercise probability failed: %s", e)

        logger.info("=== Option Screen for %s ===", args.underlying)
        try:
            ret, screen_data = quote_ctx.get_option_screen(args.underlying, [])
            if ret == ft.RetCode.SUCCESS:
                print(screen_data)
            else:
                logger.warning("Option screen failed: %s", screen_data)
        except Exception as e:
            logger.warning("Option screen error: %s", e)

    finally:
        quote_ctx.close()
        logger.info("Done.")


if __name__ == "__main__":
    main()
