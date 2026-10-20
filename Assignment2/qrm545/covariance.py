"""Covariance construction, portfolio variance, and correlation repair."""

from __future__ import annotations

import numpy as np
from numpy.typing import ArrayLike, NDArray


def _square_matrix(values: ArrayLike, name: str) -> NDArray[np.float64]:
    matrix = np.asarray(values, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"{name} must be a square matrix")
    if not np.all(np.isfinite(matrix)):
        raise ValueError(f"{name} must contain only finite values")
    return matrix


def covariance_from_correlation(correlation: ArrayLike, standard_deviations: ArrayLike) -> NDArray[np.float64]:
    """Build ``D C D`` from a correlation matrix and standard deviations."""
    corr = _square_matrix(correlation, "correlation")
    corr = (corr + corr.T) / 2.0
    sd = np.asarray(standard_deviations, dtype=float)
    if sd.ndim != 1 or sd.size != corr.shape[0]:
        raise ValueError("standard_deviations must match the matrix dimension")
    if not np.all(np.isfinite(sd)) or np.any(sd < 0):
        raise ValueError("standard deviations must be finite and nonnegative")
    diagonal = np.diag(sd)
    return diagonal @ corr @ diagonal


def portfolio_variance(covariance: ArrayLike, weights: ArrayLike) -> float:
    """Return the quadratic form ``w' covariance w``."""
    cov = _square_matrix(covariance, "covariance")
    w = np.asarray(weights, dtype=float)
    if w.ndim != 1 or w.size != cov.shape[0]:
        raise ValueError("weights must match the matrix dimension")
    return float(w @ cov @ w)


def nearest_corr_spectral(correlation: ArrayLike) -> NDArray[np.float64]:
    """Apply the Rebonato-Jackel eigenvalue-clipping repair."""
    corr = _square_matrix(correlation, "correlation")
    corr = (corr + corr.T) / 2.0
    eigenvalues, eigenvectors = np.linalg.eigh(corr)
    clipped = (eigenvectors * np.maximum(eigenvalues, 0.0)) @ eigenvectors.T
    diagonal = np.diag(clipped)
    if np.any(diagonal <= 0):
        raise ValueError("spectral repair produced a nonpositive diagonal")
    inverse_sd = 1.0 / np.sqrt(diagonal)
    repaired = clipped * np.outer(inverse_sd, inverse_sd)
    return (repaired + repaired.T) / 2.0


def nearest_corr_higham(
    correlation: ArrayLike,
    tol: float = 1e-12,
    max_iter: int = 10_000,
) -> tuple[NDArray[np.float64], int]:
    """Find an unweighted nearest correlation matrix with Higham's algorithm.

    Returns the repaired matrix and the number of alternating-projection
    iterations.  Dykstra's correction is included.
    """
    if tol <= 0 or max_iter <= 0:
        raise ValueError("tol and max_iter must be positive")
    y = _square_matrix(correlation, "correlation")
    y = (y + y.T) / 2.0
    delta = np.zeros_like(y)
    for iteration in range(1, max_iter + 1):
        residual = y - delta
        residual = (residual + residual.T) / 2.0
        eigenvalues, eigenvectors = np.linalg.eigh(residual)
        psd = (eigenvectors * np.maximum(eigenvalues, 0.0)) @ eigenvectors.T
        delta = psd - residual
        previous = y
        y = psd.copy()
        np.fill_diagonal(y, 1.0)
        y = (y + y.T) / 2.0
        change = np.linalg.norm(y - previous, ord="fro")
        scale = max(1.0, np.linalg.norm(y, ord="fro"))
        if change <= tol * scale:
            return y, iteration
    return y, max_iter
