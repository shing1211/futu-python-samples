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

"""Performance metrics for backtest results."""

import math


def compute_metrics(initial_capital: float, final_capital: float,
                    trades: list, equity_curve: list[float]):
    total_return = (final_capital / initial_capital - 1) * 100

    daily_returns = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]
        if prev != 0:
            daily_returns.append((equity_curve[i] - prev) / prev)

    sharpe = 0.0
    if len(daily_returns) > 1:
        mean_r = sum(daily_returns) / len(daily_returns)
        var_r = sum((r - mean_r) ** 2 for r in daily_returns) / len(daily_returns)
        std_r = math.sqrt(var_r)
        if std_r > 0:
            sharpe = (mean_r / std_r) * math.sqrt(252)

    peak = initial_capital
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100
        if dd > max_dd:
            max_dd = dd

    round_trips = len(trades) // 2
    wins = sum(1 for t in trades if t.get("pnl", 0) > 0)
    win_rate = (wins / len(trades) * 100) if trades else 0.0

    return {
        "total_return_pct": round(total_return, 2),
        "sharpe_ratio": round(sharpe, 2),
        "max_drawdown_pct": round(max_dd, 2),
        "win_rate_pct": round(win_rate, 2),
        "num_trades": round_trips,
        "final_capital": round(final_capital, 2),
    }
