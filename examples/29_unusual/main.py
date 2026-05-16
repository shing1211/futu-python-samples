# -*- coding: utf-8 -*-

# Copyright (c) 2026 shing1211
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""异动数据 (get_technical_unusual / get_financial_unusual / get_derivative_unusual)

Demonstrates:
  - get_technical_unusual: stocks with unusual technical indicators (volume spike, etc.)
  - get_financial_unusual: stocks with unusual financial metrics
  - get_derivative_unusual: stocks with unusual derivative metrics
  - All returned fields logged

These are screener functions that identify stocks breaking out or showing anomalies.
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
    logger.info("=== Unusual/Screener Alerts Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        # ── Technical unusual ─────────────────────────────────────────────
        logger.info("\n=== get_technical_unusual: %s ===", code)
        ret, data = ctx.get_technical_unusual(code)
        if ret != 0:
            logger.error("get_technical_unusual failed: %s", data)
        else:
            if data.empty:
                logger.info("No unusual technical alerts for %s", code)
            else:
                logger.info("Technical unusual records (%d):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %-20s = %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # ── Financial unusual ─────────────────────────────────────────────
        logger.info("\n=== get_financial_unusual: %s ===", code)
        ret, data = ctx.get_financial_unusual(code)
        if ret != 0:
            logger.error("get_financial_unusual failed: %s", data)
        else:
            if data.empty:
                logger.info("No unusual financial alerts for %s", code)
            else:
                logger.info("Financial unusual records (%d):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %-20s = %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # ── Derivative unusual ───────────────────────────────────────────
        logger.info("\n=== get_derivative_unusual: %s ===", code)
        ret, data = ctx.get_derivative_unusual(code)
        if ret != 0:
            logger.error("get_derivative_unusual failed: %s", data)
        else:
            if data.empty:
                logger.info("No unusual derivative alerts for %s", code)
            else:
                logger.info("Derivative unusual records (%d):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %-20s = %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

    finally:
        ctx.close()
        logger.info("Done.")