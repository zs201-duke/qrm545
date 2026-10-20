"""Midterm Problem 2: one-day normal VaR and ES for 100 XYZ shares.

Run with Python 3 and NumPy. The data file is resolved relative to this script.
Arithmetic returns, OLS with intercept, and the sample covariance of [SPY, e]
follow the course's Week 02/04/05 model-based simulation construction.
"""
from pathlib import Path
from statistics import NormalDist, mean, variance
import csv
import hashlib
import json
import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "problem2.csv"


def main():
    # Problem 2(a): read 501 positive prices and form 500 arithmetic returns.
    with SOURCE.open(newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 501
    dates = [row["Date"] for row in rows]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    prices = np.array([[float(row["SPY"]), float(row["XYZ"])] for row in rows])
    assert np.isfinite(prices).all() and (prices > 0).all()
    returns = prices[1:] / prices[:-1] - 1.0
    spy, xyz = returns.T
    n = len(spy)

    # Problem 2(a): estimate alpha and beta by OLS including an intercept.
    design = np.column_stack([np.ones(n), spy])
    alpha, beta = np.linalg.lstsq(design, xyz, rcond=None)[0]
    residuals = xyz - design @ np.array([alpha, beta])
    joint_covariance = np.cov(np.column_stack([spy, residuals]), rowvar=False, ddof=1)
    spy_mean = float(spy.mean())
    spy_variance, residual_variance = np.diag(joint_covariance)
    cross_covariance = float(joint_covariance[0, 1])

    # Under the course's joint-normal/independent-error model, XYZ is normal.
    # The covariance cross term is theoretically zero and numerically negligible.
    mu = float(alpha + beta * spy_mean)
    sigma2 = float(beta**2 * spy_variance + residual_variance)
    sigma = float(np.sqrt(sigma2))
    normal = NormalDist()
    position_value = float(100 * prices[-1, 1])

    # Validate OLS independently with the scalar covariance formula.
    beta_scalar = np.cov(spy, xyz, ddof=1)[0, 1] / spy_variance
    assert abs(beta - beta_scalar) < 1e-12
    assert abs(alpha - (xyz.mean() - beta_scalar * spy.mean())) < 1e-14
    assert abs(residuals.mean()) < 1e-14 and abs(cross_covariance) < 1e-14
    assert abs(mu - mean(xyz.tolist())) < 1e-14
    assert abs(sigma2 - variance(xyz.tolist())) < 1e-14

    results = []
    for confidence in (.95, .99):
        tail_probability = 1.0 - confidence
        z = normal.inv_cdf(tail_probability)
        # Problem 2(a): positive-loss VaR is minus the lower return quantile.
        var_return = -mu - sigma * z
        assert abs(var_return + NormalDist(mu, sigma).inv_cdf(tail_probability)) < 1e-14
        # Problem 2(b): positive-loss ES is minus the conditional tail mean.
        es_multiplier = normal.pdf(z) / tail_probability
        es_return = -mu + sigma * es_multiplier
        assert es_return > var_return > 0
        results.append(dict(confidence=confidence, tail_probability=tail_probability,
                            standard_normal_quantile=z, normal_es_multiplier=es_multiplier,
                            var_return=var_return, var_percent=100*var_return,
                            es_return=es_return, es_percent=100*es_return,
                            var_dollars=position_value*var_return,
                            es_dollars=position_value*es_return))

    # Numerical cross-check: simulate market and residual INDEPENDENTLY, then
    # rebuild stock returns. This checks the model construction and tail formulas.
    rng = np.random.default_rng(54502)
    nsim = 2_000_000
    simulated = (alpha + beta*rng.normal(spy_mean, np.sqrt(spy_variance), nsim)
                 + rng.normal(0, np.sqrt(residual_variance), nsim))
    mc_checks=[]
    for row in results:
        cutoff = float(np.quantile(simulated, row["tail_probability"]))
        mc_var = -cutoff
        mc_es = float(-simulated[simulated <= cutoff].mean())
        # Tolerances are on return units (0.00015 = 0.015 percentage point).
        assert abs(mc_var-row["var_return"]) < 0.00015
        assert abs(mc_es-row["es_return"]) < 0.00015
        mc_checks.append(dict(confidence=row["confidence"],var_percent=mc_var*100,es_percent=mc_es*100))

    # Record alternative variance conventions, without replacing the stated
    # sample-covariance estimator used for the primary answers.
    mle_sigma = float(np.sqrt(beta**2*np.var(spy,ddof=0)+np.mean(residuals**2)))
    regression_unbiased_sigma = float(np.sqrt(beta**2*spy_variance+(residuals@residuals)/(n-2)))
    result = dict(source=str(SOURCE),source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  price_observations=len(rows),return_observations=n,first_date=dates[0],last_date=dates[-1],
                  alpha=float(alpha),beta=float(beta),spy_mean=spy_mean,spy_variance=float(spy_variance),
                  spy_sd=float(np.sqrt(spy_variance)),residual_mean=float(residuals.mean()),
                  residual_variance=float(residual_variance),residual_sd=float(np.sqrt(residual_variance)),
                  market_residual_covariance=cross_covariance,stock_mean=mu,stock_variance=sigma2,
                  stock_sd=sigma,market_variance_contribution=float(beta**2*spy_variance),
                  shares=100,last_xyz_price=float(prices[-1,1]),position_value=position_value,
                  results=results,monte_carlo_draws=nsim,monte_carlo_checks=mc_checks,
                  alternative_conventions=dict(mle_sd=mle_sigma,regression_n_minus_2_sd=regression_unbiased_sigma))
    (HERE / "problem2_results.json").write_text(json.dumps(result,indent=2))
    with (HERE / "problem2_returns_and_residuals.csv").open("w",newline="") as stream:
        writer=csv.writer(stream);writer.writerow(["Date","SPY_return","XYZ_return","OLS_residual"])
        writer.writerows(zip(dates[1:],spy,xyz,residuals))
    with (HERE / "problem2_risk_results.csv").open("w",newline="") as stream:
        writer=csv.DictWriter(stream,fieldnames=list(results[0]));writer.writeheader();writer.writerows(results)
    print(json.dumps(result,indent=2))


if __name__ == "__main__":
    main()
