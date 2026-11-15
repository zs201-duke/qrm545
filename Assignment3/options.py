"""Own GBSM formula, Greeks, implied-volatility inversion, and CRR trees.

No external option-pricing package is used. Rates and vols are decimals; prices
refer to one share. Theta is dV/d(calendar time), expressed per model year.
"""
import numpy as np
from scipy.special import ndtr
from scipy.optimize import brentq


def gbsm(kind, spot, strike, maturity, rate, carry, vol):
    """Generalized BSM, including the deterministic and expiry limits."""
    s = np.asarray(spot, dtype=float)
    z = 1 if kind.lower() == "call" else -1
    if maturity <= 0:
        return np.maximum(z * (s - strike), 0.)
    if vol <= 0:
        return np.exp(-rate * maturity) * np.maximum(
            z * (s * np.exp(carry * maturity) - strike), 0.)
    # A zero stock remains zero; tiny prevents log(0) without changing its price.
    d1 = (np.log(np.maximum(s, 1e-300) / strike)
          + (carry + vol**2 / 2) * maturity) / (vol * np.sqrt(maturity))
    d2 = d1 - vol * np.sqrt(maturity)
    return z * (s * np.exp((carry-rate)*maturity) * ndtr(z*d1)
                - strike * np.exp(-rate*maturity) * ndtr(z*d2))


def greeks(kind, spot, strike, maturity, rate, carry, vol):
    """Analytic delta, gamma, vega and theta; vega is per 1.0 volatility."""
    z = 1 if kind.lower() == "call" else -1
    d1 = (np.log(spot/strike)+(carry+vol**2/2)*maturity)/(vol*np.sqrt(maturity))
    d2 = d1-vol*np.sqrt(maturity)
    density = np.exp(-d1*d1/2)/np.sqrt(2*np.pi)
    growth = np.exp((carry-rate)*maturity)
    return {
        "delta": float(z*growth*ndtr(z*d1)),
        "gamma": float(growth*density/(spot*vol*np.sqrt(maturity))),
        "vega": float(spot*growth*density*np.sqrt(maturity)),
        "theta": float(-spot*growth*density*vol/(2*np.sqrt(maturity))
                       -z*(carry-rate)*spot*growth*ndtr(z*d1)
                       -z*rate*strike*np.exp(-rate*maturity)*ndtr(z*d2)),
    }


def implied_vol(kind, price, spot, strike, maturity, rate, carry):
    """Return (IV, diagnostic); do not silently force invalid quotes to a root."""
    lower = float(gbsm(kind, spot, strike, maturity, rate, carry, 0.))
    upper = (spot*np.exp((carry-rate)*maturity) if kind == "Call"
             else strike*np.exp(-rate*maturity))
    if price < lower-1e-10:
        return np.nan, "below discounted intrinsic bound"
    if price >= upper:
        return np.nan, "at/above finite-volatility upper bound"
    if abs(price-lower) < 1e-10:
        return 0., "zero-volatility boundary"
    high = .5
    while gbsm(kind, spot, strike, maturity, rate, carry, high) < price:
        high *= 2
    root = brentq(lambda v: gbsm(kind, spot, strike, maturity, rate, carry, v)-price,
                  1e-10, high, xtol=1e-13)
    return float(root), "ok"


def _rollback(roots, steps, terminal, strike, u, prob, discount, american):
    """Roll back independent recombining subtrees, preserving each root.

    terminal has shape (number_of_roots, steps+1, 4). The four channels are
    European call, American call, European put, American put. At dividend
    dates subtrees stay separate; there is NO interpolation or recombination
    across distinct dividend histories.
    """
    values = terminal
    for j in range(steps-1, -1, -1):
        values = discount*((1-prob)*values[:, :-1, :]+prob*values[:, 1:, :])
        if american:
            spots = roots[:, None]*u**(2*np.arange(j+1)-j)
            values[:, :, 1] = np.maximum(values[:, :, 1], np.maximum(spots-strike, 0))
            values[:, :, 3] = np.maximum(values[:, :, 3], np.maximum(strike-spots, 0))
    return values[:, 0, :]


def crr_all(spot, strike, maturity, rate, vol, steps, dividends=()):
    """All four prices on the same exact, non-recombining cash-dividend tree.

    A dividend is (time_in_years, cash_amount). Dates MUST land on steps.
    Before each cash jump, compare the American continuation at S-D with
    intrinsic at pre-dividend S. Between cash jumps the CRR subtree recombines.
    The array batching is just a faster implementation of Week 7 recursion.
    The stock is floored at zero for remote states where cash exceeds price;
    the floor is economically irrelevant for this assignment (checked in tests).
    """
    dt = maturity/steps
    u = np.exp(vol*np.sqrt(dt))
    prob = (np.exp(rate*dt)-1/u)/(u-1/u)
    if not 0 < prob < 1:
        raise ValueError("CRR risk-neutral probability outside (0,1)")
    events = []
    for t, amount in sorted(dividends):
        step = int(round(t/dt))
        if not np.isclose(step*dt, t, atol=1e-12, rtol=0):
            raise ValueError("Dividend dates must land exactly on tree steps")
        if not 0 < step < steps:
            raise ValueError("Dividends must be strictly inside the option life")
        events.append((step, amount))
    discount = np.exp(-rate*dt)

    def segment(roots, start, event_index):
        end = events[event_index][0] if event_index < len(events) else steps
        n = end-start
        pre = roots[:, None]*u**(2*np.arange(n+1)-n)
        if event_index == len(events):
            call = np.maximum(pre-strike, 0.)
            put = np.maximum(strike-pre, 0.)
            terminal = np.stack([call, call, put, put], axis=-1)
        else:
            post = np.maximum(pre-events[event_index][1], 0.)
            terminal = segment(post.ravel(), end, event_index+1).reshape(*pre.shape, 4)
            terminal[:, :, 1] = np.maximum(terminal[:, :, 1], np.maximum(pre-strike, 0.))
            terminal[:, :, 3] = np.maximum(terminal[:, :, 3], np.maximum(strike-pre, 0.))
        return _rollback(roots, n, terminal, strike, u, prob, discount, True)

    return segment(np.atleast_1d(spot).astype(float), 0, 0).squeeze(axis=0)


def crr_american(kind, spot, strike, maturity, rate, vol, steps):
    """Convenience wrapper for a no-dividend American subtree."""
    return crr_all(spot, strike, maturity, rate, vol, steps)[1 if kind == "Call" else 3]
