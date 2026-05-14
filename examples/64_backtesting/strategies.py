"""Built-in backtest strategies."""

from abc import ABC, abstractmethod


class Signal:
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class Strategy(ABC):
    @abstractmethod
    def next(self, row: dict, state: dict) -> str:
        ...

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return self.name


class SmaCross(Strategy):
    def __init__(self, short: int = 50, long: int = 200):
        self.short = short
        self.long = long

    @property
    def description(self) -> str:
        return f"SMA Cross ({self.short}/{self.long})"

    def next(self, row: dict, state: dict) -> str:
        closes = state.get("closes", [])
        if len(closes) < self.long + 1:
            return Signal.HOLD
        sma_short = sum(closes[-self.short:]) / self.short
        sma_long = sum(closes[-self.long:]) / self.long
        prev_short = sum(closes[-self.short - 1:-1]) / self.short
        prev_long = sum(closes[-self.long - 1:-1]) / self.long
        if prev_short <= prev_long and sma_short > sma_long:
            return Signal.BUY
        if prev_short >= prev_long and sma_short < sma_long:
            return Signal.SELL
        return Signal.HOLD


class RsiStrategy(Strategy):
    def __init__(self, period: int = 14, oversold: int = 30, overbought: int = 70):
        self.period = period
        self.oversold = oversold
        self.overbought = overbought

    @property
    def description(self) -> str:
        return f"RSI ({self.period}, ovs={self.oversold}, ovb={self.overbought})"

    def next(self, row: dict, state: dict) -> str:
        closes = state.get("closes", [])
        if len(closes) < self.period + 1:
            return Signal.HOLD
        gains, losses = 0.0, 0.0
        for i in range(1, self.period + 1):
            delta = closes[-i] - closes[-i - 1]
            if delta > 0:
                gains += delta
            else:
                losses -= delta
        avg_gain = gains / self.period
        avg_loss = losses / self.period
        if avg_loss == 0:
            rsi = 100.0
        else:
            rs = avg_gain / avg_loss
            rsi = 100.0 - (100.0 / (1.0 + rs))
        prev_position = state.get("position", 0)
        if rsi < self.oversold and prev_position == 0:
            return Signal.BUY
        if rsi > self.overbought and prev_position > 0:
            return Signal.SELL
        return Signal.HOLD


class MacdStrategy(Strategy):
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    @property
    def description(self) -> str:
        return f"MACD ({self.fast}/{self.slow}/{self.signal})"

    @staticmethod
    def _ema(data: list[float], n: int) -> list[float]:
        k = 2.0 / (n + 1)
        ema_val = data[0]
        result = [ema_val]
        for v in data[1:]:
            ema_val = v * k + ema_val * (1 - k)
            result.append(ema_val)
        return result

    def next(self, row: dict, state: dict) -> str:
        closes = state.get("closes", [])
        if len(closes) < self.slow + self.signal:
            return Signal.HOLD
        ema_fast = self._ema(closes, self.fast)
        ema_slow = self._ema(closes, self.slow)
        macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
        signal_line = self._ema(macd_line, self.signal)
        macd_hist = macd_line[-1] - signal_line[-1]
        prev_hist = macd_line[-2] - signal_line[-2]
        prev_position = state.get("position", 0)
        if prev_hist <= 0 and macd_hist > 0 and prev_position == 0:
            return Signal.BUY
        if prev_hist >= 0 and macd_hist < 0 and prev_position > 0:
            return Signal.SELL
        return Signal.HOLD
