"""Small reusable statistics/risk/portfolio functions with explicit conventions."""
import numpy as np
from itertools import combinations
from scipy import stats
from scipy.optimize import minimize


def moments(x):
    """n-1 variance, finite-sample corrected standardized skew/excess kurtosis."""
    x = np.asarray(x)
    return dict(n=len(x), mean=float(x.mean()), variance=float(x.var(ddof=1)),
                sd=float(x.std(ddof=1)), skew=float(stats.skew(x, bias=False)),
                excess_kurtosis=float(stats.kurtosis(x, bias=False)))


def aicc(loglik, n, k):
    return float(-2*loglik+2*k+2*k*(k+1)/(n-k-1))


def ols(y, factors, names):
    """OLS by least squares, conventional SEs plus HC3 robustness diagnostics.

    AICc uses the Gaussian maximized likelihood, counting all coefficients
    INCLUDING intercept, PLUS the fitted residual variance. HC3 is supplemental;
    it does not change coefficients, R-squared or the Gaussian AICc.
    """
    y = np.asarray(y, float)
    f = np.asarray(factors, float).reshape(len(y), -1)
    X = np.column_stack([np.ones(len(y)), f])
    beta = np.linalg.lstsq(X, y, rcond=None)[0]
    resid = y-X@beta
    n, p = X.shape
    gram_inv = np.linalg.inv(X.T@X)
    sse = resid@resid
    se = np.sqrt(np.diag(gram_inv)*sse/(n-p))
    leverage = np.sum((X@gram_inv)*X, axis=1)
    meat = X.T@(((resid/(1-leverage))**2)[:, None]*X)
    hc3 = np.sqrt(np.diag(gram_inv@meat@gram_inv))
    ll = -n/2*(np.log(2*np.pi)+1+np.log(sse/n))
    return dict(n=n, names=["alpha"]+names, coefficients=beta.tolist(), se=se.tolist(),
                t=(beta/se).tolist(), hc3_se=hc3.tolist(), hc3_t=(beta/hc3).tolist(),
                r2=float(1-sse/np.sum((y-y.mean())**2)), aicc=aicc(ll, n, p+1),
                loglik=float(ll), parameter_count=p+1, residuals=resid.tolist(),
                durbin_watson=float(np.sum(np.diff(resid)**2)/sse))


def risk(x, alpha):
    """Loss-positive empirical VaR and integrated-quantile ES.

    VaR is the inverse empirical CDF ('inverted_cdf'). ES includes exactly
    alpha*n observations of probability mass, using a fractional boundary
    observation when needed. Thus the 1% historical ES with n=240 averages
    the worst two months plus 0.4 of the third, divided by 2.4. This preserves
    the coherence of empirical ES rather than changing alpha to 3/240.
    """
    x = np.asarray(x, float)
    k_float = len(x)*alpha
    k = int(np.floor(k_float+1e-10))
    fraction = k_float-k
    ordered = np.partition(x, min(k, len(x)-1))
    tail_sum = ordered[:k].sum()
    if fraction > 1e-10:
        tail_sum += fraction*ordered[k]
    return dict(var=float(-np.quantile(x, alpha, method="inverted_cdf")),
                es=float(-tail_sum/k_float))


def normal_risk(mean, sd, alpha):
    z = stats.norm.ppf(alpha)
    return dict(var=float(-mean-sd*z), es=float(-mean+sd*stats.norm.pdf(z)/alpha))


def fit_distributions(x):
    """Full MLE of normal (2 params) and location-scale t (3 params)."""
    x = np.asarray(x)
    mu, sd = stats.norm.fit(x)
    normal = dict(mu=float(mu), scale=float(sd), sd=float(sd),
                  loglik=float(stats.norm.logpdf(x, mu, sd).sum()))
    # Fit on standardized data for numerical scaling. Several starting nus
    # protect against poor local convergence; free location is not fixed at 0.
    center, scale = x.mean(), x.std()
    y = (x-center)/scale
    candidates = [stats.t.fit(y, df0) for df0 in (3, 5, 10, 30)]
    df, loc, sc = max(candidates, key=lambda p: stats.t.logpdf(y, *p).sum())
    loc, sc = center+scale*loc, scale*sc
    student = dict(df=float(df), mu=float(loc), scale=float(sc),
                   sd=float(sc*np.sqrt(df/(df-2))) if df > 2 else None,
                   loglik=float(stats.t.logpdf(x, df, loc, sc).sum()))
    normal["aicc"] = aicc(normal["loglik"], len(x), 2)
    student["aicc"] = aicc(student["loglik"], len(x), 3)
    return dict(Normal=normal, StudentT=student)


def tangency(mu, cov, rf, mode="long_only"):
    """Fully invested maximum Sharpe weights; no cash included in risky basket."""
    excess = np.asarray(mu)-rf
    cov = np.asarray(cov)
    if mode == "unconstrained":
        direction = np.linalg.solve(cov, excess)
        if direction.sum() <= 0:
            raise ValueError("Positive-budget tangency direction not available")
        return direction/direction.sum()
    bounds = [(0., 1.)]*len(mu)
    if mode == "capped":
        bounds[-1] = (0., .2)
    # Sharpe is homogeneous. Fix excess return to 1, minimize variance in y,
    # then normalize to weights. This is a convex quadratic program.
    # The cap w_last <= .2 becomes y_last <= .2*sum(y).
    constraints = [dict(type="eq", fun=lambda y: excess@y-1,
                        jac=lambda y: excess)]
    if mode == "capped":
        grad = np.full(len(mu), .2); grad[-1] -= 1
        constraints.append(dict(type="ineq", fun=lambda y: grad@y,
                                jac=lambda y: grad))
    initial = np.ones(len(mu))/excess.sum()
    result = minimize(lambda y: y@cov@y, initial, jac=lambda y: 2*cov@y,
                      bounds=[(0., None)]*len(mu), constraints=constraints,
                      method="SLSQP", options=dict(ftol=1e-12, maxiter=2000))
    if not result.success:
        raise RuntimeError(result.message)
    w = result.x/result.x.sum()
    if mode == "capped" and w[-1] > .200001:
        raise AssertionError("Cap violated")
    return w


def efficient_weights(mu, cov, target):
    """Exact active-set enumeration for the small long-only frontier (four assets).

    For each possible nonzero support solve the equality-constrained minimum
    variance problem, reject negative weights and keep the lowest variance.
    This avoids endpoint line-search failures at a one-asset portfolio.
    """
    mu, cov = np.asarray(mu), np.asarray(cov)
    candidates = []
    for size in range(1, len(mu)+1):
        for subset in combinations(range(len(mu)), size):
            ids = np.array(subset)
            if size == 1:
                if abs(mu[ids[0]]-target)>1e-12: continue
                ws = np.ones(1)
            else:
                A = np.vstack([np.ones(size), mu[ids]*100])
                inv_a = np.linalg.solve(cov[np.ix_(ids,ids)], A.T)
                ws = inv_a@np.linalg.solve(A@inv_a, [1.,target*100])
            if ws.min() < -1e-8: continue
            w = np.zeros(len(mu)); w[ids] = ws
            candidates.append(w)
    if not candidates: raise RuntimeError("No feasible frontier portfolio")
    return min(candidates, key=lambda w: w@cov@w)
