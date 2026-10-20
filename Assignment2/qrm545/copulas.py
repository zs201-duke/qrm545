"""Elliptical-copula estimation helpers and simulators."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray
from scipy import special, stats


def _uniform_matrix(values: ArrayLike) -> NDArray[np.float64]:
    uniforms = np.asarray(values, dtype=float)
    if uniforms.ndim != 2 or uniforms.shape[1] < 2:
        raise ValueError("uniforms must be a two-dimensional matrix")
    if not np.all((uniforms > 0.0) & (uniforms < 1.0)):
        raise ValueError("uniforms must lie strictly between zero and one")
    return uniforms


def _correlation_matrix(values: ArrayLike, dimension: int) -> NDArray[np.float64]:
    corr = np.asarray(values, dtype=float)
    if corr.shape != (dimension, dimension):
        raise ValueError("correlation matrix has the wrong dimension")
    corr = (corr + corr.T) / 2.0
    if not np.allclose(np.diag(corr), 1.0):
        raise ValueError("correlation matrix must have a unit diagonal")
    if np.linalg.eigvalsh(corr).min() <= 0:
        raise ValueError("correlation matrix must be positive definite")
    return corr


def gaussian_copula_log_contributions(uniforms: ArrayLike, correlation: ArrayLike) -> NDArray[np.float64]:
    """Return observation-level Gaussian copula log densities."""
    u = _uniform_matrix(uniforms)
    corr = _correlation_matrix(correlation, u.shape[1])
    z = stats.norm.ppf(u)
    inverse = np.linalg.inv(corr)
    _, log_determinant = np.linalg.slogdet(corr)
    return -0.5 * log_determinant - 0.5 * np.einsum(
        "ni,ij,nj->n", z, inverse - np.eye(corr.shape[0]), z
    )


def t_copula_log_contributions(
    uniforms: ArrayLike,
    correlation: ArrayLike,
    df: float,
) -> NDArray[np.float64]:
    """Return observation-level Student t copula log densities."""
    if df <= 0:
        raise ValueError("df must be positive")
    u = _uniform_matrix(uniforms)
    corr = _correlation_matrix(correlation, u.shape[1])
    y = stats.t.ppf(u, df=df)
    dimension = corr.shape[0]
    inverse = np.linalg.inv(corr)
    _, log_determinant = np.linalg.slogdet(corr)
    quadratic = np.einsum("ni,ij,nj->n", y, inverse, y)
    joint = (
        special.gammaln((df + dimension) / 2)
        - special.gammaln(df / 2)
        - 0.5 * log_determinant
        - dimension / 2 * np.log(df * np.pi)
        - (df + dimension) / 2 * np.log1p(quadratic / df)
    )
    marginal = np.sum(stats.t.logpdf(y, df=df), axis=1)
    return joint - marginal


def kendall_correlation(observations: ArrayLike) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
    """Estimate Kendall's tau and its elliptical correlation transform."""
    x = np.asarray(observations, dtype=float)
    if x.ndim != 2 or x.shape[1] < 2 or not np.all(np.isfinite(x)):
        raise ValueError("observations must be a finite two-dimensional matrix")
    dimension = x.shape[1]
    tau = np.eye(dimension)
    for i in range(dimension):
        for j in range(i + 1, dimension):
            estimate = float(stats.kendalltau(x[:, i], x[:, j]).statistic)
            tau[i, j] = tau[j, i] = estimate
    return tau, np.sin(np.pi * tau / 2.0)


def simulate_gaussian_copula(
    correlation: ArrayLike,
    size: int,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Simulate uniforms from a Gaussian copula."""
    corr = np.asarray(correlation, dtype=float)
    corr = _correlation_matrix(corr, corr.shape[0])
    if size <= 0:
        raise ValueError("size must be positive")
    generator = np.random.default_rng() if rng is None else rng
    z = generator.multivariate_normal(np.zeros(corr.shape[0]), corr, size=size)
    return np.clip(stats.norm.cdf(z), 1e-10, 1 - 1e-10)


def simulate_t_copula(
    correlation: ArrayLike,
    df: float,
    size: int,
    rng: np.random.Generator | None = None,
) -> NDArray[np.float64]:
    """Simulate uniforms from a Student t copula."""
    corr = np.asarray(correlation, dtype=float)
    corr = _correlation_matrix(corr, corr.shape[0])
    if df <= 0 or size <= 0:
        raise ValueError("df and size must be positive")
    generator = np.random.default_rng() if rng is None else rng
    scale = generator.chisquare(df, size=size)
    normal = generator.multivariate_normal(np.zeros(corr.shape[0]), corr, size=size)
    t_draw = normal / np.sqrt(scale[:, None] / df)
    return np.clip(stats.t.cdf(t_draw, df=df), 1e-10, 1 - 1e-10)


def t_tail_dependence(rho: float, df: float) -> float:
    """Return either tail-dependence coefficient of a bivariate t copula."""
    if not -1.0 < rho < 1.0 or df <= 0:
        raise ValueError("require -1 < rho < 1 and df > 0")
    argument = -np.sqrt((df + 1) * (1 - rho) / (1 + rho))
    return float(2 * stats.t.cdf(argument, df=df + 1))
