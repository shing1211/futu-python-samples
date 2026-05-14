"""Backtest engine — runs a strategy over historical price data."""

import math
from strategies import Strategy, Signal
from metrics import compute_metrics


def backtest(df, strategy: Strategy, initial_capital: float = 1_000_000,
             lot_size: int = 100):
    closes = df["close"].tolist()
    capital = initial_capital
    position = 0
    trades = []
    equity_curve = [initial_capital]

    for i in range(len(df)):
        row = df.iloc[i]
        price = float(row["close"])
        closes_sofar = closes[:i + 1]
        state = {"closes": closes_sofar, "position": position}

        signal = strategy.next(row, state)

        if signal == Signal.BUY and position == 0:
            qty = int(capital / price / lot_size) * lot_size
            if qty < lot_size:
                continue
            cost = qty * price
            capital -= cost
            position = qty
            trades.append({
                "date": str(row.get("time_key", "")),
                "type": "BUY",
                "price": price,
                "qty": qty,
                "cost": cost,
            })

        elif signal == Signal.SELL and position > 0:
            proceeds = position * price
            trade_pnl = proceeds - sum(t["cost"] for t in trades if t["type"] == "BUY")
            capital += proceeds
            trades.append({
                "date": str(row.get("time_key", "")),
                "type": "SELL",
                "price": price,
                "qty": position,
                "pnl": trade_pnl,
            })
            position = 0

        equity_curve.append(capital + position * price)

    if position > 0:
        last_price = float(df.iloc[-1]["close"])
        capital += position * last_price
        trades.append({
            "date": str(df.iloc[-1].get("time_key", "")),
            "type": "CLOSE",
            "price": last_price,
            "qty": position,
            "pnl": capital - initial_capital,
        })
        position = 0

    metrics = compute_metrics(initial_capital, capital, trades, equity_curve)
    return metrics, trades, equity_curve
