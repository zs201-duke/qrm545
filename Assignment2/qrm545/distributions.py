"""Distribution fitting and information criteria."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike
from scipy import optimize, stats


def aicc(loglik: float, parameters: int, observations: int) -> float:
    """Return corrected Akaike information criterion.

    The finite-sample correction is infinite when there are not enough
    observations for the requested parameter count.
    """
    if parameters < 0 or observations <= 0:
        raise ValueError("parameters must be nonnegative and observations positive")
    correction = np.inf
    if observations > parameters + 1:
        correction = 2 * parameters * (parameters + 1) / (observations - parameters - 1)
    return float(-2 * loglik + 2 * parameters + correction)


def fit_student_t(
    values: ArrayLike,
    min_df: float = 2.01,
    max_df: float = 200.0,
) -> dict[str, float | bool]:
    """Fit a three-parameter Student t by maximum likelihood.

    Several starting degrees of freedom reduce sensitivity to a local optimizer
    failure.  The degree-of-freedom parameter is constrained to the open range
    between ``min_df`` and ``max_df``.
    """
    x = np.asarray(values, dtype=float)
    if x.ndim != 1 or x.size < 3 or not np.all(np.isfinite(x)):
        raise ValueError("values must be a finite one-dimensional sample")
    if not 0 < min_df < max_df:
        raise ValueError("require 0 < min_df < max_df")
    location_start = float(np.median(x))
    scale_start = float(np.std(x, ddof=1))
    if scale_start <= 0:
        raise ValueError("values must not be constant")

    def unpack(theta):
        df = min_df + (max_df - min_df) / (1.0 + np.exp(-theta[0]))
        return df, theta[1], np.exp(theta[2])

    def objective(theta):
        df, location, scale = unpack(theta)
        return -np.sum(stats.t.logpdf(x, df=df, loc=location, scale=scale))

    candidates = []
    for df_start in (3.0, 5.0, 10.0, 30.0, 100.0):
        bounded_start = min(max(df_start, min_df + 1e-8), max_df - 1e-8)
        probability = (bounded_start - min_df) / (max_df - min_df)
        logit = np.log(probability / (1.0 - probability))
        result = optimize.minimize(
            objective,
            np.array([logit, location_start, np.log(scale_start)]),
            method="L-BFGS-B",
            bounds=[
                (-15, 15),
                (float(np.min(x)), float(np.max(x))),
                (np.log(scale_start / 100), np.log(scale_start * 10)),
            ],
        )
        candidates.append(result)
    best = min(candidates, key=lambda result: result.fun)
    df, location, scale = unpack(best.x)
    return {
        "df": float(df),
        "loc": float(location),
        "scale": float(scale),
        "loglik": float(-best.fun),
        "success": bool(best.success),
    }
