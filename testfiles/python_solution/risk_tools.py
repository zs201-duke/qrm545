"""Numerical implementations for Tests.xlsx, tests 1.1 through 7.6.

Conventions match the course Julia library. No reference CSV is used here.
"""
import numpy as np
import pandas as pd
from scipy import optimize, special, stats


def missing_covariance(x, *, pairwise=False, correlation=False):
    x = np.asarray(x, dtype=float)
    if not pairwise:
        x = x[~np.isnan(x).any(axis=1)]
    result = np.empty((x.shape[1], x.shape[1]))
    for i in range(x.shape[1]):
        for j in range(i + 1):
            pair = x[:, [i, j]]
            pair = pair[~np.isnan(pair).any(axis=1)]
            if len(pair) < 2:
                raise ValueError("At least two complete observations per pair required")
            fun = np.corrcoef if correlation else np.cov
            result[i, j] = result[j, i] = fun(pair, rowvar=False)[0, 1]
    return result


def ew_covariance(x, decay):
    """Normalized exponential weights; last row newest; weighted centering."""
    x = np.asarray(x, dtype=float)
    if not 0 < decay < 1 or not np.isfinite(x).all():
        raise ValueError("Require 0 < decay < 1 and finite observations")
    weights = (1 - decay) * decay ** np.arange(len(x) - 1, -1, -1)
    weights /= weights.sum()
    centered = x - weights @ x
    return centered.T @ (weights[:, None] * centered)


def correlation_from_covariance(cov):
    sd = np.sqrt(np.diag(cov))
    if np.any(sd <= 0):
        raise ValueError("Positive variances required")
    return cov / np.outer(sd, sd)


def _symmetric(a):
    a = np.asarray(a, dtype=float)
    if a.ndim != 2 or a.shape[0] != a.shape[1] or not np.isfinite(a).all():
        raise ValueError("A finite square matrix is required")
    if not np.allclose(a, a.T, atol=1e-12, rtol=1e-12):
        raise ValueError("A symmetric matrix is required")
    return (a + a.T) / 2


def near_psd(a, epsilon=0.0):
    """Clip correlation eigenvalues, normalize diagonal, restore variances."""
    a = _symmetric(a)
    sd = np.sqrt(np.diag(a))
    corr = correlation_from_covariance(a)
    values, vectors = np.linalg.eigh(corr)
    root = vectors * np.sqrt(np.maximum(values, epsilon))
    root /= np.sqrt(np.sum(root * root, axis=1))[:, None]
    return (root @ root.T) * np.outer(sd, sd)


def higham_psd(a, tolerance=1e-9, max_iterations=100):
    """Higham alternating projections with Dykstra correction, unit weights."""
    a = _symmetric(a)
    sd = np.sqrt(np.diag(a))
    original = correlation_from_covariance(a)
    y = original.copy()
    correction = np.zeros_like(y)
    previous = np.inf
    for _ in range(max_iterations):
        r = y - correction
        values, vectors = np.linalg.eigh(r)
        x = (vectors * np.maximum(values, 0)) @ vectors.T
        correction = x - r
        y = x.copy()
        np.fill_diagonal(y, 1)
        distance = np.sum((y - original) ** 2)
        if abs(distance - previous) < tolerance and np.linalg.eigvalsh(y)[0] > -tolerance:
            return y * np.outer(sd, sd)
        previous = distance
    raise RuntimeError("Higham projection did not converge")


def chol_psd(a, tolerance=1e-8):
    """Lower triangular Cholesky factor, allowing numerical zero pivots."""
    a = _symmetric(a)
    root = np.zeros_like(a)
    for j in range(len(a)):
        pivot = a[j, j] - root[j, :j] @ root[j, :j]
        if pivot < -tolerance:
            raise ValueError("Matrix is not positive semidefinite")
        root[j, j] = np.sqrt(max(pivot, 0.0))
        residual = a[j + 1:, j] - root[j + 1:, :j] @ root[j, :j]
        if root[j, j] == 0:
            if np.any(np.abs(residual) > tolerance):
                raise ValueError("Inconsistent zero pivot in PSD factorization")
        else:
            root[j + 1:, j] = residual / root[j, j]
    return root


def simulate_normal(cov, n=100_000, seed=1234, repair=near_psd):
    cov = _symmetric(cov)
    # Repair only genuinely indefinite input; numerical zero eigenvalues are valid.
    target = repair(cov) if np.linalg.eigvalsh(cov)[0] < -1e-10 else cov.copy()
    root = chol_psd(target)
    sample = np.random.default_rng(seed).standard_normal((n, len(cov))) @ root.T
    return sample, target


def simulate_pca(cov, n=100_000, explained=0.99, seed=1234):
    cov = _symmetric(cov)
    if not 0 < explained <= 1:
        raise ValueError("Explained variance must be in (0, 1]")
    values, vectors = np.linalg.eigh(cov)
    if values[0] < -1e-10:
        raise ValueError("PCA requires PSD input")
    values, vectors = values[::-1], vectors[:, ::-1]
    positive = values >= 1e-8  # Same eigenvalue cutoff as the course library.
    total = values.sum()
    values, vectors = values[positive], vectors[:, positive]
    if not len(values):
        raise ValueError("No positive principal components")
    count = min(np.searchsorted(np.cumsum(values) / total, explained) + 1, len(values))
    root = vectors[:, :count] * np.sqrt(values[:count])
    sample = np.random.default_rng(seed).standard_normal((n, count)) @ root.T
    return sample, root @ root.T, int(count), float(values[:count].sum() / total)


def calculate_returns(prices, logarithmic=False, date_column="Date"):
    values = prices.drop(columns=[date_column]).to_numpy(dtype=float)
    if not np.isfinite(values).all() or np.any(values <= 0):
        raise ValueError("Prices must be finite and positive")
    ratio = values[1:] / values[:-1]
    result = pd.DataFrame(np.log(ratio) if logarithmic else ratio - 1,
                          columns=prices.columns.drop(date_column))
    result.insert(0, date_column, prices[date_column].iloc[1:].to_numpy())
    return result


def fit_normal(x):
    return {"mu": float(np.mean(x)), "sigma": float(np.std(x, ddof=1))}


def _fit_t_linear(y, design):
    """Joint t MLE with analytic gradient; nu >= 2.0001 as in the course."""
    n, p = design.shape
    initial_beta = np.linalg.lstsq(design, y, rcond=None)[0]
    residual_sd = np.std(y - design @ initial_beta, ddof=1)

    def objective(theta):
        beta, sigma, nu = theta[:p], np.exp(theta[p]), theta[p + 1]
        residual = y - design @ beta
        z2 = (residual / sigma) ** 2
        loglike = stats.t.logpdf(residual / sigma, nu).sum() - n * np.log(sigma)
        gradient = np.empty(p + 2)
        gradient[:p] = -(nu + 1) * design.T @ (residual / (nu * sigma**2 + residual**2))
        gradient[p] = n - np.sum((nu + 1) * z2 / (nu + z2))
        gradient[p + 1] = -np.sum(
            0.5 * special.digamma((nu + 1) / 2) - 0.5 * special.digamma(nu / 2)
            - 0.5 / nu - 0.5 * np.log1p(z2 / nu)
            + (nu + 1) * z2 / (2 * nu * (nu + z2)))
        return -loglike, gradient

    fits = []
    for nu in (4.0, 10.0, 30.0):
        start = np.r_[initial_beta, np.log(residual_sd * np.sqrt((nu - 2) / nu)), nu]
        fit = optimize.minimize(objective, start, jac=True, method="L-BFGS-B",
                                bounds=[(None, None)] * p + [(-20, 20), (2.0001, None)],
                                options={"ftol": 1e-14, "gtol": 1e-8, "maxiter": 3000})
        if fit.success and np.isfinite(fit.fun):
            fits.append(fit)
    if not fits:
        raise RuntimeError("Student t optimization failed at every starting value")
    best = min(fits, key=lambda fit: fit.fun)
    return best.x[:p], np.exp(best.x[p]), best.x[p + 1], {
        "converged_starts": len(fits), "negative_loglike": float(best.fun),
        "start_objective_spread": float(np.ptp([fit.fun for fit in fits])),
        "gradient_max_abs": float(np.max(np.abs(best.jac))),
    }


def fit_t(x):
    x = np.asarray(x, dtype=float)
    center, scale = x.mean(), x.std(ddof=1)
    beta, sigma, nu, diagnostics = _fit_t_linear((x - center) / scale, np.ones((len(x), 1)))
    return {"mu": float(center + scale * beta[0]), "sigma": float(scale * sigma),
            "nu": float(nu)}, diagnostics


def fit_t_regression(y, x):
    x, y = np.asarray(x, dtype=float), np.asarray(y, dtype=float)
    xm, xs, ym, ys = x.mean(axis=0), x.std(axis=0, ddof=1), y.mean(), y.std(ddof=1)
    design = np.column_stack([np.ones(len(y)), (x - xm) / xs])
    beta, sigma, nu, diagnostics = _fit_t_linear((y - ym) / ys, design)
    slopes = ys * beta[1:] / xs
    result = {"mu": 0.0, "sigma": float(ys * sigma), "nu": float(nu),
              "Alpha": float(ym + ys * beta[0] - xm @ slopes)}
    result.update({f"B{i + 1}": float(value) for i, value in enumerate(slopes)})
    return result, diagnostics


def t_aicc(x, parameters):
    n, k = len(x), 3
    ll = stats.t.logpdf(x, parameters["nu"], loc=parameters["mu"], scale=parameters["sigma"]).sum()
    return float(-2 * ll + 2 * k + 2 * k * (k + 1) / (n - k - 1))


def fit_nig_moments(x):
    # StatsBase: sample variance, unadjusted standardized skew/excess kurtosis.
    m, v = np.mean(x), np.var(x, ddof=1)
    skew, excess = stats.skew(x, bias=True), stats.kurtosis(x, fisher=True, bias=True)
    if excess <= 0 or excess <= 5 * skew**2 / 3:
        raise ValueError("Sample moments are outside the NIG feasible region")
    ratio = skew**2 / excess
    rho2 = ratio / (3 - 4 * ratio)
    rho = np.sign(skew) * np.sqrt(rho2)
    dgamma = 3 * (1 + 4 * rho2) / excess
    alpha = np.sqrt(dgamma / (v * (1 - rho2)**2))
    beta = rho * alpha
    gamma = np.sqrt(alpha**2 - beta**2)
    delta = dgamma / gamma
    return {"mu": float(m - delta * beta / gamma), "alpha": float(alpha),
            "beta": float(beta), "delta": float(delta)}


def fit_nig_mle(x):
    a, b, loc, scale = stats.norminvgauss.fit(x)
    return {"mu": float(loc), "alpha": float(a / scale),
            "beta": float(b / scale), "delta": float(scale)}


def nig_distribution(parameters):
    p = parameters
    return stats.norminvgauss(p["alpha"] * p["delta"], p["beta"] * p["delta"],
                             loc=p["mu"], scale=p["delta"])
