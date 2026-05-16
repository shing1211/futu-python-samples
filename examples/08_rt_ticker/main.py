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

"""分时成交明细 (get_rt_ticker / get_rt_data)

Demonstrates:
  - get_rt_ticker: tick-by-tick trade records for a stock
  - get_rt_data: intraday minute-level OHLCV data
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
    logger.info("=== RT Ticker & RT Data Demo ===")

    ctx = create_quote_context()

    try:
        code = "HK.00700"

        # ── get_rt_ticker: tick-by-tick trades ─────────────────────────
        logger.info("\n=== get_rt_ticker: %s (last 50 ticks) ===", code)
        ret, data = ctx.get_rt_ticker(code, num=50)
        if ret != 0:
            logger.error("get_rt_ticker failed: %s", data)
        else:
            logger.info("Retrieved %d tick records | Columns: %s", len(data), list(data.columns))
            for col in data.columns:
                logger.info("  %-20s = %s", col, data[col].tolist())
            logger.info("\nLast 5 ticks:\n%s", data.tail(5).to_string())

        # ── get_rt_data: minute-level intraday bars ───────────────────────
        logger.info("\n=== get_rt_data: %s (full intraday) ===", code)
        ret, data = ctx.get_rt_data(code)
        if ret != 0:
            logger.error("get_rt_data failed: %s", data)
        else:
            logger.info("Retrieved %d minute bars | Columns: %s", len(data), list(data.columns))
            for col in data.columns:
                logger.info("  %-20s = %s", col, data[col].tolist())
            if not data.empty:
                cols = data.columns
                logger.info("\nFirst bar: time=%s O=%.2f H=%.2f L=%.2f C=%.2f vol=%d",
                            data['time'].iloc[0] if 'time' in cols else '?',
                            data['open'].iloc[0] if 'open' in cols else 0,
                            data['high'].iloc[0] if 'high' in cols else 0,
                            data['low'].iloc[0] if 'low' in cols else 0,
                            data['close'].iloc[0] if 'close' in cols else 0,
                            data['volume'].iloc[0] if 'volume' in cols else 0)
                logger.info("Last bar:  time=%s O=%.2f H=%.2f L=%.2f C=%.2f vol=%d",
                            data['time'].iloc[-1] if 'time' in cols else '?',
                            data['open'].iloc[-1] if 'open' in cols else 0,
                            data['high'].iloc[-1] if 'high' in cols else 0,
                            data['low'].iloc[-1] if 'low' in cols else 0,
                            data['close'].iloc[-1] if 'close' in cols else 0,
                            data['volume'].iloc[-1] if 'volume' in cols else 0)

    finally:
        ctx.close()
        logger.info("Done.")