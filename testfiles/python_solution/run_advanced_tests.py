"""Compute Tests 8.1–13.9 and validate against the provided course outputs."""
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import scipy
from scipy import stats

from risk_tools import fit_normal, fit_t
from advanced_risk import (
    aggregate_risk, american_greeks, american_option, copula_information_criteria,
    distribution_risk, empirical_risk, expost_attribution, fit_multivariate_t,
    gaussian_copula_loglike, gbsm, kendall_correlation, maximum_sharpe,
    profile_nu, risk_parity, simulate_copula, t_copula_loglike, tail_dependence_t,
)

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUTPUT = HERE / "results"


def read(name):
    return pd.read_csv(DATA / name)


def fitted_t(values):
    p, diagnostics = fit_t(np.asarray(values))
    return stats.t(p["nu"], loc=p["mu"], scale=p["sigma"]), p, diagnostics


def risk_standard_errors(values, centered=False, distribution=None, alpha=.05):
    """Asymptotic VaR/ES errors from influence functions; no fixture calibration."""
    x = np.asarray(values, float)
    var, _ = empirical_risk(x, alpha)
    q = -var
    # Exact fitted marginal density where known; KDE for aggregate portfolio P&L.
    density = distribution.pdf(q) if distribution is not None else stats.gaussian_kde(x)([q])[0]
    var_if = ((x <= q).astype(float) - alpha) / density
    tail = np.minimum(x - q, 0)
    es_if = -(tail - tail.mean()) / alpha
    if centered:
        var_if += x - x.mean()
        es_if += x - x.mean()
    return np.std(np.column_stack([var_if, es_if]), axis=0, ddof=1) / np.sqrt(len(x))


def portfolio_standard_errors(returns, values, distributions):
    pnl = returns * values
    rows = []
    for j in range(pnl.shape[1]+1):
        observations = pnl[:, j] if j < pnl.shape[1] else pnl.sum(axis=1)
        value = values[j] if j < pnl.shape[1] else values.sum()
        # Dollar-density wrapper for the fitted return marginal.
        if j < len(distributions):
            class ScaledDensity:
                def pdf(self, q):
                    return distributions[j].pdf(q/value)/value
            density = ScaledDensity()
        else:
            density = None
        se = risk_standard_errors(observations, distribution=density)
        rows.append([*se, *(se/value)])
    return np.array(rows)


def main():
    OUTPUT.mkdir(exist_ok=True)
    sources = [HERE.parent / "Tests.xlsx", *sorted(DATA.glob("*.csv"))]
    hashes = {str(p.relative_to(HERE.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    results, simulation_se, diagnostic = {}, {}, {}
    normal_parameters = fit_normal(read("test7_1.csv").iloc[:, 0].to_numpy())
    normal = stats.norm(loc=normal_parameters["mu"], scale=normal_parameters["sigma"])
    tdist, tparameters, _ = fitted_t(read("test7_2.csv").iloc[:, 0])
    for test, distribution, metric in [("8.1", normal, "VaR"), ("8.2", tdist, "VaR"),
                                         ("8.4", normal, "ES"), ("8.5", tdist, "ES")]:
        index = 0 if metric == "VaR" else 1
        absolute = distribution_risk(distribution)[index]
        results[test] = pd.DataFrame([{f"{metric} Absolute": absolute,
                                      f"{metric} Diff from Mean": absolute + distribution.mean()}])
    diagnostic["univariate_t_parameters"] = tparameters
    for test, metric, seed in [("8.3", "VaR", 8), ("8.6", "ES", 86)]:
        x = tdist.ppf(np.random.default_rng(seed).random(10_000))
        index = 0 if metric == "VaR" else 1
        absolute = empirical_risk(x)[index]
        results[test] = pd.DataFrame([{f"{metric} Absolute": absolute,
                                      f"{metric} Diff from Mean": absolute + x.mean()}])
        simulation_se[test] = np.array([[risk_standard_errors(x, distribution=tdist)[index],
                                        risk_standard_errors(x, centered=True, distribution=tdist)[index]]])
        analytic = np.array([distribution_risk(tdist)[index], distribution_risk(tdist)[index]+tdist.mean()])
        z = np.abs(results[test].to_numpy()[0] - analytic) / simulation_se[test][0]
        diagnostic[test] = {"sample_size": len(x), "seed": seed, "analytic_max_z": float(z.max())}
        assert z.max() < 6

    print("Computed 8.1–8.6: analytic and simulated VaR/ES.", flush=True)
    returns = read("test9_1_returns.csv")
    portfolio = read("test9_1_portfolio.csv")
    names = portfolio.Stock.tolist()
    distributions = []
    for row in portfolio.itertuples(index=False, name=None):
        name, _, _, family = row
        if family == "Normal":
            p = fit_normal(returns[name].to_numpy())
            distribution = stats.norm(loc=p["mu"], scale=p["sigma"])
        elif family == "T":
            distribution, _, _ = fitted_t(returns[name])
        else:
            raise ValueError(f"Unknown margin family: {family}")
        distributions.append(distribution)
    uniforms = np.column_stack([d.cdf(returns[name]) for name, d in zip(names, distributions)])
    # Test 9.1 explicitly uses Spearman correlation directly, unlike Test 13.
    ranks = np.apply_along_axis(stats.rankdata, 0, uniforms)
    correlation = np.corrcoef(ranks, rowvar=False)
    sim_u = simulate_copula(correlation, 100_000, seed=1234)
    simulated_returns = np.column_stack([d.ppf(sim_u[:, j]) for j, d in enumerate(distributions)])
    values = (portfolio.Holding * portfolio["Starting Price"]).to_numpy()
    results["9.1"] = aggregate_risk(simulated_returns, names, values)
    simulation_se["9.1"] = portfolio_standard_errors(simulated_returns, values, distributions)
    diagnostic["9.1"] = {"sample_size": 100_000, "seed": 1234,
                          "correlation": correlation.tolist(), "current_values": values.tolist()}

    cov = read("test5_2.csv").to_numpy()
    for test, budget in [("10.1", np.ones(5)), ("10.2", np.array([1., 1., 1., 1., .5]))]:
        weights = risk_parity(cov, budget)
        results[test] = pd.DataFrame({"W": weights})
        shares = weights * (cov @ weights) / (weights @ cov @ weights)
        diagnostic[test] = {"risk_shares": shares.tolist(), "budget": (budget / budget.sum()).tolist()}
    means = read("test10_3_means.csv").Mean.to_numpy()
    for test, lower, upper in [("10.3", 0., 1.), ("10.4", .1, .5)]:
        weights = maximum_sharpe(cov, means, .04, lower, upper)
        results[test] = pd.DataFrame({"W": weights})
        assert abs(weights.sum()-1) < 1e-10 and np.all(weights >= lower-1e-10) and np.all(weights <= upper+1e-10)
        # Record the source mismatch rather than silently using the wrong input.
        alternate = maximum_sharpe(read("test5_3.csv").to_numpy(), means, .04, lower, upper)
        diagnostic[test] = {"input": "test5_2.csv (specified by Tests.xlsx)",
                            "reference_generator_input": "test5_3.csv",
                            "alternate_input_weights": alternate.tolist(),
                            "alternate_weight_max_difference": float(np.max(abs(weights-alternate))),
                            "sharpe": float((weights@means-.04)/np.sqrt(weights@cov@weights))}

    returns = read("test11_1_returns.csv")
    results["11.1"] = expost_attribution(read("test11_1_weights.csv").W, returns, returns,
                                         np.eye(returns.shape[1]), include_alpha=False)
    results["11.2"] = expost_attribution(read("test11_2_weights.csv").W,
                                         read("test11_2_stock_returns.csv"), read("test11_2_factor_returns.csv"),
                                         read("test11_2_beta.csv").iloc[:, 1:].to_numpy())
    print("Computed 9.1–11.2: copula portfolio risk, optimal weights, attribution.", flush=True)

    options = read("test12_1.csv").dropna(subset=["ID"])
    european, american = [], []
    for _, row in options.iterrows():
        parameters = (row["Option Type"] == "Call", row.Underlying, row.Strike,
                      row.DaysToMaturity/row.DayPerYear, row.RiskFreeRate,
                      row.RiskFreeRate-row.DividendRate, row.ImpliedVol)
        e, a = gbsm(*parameters), american_greeks(*parameters)
        european.append({"ID": int(row.ID), **e})
        american.append({"ID": int(row.ID), **a})
        # The CRR approximation may be slightly below the analytic European price.
        assert a["Value"] >= e["Value"] - .01
    results["12.1"], results["12.2"] = pd.DataFrame(european), pd.DataFrame(american)
    discrete = []
    print("Computed 12.1–12.2; pricing the discrete-dividend trees.", flush=True)
    for _, row in read("test12_3.csv").dropna(subset=["ID"]).iterrows():
        value = american_option(row["Option Type"] == "Call", row.Underlying, row.Strike,
                                row.DaysToMaturity/row.DayPerYear, row.RiskFreeRate,
                                row.RiskFreeRate, row.ImpliedVol, steps=int(row.DaysToMaturity*2),
                                dividends=[float(x) for x in str(row.DividendAmts).split(",")],
                                dividend_steps=[int(x)*2 for x in str(row.DividendDates).split(",")])
        discrete.append({"ID": int(row.ID), "Value": value})
    results["12.3"] = pd.DataFrame(discrete)

    returns = read("test13_returns.csv")
    x = returns.to_numpy()
    r = kendall_correlation(x)
    results["13.1"] = pd.DataFrame(r, columns=[f"x{i+1}" for i in range(x.shape[1])])
    mu, scale, nu, ll = fit_multivariate_t(x)
    results["13.2"] = pd.DataFrame({"mu": mu})
    results["13.3"] = pd.DataFrame(scale, columns=results["13.1"].columns)
    results["13.4"] = pd.DataFrame([{"nu": nu, "ll": ll}])
    np.testing.assert_allclose(np.diag(scale)*nu/(nu-2), x.var(axis=0, ddof=1))
    distributions, parameters, fitting = [], [], []
    for column in returns:
        distribution, p, info = fitted_t(returns[column])
        distributions.append(distribution)
        parameters.append(p)
        fitting.append(info)
    u = np.column_stack([d.cdf(x[:, j]) for j, d in enumerate(distributions)])
    rc = kendall_correlation(u)
    np.testing.assert_allclose(rc, r, atol=1e-12)
    ll_g = gaussian_copula_loglike(u, rc)
    nu_c, ll_t = profile_nu(lambda nu: t_copula_loglike(u, rc, nu))
    results["13.5"] = pd.DataFrame([{"ll": ll_g}])
    results["13.6"] = pd.DataFrame([{"nu": nu_c, "ll": ll_t}])
    rows = []
    for name, likelihood, k in [("Gaussian", ll_g, 0), ("T", ll_t, 1)]:
        aicc, bic = copula_information_criteria(likelihood, k, len(x))
        rows.append([name, likelihood, k, aicc, bic])
    results["13.7"] = pd.DataFrame(rows, columns=["Copula", "LL", "K", "AICC", "BIC"])
    results["13.8"] = pd.DataFrame(
        [[i+1, j+1, rc[i, j], tail_dependence_t(rc[i, j], nu_c)]
         for i in range(x.shape[1]) for j in range(i+1, x.shape[1])], columns=["I", "J", "Rho", "Lambda"])
    portfolio = read("test13_portfolio.csv")
    assert portfolio.Stock.tolist() == returns.columns.tolist()
    sim_u = simulate_copula(rc, 100_000, seed=13, nu=nu_c)
    simulated_returns = np.column_stack([d.ppf(sim_u[:, j]) for j, d in enumerate(distributions)])
    values = portfolio.currentValue.to_numpy()
    results["13.9"] = aggregate_risk(simulated_returns, portfolio.Stock.tolist(), values)
    simulation_se["13.9"] = portfolio_standard_errors(simulated_returns, values, distributions)
    diagnostic["13"] = {"margin_parameters": parameters, "margin_fit_diagnostics": fitting,
                         "multivariate_nu": nu, "copula_nu": nu_c, "sample_size": 100_000, "seed": 13,
                         "AICc_choice": results["13.7"].loc[results["13.7"].AICC.idxmin(), "Copula"],
                         "BIC_choice": results["13.7"].loc[results["13.7"].BIC.idxmin(), "Copula"]}
    print("Computed 12.3–13.9; comparing all 25 outputs with course references.", flush=True)

    checks = []
    for test in sorted(results, key=lambda s: tuple(map(int, s.split(".")))):
        actual = results[test]
        name = f"testout{test.replace('.', '_')}.csv"
        actual.to_csv(OUTPUT/name, index=False, float_format="%.17g")
        expected = read(name)
        assert actual.shape == expected.shape and list(actual.columns) == list(expected.columns)
        for column in expected.select_dtypes(exclude="number"):
            assert actual[column].equals(expected[column]), f"Label mismatch in {test}:{column}"
        for identifier in ("ID", "I", "J", "K"):
            if identifier in expected:
                np.testing.assert_array_equal(actual[identifier], expected[identifier])
        a, b = actual.select_dtypes("number").to_numpy(), expected.select_dtypes("number").to_numpy()
        assert np.isfinite(a).all()
        row = {"test": test, "output": name, "max_abs_reference_error": float(abs(a-b).max())}
        if test in simulation_se:
            se = simulation_se[test]
            z = abs(a-b)/(np.sqrt(2)*se)
            passed = bool((z < 6).all())
            row.update(check="Monte Carlo: 6 combined asymptotic SE", max_reference_z=float(z.max()))
            diagnostic[test] = {**diagnostic.get(test, {}), "standard_errors": se.tolist()}
        else:
            rtol, atol = 1e-8, 1e-8
            if test.startswith("10."):
                rtol, atol = 1e-5, 5e-7  # Julia's constrained optimum has tiny negative weights.
            elif test == "12.2":
                rtol, atol = 1e-5, 5e-6  # Numerical differentiation of a finite tree.
            elif test in {"13.5", "13.6", "13.7", "13.8"}:
                rtol, atol = 1e-7, 1e-6  # Margin MLE and inverse-CDF engine differences.
            passed = np.allclose(a, b, rtol=rtol, atol=atol)
            row["check"] = f"allclose: rtol={rtol:g}, atol={atol:g}"
        row["status"] = "PASS" if passed else "FAIL"
        checks.append(row)
    summary = pd.DataFrame(checks)
    summary.to_csv(OUTPUT/"advanced_validation_summary.csv", index=False)
    diagnostic.update(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                      pandas=pd.__version__, source_sha256=hashes, checks=checks)
    (OUTPUT/"advanced_diagnostics.json").write_text(json.dumps(diagnostic, indent=2), encoding="utf-8")
    for p in sources:
        assert hashlib.sha256(p.read_bytes()).hexdigest() == hashes[str(p.relative_to(HERE.parent))]
    print(summary[["test", "status", "max_abs_reference_error"]].to_string(index=False))
    print(f"\n{sum(summary.status == 'PASS')}/{len(summary)} advanced tests passed. Results: {OUTPUT}")
    if len(summary) != 25 or not (summary.status == "PASS").all():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
