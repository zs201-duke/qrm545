#!/usr/bin/env python3
"""Reproducible analysis for QRM 545 Assignment 2.

Run ``python analysis.py prepare`` before writing predictions, then run
``python analysis.py fit``.  The split makes the prediction-before-fitting
requirement visible and auditable.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import optimize, stats

from qrm545 import (
    aicc,
    covariance_from_correlation,
    ew_weights,
    fit_student_t,
    gaussian_copula_log_contributions,
    historical_risk,
    kendall_correlation,
    moments,
    nearest_corr_higham,
    nearest_corr_spectral,
    normal_risk,
    portfolio_variance,
    simulate_gaussian_copula,
    simulate_t_copula,
    t_copula_log_contributions,
    t_tail_dependence,
)


ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
FIG = ROOT / "figures"
RESULTS = ROOT / "results"
for directory in (FIG, RESULTS):
    directory.mkdir(parents=True, exist_ok=True)

ALPHA = 0.05
NOTIONAL = 1_000_000.0
RNG_SEED = 5452026


def native(obj):
    """Convert numpy objects recursively so json.dump can serialize them."""
    if isinstance(obj, dict):
        return {str(k): native(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [native(v) for v in obj]
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, (np.floating, np.integer, np.bool_)):
        return obj.item()
    return obj


def dump_json(name: str, obj) -> None:
    with (RESULTS / name).open("w", encoding="utf-8") as handle:
        json.dump(native(obj), handle, indent=2, allow_nan=False)


def prepare_problem1() -> None:
    df = pd.read_csv(DATA / "problem1.csv")
    variables = [c for c in df.columns if c != "Day"]
    counts = df[variables].notna().astype(int).T @ df[variables].notna().astype(int)
    payload = {
        "row_count": len(df),
        "variables": variables,
        "nonmissing": df[variables].count().to_dict(),
        "pair_counts": counts.to_dict(),
        "complete_rows": int(df[variables].dropna().shape[0]),
    }
    dump_json("problem1_prepare.json", payload)


def fit_problem1() -> None:
    df = pd.read_csv(DATA / "problem1.csv")
    cols = [c for c in df.columns if c != "Day"]
    complete = df[cols].dropna()
    c_complete = complete.corr().to_numpy()
    c_pair = df[cols].corr().to_numpy()
    eig_complete = np.linalg.eigvalsh(c_complete)
    eig_pair = np.linalg.eigvalsh(c_pair)

    def chol_ok(a):
        try:
            np.linalg.cholesky(a)
            return True
        except np.linalg.LinAlgError:
            return False

    full_sd = df[cols].std(ddof=1).to_numpy()
    covariance_pair = covariance_from_correlation(c_pair, full_sd)
    weights = np.array([-0.4, -0.3, -0.2, -0.1, 1.0])
    rj = nearest_corr_spectral(c_pair)
    higham, higham_iterations = nearest_corr_higham(c_pair)
    changes = []
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            changes.append({
                "pair": f"{cols[i]}-{cols[j]}",
                "before": c_pair[i, j],
                "after": higham[i, j],
                "absolute_change": abs(higham[i, j] - c_pair[i, j]),
            })
    changes.sort(key=lambda row: row["absolute_change"], reverse=True)

    out = {
        "columns": cols,
        "complete_correlation": c_complete,
        "pairwise_correlation": c_pair,
        "complete_eigenvalues": eig_complete,
        "pairwise_eigenvalues": eig_pair,
        "complete_cholesky": chol_ok(c_complete),
        "pairwise_cholesky": chol_ok(c_pair),
        "full_history_sd": dict(zip(cols, full_sd)),
        "raw_pairwise_covariance": covariance_pair,
        "tracking_variance_raw": portfolio_variance(covariance_pair, weights),
        "rj_correlation": rj,
        "rj_min_eigenvalue": np.linalg.eigvalsh(rj).min(),
        "rj_frobenius_distance": np.linalg.norm(rj - c_pair, ord="fro"),
        "tracking_variance_rj": portfolio_variance(covariance_from_correlation(rj, full_sd), weights),
        "higham_correlation": higham,
        "higham_min_eigenvalue": np.linalg.eigvalsh(higham).min(),
        "higham_frobenius_distance": np.linalg.norm(higham - c_pair, ord="fro"),
        "tracking_variance_higham": portfolio_variance(covariance_from_correlation(higham, full_sd), weights),
        "higham_iterations": higham_iterations,
        "largest_higham_changes": changes[:6],
        "estimator_gap_frobenius": np.linalg.norm(c_complete - c_pair, ord="fro"),
    }
    dump_json("problem1_fit.json", out)


def prepare_problem2() -> None:
    df = pd.read_csv(DATA / "problem2.csv")
    prices = df["Price"].to_numpy()
    returns = prices[1:] / prices[:-1] - 1.0
    centered = returns - returns.mean()
    fig, ax = plt.subplots(figsize=(9.0, 3.8))
    ax.plot(np.arange(1, len(centered) + 1), centered * 100, lw=0.8, color="#174a7e")
    ax.axhline(0, color="black", lw=0.6)
    ax.set(xlabel="Return day", ylabel="Demeaned return (%)", title="Problem 2: arithmetic returns")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(FIG / "problem2_returns.png", dpi=180)
    plt.close(fig)
    payload = {"moments": moments(centered), "return_count": len(centered)}
    for lam in (0.97, 0.94):
        w = ew_weights(len(centered), lam)
        payload[f"lambda_{lam}"] = {
            "effective_sample_size": 1 / np.sum(w**2),
            "half_life": np.log(0.5) / np.log(lam),
            "recent_50_weight": np.sum(w[-50:]),
        }
    dump_json("problem2_prepare.json", payload)


def fit_problem2() -> None:
    df = pd.read_csv(DATA / "problem2.csv")
    returns = df["Price"].to_numpy()[1:] / df["Price"].to_numpy()[:-1] - 1
    x = returns - returns.mean()
    z = -stats.norm.ppf(ALPHA)
    estimates = {}
    for name, lam in (("EW_0.97", 0.97), ("EW_0.94", 0.94)):
        w = ew_weights(len(x), lam)
        sigma = np.sqrt(np.sum(w * x**2))
        neff = 1 / np.sum(w**2)
        var = z * sigma * NOTIONAL
        estimates[name] = {
            "sigma": sigma,
            "VaR": var,
            "neff": neff,
            "half_life": np.log(0.5) / np.log(lam),
            "recent_50_weight": np.sum(w[-50:]),
            "sigma_se": sigma / np.sqrt(2 * neff),
            "VaR_se": z * NOTIONAL * sigma / np.sqrt(2 * neff),
        }
    equal_sigma = np.std(x, ddof=1)
    estimates["Normal_equal"] = {"sigma": equal_sigma, "VaR": z * equal_sigma * NOTIONAL}
    tfit = fit_student_t(x)
    estimates["Student_t"] = {
        **tfit,
        "VaR": -stats.t.ppf(ALPHA, tfit["df"], loc=tfit["loc"], scale=tfit["scale"]) * NOTIONAL,
    }
    estimates["Historical"] = {"VaR": historical_risk(x * NOTIONAL, ALPHA)["VaR"]}
    recent_days = 50
    s_old = np.std(x[:-recent_days], ddof=1)
    s_new = np.std(x[-recent_days:], ddof=1)
    w_old = (len(x) - recent_days) / len(x)
    w_new = recent_days / len(x)
    mixture_excess = 3 * (w_old * s_old**4 + w_new * s_new**4) / (w_old * s_old**2 + w_new * s_new**2) ** 2 - 3
    gap = abs(estimates["EW_0.94"]["VaR"] - estimates["EW_0.97"]["VaR"])
    combined_se = math.hypot(estimates["EW_0.94"]["VaR_se"], estimates["EW_0.97"]["VaR_se"])
    out = {
        "estimates": estimates,
        "ranking_high_to_low": sorted(estimates, key=lambda k: estimates[k]["VaR"], reverse=True),
        "regime_recent_days": recent_days,
        "old_regime_sd": s_old,
        "new_regime_sd": s_new,
        "two_regime_normal_mixture_excess_kurtosis": mixture_excess,
        "ew_var_gap": gap,
        "ew_gap_over_combined_se": gap / combined_se,
    }
    dump_json("problem2_fit.json", out)


def prepare_problem3() -> None:
    df = pd.read_csv(DATA / "problem3.csv")
    a, b = df["A"].to_numpy(), df["B"].to_numpy()
    payload = {
        "A_moments": moments(a),
        "B_moments": moments(b),
        "A_below_minus_20pct": int(np.sum(a < -0.20)),
        "B_below_minus_20pct": int(np.sum(b < -0.20)),
        "at_least_one_below_minus_20pct": int(np.sum((a < -0.20) | (b < -0.20))),
        "both_below_minus_20pct": int(np.sum((a < -0.20) & (b < -0.20))),
    }
    dump_json("problem3_prepare.json", payload)
    fig, axes = plt.subplots(1, 2, figsize=(9.0, 3.6), sharey=True)
    choices = {"$2m in A": 2 * NOTIONAL * a, "$1m A + $1m B": NOTIONAL * (a + b)}
    for ax, (label, pnl) in zip(axes, choices.items()):
        ax.hist(pnl / 1000, bins=60, color="#2a7f62", alpha=0.85)
        ax.set_title(label)
        ax.set_xlabel("One-year P&L ($000)")
        ax.set_yscale("log")
        ax.grid(alpha=0.2)
    axes[0].set_ylabel("Scenario count (log scale)")
    fig.suptitle("Problem 3: payoff distributions")
    fig.tight_layout()
    fig.savefig(FIG / "problem3_pnl.png", dpi=180)
    plt.close(fig)


def fit_problem3() -> None:
    df = pd.read_csv(DATA / "problem3.csv")
    a, b = df["A"].to_numpy(), df["B"].to_numpy()
    positions = {
        "$1m A": NOTIONAL * a,
        "$1m B": NOTIONAL * b,
        "$2m A": 2 * NOTIONAL * a,
        "$1m A + $1m B": NOTIONAL * (a + b),
    }
    out = {"alpha_5pct": {}, "alpha_1pct": {}}
    for label, pnl in positions.items():
        out["alpha_5pct"][label] = {
            "historical": historical_risk(pnl, 0.05),
            "normal": normal_risk(pnl, 0.05),
        }
        out["alpha_1pct"][label] = {
            "historical": historical_risk(pnl, 0.01),
            "normal": normal_risk(pnl, 0.01),
        }
    for level, alpha in (("alpha_5pct", 0.05), ("alpha_1pct", 0.01)):
        va = out[level]["$1m A"]["historical"]
        vb = out[level]["$1m B"]["historical"]
        vab = out[level]["$1m A + $1m B"]["historical"]
        out[level]["subadditivity"] = {
            "VaR_A_plus_VaR_B_minus_VaR_AB": va["VaR"] + vb["VaR"] - vab["VaR"],
            "ES_A_plus_ES_B_minus_ES_AB": va["ES"] + vb["ES"] - vab["ES"],
        }
    dump_json("problem3_fit.json", out)


def prepare_problem4() -> None:
    df = pd.read_csv(DATA / "problem4.csv")
    cols = ["X1", "X2", "X3"]
    x = df[cols].to_numpy()
    full = {c: moments(df[c].to_numpy()) for c in cols}
    leave_one_out = {}
    for j, c in enumerate(cols):
        idx = int(np.argmax(np.abs((x[:, j] - x[:, j].mean()) / x[:, j].std(ddof=1))))
        leave_one_out[c] = {"removed_row": idx + 1, "removed_value": x[idx, j], "moments_without": moments(np.delete(x[:, j], idx))}
    u_rank = np.column_stack([stats.rankdata(x[:, j], method="average") / (len(x) + 1) for j in range(3)])
    pairs = []
    for i in range(3):
        for j in range(i + 1, 3):
            pairs.append({
                "pair": f"{cols[i]}-{cols[j]}",
                "lower_joint_count": int(np.sum((u_rank[:, i] <= 0.025) & (u_rank[:, j] <= 0.025))),
                "upper_joint_count": int(np.sum((u_rank[:, i] >= 0.975) & (u_rank[:, j] >= 0.975))),
                "independence_expected": len(x) * 0.025**2,
            })
    payload = {"moments": full, "single_observation_check": leave_one_out, "rank_tail_counts": pairs}
    dump_json("problem4_prepare.json", payload)

    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.3))
    for ax, (i, j) in zip(axes, ((0, 1), (0, 2), (1, 2))):
        ax.scatter(u_rank[:, i], u_rank[:, j], s=9, alpha=0.45, color="#6a3d9a", edgecolors="none")
        ax.axvline(0.025, color="grey", ls="--", lw=0.7)
        ax.axhline(0.025, color="grey", ls="--", lw=0.7)
        ax.axvline(0.975, color="grey", ls="--", lw=0.7)
        ax.axhline(0.975, color="grey", ls="--", lw=0.7)
        ax.set(xlabel=f"rank U({cols[i]})", ylabel=f"rank U({cols[j]})")
        ax.grid(alpha=0.15)
    fig.suptitle("Problem 4: rank-transformed pairs")
    fig.tight_layout()
    fig.savefig(FIG / "problem4_rank_pairs.png", dpi=180)
    plt.close(fig)


def fit_problem4() -> None:
    df_data = pd.read_csv(DATA / "problem4.csv")
    cols = ["X1", "X2", "X3"]
    x = df_data[cols].to_numpy()
    n, d = x.shape
    margin_fits = {}
    u = np.empty_like(x)
    selected = {}
    for j, col in enumerate(cols):
        series = x[:, j]
        mu = np.mean(series)
        sigma = np.sqrt(np.mean((series - mu) ** 2))
        ll_normal = np.sum(stats.norm.logpdf(series, loc=mu, scale=sigma))
        normal = {"loc": mu, "scale": sigma, "loglik": ll_normal, "AICc": aicc(ll_normal, 2, n)}
        tfit = fit_student_t(series)
        student = {**tfit, "AICc": aicc(tfit["loglik"], 3, n)}
        choice = "t" if student["AICc"] < normal["AICc"] else "normal"
        margin_fits[col] = {"normal": normal, "t": student, "selected": choice, "AICc_difference_t_minus_normal": student["AICc"] - normal["AICc"]}
        selected[col] = choice
        if choice == "t":
            u[:, j] = stats.t.cdf(series, student["df"], loc=student["loc"], scale=student["scale"])
        else:
            u[:, j] = stats.norm.cdf(series, loc=normal["loc"], scale=normal["scale"])
    u = np.clip(u, 1e-10, 1 - 1e-10)
    tau, corr = kendall_correlation(x)
    if np.linalg.eigvalsh(corr).min() < -1e-12:
        corr = nearest_corr_higham(corr)[0]

    gc = gaussian_copula_log_contributions(u, corr)
    objective = lambda nu: -np.sum(t_copula_log_contributions(u, corr, float(nu)))
    opt = optimize.minimize_scalar(objective, bounds=(2.01, 100.0), method="bounded", options={"xatol": 1e-8})
    t_df = float(opt.x)
    tc = t_copula_log_contributions(u, corr, t_df)
    ll_g, ll_t = np.sum(gc), np.sum(tc)
    copula_fit = {
        "kendall_tau": tau,
        "correlation_from_tau": corr,
        "min_correlation_eigenvalue": np.linalg.eigvalsh(corr).min(),
        "gaussian": {"loglik": ll_g, "AICc": aicc(ll_g, 0, n), "BIC": -2 * ll_g},
        "t": {"df": t_df, "loglik": ll_t, "AICc": aicc(ll_t, 1, n), "BIC": -2 * ll_t + np.log(n)},
    }

    rng = np.random.default_rng(RNG_SEED)
    sims = 100_000
    u_g = simulate_gaussian_copula(corr, sims, rng)
    u_t = simulate_t_copula(corr, t_df, sims, rng)

    def inverse_margins(u_sim):
        out = np.empty_like(u_sim)
        for j, col in enumerate(cols):
            fit = margin_fits[col][selected[col]]
            if selected[col] == "t":
                out[:, j] = stats.t.ppf(u_sim[:, j], fit["df"], loc=fit["loc"], scale=fit["scale"])
            else:
                out[:, j] = stats.norm.ppf(u_sim[:, j], loc=fit["loc"], scale=fit["scale"])
        return out

    sim_g = inverse_margins(u_g)
    sim_t = inverse_margins(u_t)
    risk = {"historical": {}, "gaussian_copula": {}, "t_copula": {}}
    for alpha in (0.05, 0.01):
        key = f"alpha_{int(alpha * 100)}pct"
        risk["historical"][key] = historical_risk(NOTIONAL * x.sum(axis=1), alpha)
        risk["gaussian_copula"][key] = historical_risk(NOTIONAL * sim_g.sum(axis=1), alpha)
        risk["t_copula"][key] = historical_risk(NOTIONAL * sim_t.sum(axis=1), alpha)

    pair_tail = {"gaussian": [], "t": []}
    for i in range(d):
        for j in range(i + 1, d):
            for label, uu in (("gaussian", u_g), ("t", u_t)):
                pair_tail[label].append({
                    "pair": f"{cols[i]}-{cols[j]}",
                    "lower_per_1000": 1000 * np.mean((uu[:, i] <= 0.025) & (uu[:, j] <= 0.025)),
                    "upper_per_1000": 1000 * np.mean((uu[:, i] >= 0.975) & (uu[:, j] >= 0.975)),
                })
    ll_diff = tc - gc
    central = np.all((u > 0.05) & (u < 0.95), axis=1)
    rho_pairs = []
    for i in range(d):
        for j in range(i + 1, d):
            rho = corr[i, j]
            lambda_t = t_tail_dependence(rho, t_df)
            rho_pairs.append({"pair": f"{cols[i]}-{cols[j]}", "rho": rho, "t_tail_dependence": lambda_t, "gaussian_tail_dependence": 0.0})
    out = {
        "margin_fits": margin_fits,
        "selected_margins": selected,
        "copula_fit": copula_fit,
        "risk": risk,
        "simulated_joint_tail_counts_per_1000": pair_tail,
        "loglik_difference_per_day_mean": np.mean(ll_diff),
        "central_day_count": int(np.sum(central)),
        "fraction_loglik_advantage_from_central_days": np.sum(ll_diff[central]) / np.sum(ll_diff),
        "tail_dependence": rho_pairs,
        "simulation_count": sims,
    }
    dump_json("problem4_fit.json", out)


def prepare_problem5() -> None:
    dump_json("problem5_prepare.json", {
        "theory": "For positive residual covariance, the covariance term is +2 Cov(eA,eB) in P1 variance and -2 Cov(eA,eB) in P2 variance."
    })


def fit_problem5() -> None:
    df = pd.read_csv(DATA / "problem5.csv")
    prices = df[["MKT", "A", "B"]].to_numpy()
    r = prices[1:] / prices[:-1] - 1
    mkt, a, b = r[:, 0], r[:, 1], r[:, 2]
    design = np.column_stack([np.ones(len(mkt)), mkt])
    coef_a = np.linalg.lstsq(design, a, rcond=None)[0]
    coef_b = np.linalg.lstsq(design, b, rcond=None)[0]
    eps = np.column_stack([a - design @ coef_a, b - design @ coef_b])
    residual_cov = np.cov(eps, rowvar=False, ddof=1)
    residual_corr = np.corrcoef(eps, rowvar=False)
    mkt_var = np.var(mkt, ddof=1)
    betas = np.array([coef_a[1], coef_b[1]])
    implied_full = np.outer(betas, betas) * mkt_var + residual_cov
    implied_independent = np.outer(betas, betas) * mkt_var + np.diag(np.diag(residual_cov))
    sample_cov = np.cov(np.column_stack([a, b]), rowvar=False, ddof=1)

    rng = np.random.default_rng(RNG_SEED + 5)
    nsim = 100_000
    market_draw = rng.normal(0, np.sqrt(mkt_var), size=nsim)
    standard_errors = rng.normal(size=(nsim, 2))
    full_errors = standard_errors @ np.linalg.cholesky(residual_cov).T
    independent_errors = standard_errors * np.sqrt(np.diag(residual_cov))
    sim_full = market_draw[:, None] * betas + full_errors
    sim_ind = market_draw[:, None] * betas + independent_errors
    portfolios = {"P1_long_A_long_B": np.array([NOTIONAL, NOTIONAL]), "P2_long_A_short_B": np.array([NOTIONAL, -NOTIONAL])}
    risks = {}
    z = -stats.norm.ppf(ALPHA)
    for label, w in portfolios.items():
        full_pnl = sim_full @ w
        ind_pnl = sim_ind @ w
        delta_var = z * np.sqrt(w @ sample_cov @ w)
        risks[label] = {
            "full_residual_simulation_VaR": historical_risk(full_pnl, ALPHA)["VaR"],
            "zero_residual_correlation_simulation_VaR": historical_risk(ind_pnl, ALPHA)["VaR"],
            "delta_normal_VaR": delta_var,
            "full_minus_zero": historical_risk(full_pnl, ALPHA)["VaR"] - historical_risk(ind_pnl, ALPHA)["VaR"],
            "full_minus_delta": historical_risk(full_pnl, ALPHA)["VaR"] - delta_var,
        }
    out = {
        "regression": {
            "A": {"alpha": coef_a[0], "beta": coef_a[1], "residual_sd": np.std(eps[:, 0], ddof=1)},
            "B": {"alpha": coef_b[0], "beta": coef_b[1], "residual_sd": np.std(eps[:, 1], ddof=1)},
        },
        "residual_correlation": residual_corr[0, 1],
        "residual_covariance": residual_cov,
        "market_sd": np.sqrt(mkt_var),
        "sample_stock_covariance": sample_cov,
        "implied_full_covariance": implied_full,
        "implied_zero_residual_corr_covariance": implied_independent,
        "max_abs_sample_minus_implied_full": np.max(np.abs(sample_cov - implied_full)),
        "risk": risks,
        "simulation_count": nsim,
    }
    dump_json("problem5_fit.json", out)


def prepare() -> None:
    prepare_problem1()
    prepare_problem2()
    prepare_problem3()
    prepare_problem4()
    prepare_problem5()
    print("Preparation complete. Review figures/results and write predictions before fitting.")


def fit() -> None:
    prediction_file = ROOT / "predictions.md"
    if not prediction_file.exists():
        raise SystemExit("predictions.md must exist before the fitting stage.")
    fit_problem1()
    fit_problem2()
    fit_problem3()
    fit_problem4()
    fit_problem5()
    print("All fits and simulations complete.")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "fit"}:
        raise SystemExit("Usage: python analysis.py {prepare|fit}")
    prepare() if sys.argv[1] == "prepare" else fit()
