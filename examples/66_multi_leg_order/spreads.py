"""Multi-leg options strategy definitions."""


class VerticalSpread:
    def __init__(self, underlying: str, expiry: str,
                 strike_long: float, strike_short: float,
                 bid_long: float, ask_long: float,
                 bid_short: float, ask_short: float):
        self.underlying = underlying
        self.expiry = expiry
        self.strike_long = strike_long
        self.strike_short = strike_short
        self.bid_long = bid_long
        self.ask_long = ask_long
        self.bid_short = bid_short
        self.ask_short = ask_short

    @property
    def leg1_code(self) -> str:
        return f"{self.underlying}{self.expiry}C{self.strike_long:.0f}"

    @property
    def leg2_code(self) -> str:
        return f"{self.underlying}{self.expiry}C{self.strike_short:.0f}"

    @property
    def net_debit(self) -> float:
        return self.ask_long - self.bid_short

    @property
    def max_profit(self) -> float:
        width = self.strike_short - self.strike_long
        return width - self.net_debit

    @property
    def max_loss(self) -> float:
        return self.net_debit

    def summary(self) -> str:
        return (f"  Vertical Call Spread: {self.underlying} {self.expiry}\n"
                f"    Leg 1: BUY  {self.strike_long:.0f}C @ {self.ask_long:.2f}\n"
                f"    Leg 2: SELL {self.strike_short:.0f}C @ {self.bid_short:.2f}\n"
                f"    Net debit: {self.net_debit:.2f}\n"
                f"    Max profit: {self.max_profit:.2f}\n"
                f"    Max loss:   {self.max_loss:.2f}")


class IronCondor:
    def __init__(self, underlying: str, expiry: str,
                 put_long_strike: float, put_short_strike: float,
                 call_short_strike: float, call_long_strike: float,
                 bid_put_long: float, ask_put_long: float,
                 bid_put_short: float, ask_put_short: float,
                 bid_call_short: float, ask_call_short: float,
                 bid_call_long: float, ask_call_long: float):
        self.put_long_strike = put_long_strike
        self.put_short_strike = put_short_strike
        self.call_short_strike = call_short_strike
        self.call_long_strike = call_long_strike
        self.net_credit = (bid_put_short + bid_call_short) - (ask_put_long + ask_call_long)

    @property
    def max_profit(self) -> float:
        return self.net_credit

    @property
    def max_loss(self) -> float:
        width = self.call_short_strike - self.put_short_strike
        return width - self.net_credit

    def summary(self) -> str:
        return (f"  Iron Condor\n"
                f"    Net credit: {self.net_credit:.2f}\n"
                f"    Max profit: {self.max_profit:.2f}\n"
                f"    Max loss:   {self.max_loss:.2f}")
