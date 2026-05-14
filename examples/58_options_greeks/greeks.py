"""Black-Scholes Greeks computation — pure Python, no numpy/scipy."""

import math

SQRT2 = math.sqrt(2.0)


def _cdf(x: float) -> float:
    """Standard normal CDF using Abramowitz & Stegun approximation."""
    if x < -8:
        return 0.0
    if x > 8:
        return 1.0
    a1, a2, a3, a4, a5 = 0.254829592, -0.284496736, 1.421413741, -1.453152027, 1.061405429
    p = 0.3275911
    sign = 1.0 if x >= 0 else -1.0
    x = abs(x)
    t = 1.0 / (1.0 + p * x)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x * x)
    return 0.5 * (1.0 + sign * y)


def _pdf(x: float) -> float:
    """Standard normal PDF."""
    return math.exp(-x * x / 2.0) / math.sqrt(2.0 * math.pi)


def compute_greeks(S: float, K: float, T: float, r: float, sigma: float,
                   option_type: str = "CALL"):
    """
    Compute all five Greeks using Black-Scholes.

    Args:
        S: Underlying price
        K: Strike price
        T: Time to expiry in years
        r: Risk-free rate (e.g. 0.045 for 4.5%)
        sigma: Implied volatility (e.g. 0.25 for 25%)
        option_type: "CALL" or "PUT"

    Returns:
        dict with keys: delta, gamma, theta, vega, rho, price
        All values are None if computation fails (invalid params).
    """
    if S <= 0 or K <= 0 or T <= 0 or sigma <= 0:
        return {"delta": None, "gamma": None, "theta": None,
                "vega": None, "rho": None, "price": None}

    sqrt_T = math.sqrt(T)
    sigma_sqrt_T = sigma * sqrt_T
    if sigma_sqrt_T == 0:
        return {"delta": None, "gamma": None, "theta": None,
                "vega": None, "rho": None, "price": None}

    d1 = (math.log(S / K) + (r + sigma * sigma / 2.0) * T) / sigma_sqrt_T
    d2 = d1 - sigma_sqrt_T

    if option_type == "CALL":
        delta = _cdf(d1)
        gamma = _pdf(d1) / (S * sigma_sqrt_T)
        theta = (-S * _pdf(d1) * sigma / (2.0 * sqrt_T)
                 - r * K * math.exp(-r * T) * _cdf(d2))
        vega = S * _pdf(d1) * sqrt_T / 100.0
        rho = K * T * math.exp(-r * T) * _cdf(d2) / 100.0
        price = S * _cdf(d1) - K * math.exp(-r * T) * _cdf(d2)
    else:
        delta = _cdf(d1) - 1.0
        gamma = _pdf(d1) / (S * sigma_sqrt_T)
        theta = (-S * _pdf(d1) * sigma / (2.0 * sqrt_T)
                 + r * K * math.exp(-r * T) * _cdf(-d2))
        vega = S * _pdf(d1) * sqrt_T / 100.0
        rho = -K * T * math.exp(-r * T) * _cdf(-d2) / 100.0
        price = K * math.exp(-r * T) * _cdf(-d2) - S * _cdf(-d1)

    result = {
        "delta": round(delta, 4) if not math.isnan(delta) else None,
        "gamma": round(gamma, 6) if not math.isnan(gamma) else None,
        "theta": round(theta, 4) if not math.isnan(theta) else None,
        "vega": round(vega, 4) if not math.isnan(vega) else None,
        "rho": round(rho, 4) if not math.isnan(rho) else None,
        "price": round(price, 2) if not math.isnan(price) else None,
    }
    return result
