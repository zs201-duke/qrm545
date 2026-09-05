"""Reproduce Assignment 1: preliminary diagnostics first, then model fitting.

Run `python analysis.py --stage prepare` before inspecting any fitted results.
The separate `fit` stage deliberately preserves the pre-fit prediction record.
All inputs and outputs are relative to this script, not the working directory.
"""
from pathlib import Path
import argparse
import json
import os
import platform

BASE = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(BASE / ".mplconfig"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import scipy
from scipy import optimize, stats
import statsmodels
import statsmodels.api as sm
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import acf, pacf

plt.rcParams.update({"figure.dpi": 130, "savefig.dpi": 190,
                    "font.size": 10, "axes.spines.top": False,
                    "axes.spines.right": False, "axes.titleweight": "bold"})
BLUE, ORANGE = "#22628a", "#c75f32"


def data(i):
    """Fail on missing or nonfinite inputs instead of silently changing samples."""
    df = pd.read_csv(BASE / "data" / f"problem{i}.csv")
    expected = {1: ["x"], 2: ["x", "y"], 3: ["x1", "x2", "x3", "x4"],
                4: ["x1", "x2"], 5: ["x"]}[i]
    assert list(df.columns) == expected, (i, df.columns)
    assert np.isfinite(df.to_numpy()).all()
    return df


def save_json(name, obj):
    (BASE / "results" / name).write_text(json.dumps(obj, indent=2, allow_nan=False) + "\n")


def savefig(name):
    plt.tight_layout()
    plt.savefig(BASE / "figures" / name, bbox_inches="tight")
    plt.close()


def aicc(ll, k, n):
    """Count every estimated coefficient, location/mean, scale, and shape parameter."""
    assert n > k + 1
    return -2 * ll + 2 * k + 2 * k * (k + 1) / (n - k - 1)


def prepare():
    """Only the summaries/plots permitted in the Predict parts; no model fitting."""
    x = data(1).x.to_numpy()
    d = x - x.mean()
    m2, m3, m4 = [np.mean(d ** j) for j in (2, 3, 4)]
    preliminary = {"problem1": {
        "n": len(x), "mean": float(x.mean()), "variance_unbiased": float(x.var(ddof=1)),
        "central_moment2_n": float(m2), "central_moment3_n": float(m3),
        "central_moment4_n": float(m4),
        "skewness_moment": float(m3 / m2 ** 1.5),
        "excess_kurtosis_moment": float(m4 / m2 ** 2 - 3),
        "skewness_bias_corrected": float(stats.skew(x, bias=False)),
        "excess_kurtosis_bias_corrected": float(stats.kurtosis(x, fisher=True, bias=False))}}
    d2 = data(2)
    plt.figure(figsize=(7.5, 4.2))
    plt.scatter(d2.x, d2.y, s=17, alpha=.7, color=BLUE)
    plt.xlabel("x"); plt.ylabel("y"); plt.title("Problem 2 | Scatter before fitting")
    savefig("p2_prefit.png")

    d3 = data(3)
    fig, axes = plt.subplots(2, 3, figsize=(10, 6))
    from itertools import combinations
    for ax, (a, b) in zip(axes.flat, combinations(d3.columns, 2)):
        ax.scatter(d3[a], d3[b], s=8, alpha=.55, color=BLUE)
        ax.set(xlabel=a, ylabel=b, title=f"{a} vs {b}")
    fig.suptitle("Problem 3 | All six pairs before fitting", fontweight="bold")
    savefig("p3_pairs.png")

    # For P4 the only preliminary numeric diagnostic is the sample covariance.
    d4 = data(4)
    cov = d4.cov().to_numpy()
    cv = cov[1, 1] - cov[1, 0] * cov[0, 1] / cov[0, 0]
    preliminary["problem4"] = {"n": len(d4), "covariance": cov.tolist(),
        "conditional_variance": float(cv), "variance_remaining": float(cv / cov[1, 1])}

    x5 = data(5).x.to_numpy()
    # Fixed +/-1.96/sqrt(n) bands follow Week 2's model-identification convention.
    # These are pointwise heuristic bands, not a simultaneous test over 30 lags.
    av = acf(x5, nlags=30, fft=False, adjusted=False)
    pv = pacf(x5, nlags=30, method="ywm")
    band = 1.96 / np.sqrt(len(x5))
    preliminary["problem5"] = {"n": len(x5), "band": float(band),
                                "acf": av.tolist(), "pacf": pv.tolist()}
    fig, axes = plt.subplots(3, 1, figsize=(8.5, 8))
    axes[0].plot(np.arange(1, len(x5)+1), x5, lw=.8, color=BLUE)
    axes[0].set(xlabel="Observation (file order)", ylabel="x", title="Problem 5 | Series before fitting")
    for ax, vals, title in zip(axes[1:], (av, pv), ("ACF", "PACF (Yule-Walker, MLE convention)")):
        ax.axhspan(-band, band, color=BLUE, alpha=.13)
        ax.stem(np.arange(1, 31), vals[1:], basefmt=" ")
        ax.axhline(0, color="grey", lw=.7)
        ax.set(xlabel="Lag", ylabel="Correlation", title=title, xlim=(.3, 30.7))
    savefig("p5_prefit.png")
    save_json("preliminary.json", preliminary)
    print(json.dumps(preliminary, indent=2))


def fit():
    """Fit only after pre-fit plots and a written prediction record exist."""
    assert (BASE / "predictions.md").exists(), "Record predictions before fitting."
    pre = json.loads((BASE / "results" / "preliminary.json").read_text())
    res = {"versions": {"python": platform.python_version(), "numpy": np.__version__,
            "pandas": pd.__version__, "scipy": scipy.__version__,
            "statsmodels": statsmodels.__version__, "matplotlib": matplotlib.__version__}}
    x = data(1).x.to_numpy()
    mu, sd = x.mean(), x.std(ddof=1)
    q = stats.norm.ppf(.01, loc=mu, scale=sd)
    p1 = dict(pre["problem1"])
    p1.update({"normal_sd": float(sd), "normal_q01": float(q),
               "observed_below_q01": int(np.sum(x < q)), "expected_below_q01": .01 * len(x),
               "empirical_q01": float(np.quantile(x, .01))})
    res["problem1"] = p1
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 3.9))
    grid = np.linspace(x.min(), x.max(), 700)
    axes[0].hist(x, bins=55, density=True, color=BLUE, alpha=.5, label="Sample")
    axes[0].plot(grid, stats.norm.pdf(grid, mu, sd), color=ORANGE, label="Moment-matched Normal")
    axes[0].set(xlabel="x", ylabel="Density", title="Sample shape vs fitted Normal")
    axes[0].legend(fontsize=8)
    sx = np.sort(x)
    axes[1].step(sx, np.arange(1, len(x)+1)/len(x), where="post", label="Empirical CDF", color=BLUE)
    axes[1].plot(grid, stats.norm.cdf(grid, mu, sd), color=ORANGE, label="Normal CDF")
    axes[1].axvline(q, color="black", ls="--", lw=1, label="Normal 1% quantile")
    axes[1].set(xlim=(x.min(), mu-1.2*sd), ylim=(0, .13), xlabel="x", ylabel="Cumulative probability", title="Left-tail calibration")
    axes[1].legend(fontsize=8)
    savefig("p1_normal.png")

    d2 = data(2); xx = d2.x.to_numpy(); yy = d2.y.to_numpy(); n = len(xx)
    X = sm.add_constant(xx)
    ols = sm.OLS(yy, X).fit()
    sigma_n = np.sqrt(np.mean(ols.resid ** 2))
    # Normal MLE has an exact solution: the same coefficients as OLS, SSE/n scale.
    ll_n = float(np.sum(stats.norm.logpdf(ols.resid, loc=0, scale=sigma_n)))
    # The intercept absorbs location; fitting another error location is unidentified.
    # Positive scale and df are optimized on log scales; df is NOT forced above 2.
    def t_nll(par):
        alpha, beta, log_scale, log_df = par
        scale, df = np.exp(log_scale), np.exp(log_df)
        return -np.sum(stats.t.logpdf((yy-alpha-beta*xx)/scale, df=df)-log_scale)
    starts = []
    for df0 in (1.5, 3., 5., 10., 30.):
        scale0 = sigma_n * np.sqrt((df0-2)/df0) if df0 > 2 else sigma_n*.5
        start = [*ols.params, np.log(scale0), np.log(df0)]
        candidate = optimize.minimize(t_nll, start, method="L-BFGS-B",
            bounds=[(None,None), (None,None), (-15,15), (np.log(.1),np.log(10000))],
            options={"ftol": 1e-13, "gtol": 1e-7, "maxiter": 3000})
        starts.append(candidate)
    good = [c for c in starts if c.success and np.isfinite(c.fun)]
    assert good, "No Student t optimizer converged."
    best = min(good, key=lambda c: c.fun)
    aa, bb, ls, ld = best.x; scale_t, df_t = np.exp(ls), np.exp(ld)
    tstd = scale_t * np.sqrt(df_t/(df_t-2)) if df_t > 2 else None
    models = [
        {"model": "OLS", "alpha": float(ols.params[0]), "beta": float(ols.params[1]),
         "error_scale": float(np.sqrt(ols.scale)), "error_df": None,
         "se_alpha": float(ols.bse[0]), "se_beta": float(ols.bse[1]),
         "loglik": ll_n, "k": 3, "aicc": aicc(ll_n,3,n)},
        {"model": "Normal MLE", "alpha": float(ols.params[0]), "beta": float(ols.params[1]),
         "error_scale": float(sigma_n), "error_df": None,
         "se_alpha": None, "se_beta": None, "loglik": ll_n, "k": 3, "aicc": aicc(ll_n,3,n)},
        {"model": "Student t MLE", "alpha": float(aa), "beta": float(bb),
         "error_scale": float(scale_t), "error_df": float(df_t),
         "se_alpha": None, "se_beta": None, "loglik": float(-best.fun), "k": 4,
         "aicc": aicc(-best.fun,4,n)}]
    # Quantiles are one-sided CDF percentiles, not the endpoints of central intervals.
    qs = [{"p": p, "normal": float(stats.norm.ppf(p, scale=sigma_n)),
           "student_t": float(stats.t.ppf(p, df_t, scale=scale_t))} for p in (.95,.995)]
    res["problem2"] = {"n": n, "models": models, "quantiles": qs,
        "t_error_sd": float(tstd) if tstd else None,
        "hc3_se_beta": float(ols.get_robustcov_results(cov_type="HC3").bse[1]),
        "slope_difference_t_minus_ols": float(bb-ols.params[1]),
        "optimizer_runs": [{"success": bool(c.success), "nll": float(c.fun)} for c in starts]}
    pd.DataFrame(models).to_csv(BASE/"results"/"p2_models.csv", index=False)
    fig, axes = plt.subplots(1, 2, figsize=(9.5, 4))
    axes[0].scatter(xx, yy, s=12, alpha=.5, color=BLUE)
    gx = np.linspace(xx.min(),xx.max(),300)
    axes[0].plot(gx,ols.params[0]+ols.params[1]*gx,color=ORANGE,label="OLS / Normal MLE")
    axes[0].plot(gx,aa+bb*gx,color="black",ls="--",label="Student t MLE")
    axes[0].set(xlabel="x",ylabel="y",title="Fitted slopes"); axes[0].legend(fontsize=8)
    rr = np.linspace(min(ols.resid.min(), -qs[1]["student_t"]), max(ols.resid.max(),qs[1]["student_t"]),1000)
    axes[1].plot(rr,stats.norm.pdf(rr,scale=sigma_n),color=ORANGE,label="Normal error")
    axes[1].plot(rr,stats.t.pdf(rr,df_t,scale=scale_t),color=BLUE,label="Student t error")
    axes[1].set(xlabel="Error",ylabel="Density",title="Error distributions"); axes[1].legend(fontsize=8)
    savefig("p2_fits.png")

    d3 = data(3); pearson = d3.corr(method="pearson"); spearman = d3.corr(method="spearman")
    gaps = []
    for i in range(4):
        for j in range(i+1,4):
            gaps.append({"pair": f"x{i+1}, x{j+1}", "pearson": float(pearson.iloc[i,j]),
                "spearman": float(spearman.iloc[i,j]),
                "absolute_gap": float(abs(pearson.iloc[i,j]-spearman.iloc[i,j]))})
    pearson.to_csv(BASE/"results"/"p3_pearson.csv")
    spearman.to_csv(BASE/"results"/"p3_spearman.csv")
    res["problem3"] = {"n": len(d3), "pearson": pearson.to_numpy().tolist(),
        "spearman": spearman.to_numpy().tolist(), "pairs": gaps,
        "largest_gap": max(gaps, key=lambda z:z["absolute_gap"])}

    d4 = data(4); v = np.array(pre["problem4"]["covariance"])
    mean = d4.mean().to_numpy(); slope = v[1,0]/v[0,0]; intercept = mean[1]-slope*mean[0]
    cv = pre["problem4"]["conditional_variance"]
    half = stats.norm.ppf(.975)*np.sqrt(cv)
    fitted = intercept + slope*d4.x1.to_numpy(); residual = d4.x2.to_numpy()-fitted
    inside = np.abs(residual) <= half
    z = np.abs(d4.x1.to_numpy()-mean[0])/np.sqrt(v[0,0])
    buckets = []
    for label, mask in [("Within 1 SD", z<=1), ("Between 1 and 2 SD", (z>1)&(z<=2)), ("Beyond 2 SD",z>2)]:
        buckets.append({"bucket":label, "n": int(mask.sum()), "inside":int(inside[mask].sum()),
            "coverage": float(inside[mask].mean()),
            "residual_mean":float(residual[mask].mean()),
            "residual_sd":float(residual[mask].std(ddof=1)),
            "residual_rms":float(np.sqrt(np.mean(residual[mask]**2)))})
    res["problem4"] = dict(pre["problem4"], mean=mean.tolist(), slope=float(slope),
        intercept=float(intercept), half_width=float(half), inside=int(inside.sum()),
        coverage=float(inside.mean()), buckets=buckets)
    pd.DataFrame(buckets).to_csv(BASE/"results"/"p4_coverage.csv",index=False)
    fig, axes = plt.subplots(1,2,figsize=(10,4.3),gridspec_kw={"width_ratios":[1.7,1]})
    grid = np.linspace(d4.x1.min(),d4.x1.max(),350); line=intercept+slope*grid
    axes[0].fill_between(grid,line-half,line+half,color=BLUE,alpha=.17,label="95% Gaussian observation band")
    axes[0].scatter(d4.x1,d4.x2,s=7,alpha=.4,color=BLUE)
    axes[0].plot(grid,line,color=ORANGE,label="Gaussian conditional mean / OLS line")
    axes[0].set(xlabel="x1",ylabel="x2",title="Conditional model"); axes[0].legend(fontsize=7)
    axes[1].bar(["Within 1 SD","1 to 2 SD",">2 SD"],[b["coverage"]*100 for b in buckets],color=BLUE)
    axes[1].axhline(95,color=ORANGE,ls="--",label="Nominal 95%")
    axes[1].set(ylim=(0,105),ylabel="Coverage (%)",title="Coverage by distance from mean")
    axes[1].tick_params(axis="x",labelsize=8); axes[1].legend(fontsize=8)
    savefig("p4_conditional.png")
    # Cross-check the partition formula against least squares, without assuming normality.
    ols4 = sm.OLS(d4.x2,sm.add_constant(d4.x1)).fit()
    assert np.allclose(ols4.params,[intercept,slope])
    assert np.isclose(np.sum(residual**2)/(len(d4)-1),cv)

    x5 = data(5).x.to_numpy(); n5=len(x5); fits=[]
    # Same full sample and exact stationary Gaussian likelihood for all six models.
    # trend='c' estimates the unconditional mean, not the AR recurrence intercept.
    for kind in ("AR","MA"):
        for order in (1,2,3):
            pq=(order,0,0) if kind=="AR" else (0,0,order)
            model=ARIMA(x5,order=pq,trend="c",enforce_stationarity=True,enforce_invertibility=True)
            fitted=model.fit(method="statespace",method_kwargs={"maxiter":2000,"disp":0})
            assert fitted.mle_retvals.get("converged",False), (kind,order,fitted.mle_retvals)
            k=len(fitted.params)
            assert k==order+2 and fitted.nobs==n5 and fitted.loglikelihood_burn==0
            score=aicc(fitted.llf,k,n5)
            assert np.isclose(score,fitted.aicc)
            fits.append({"model":f"{kind}({order})", "n":n5, "k":k,
                "loglik":float(fitted.llf), "aicc":float(score),
                "params":dict(zip(fitted.param_names,map(float,fitted.params))),
                "standard_errors":dict(zip(fitted.param_names,map(float,fitted.bse))),
                "converged":True})
    # Illustrate the R-squared claim on IDENTICAL response rows for nested OLS AR fits.
    # This is a separate diagnostic; it does not replace exact-likelihood AR estimates.
    lag_columns=np.column_stack([x5[3-j:n5-j] for j in (1,2,3)])
    r2={}
    for p in (2,3):
        nested=sm.OLS(x5[3:],sm.add_constant(lag_columns[:,:p])).fit()
        r2[f"AR({p})"]={"n":n5-3,"r_squared":float(nested.rsquared),"sse":float(nested.ssr)}
    res["problem5"] = dict(pre["problem5"],models=fits,selected=min(fits,key=lambda z:z["aicc"])["model"],
                            common_sample_ols=r2)
    pd.DataFrame([{k:v for k,v in r.items() if k not in ("params","standard_errors")} for r in fits]).to_csv(BASE/"results"/"p5_models.csv",index=False)
    # Basic reproducibility checks catch data loss and parameter-count convention errors.
    assert sum(b["n"] for b in buckets)==len(d4)
    assert sum(b["inside"] for b in buckets)==int(inside.sum())
    assert np.allclose(pearson,pearson.T) and np.allclose(spearman,spearman.T)
    assert res["problem2"]["models"][0]["beta"] == res["problem2"]["models"][1]["beta"]
    save_json("results.json",res)
    print(json.dumps(res,indent=2))


if __name__ == "__main__":
    for directory in ("results","figures"):
        (BASE/directory).mkdir(exist_ok=True)
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",choices=("prepare","fit","all"),default="all")
    stage=parser.parse_args().stage
    if stage in ("prepare","all"): prepare()
    if stage in ("fit","all"): fit()
