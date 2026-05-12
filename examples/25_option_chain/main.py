# -*- coding: utf-8 -*-
"""期权链 (get_option_chain / get_option_expiration_date)

Demonstrates:
  - get_option_expiration_date: list expiry dates for index options
  - get_option_chain: fetch option contracts for a given expiry
  - IndexOptionType: NORMAL, WEEKLY, MONTHLY
  - OptionType: CALL, PUT, ALL
  - All returned fields logged
"""
import logging
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_quote_context

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Option Chain Demo ===")

    ctx = create_quote_context()

    try:
        code = "US.NDX"  # Nasdaq index options

        # ── Get expiration dates ────────────────────────────────────────
        logger.info("\n=== get_option_expiration_date: %s (NORMAL) ===", code)
        ret, dates = ctx.get_option_expiration_date(code, ft.IndexOptionType.NORMAL)
        if ret != 0:
            logger.error("get_option_expiration_date failed: %s", dates)
        else:
            logger.info("Expiration dates (%d): %s", len(dates), dates[:10] if isinstance(dates, list) else dates)

        if isinstance(dates, list) and len(dates) > 0:
            nearest = dates[0]
            logger.info("Using nearest expiry: %s", nearest)

            # ── Get option chain ─────────────────────────────────────────
            for opt_type_label, opt_type in [
                ("CALL", ft.OptionType.CALL),
                ("PUT", ft.OptionType.PUT),
                ("ALL", ft.OptionType.ALL),
            ]:
                logger.info("\n=== get_option_chain: %s @ %s [%s] ===", code, nearest, opt_type_label)
                ret, data = ctx.get_option_chain(
                    code,
                    index_option_type=ft.IndexOptionType.NORMAL,
                    start=nearest,
                    end=nearest,
                    option_type=opt_type,
                )
                if ret != 0:
                    logger.error("get_option_chain failed: %s", data)
                else:
                    if data.empty:
                        logger.info("No contracts returned for type=%s", opt_type_label)
                    else:
                        logger.info("Contracts: %d | Columns: %s", len(data), list(data.columns))
                        for col in data.columns:
                            logger.info("  %-20s = %s", col, data[col].tolist()[:10])
                        logger.info("\nFirst 3 contracts:\n%s", data.head(3).to_string())

    finally:
        ctx.close()
        logger.info("Done.")