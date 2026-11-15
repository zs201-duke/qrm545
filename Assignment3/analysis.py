"""Reproduce Assignment 3 in two chronological stages: prepare, then fit.

Run from any directory. Input files are copied unchanged into data/. Outputs
are relative to this script. See README.md for commands and conventions.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(ROOT/".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import stats
from scipy.optimize import brentq, minimize

from options import gbsm, greeks, implied_vol, crr_all, crr_american
from risklib import moments, ols, risk, normal_risk, fit_distributions, tangency, efficient_weights

plt.rcParams.update({"figure.dpi": 150, "savefig.dpi": 180, "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False,
                     "axes.grid": True, "grid.alpha": .2})
COLORS = ["#146C94", "#D66B30", "#5D9463", "#925A9B"]
ASSETS = ["EQ", "BOND", "STK", "PUTW"]
FACTORS = ["Mkt-RF", "SMB", "HML", "Mom"]


def save_json(name, obj):
    def convert(x):
        if isinstance(x, np.ndarray): return x.tolist()
        if isinstance(x, np.generic): return x.item()
        if isinstance(x, (pd.Timestamp, datetime)): return x.isoformat()
        raise TypeError(type(x))
    (ROOT/"results"/name).write_text(json.dumps(obj, indent=2, default=convert,
                                               allow_nan=False)+"\n")


def data(name):
    return pd.read_csv(ROOT/"data"/name)


def factor_data():
    """These provided factor CSVs have headers and daily rows, no French preamble."""
    ff = data("F-F_Research_Data_Factors_daily.CSV")
    mom = data("F-F_Momentum_Factor_daily.CSV")
    for frame in (ff, mom):
        frame.columns = frame.columns.str.strip()
        frame["Date"] = pd.to_datetime(frame["Date"].astype(str), format="%Y%m%d")
        for c in frame.columns.drop("Date"):
            if (frame[c] <= -99).any():
                raise ValueError("Missing-value sentinel must be handled explicitly")
            frame[c] /= 100.
        if frame["Date"].duplicated().any(): raise ValueError("Duplicate factor date")
    factors = ff.merge(mom, on="Date", how="inner", validate="one_to_one")
    funds = data("problem5.csv")
    funds["Date"] = pd.to_datetime(funds["Date"])
    joined = funds.merge(factors, on="Date", how="inner", validate="one_to_one")
    if len(joined) != len(funds): raise ValueError("Unmatched fund dates")
    return factors, joined


def books_at_spot():
    prices = data("problem3.csv")
    spot = float(prices.ABC.iloc[-1])
    books = data("problem3_portfolios.csv")
    summary = {}
    for name, book in books.groupby("Portfolio", sort=False):
        totals = dict(value=0., delta=0., gamma=0., theta=0.)
        for row in book.itertuples():
            if row.Type == "Stock":
                value, g = spot, dict(delta=1., gamma=0., theta=0.)
            else:
                T = row.DaysToExpiry/255
                value = float(gbsm(row.Type, spot, row.Strike, T, .0425, .0425, row.ImpliedVol))
                g = greeks(row.Type, spot, row.Strike, T, .0425, .0425, row.ImpliedVol)
            totals["value"] += row.Holding*value
            for k in ("delta", "gamma", "theta"): totals[k] += row.Holding*g[k]
        summary[name] = totals
    return spot, prices, books, summary


def prepare():
    """Only diagnostics explicitly permitted BEFORE fitting/optimization/simulation."""
    chain = data("problem1.csv")
    chain["Mid"] = (chain.Bid+chain.Ask)/2
    T = (pd.Timestamp("2026-12-18")-pd.Timestamp("2026-11-13")).days/365
    parity = []
    for strike, group in chain.groupby("Strike"):
        c = group[group.Type == "Call"].iloc[0]
        p = group[group.Type == "Put"].iloc[0]
        forward = 182.4*np.exp(-.006*T)-strike*np.exp(-.0425*T)
        gap = float(c.Mid-p.Mid-forward)
        band = float(c.Ask-c.Bid+p.Ask-p.Bid)
        parity.append(dict(strike=float(strike), call_mid=float(c.Mid), put_mid=float(p.Mid),
                           gap=gap, band=band, flag=bool(abs(gap)>band)))
    pd.DataFrame(parity).to_csv(ROOT/"results/p1_parity_prefit.csv", index=False)
    spot, prices, books, book_greeks = books_at_spot()
    returns = prices.ABC.pct_change().dropna().to_numpy()
    p4 = data("problem4.csv")
    rf = .03/12  # Stated convention: nominal annual rate / 12.
    p4stats = {}
    for asset in ASSETS:
        x = p4[asset].to_numpy()
        m = moments(x)
        extreme = int(np.argmax(abs(x-x.mean())))
        without = np.delete(x, extreme)
        m.update(sharpe=float(np.sqrt(12)*(x.mean()-rf)/x.std(ddof=1)),
                 se_mean=float(x.std(ddof=1)/np.sqrt(len(x))),
                 extreme_month=str(p4.Month.iloc[extreme]), extreme_return=float(x[extreme]),
                 extreme_variance_share=float((x[extreme]-x.mean())**2/np.sum((x-x.mean())**2)),
                 without_extreme=moments(without),
                 sharpe_without_extreme=float(np.sqrt(12)*(without.mean()-rf)/without.std(ddof=1)))
        p4stats[asset] = m
    factors, joined = factor_data()
    fundstats = {}
    for fund in ("FUND1", "FUND2"):
        y = joined[fund]-joined.RF
        capm = ols(y, joined[["Mkt-RF"]], ["Mkt-RF"])
        fundstats[fund] = dict(moments=moments(joined[fund]), excess_moments=moments(y),
            annual_sharpe=float(np.sqrt(255)*y.mean()/y.std(ddof=1)), capm=capm,
            residual_correlations={f: float(np.corrcoef(capm["residuals"], joined[f])[0, 1])
                                   for f in FACTORS[1:]})
    # Diagnostic plots are saved before the later model fits are run.
    fig, ax = plt.subplots(2, 2, figsize=(10, 6.5))
    ax[0, 0].plot(prices.Date, prices.ABC, color=COLORS[0]); ax[0, 0].set_title("ABC price history")
    ax[0, 0].set_xticks([]); ax[0, 0].set_ylabel("Price ($)")
    ax[0, 1].hist(returns*100, bins=45, color=COLORS[0]); ax[0, 1].set_title("ABC daily arithmetic returns")
    ax[0, 1].set_xlabel("Return (%)")
    ax[1, 0].plot(pd.to_datetime(p4.Month), p4.PUTW*100, color=COLORS[1]); ax[1, 0].set_title("PUTW monthly returns")
    ax[1, 0].set_ylabel("Return (%)")
    for i, fund in enumerate(("FUND1", "FUND2")):
        ax[1, 1].plot(joined.Date, (1+joined[fund]).cumprod(), label=fund, color=COLORS[i])
    ax[1, 1].set_title("Fund cumulative growth"); ax[1, 1].legend()
    fig.tight_layout(); fig.savefig(ROOT/"figures/prefit_diagnostics.png"); plt.close(fig)
    sources = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted((ROOT/"data").glob("*"))}
    out = dict(prepared_at_utc=datetime.now(timezone.utc).isoformat(), source_sha256=sources,
               p1=dict(T=T, parity=parity),
               p2=dict(thresholds=[50*(1-np.exp(-.045*(.5-t))) for t in (.1, .4)]),
               p3=dict(spot=spot, date=prices.Date.iloc[-1], greeks=book_greeks, moments=moments(returns)),
               p4=p4stats, p5=dict(start=joined.Date.min(), end=joined.Date.max(), n=len(joined), funds=fundstats))
    save_json("prefit.json", out)
    print(json.dumps(out, indent=2, default=str))


def fit_p1():
    chain = data("problem1.csv")
    chain["Mid"] = (chain.Bid+chain.Ask)/2
    T = 35/365
    rows = []
    for row in chain.itertuples():
        out = dict(type=row.Type, strike=row.Strike, bid=row.Bid, mid=row.Mid, ask=row.Ask)
        for label, price in (("bid", row.Bid), ("mid", row.Mid), ("ask", row.Ask)):
            iv, status = implied_vol(row.Type, price, 182.4, row.Strike, T, .0425, .0365)
            out[f"iv_{label}"] = None if np.isnan(iv) else iv
            out[f"status_{label}"] = status
        if out["iv_mid"] is not None and out["iv_mid"] > 0:
            vega = greeks(row.Type, 182.4, row.Strike, T, .0425, .0365, out["iv_mid"])["vega"]
            out.update(vega=vega, vol_points_per_cent=1/vega)
        rows.append(out)
    frame = pd.DataFrame(rows)
    frame.to_csv(ROOT/"results/p1_quotes.csv", index=False)
    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, kind in enumerate(("Call", "Put")):
        f = frame[frame.type == kind]
        ax.plot(f.strike, f.iv_mid*100, "o-", color=COLORS[i], label=f"{kind} mid IV")
        ax.fill_between(f.strike, f.iv_bid*100, f.iv_ask*100, color=COLORS[i], alpha=.14,
                        label=f"{kind} bid/ask IV")
    ax.set(xlabel="Strike ($)", ylabel="Annual implied volatility (%)", title="Dirty chain: mid IV and bid/ask range")
    ax.legend(ncol=2); fig.tight_layout(); fig.savefig(ROOT/"figures/p1_iv_smile.png"); plt.close(fig)
    save_json("p1.json", rows)


def fit_p2(base_steps):
    args = (48.5, 50., .5, .045, .30)
    divs = ((.1, .25), (.4, 1.5))
    convergence = []
    grid = sorted(set([25, 50, 55, 100, 105, 150, 200, 205, 300, 305, 600, 605, base_steps, base_steps+5]))
    for n in grid:
        start = time.monotonic()
        with_div = crr_all(*args, n, divs)
        no_div = crr_all(*args, n)
        convergence.append(dict(N=n, with_div=with_div.tolist(), no_div=no_div.tolist()))
        print(f"P2: N={n}, American call={with_div[1]:.8f}, put={with_div[3]:.8f}; {time.monotonic()-start:.2f}s", flush=True)
    base = next(x for x in convergence if x["N"] == base_steps)
    v = np.array(base["with_div"])
    greek_rows = []
    for h in (1., .1, .01, .001):
        plus = crr_all(48.5+h, *args[1:], base_steps, divs)
        minus = crr_all(48.5-h, *args[1:], base_steps, divs)
        greek_rows.append(dict(bump=h, call_delta=(plus[1]-minus[1])/(2*h),
                               call_gamma=(plus[1]+minus[1]-2*v[1])/h**2,
                               put_delta=(plus[3]-minus[3])/(2*h),
                               put_gamma=(plus[3]+minus[3]-2*v[3])/h**2))
    sensitivities = []
    for i in range(2):
        bumps = []
        # Two sizes expose discretization noise rather than hiding it in one result.
        for h in (.01, .001):
            plus, minus = list(divs), list(divs)
            plus[i] = (divs[i][0], divs[i][1]+h)
            minus[i] = (divs[i][0], divs[i][1]-h)
            sensitivity = (crr_all(*args, base_steps, plus)-crr_all(*args, base_steps, minus))/(2*h)
            bumps.append(dict(bump=h, values=sensitivity.tolist()))
        sensitivities.append(dict(dividend=i+1, time=divs[i][0], estimates=bumps))
    # Just before the FINAL dividend the remaining tree has no cash jumps.
    # Exercise boundary is pre-dividend S; solve C_A(S-D, remaining)=S-K.
    remain_steps = base_steps//5
    def advantage(s):
        return s-50-crr_american("Call", s-1.5, 50, .1, .045, .3, remain_steps)
    boundary = brentq(advantage, 50.00001, 100)
    exact_boundary = brentq(lambda s: s-50-gbsm("Call",s-1.5,50,.1,.045,.045,.3),50.00001,100)
    pvdiv = sum(d*np.exp(-.045*t) for t, d in divs)
    result = dict(N=base_steps, order=["EuropeanCall", "AmericanCall", "EuropeanPut", "AmericanPut"],
                  no_div=base["no_div"], with_div=base["with_div"], convergence=convergence,
                  gbsm_no_div=[float(gbsm(k, 48.5, 50, .5, .045, .045, .3)) for k in ("Call", "Put")],
                  pv_dividends=pvdiv,
                  gbsm_pv_adjusted=[float(gbsm(k, 48.5-pvdiv, 50, .5, .045, .045, .3)) for k in ("Call", "Put")],
                  finite_differences=greek_rows, dividend_sensitivity=sensitivities,
                  second_dividend_exercise_boundary=boundary,
                  second_dividend_continuous_boundary=exact_boundary)
    save_json("p2.json", result)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.7))
    for i, title in enumerate(("American call", "American put")):
        j = 1 if i == 0 else 3
        ax[i].plot([x["N"] for x in convergence], [x["with_div"][j] for x in convergence], "o-", color=COLORS[i])
        ax[i].set(title=title+" with dividends", xlabel="Steps N", ylabel="Value ($)")
    fig.tight_layout(); fig.savefig(ROOT/"figures/p2_convergence.png"); plt.close(fig)


def revalue_book(book, spot, horizon=10):
    value = np.zeros_like(np.asarray(spot, float))
    for row in book.itertuples():
        if row.Type == "Stock": price = spot
        else:
            price = gbsm(row.Type, spot, row.Strike, (row.DaysToExpiry-horizon)/255,
                         .0425, .0425, row.ImpliedVol)
        value = value+row.Holding*price
    return value


def fit_p3(nsim, seed):
    spot, prices, books, summary = books_at_spot()
    returns = prices.ABC.pct_change().dropna().to_numpy()
    fitted = fit_distributions(returns)
    # Standard delta-normal uses n-1 historical variance, not fitted t scale.
    sd10 = returns.std(ddof=1)*np.sqrt(10)
    dn = {name: {str(a): normal_risk(0, abs(g["delta"])*spot*sd10, a)
                 for a in (.05, .01)} for name, g in summary.items()}
    simulation = {}
    # Independent reproducible streams; same terminal price scenarios within a
    # model for all books, so book comparisons are not contaminated by new draws.
    for mi, model in enumerate(("Normal", "StudentT")):
        rng = np.random.default_rng(seed+mi)
        fit = fitted[model]
        if model == "Normal": draws = rng.normal(0, fit["scale"], (nsim, 10))
        else: draws = rng.standard_t(fit["df"], (nsim, 10))*fit["scale"]
        if np.any(draws <= -1):
            raise ValueError("Sampled arithmetic return <= -100%; inspect model support")
        terminal = spot*np.prod(1+draws, axis=1)
        ds = terminal-spot
        simulation[model] = {}
        for name, book in books.groupby("Portfolio", sort=False):
            g = summary[name]
            pnl = revalue_book(book, terminal)-g["value"]
            gamma_only = g["delta"]*ds+.5*g["gamma"]*ds**2
            dgt = gamma_only+g["theta"]*10/255
            # Independent batches supply an empirical MC standard error for
            # reported tail estimates. It is not parameter uncertainty.
            batches = np.array_split(pnl, 20)
            mc_se = {str(a): {key: float(np.std([risk(b, a)[key] for b in batches], ddof=1)/np.sqrt(20))
                              for key in ("var", "es")} for a in (.05, .01)}
            simulation[model][name] = dict(mean=float(pnl.mean()), mean_mc_se=float(pnl.std(ddof=1)/np.sqrt(nsim)),
                full={str(a): risk(pnl, a) for a in (.05, .01)},
                delta_gamma={str(a): risk(gamma_only, a) for a in (.05, .01)},
                delta_gamma_theta={str(a): risk(dgt, a) for a in (.05, .01)}, mc_se=mc_se,
                pnl_sd=float(pnl.std(ddof=1)), pnl_skew=float(stats.skew(pnl)),
                terminal_return_mean=float((terminal/spot-1).mean()))
        print(f"P3: completed {model}, {nsim:,} paths", flush=True)
    no_move = {}
    fig, axs = plt.subplots(2, 2, figsize=(10, 7))
    price_grid = np.linspace(spot*.65, spot*1.35, 700)
    for ax, (name, book) in zip(axs.ravel(), books.groupby("Portfolio", sort=False)):
        g = summary[name]
        pnl = revalue_book(book, price_grid)-g["value"]
        no_move[name] = float(revalue_book(book, spot)-g["value"])
        ax.plot(price_grid, pnl, color=COLORS[0], label="Full value, 20 days left")
        ax.plot(price_grid, g["delta"]*(price_grid-spot), "--", color=COLORS[1], label="Delta only")
        ax.axhline(0, color="grey", lw=.6); ax.axvline(spot, color="grey", lw=.6)
        ax.set(title=name, xlabel="ABC in 10 days ($)", ylabel="10-day P&L ($)")
        ax.legend(fontsize=8)
    fig.tight_layout(); fig.savefig(ROOT/"figures/p3_book_pnl.png"); plt.close(fig)
    save_json("p3.json", dict(nsim=nsim, seed=seed, moments=moments(returns), fitted=fitted,
              delta_normal=dn, simulation=simulation, no_move=no_move, greeks=summary,
              spot=spot, sd10=sd10, chosen=min(fitted, key=lambda m: fitted[m]["aicc"])))


def fit_p4(bootstrap, seed):
    p4 = data("problem4.csv")
    X = p4[ASSETS].to_numpy(); mu = X.mean(axis=0); cov = np.cov(X, rowvar=False)
    rf = .03/12
    portfolios = {}
    for mode in ("unconstrained", "long_only", "capped"):
        w = tangency(mu, cov, rf, mode); r = X@w
        portfolios[mode] = dict(weights=w.tolist(), monthly_mean=float(r.mean()),
            monthly_sd=float(r.std(ddof=1)), annual_sharpe=float(np.sqrt(12)*(r.mean()-rf)/r.std(ddof=1)),
            risk={str(a): dict(historical=risk(r, a), normal=normal_risk(r.mean(), r.std(ddof=1), a),
                              course_tail_mean_es=float(-r[r<=np.quantile(r,a)].mean()))
                  for a in (.05, .01)})
    y = p4.PUTW-rf; market = p4.EQ-rf
    capm = ols(y, market, ["EQ-RF"])
    stress = market < -.05
    stress_capm = ols(y[stress], market[stress], ["EQ-RF"])
    boot = {mode: [] for mode in portfolios}
    rng = np.random.default_rng(seed)
    # Resample WHOLE MONTHS, preserving contemporaneous dependence.
    for _ in range(bootstrap):
        sample = X[rng.integers(0, len(X), len(X))]
        m = sample.mean(axis=0); c = np.cov(sample, rowvar=False)
        for mode in boot:
            try:
                boot[mode].append(tangency(m, c, rf, mode).tolist())
            except (ValueError, RuntimeError, np.linalg.LinAlgError):
                # Report failure count rather than pretending all replicates fit.
                pass
    boot_summary = {}
    for mode, weights in boot.items():
        w = np.array(weights)
        boot_summary[mode] = dict(successful=len(w), attempted=bootstrap,
            p05=np.quantile(w, .05, axis=0).tolist(), median=np.median(w, axis=0).tolist(),
            p95=np.quantile(w, .95, axis=0).tolist(),
            zero_fraction=(abs(w)<1e-6).mean(axis=0).tolist())
    # Trace only the efficient (upper) branch starting at global minimum variance.
    constraints = [dict(type="eq", fun=lambda w: w.sum()-1)]
    gmv = minimize(lambda w: w@cov@w, np.ones(4)/4, jac=lambda w: 2*cov@w,
                   constraints=constraints, bounds=[(0,1)]*4, method="SLSQP",
                   options=dict(ftol=1e-13, maxiter=1000))
    if not gmv.success: raise RuntimeError(gmv.message)
    frontier = []
    for target in np.linspace(mu@gmv.x, mu.max(), 90):
        w = efficient_weights(mu, cov, target)
        frontier.append([float(np.sqrt(w@cov@w)*np.sqrt(12)), float(target*12)])
    fig, ax = plt.subplots(figsize=(9, 5))
    f = np.array(frontier)
    ax.plot(f[:, 0]*100, f[:, 1]*100, color=COLORS[0], label="Long-only efficient frontier")
    for i, a in enumerate(ASSETS):
        x = np.sqrt(cov[i,i])*np.sqrt(12)*100; y0=mu[i]*12*100
        ax.scatter(x,y0,color=COLORS[i],s=45); ax.annotate(a,(x,y0),xytext=(5,5),textcoords="offset points")
    sigma = np.linspace(0, np.sqrt(np.diag(cov)).max()*np.sqrt(12)*1.05,100)
    ax.plot(sigma*100,(.03+portfolios["long_only"]["annual_sharpe"]*sigma)*100,
            "--",color=COLORS[1],label="CML through long-only tangency")
    w=np.array(portfolios["long_only"]["weights"])
    ax.scatter(np.sqrt(w@cov@w)*np.sqrt(12)*100,mu@w*12*100,marker="*",s=160,color="black",label="Long-only tangency")
    ax.set(xlabel="Annualized standard deviation (%)",ylabel="Annualized arithmetic mean (%)",
           title="Monthly returns: efficient frontier and capital market line")
    ax.legend(fontsize=8);fig.tight_layout();fig.savefig(ROOT/"figures/p4_frontier.png");plt.close(fig)
    save_json("p4.json",dict(rf_monthly=rf, portfolios=portfolios, capm=capm, stress_capm=stress_capm,
              stress_months=p4.Month[stress].tolist(), bootstrap=boot_summary, bootstrap_seed=seed, frontier=frontier))
    print(f"P4: optimization and {bootstrap} whole-month bootstrap samples complete",flush=True)


def fit_p5():
    factors, joined = factor_data()
    end = factors.Date.max(); start = end-pd.DateOffset(years=10)
    recent = factors[(factors.Date>start)&(factors.Date<=end)]
    means = recent[FACTORS+["RF"]].mean()
    sample_means = joined[FACTORS+["RF"]].mean()
    worst = factors.loc[factors.Mom.idxmin()]
    funds = {}
    for fund in ("FUND1", "FUND2"):
        y = joined[fund]-joined.RF
        fits = {name: ols(y, joined[cols], cols) for name,cols in
                [("CAPM",["Mkt-RF"]),("FF3",FACTORS[:3]),("Carhart4",FACTORS)]}
        coefs = np.array(fits["Carhart4"]["coefficients"])
        daily_without = float(means.RF+coefs[1:]@means[FACTORS].to_numpy())
        daily_with = daily_without+coefs[0]
        realized = joined[fund].to_numpy()
        shock = float(coefs[-1]*worst.Mom)
        # Omitted-factor identity accounts for the CAPM-to-four-factor alpha
        # change exactly, including the portion projected onto the market.
        omitted = {}
        for i,f in enumerate(FACTORS[1:],start=2):
            projection = ols(joined[f],joined[["Mkt-RF"]],["Mkt-RF"])
            omitted[f] = dict(beta=float(coefs[i]), mean=float(sample_means[f]),
                market_projection_beta=projection["coefficients"][1],
                residual_mean=projection["coefficients"][0],
                contribution_to_capm_alpha=float(coefs[i]*projection["coefficients"][0]))
        funds[fund] = dict(fits=fits, daily_expected_without_alpha=daily_without,
            daily_expected_with_alpha=daily_with,
            annual_expected_without_alpha=255*daily_without,
            annual_expected_with_alpha=255*daily_with,
            compounded_expected_without_alpha=(1+daily_without)**255-1,
            compounded_expected_with_alpha=(1+daily_with)**255-1,
            realized_annual_arithmetic=float(255*realized.mean()),
            realized_cagr=float(np.exp(np.log1p(realized).mean()*255)-1),
            realized_sample_total=float(np.expm1(np.log1p(realized).sum())),
            momentum_scenario_return=shock, momentum_scenario_loss=-1e7*shock,
            momentum_scenario_sigma=-shock/realized.std(ddof=1), omitted_factor_attribution=omitted)
    save_json("p5.json", dict(funds=funds, recent_start_exclusive=start, recent_first=recent.Date.min(),
        recent_last=end, recent_n=len(recent), recent_daily_factor_means=means.to_dict(),
        sample_daily_factor_means=sample_means.to_dict(), sample_start=joined.Date.min(), sample_end=joined.Date.max(),
        sample_n=len(joined), worst_momentum_date=worst.Date, worst_momentum_return=worst.Mom))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["prepare","fit"])
    parser.add_argument("--problem", type=int, choices=range(1,6))
    parser.add_argument("--steps", type=int, default=400)
    parser.add_argument("--nsim", type=int, default=1000000)
    parser.add_argument("--bootstrap", type=int, default=500)
    parser.add_argument("--seed", type=int, default=5452026)
    args = parser.parse_args()
    for d in ("results","figures"): (ROOT/d).mkdir(parents=True,exist_ok=True)
    if args.stage == "prepare": prepare(); return
    prediction = ROOT/"predictions.md"
    if not prediction.exists(): raise RuntimeError("Save predictions.md BEFORE running fit")
    if args.steps%5: raise ValueError("steps must be a multiple of 5")
    prefit = json.loads((ROOT/"results/prefit.json").read_text())
    for name,digest in prefit["source_sha256"].items():
        if hashlib.sha256((ROOT/"data"/name).read_bytes()).hexdigest()!=digest:
            raise ValueError("Input data changed after preparation")
    save_json("fit_provenance.json",dict(started_at_utc=datetime.now(timezone.utc).isoformat(),
        predictions_sha256=hashlib.sha256(prediction.read_bytes()).hexdigest(),
        prepared_at_utc=prefit["prepared_at_utc"], arguments=vars(args)))
    if args.problem in (None,1): fit_p1()
    if args.problem in (None,2): fit_p2(args.steps)
    if args.problem in (None,3): fit_p3(args.nsim,args.seed)
    if args.problem in (None,4): fit_p4(args.bootstrap,args.seed+10)
    if args.problem in (None,5): fit_p5()


if __name__ == "__main__": main()
