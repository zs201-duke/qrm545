"""Reusable algorithms for Tests 8.1–13.9; no reference-output access."""
import numpy as np
import pandas as pd
from scipy import optimize, stats

from risk_tools import higham_psd, simulate_pca


def empirical_risk(values, alpha=.05):
    """Course order-statistic convention, with negative lower-tail P&L as loss."""
    x = np.sort(np.asarray(values, dtype=float))
    if x.ndim != 1 or not np.isfinite(x).all() or not 0 < alpha < 1:
        raise ValueError("Require a finite vector and 0 < alpha < 1")
    lo, hi = int(np.floor(len(x) * alpha)), int(np.ceil(len(x) * alpha))
    if lo < 1:
        raise ValueError("Insufficient observations for this tail probability")
    quantile = (x[lo - 1] + x[hi - 1]) / 2
    return float(-quantile), float(-x[x <= quantile].mean())


def distribution_risk(distribution, alpha=.05):
    """Analytic Normal / location-scale Student t VaR and ES."""
    q = distribution.ppf(alpha)
    if distribution.dist.name == "norm":
        es = -distribution.mean() + distribution.std() * stats.norm.pdf(stats.norm.ppf(alpha)) / alpha
    elif distribution.dist.name == "t":
        nu = distribution.args[0] if distribution.args else distribution.kwds["df"]
        if nu <= 1:
            raise ValueError("Student t ES requires degrees of freedom greater than one")
        loc, scale = distribution.kwds.get("loc", 0), distribution.kwds.get("scale", 1)
        z = stats.t.ppf(alpha, nu)
        es = -loc + scale * (nu + z*z) / (nu - 1) * stats.t.pdf(z, nu) / alpha
    else:
        raise ValueError("Only Normal and Student t distributions supported")
    return float(-q), float(es)


def aggregate_risk(returns, names, current_values, alpha=.05):
    """Individual positions and portfolio total, in dollars and value fractions."""
    returns = np.asarray(returns, dtype=float)
    values = np.asarray(current_values, dtype=float)
    if returns.shape[1] != len(values) or len(names) != len(values) or np.any(values <= 0):
        raise ValueError("Provide matching names and strictly positive position values")
    pnl = returns * values
    columns = np.column_stack([pnl, pnl.sum(axis=1)])
    rows = []
    for name, value, observations in zip([*names, "Total"], [*values, values.sum()], columns.T):
        var, es = empirical_risk(observations, alpha)
        rows.append([name, var, es, var / value, es / value])
    return pd.DataFrame(rows, columns=["Stock", "VaR95", "ES95", "VaR95_Pct", "ES95_Pct"])


def risk_parity(covariance, budget=None):
    """Convex risk-budget solve: min 1/2 x' C x - sum b_i log(x_i)."""
    cov = np.asarray(covariance, dtype=float)
    n = len(cov)
    budget = np.ones(n) if budget is None else np.asarray(budget, dtype=float)
    if np.any(budget <= 0) or budget.shape != (n,):
        raise ValueError("Risk budgets must be positive and match covariance dimensions")
    if np.linalg.eigvalsh(cov)[0] < -1e-10:
        raise ValueError("Risk parity requires PSD covariance")
    # Scale the variables to unit diagonal for numerical conditioning.
    sd = np.sqrt(np.diag(cov))
    corr = cov / np.outer(sd, sd)
    b = budget / budget.sum()

    def f(z):
        return .5 * z @ corr @ z - b @ np.log(z)

    def g(z):
        return corr @ z - b / z

    fit = optimize.minimize(f, np.sqrt(b), jac=g, method="L-BFGS-B",
                            bounds=[(1e-10, None)] * n,
                            options={"ftol": 1e-15, "gtol": 1e-10, "maxiter": 2000})
    if not fit.success:
        raise RuntimeError(f"Risk parity optimization failed: {fit.message}")
    weights = fit.x / sd
    weights /= weights.sum()
    contributions = weights * (cov @ weights) / (weights @ cov @ weights)
    if np.max(np.abs(contributions - b)) > 1e-7:
        raise RuntimeError("Risk-budget contributions did not converge")
    return weights


def maximum_sharpe(covariance, means, risk_free=.04, lower=0., upper=1.):
    """Long-only, fully invested maximum Sharpe portfolio with box constraints."""
    cov, means = np.asarray(covariance, float), np.asarray(means, float)
    n = len(means)
    low, high = np.broadcast_to(lower, (n,)), np.broadcast_to(upper, (n,))
    if low.sum() > 1 or high.sum() < 1 or np.any(low > high):
        raise ValueError("Infeasible weight bounds")
    excess = means - risk_free

    def objective(w):
        variance = w @ cov @ w
        if variance <= 0:
            raise ValueError("Nonpositive portfolio variance")
        vol = np.sqrt(variance)
        reward = w @ excess
        return -reward / vol, -excess / vol + reward * (cov @ w) / vol**3

    constraints = {"type": "eq", "fun": lambda w: w.sum() - 1,
                   "jac": lambda w: np.ones(n)}
    starts = [np.full(n, 1/n), low + (1 - low.sum()) * (high - low) / (high - low).sum()]
    fits = [optimize.minimize(objective, start, jac=True, method="SLSQP",
                             bounds=list(zip(low, high)), constraints=constraints,
                             options={"ftol": 1e-13, "maxiter": 2000}) for start in starts]
    valid = [fit for fit in fits if fit.success]
    if not valid:
        raise RuntimeError("Maximum Sharpe optimization failed")
    return min(valid, key=lambda fit: fit.fun).x


def expost_attribution(initial_weights, returns, factors, betas, include_alpha=True):
    """Buy-and-hold weights, Carino return linking, and component volatility."""
    r, f = np.asarray(returns, float), np.asarray(factors, float)
    beta, w = np.asarray(betas, float), np.asarray(initial_weights, float).copy()
    if not np.isclose(w.sum(), 1) or np.any(r <= -1) or len(r) != len(f):
        raise ValueError("Require fully invested weights and aligned valid returns")
    port = np.empty(len(r))
    exposure = np.empty_like(f)
    for i in range(len(r)):
        exposure[i] = w @ beta
        updated = w * (1 + r[i])
        gross = updated.sum()
        port[i] = gross - 1
        w = updated / gross
    contributions = f * exposure
    residual = port - contributions.sum(axis=1)
    components = np.column_stack([contributions, residual])
    total = np.expm1(np.log1p(port).sum())

    def log_ratio(x):
        x = np.asarray(x)
        return np.divide(np.log1p(x), x, out=np.ones_like(x), where=x != 0)

    link = log_ratio(port) / log_ratio(total)
    attributed = (components * link[:, None]).sum(axis=0)
    port_sd = np.std(port, ddof=1)
    if port_sd == 0:
        vol = np.zeros(components.shape[1])
    else:
        vol = ((components - components.mean(axis=0)).T @ (port - port.mean())) / ((len(port) - 1) * port_sd)
    raw = np.column_stack([f, residual])
    names = [*factors.columns, "Alpha"]
    out = pd.DataFrame({"Value": ["TotalReturn", "Return Attribution", "Vol Attribution"]})
    for j, name in enumerate(names):
        out[name] = [np.expm1(np.log1p(raw[:, j]).sum()), attributed[j], vol[j]]
    out["Portfolio"] = [total, total, port_sd]
    np.testing.assert_allclose(attributed.sum(), total, atol=1e-12)
    np.testing.assert_allclose(vol.sum(), port_sd, atol=1e-12)
    return out if include_alpha else out.drop(columns="Alpha")


def gbsm(call, spot, strike, maturity, rate, carry, volatility):
    """Generalized BSM; annual theta, rho with dividend yield held fixed."""
    sign = 1 if call else -1
    root_t = np.sqrt(maturity)
    d1 = (np.log(spot / strike) + (carry + volatility**2 / 2) * maturity) / (volatility * root_t)
    d2 = d1 - volatility * root_t
    growth, discount = np.exp((carry - rate) * maturity), np.exp(-rate * maturity)
    n1, n2, density = stats.norm.cdf(sign*d1), stats.norm.cdf(sign*d2), stats.norm.pdf(d1)
    return {"Value": sign * (spot * growth * n1 - strike * discount * n2),
            "Delta": sign * growth * n1,
            "Gamma": growth * density / (spot * volatility * root_t),
            "Vega": spot * growth * density * root_t,
            "Rho": sign * maturity * strike * discount * n2,
            "Theta": -spot * growth * density * volatility / (2 * root_t)
                     - sign * (carry - rate) * spot * growth * n1
                     - sign * rate * strike * discount * n2}


def _american_batch(call, spots, strike, maturity, rate, carry, volatility, steps,
                    dividends=(), dividend_steps=()):
    """Exact recursive cash-dividend tree, vectorized over starting spots."""
    spots = np.asarray(spots, float).reshape(-1)
    sign = 1 if call else -1
    if steps == 0 or maturity == 0:
        return np.maximum(sign * (spots - strike), 0)
    dt = maturity / steps
    u = np.exp(volatility * np.sqrt(dt))
    d = 1 / u
    pu = (np.exp(carry * dt) - d) / (u - d)
    if not 0 <= pu <= 1:
        raise ValueError("Tree probability outside [0,1]; increase steps")
    df = np.exp(-rate * dt)
    has_dividend = bool(dividends) and dividend_steps[0] <= steps
    terminal = int(dividend_steps[0]) if has_dividend else steps
    levels = np.arange(terminal + 1)
    prices = spots[:, None] * u**levels * d**(terminal - levels)
    values = np.maximum(sign * (prices - strike), 0)
    if has_dividend:
        next_spots = np.maximum(prices - dividends[0], 0).ravel()
        continuation = np.empty_like(next_spots)
        for start in range(0, len(next_spots), 512):
            continuation[start:start+512] = _american_batch(
                call, next_spots[start:start+512], strike, maturity - terminal*dt,
                rate, rate, volatility, steps - terminal, dividends[1:],
                tuple(t - terminal for t in dividend_steps[1:]))
        values = np.maximum(values, continuation.reshape(prices.shape))
    for j in range(terminal - 1, -1, -1):
        levels = np.arange(j + 1)
        prices = spots[:, None] * u**levels * d**(j - levels)
        hold = df * (pu * values[:, 1:j+2] + (1-pu) * values[:, :j+1])
        values = np.maximum(np.maximum(sign * (prices - strike), 0), hold)
    return values[:, 0]


def american_option(call, spot, strike, maturity, rate, carry, volatility, steps=500,
                    dividends=(), dividend_steps=()):
    if len(dividends) != len(dividend_steps) or any(t <= 0 for t in dividend_steps):
        raise ValueError("Dividend amounts and strictly positive grid dates must align")
    if any(b <= a for a, b in zip(dividend_steps, dividend_steps[1:])):
        raise ValueError("Dividend grid dates must be increasing")
    return float(_american_batch(call, [spot], strike, maturity, rate, carry, volatility,
                                 steps, tuple(dividends), tuple(dividend_steps))[0])


def american_greeks(call, spot, strike, maturity, rate, carry, volatility, steps=500):
    """Match Test 12.2: fixed-carry rho, +dV/dT, and gamma spot bump of 1.5."""
    parameters = np.array([spot, strike, maturity, rate, carry, volatility], float)
    value = american_option(call, *parameters, steps=steps)
    gradient = {}
    for index, name in [(0, "Delta"), (2, "Theta"), (3, "Rho"), (5, "Vega")]:
        h = np.cbrt(np.finfo(float).eps) * max(abs(parameters[index]), 1)
        above, below = parameters.copy(), parameters.copy()
        above[index] += h
        below[index] -= h
        gradient[name] = (american_option(call, *above, steps=steps)
                          - american_option(call, *below, steps=steps)) / (2*h)
    h = 1.5
    gamma = (american_option(call, spot+h, *parameters[1:], steps=steps)
             + american_option(call, spot-h, *parameters[1:], steps=steps) - 2*value) / h**2
    return {"Value": value, "Delta": gradient["Delta"], "Gamma": gamma,
            "Vega": gradient["Vega"], "Rho": gradient["Rho"], "Theta": gradient["Theta"]}


def fix_correlation(correlation, tolerance=1e-8, ridge=1e-8):
    r = np.asarray(correlation, float).copy()
    if np.linalg.eigvalsh(r)[0] < -tolerance:
        r = higham_psd(r)
    r = (r + r.T) / 2
    if np.linalg.eigvalsh(r)[0] < ridge:
        r = (r + ridge * np.eye(len(r))) / (1 + ridge)
    np.linalg.cholesky(r)
    return r


def kendall_correlation(x):
    x = np.asarray(x, float)
    r = np.eye(x.shape[1])
    for i in range(x.shape[1]):
        for j in range(i):
            tau = stats.kendalltau(x[:, i], x[:, j]).statistic
            r[i, j] = r[j, i] = np.sin(np.pi * tau / 2)
    return fix_correlation(r)


def profile_nu(loglike, low=.01, high=.49, grid_size=200):
    """The course's two-stage grid search over theta=1/nu (not continuous MLE)."""
    grid = np.linspace(low, high, grid_size)
    ll = np.array([loglike(1/theta) for theta in grid])
    i = np.argmax(ll)
    fine = np.linspace(grid[max(i-1, 0)], grid[min(i+1, grid_size-1)], grid_size)
    values = np.array([loglike(1/theta) for theta in fine])
    j = np.argmax(values)
    return float(1/fine[j]), float(values[j])


def fit_multivariate_t(x):
    """Rank-based profile: fixed sample mean/SD, Kendall R, profile nu."""
    x = np.asarray(x, float)
    mean, sd = x.mean(axis=0), x.std(axis=0, ddof=1)
    correlation = kendall_correlation(x)

    def scale(nu):
        return np.outer(sd, sd) * correlation * ((nu - 2) / nu)

    nu, ll = profile_nu(lambda nu: stats.multivariate_t.logpdf(x, loc=mean, shape=scale(nu), df=nu).sum())
    return mean, scale(nu), nu, ll


def gaussian_copula_loglike(uniforms, correlation):
    z = stats.norm.ppf(uniforms)
    return float(stats.multivariate_normal.logpdf(z, cov=correlation).sum() - stats.norm.logpdf(z).sum())


def t_copula_loglike(uniforms, correlation, nu):
    z = stats.t.ppf(uniforms, nu)
    return float(stats.multivariate_t.logpdf(z, shape=correlation, df=nu).sum()
                 - stats.t.logpdf(z, nu).sum())


def simulate_copula(correlation, n, seed=1234, nu=None):
    z, _, _, _ = simulate_pca(correlation, n=n, explained=1., seed=seed)
    if nu is None:
        return stats.norm.cdf(z)
    shock = np.random.default_rng(seed + 1).chisquare(nu, size=n)
    return stats.t.cdf(z * np.sqrt(nu/shock)[:, None], nu)


def copula_information_criteria(loglike, parameters, n):
    return (-2*loglike + 2*parameters + 2*parameters*(parameters+1)/(n-parameters-1),
            parameters*np.log(n) - 2*loglike)


def tail_dependence_t(rho, nu):
    return float(2 * stats.t.cdf(-np.sqrt((nu+1)*(1-rho)/(1+rho)), nu+1))
