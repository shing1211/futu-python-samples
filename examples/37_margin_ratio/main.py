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

"""查询账户持仓的保证金率 (get_margin_ratio)

Demonstrates:
  - get_margin_ratio: margin ratio per position
  - Empty code_list = all positions
  - All returned fields logged
"""
import sys
import logging
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
import futu as ft
from connect import create_trade_context, get_demo_trade_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


if __name__ == "__main__":
    logger.info("=== Margin Ratio Demo ===")

    trd_ctx = create_trade_context(filter_trdmarket=ft.TrdMarket.HK)

    try:
        pwd = get_demo_trade_password()
        ret, data = trd_ctx.unlock_trade(pwd)
        if ret != ft.RET_OK:
            logger.error("unlock_trade failed: %s", data)
            raise SystemExit(1)
        logger.info("unlock_trade: OK")

        # All positions
        logger.info("\n=== get_margin_ratio: all positions (empty code_list) ===")
        ret, data = trd_ctx.get_margin_ratio(code_list=[])
        if ret != ft.RET_OK:
            logger.error("get_margin_ratio failed: %s", data)
        else:
            if data.empty:
                logger.info("No positions or margin ratio not applicable")
            else:
                logger.info("Margin ratios (%d rows):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %-25s = %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

        # Specific codes
        codes = ["HK.00700", "HK.HSImain"]
        logger.info("\n=== get_margin_ratio: specific codes=%s ===", codes)
        ret, data = trd_ctx.get_margin_ratio(code_list=codes)
        if ret != ft.RET_OK:
            logger.error("get_margin_ratio (specific) failed: %s", data)
        else:
            if data.empty:
                logger.info("No margin ratio data for %s", codes)
            else:
                logger.info("Margin ratios (%d rows):", len(data))
                logger.info("Columns: %s", list(data.columns))
                for col in data.columns:
                    logger.info("  %-25s = %s", col, data[col].tolist())
                logger.info("\n%s", data.to_string())

    finally:
        trd_ctx.close()
        logger.info("Done.")