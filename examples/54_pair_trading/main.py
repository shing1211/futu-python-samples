#!/usr/bin/env python3
"""
54 — Pair Trading Signal

Watches two correlated stocks via live CurKlineHandler and computes
the rolling spread z-score in real time.

When z-score crosses ±2, the pair is statistically "far apart" —
a mean-reversion signal fires.  When it crosses back to zero,
the trade is closed.

Pair: HK.00700 (Tencent) and HK.09988 (Alibaba/Ant).
Both are large-cap Chinese tech; they share sentiment drivers
and often drift together.  When they diverge, mean reversion follows.

What you'll see:
  Each tick prints the current z-score and a one-character signal:
    ● 0.0–1.0  : no signal
    ◐ 1.0–2.0  : watch — pair starting to diverge
    ◑ -1.0–-2.0: watch — pair starting to diverge
    ⬤ +2.0     : STRONG BUY signal — long the underperformer
    ⬖ -2.0     : STRONG SELL signal — short the overperformer

SDK: OpenQuoteContext + CurKlineHandlerBase + K_60M + rolling OLS
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import time
import math
import futu as ft
from connect import create_quote_context


# ── Rolling statistics ──────────────────────────────────────────────────────

class RollingOLS:
    """Minimal online ordinary least-squares: y = β·x + α, no numpy needed."""

    def __init__(self, window: int = 60):
        self.window = window
        self.x_vals: list[float] = []
        self.y_vals: list[float] = []
        self.ready = False

    def update(self, x: float, y: float):
        self.x_vals.append(x)
        self.y_vals.append(y)
        if len(self.x_vals) > self.window:
            self.x_vals.pop(0)
            self.y_vals.pop(0)
        self.ready = len(self.x_vals) == self.window

    @property
    def beta(self) -> float:
        if not self.ready:
            return 0.0
        n = self.window
        xm = sum(self.x_vals) / n
        ym = sum(self.y_vals) / n
        num = sum((xi - xm) * (yi - ym) for xi, yi in zip(self.x_vals, self.y_vals))
        den = sum((xi - xm) ** 2 for xi in self.x_vals)
        return num / den if den != 0 else 0.0

    @property
    def alpha(self) -> float:
        if not self.ready:
            return 0.0
        n = self.window
        return (sum(self.y_vals) - self.beta * sum(self.x_vals)) / n

    def predict(self, x: float) -> float:
        return self.beta * x + self.alpha

    def residual_zscore(self, x: float, y: float) -> float:
        if not self.ready:
            return 0.0
        predicted = self.predict(x)
        residuals = [yi - (self.beta * xi + self.alpha)
                     for xi, yi in zip(self.x_vals, self.y_vals)]
        mean_r = sum(residuals) / len(residuals)
        std_r = math.sqrt(sum((r - mean_r) ** 2 for r in residuals) / len(residuals))
        if std_r < 1e-10:
            return 0.0
        return (y - predicted) / std_r


# ── CurKline handler ────────────────────────────────────────────────────────

class PairKlineHandler(ft.CurKlineHandlerBase):
    """Accumulates 60M candles for two stocks and emits z-score signals."""

    def __init__(self, stock_a: str, stock_b: str):
        super().__init__()
        self.stock_a = stock_a
        self.stock_b = stock_b
        # Each stock's most-recent close price
        self.price_a: float | None = None
        self.price_b: float | None = None
        # Rolling regression window (in candles)
        self.ols = RollingOLS(window=60)
        self.signal = "●"
        self.tick_count = 0
        # Last printed z-score so we only print on change
        self._last_z: float = 999.0

    def on_recv_rsp(self, rsp_pb) -> tuple:
        ret_code, content = super().on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            return ft.RET_ERROR, content

        for _, row in content.iterrows():
            code = row.get("code", "")
            if code not in (self.stock_a, self.stock_b):
                continue

            close = float(row.get("close", 0))
            if code == self.stock_a:
                self.price_a = close
            else:
                self.price_b = close

            if self.price_a is None or self.price_b is None:
                continue

            self.ols.update(self.price_b, self.price_a)
            self.tick_count += 1

            z = self.ols.residual_zscore(self.price_b, self.price_a)
            self.signal = self._z_to_signal(z)

            # Only print when z-score changes meaningfully
            if abs(z - self._last_z) >= 0.05:
                self._last_z = z
                self._print(z)

        return ft.RET_OK, content

    @staticmethod
    def _z_to_signal(z: float) -> str:
        if z >= 2.0:
            return "⬤  LONG  A"      # A has diverged below B — long A
        elif z <= -2.0:
            return "⬖  SHORT A"      # A has diverged above B — short A
        elif z >= 1.0:
            return "◐  watch"
        elif z <= -1.0:
            return "◑  watch"
        return "●  neutral"

    def _print(self, z: float):
        pct = (z / 2.0) * 100
        print(f"  z={z:+.2f} [{self.signal}]  "
              f"{self.stock_a}={self.price_a}  "
              f"{self.stock_b}={self.price_b}  "
              f"(β={self.ols.beta:+.3f}  n={self.tick_count})")


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    stock_a = "HK.00700"
    stock_b = "HK.09988"
    ktype   = ft.SubType.K_60M

    ctx = create_quote_context()
    try:
        ctx.set_handler(PairKlineHandler(stock_a, stock_b))
    
        print(f"Pair: {stock_a} vs {stock_b}")
        print(f"Streaming {ktype} candles and computing rolling z-score.\n")
        print(f"  β = hedge ratio   z = (A - β·B - α) / σ_resid\n")
    
        for stock in [stock_a, stock_b]:
            ret, _ = ctx.subscribe(stock, ktype)
            if ret != 0:
                print(f"  Subscribe {stock} failed: {ret}")
                return
    
        print("Waiting 60s for first z-score (needs 60 candles for OLS window)...\n")
        time.sleep(60)
    
    finally:
        ctx.close()
    print("\nDone.")


if __name__ == "__main__":
    main()
