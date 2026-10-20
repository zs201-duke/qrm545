"""Univariate sample statistics and P&L risk measures."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import stats


def _finite_vector(values: ArrayLike, name: str) -> NDArray[np.float64]:
    array = np.asarray(values, dtype=float)
    if array.ndim != 1 or array.size == 0:
        raise ValueError(f"{name} must be a non-empty one-dimensional array")
    if not np.all(np.isfinite(array)):
        raise ValueError(f"{name} must contain only finite values")
    return array


def _check_alpha(alpha: float) -> None:
    if not 0.0 < alpha < 1.0:
        raise ValueError("alpha must be strictly between zero and one")


def moments(values: ArrayLike) -> dict[str, float | int]:
    """Return n, mean, sample variance, skewness, and excess kurtosis.

    Variance uses ``n - 1``.  Skewness and kurtosis use SciPy's finite-sample
    bias corrections, matching the conventions used in the course.
    """
    x = _finite_vector(values, "values")
    if x.size < 3:
        raise ValueError("at least three observations are required")
    return {
        "n": int(x.size),
        "mean": float(np.mean(x)),
        "variance": float(np.var(x, ddof=1)),
        "skewness": float(stats.skew(x, bias=False)),
        "excess_kurtosis": float(stats.kurtosis(x, fisher=True, bias=False)),
    }


def historical_risk(pnl: ArrayLike, alpha: float = 0.05) -> dict[str, float]:
    """Compute empirical VaR and ES using the positive-loss convention.

    ES is the negative mean of observations at or below the linearly
    interpolated empirical quantile.  A negative VaR means the quantile is a
    profit rather than a loss.
    """
    x = _finite_vector(pnl, "pnl")
    _check_alpha(alpha)
    quantile = float(np.quantile(x, alpha, method="linear"))
    tail = x[x <= quantile]
    return {"VaR": -quantile, "ES": -float(np.mean(tail)), "quantile": quantile}


def normal_risk(pnl: ArrayLike, alpha: float = 0.05) -> dict[str, float]:
    """Compute Normal VaR and ES from the sample mean and sample SD."""
    x = _finite_vector(pnl, "pnl")
    _check_alpha(alpha)
    if x.size < 2:
        raise ValueError("at least two observations are required")
    mean = float(np.mean(x))
    sd = float(np.std(x, ddof=1))
    z = float(stats.norm.ppf(alpha))
    return {
        "VaR": -(mean + z * sd),
        "ES": -(mean - sd * stats.norm.pdf(z) / alpha),
        "mean": mean,
        "sd": sd,
    }


def ew_weights(n: int, decay: float) -> NDArray[np.float64]:
    """Return normalized EW weights in chronological order.

    The first element is the oldest observation and the last element is the
    newest.  ``decay`` is the usual lambda parameter.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if not 0.0 < decay < 1.0:
        raise ValueError("decay must be strictly between zero and one")
    ages = np.arange(n - 1, -1, -1, dtype=float)
    raw = (1.0 - decay) * decay**ages
    return raw / raw.sum()
