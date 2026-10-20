"""Midterm Problem 3: marginal MLE, copula comparison, portfolio VaR and ES.

Python 3 + NumPy + SciPy. Run `python3 problem3_analysis.py` for all stages,
or pass --stage fit / copula / simulate to rerun one saved-data stage.
Data paths are relative to this script. No source data is modified.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import warnings
import numpy as np
import scipy
from scipy import optimize, special, stats, integrate
from scipy.stats.sampling import NumericalInversePolynomial

HERE = Path(__file__).resolve().parent
PRICE_FILE = HERE.parent / "problem3.csv"
HOLDING_FILE = HERE.parent / "problem3_holdings.csv"
FAMILIES = ("Normal", "Student t", "NIG")
IC_K = {"Normal": 2, "Student t": 3, "NIG": 4}


def save_json(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, allow_nan=False))


def save_csv(name, records):
    with (HERE / name).open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader(); writer.writerows(records)


def load_data():
    with PRICE_FILE.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    names = [f"S{i}" for i in range(1, 11)]
    assert len(rows) == 1001 and list(rows[0]) == ["Date", *names]
    dates = [r["Date"] for r in rows]
    assert dates == sorted(dates) and len(set(dates)) == len(dates)
    prices = np.array([[float(r[n]) for n in names] for r in rows])
    assert np.isfinite(prices).all() and (prices > 0).all()
    returns = prices[1:] / prices[:-1] - 1.0
    with HOLDING_FILE.open(newline="") as stream:
        holdings = list(csv.DictReader(stream))
    lookup = {r["Stock"]: r for r in holdings}
    assert set(lookup) == set(names) and len(holdings) == len(names)
    shares = np.array([float(lookup[n]["Holding"]) for n in names])
    books = [lookup[n]["Book"] for n in names]
    return names, prices, returns, shares, books, dates


def information_criteria(ll, k, n):
    aic = -2 * ll + 2 * k
    return dict(loglik=float(ll), k=k, AIC=float(aic),
                AICc=float(aic + 2*k*(k+1)/(n-k-1)), BIC=float(-2*ll+k*np.log(n)))


def nig_unpack(theta):
    # Stable free parameters: mean, log SD, log a, and atanh(b/a).
    m, log_sd, log_a, eta = theta
    a, ratio, sd = np.exp(log_a), np.tanh(eta), np.exp(log_sd)
    scale = sd * np.sqrt(a) * (1-ratio**2)**0.75
    b = a * ratio
    loc = m - scale * ratio / np.sqrt(1-ratio**2)
    return a, b, loc, scale


def nig_logpdf(x, a, b, loc, scale):
    y = (x-loc)/scale
    radius = np.hypot(1.0, y)
    # k1e avoids Bessel underflow. Rearranging the exponential further limits
    # cancellation in nearly normal, large-a fits.
    gamma = np.sqrt((a-b)*(a+b))
    return (np.log(a)-np.log(np.pi)-np.log(scale)-np.log(radius)
            + np.log(special.k1e(a*radius)) + (gamma-a*radius) + b*y)


def fit_t(z):
    def objective(theta):
        m, log_scale, log_nu_minus_2 = theta
        nu = 2 + np.exp(log_nu_minus_2)
        return -np.sum(stats.t.logpdf(z, nu, loc=m, scale=np.exp(log_scale)))
    bounds = [(-5,5),(-5,3),(np.log(1e-5),np.log(1e6))]
    candidates=[]
    for nu in (3., 6., 12., 40., 1000.):
        start=[np.median(z), .5*np.log((nu-2)/nu), np.log(nu-2)]
        fit=optimize.minimize(objective,start,method="L-BFGS-B",bounds=bounds,
                              options=dict(ftol=1e-13,gtol=1e-7,maxiter=2000))
        candidates.append(fit)
    best=min(candidates,key=lambda r:r.fun)
    refined=optimize.minimize(objective,best.x,method="Nelder-Mead",bounds=bounds,
                              options=dict(maxiter=5000,xatol=1e-9,fatol=1e-9))
    if refined.fun < best.fun: best=refined
    m,log_s,log_nu=best.x
    return (2+np.exp(log_nu),m,np.exp(log_s)),best


def fit_nig(z):
    def objective(theta):
        values=nig_logpdf(z,*nig_unpack(theta))
        return -np.sum(values) if np.isfinite(values).all() else 1e100
    # Bounds exclude numerical singularities; all selected NIG fits are checked
    # to be interior. Large-a near-normal limits are separately identified.
    bounds=[(-5,5),(-3,3),(np.log(.001),np.log(1e5)),(-3,3)]
    skew=np.sign(stats.skew(z))
    candidates=[]
    for a in (.5,2.,10.,100.):
        for ratio in (0.,.5*skew):
            start=[0.,0.,np.log(a),np.arctanh(ratio)]
            fit=optimize.minimize(objective,start,method="L-BFGS-B",bounds=bounds,
                                  options=dict(ftol=1e-13,gtol=1e-6,maxiter=3000))
            candidates.append(fit)
    best=min(candidates,key=lambda r:r.fun)
    refined=optimize.minimize(objective,best.x,method="Nelder-Mead",bounds=bounds,
                              options=dict(maxiter=6000,xatol=1e-9,fatol=1e-9))
    if refined.fun < best.fun: best=refined
    if not best.success:
        # Near-normal NIG parameters are weakly identified. Avoid demanding
        # parameter accuracy beyond what the nearly flat likelihood supports.
        start=np.clip(best.x,[b[0] for b in bounds],[b[1] for b in bounds])
        polished=optimize.minimize(objective,start,method="Nelder-Mead",bounds=bounds,
                                   options=dict(maxiter=10000,xatol=1e-5,fatol=1e-6))
        if polished.success and polished.fun<=best.fun+1e-5:best=polished
    return nig_unpack(best.x),best


def frozen(model):
    family,p=model["family"],model["scipy_parameters"]
    if family=="Normal":return stats.norm(loc=p[0],scale=p[1])
    if family=="Student t":return stats.t(p[0],loc=p[1],scale=p[2])
    return stats.norminvgauss(p[0],p[1],loc=p[2],scale=p[3])


def marginal_stage():
    # Problem 3(a): arithmetic returns and all three maximum-likelihood fits.
    names,prices,returns,shares,books,dates=load_data()
    n=returns.shape[0]
    all_models=[]; selected=[]; diagnostics=[]
    for j,name in enumerate(names):
        x=returns[:,j]; center=float(x.mean()); unit=float(x.std(ddof=0));z=(x-center)/unit
        models=[]
        models.append(dict(stock=name,family="Normal",scipy_parameters=[center,unit],
                           parameters=dict(mu=center,sigma=unit),success=True,near_normal_limit=False))
        (nu,m,s),res=fit_t(z)
        models.append(dict(stock=name,family="Student t",scipy_parameters=[float(nu),float(center+unit*m),float(unit*s)],
                           parameters=dict(nu=float(nu),mu=float(center+unit*m),scale=float(unit*s)),
                           success=bool(res.success),near_normal_limit=bool(nu>1e4)))
        (a,b,loc,scale),res=fit_nig(z)
        loc=float(center+unit*loc);scale=float(unit*scale);a=float(a);b=float(b)
        models.append(dict(stock=name,family="NIG",scipy_parameters=[a,b,loc,scale],
                           parameters=dict(alpha=a/scale,beta=b/scale,delta=scale,mu=loc,a=a,b=b),
                           success=bool(res.success),
                           near_normal_limit=bool(stats.norminvgauss.stats(a,b,moments="k")<.01)))
        for model in models:
            dist=frozen(model)
            ll=float(np.sum(dist.logpdf(x)))
            if model["family"]=="NIG":
                custom=float(np.sum(nig_logpdf(x,*model["scipy_parameters"])))
                assert abs(custom-ll)<1e-5
            model.update(information_criteria(ll,IC_K[model["family"]],n))
            assert np.isfinite(ll)
        best=min(models,key=lambda m:m["AICc"])
        best_bic=min(models,key=lambda m:m["BIC"])
        for model in models:
            model["delta_AICc"]=model["AICc"]-best["AICc"]
            model["selected"]=model is best
        all_models.extend(models);selected.append(best)
        diagnostics.append(dict(stock=name,mean=center,sd=float(x.std(ddof=1)),
                                skew=float(stats.skew(x,bias=False)),excess_kurtosis=float(stats.kurtosis(x,bias=False)),
                                AICc_choice=best["family"],BIC_choice=best_bic["family"]))
        print(name,"selected",best["family"],"IC",[(m["family"],round(m["loglik"],4),round(m["AICc"],4)) for m in models],flush=True)
    result=dict(n=n,names=names,models=all_models,selected=selected,diagnostics=diagnostics,
                dates=[dates[0],dates[-1]],scipy_version=scipy.__version__,numpy_version=np.__version__,
                prices_sha256=hashlib.sha256(PRICE_FILE.read_bytes()).hexdigest(),
                holdings_sha256=hashlib.sha256(HOLDING_FILE.read_bytes()).hexdigest())
    save_json("problem3_marginal_fits.json",result)
    flat=[]
    for model in all_models:
        flat.append({k:model[k] for k in ("stock","family","loglik","k","AICc","BIC","delta_AICc","selected")}
                    |{k:model["parameters"].get(k,"") for k in ("nu","sigma","scale","alpha","beta","delta","mu","a","b")})
    save_csv("problem3_marginal_fits.csv",flat)
    save_csv("problem3_sample_diagnostics.csv",diagnostics)
    with (HERE/"problem3_returns.csv").open("w",newline="") as stream:
        writer=csv.writer(stream);writer.writerow(["Date",*names]);writer.writerows(zip(dates[1:],*returns.T))


def copula_loglik(u,r,nu=None):
    n,d=u.shape
    inverse=np.linalg.inv(r);logdet=np.linalg.slogdet(r)[1]
    if nu is None:
        z=stats.norm.ppf(u)
        return float(-n*logdet/2-.5*np.einsum("ni,ij,nj->",z,inverse-np.eye(d),z))
    y=stats.t.ppf(u,nu)
    q=np.einsum("ni,ij,nj->n",y,inverse,y)
    joint=(special.gammaln((nu+d)/2)-special.gammaln(nu/2)-.5*logdet
           -d/2*np.log(nu*np.pi)-(nu+d)/2*np.log1p(q/nu))
    return float(np.sum(joint)-np.sum(stats.t.logpdf(y,nu)))


def copula_stage():
    # Problem 3(b): freeze selected marginals and share Kendall-derived R.
    fits=json.loads((HERE/"problem3_marginal_fits.json").read_text())
    names,_,returns,_,_,_=load_data();n,d=returns.shape
    u=np.column_stack([frozen(m).cdf(returns[:,j]) for j,m in enumerate(fits["selected"])])
    clipping=int(np.count_nonzero((u<=1e-12)|(u>=1-1e-12)))
    u=np.clip(u,1e-12,1-1e-12)
    tau=np.eye(d)
    for i in range(d):
        for j in range(i):tau[i,j]=tau[j,i]=stats.kendalltau(returns[:,i],returns[:,j]).statistic
    r=np.sin(np.pi*tau/2);np.fill_diagonal(r,1)
    original_min=float(np.linalg.eigvalsh(r)[0])
    if original_min<=1e-10:
        from problem1_analysis import higham_nearest_correlation
        r,*_=higham_nearest_correlation(r)
        ridge=max(0.,1e-10-float(np.linalg.eigvalsh(r)[0]))
        r=(r+ridge*np.eye(d))/(1+ridge)
    assert np.linalg.eigvalsh(r)[0]>0
    # Course profile: theta=1/nu in [.01,.49], 200-point grid then refinement.
    theta_grid=np.linspace(.01,.49,200)
    ll_grid=np.array([copula_loglik(u,r,1/t) for t in theta_grid])
    extended=False
    if int(ll_grid.argmax())==0:
        # A boundary at the course's nu=100 cap is not evidence of a finite
        # optimum. Extend toward the nested Gaussian limit and reprofile.
        extended=True
        extra=np.geomspace(1e-6,.01,80)[:-1]
        theta_grid=np.r_[extra,theta_grid]
        ll_grid=np.r_[[copula_loglik(u,r,1/t) for t in extra],ll_grid]
    i=int(ll_grid.argmax());lo=theta_grid[max(i-1,0)];hi=theta_grid[min(i+1,len(theta_grid)-1)]
    refined=optimize.minimize_scalar(lambda theta:-copula_loglik(u,r,1/theta),bounds=(lo,hi),
                                     method="bounded",options=dict(xatol=1e-11))
    candidates=[(theta_grid[i],ll_grid[i]),(refined.x,-refined.fun)]
    theta,ll_t=max(candidates,key=lambda p:p[1]);nu=float(1/theta)
    ll_g=copula_loglik(u,r)
    scores=[dict(family="Gaussian",**information_criteria(ll_g,0,n)),
            dict(family="Student t",nu=nu,**information_criteria(ll_t,1,n))]
    chosen=min(scores,key=lambda s:s["AICc"])["family"]
    # Independently verify density decomposition with library distributions.
    z=stats.norm.ppf(u)
    verify_g=np.sum(stats.multivariate_normal(cov=r).logpdf(z))-np.sum(stats.norm.logpdf(z))
    y=stats.t.ppf(u,nu)
    verify_t=np.sum(stats.multivariate_t(shape=r,df=nu).logpdf(y))-np.sum(stats.t.logpdf(y,nu))
    assert abs(verify_g-ll_g)<1e-8 and abs(verify_t-ll_t)<1e-8
    result=dict(names=names,n=n,dimension=d,correlation=r.tolist(),kendall_tau=tau.tolist(),
                original_min_eigenvalue=original_min,eigenvalues=np.linalg.eigvalsh(r).tolist(),
                clipped_observations=clipping,nu=nu,scores=scores,chosen=chosen,
                search_extended_above_100=extended,
                delta_BIC=float(2*(ll_t-ll_g)-np.log(n)),
                uniform_min=float(u.min()),uniform_max=float(u.max()))
    save_json("problem3_copula_fit.json",result)
    save_csv("problem3_copula_comparison.csv",[{k:s.get(k,"") for k in ("family","nu","loglik","k","AICc","BIC")} for s in scores])
    with (HERE/"problem3_copula_correlation.csv").open("w",newline="") as stream:
        writer=csv.writer(stream);writer.writerow(["stock",*names]);writer.writerows(zip(names,*r.T))
    save_csv("problem3_copula_profile.csv",[dict(nu=float(1/t),loglik=float(ll)) for t,ll in zip(theta_grid,ll_grid)])
    print("COPULA",json.dumps(result,indent=2),flush=True)


def risk(pnl,tail=.05):
    # Problem 3(c): exactly average the worst N*p scenarios (N*p is an integer).
    n=len(pnl);k=int(round(n*tail));assert abs(k-n*tail)<1e-8
    worst=np.partition(pnl,k-1)[:k]
    return -float(np.quantile(pnl,tail,method="linear")),-float(worst.mean())


def simulation_stage(nsim=200000,seed=54503):
    # Problem 3(c): joint copula uniforms, selected inverse CDFs, full repricing.
    fits=json.loads((HERE/"problem3_marginal_fits.json").read_text())
    cop=json.loads((HERE/"problem3_copula_fit.json").read_text())
    names,prices,returns,shares,books,dates=load_data();d=len(names)
    assert nsim>=5000 and nsim%400==0
    r=np.array(cop["correlation"]);rng=np.random.default_rng(seed)
    z=rng.standard_normal((nsim,d))@np.linalg.cholesky(r).T
    if cop["chosen"]=="Student t":
        # One common chi-square draw per scenario creates t tail dependence.
        latent=z/np.sqrt(rng.chisquare(cop["nu"],nsim)[:,None]/cop["nu"])
        u=stats.t.cdf(latent,cop["nu"])
    else:u=stats.norm.cdf(z)
    u=np.clip(u,np.finfo(float).eps,1-np.finfo(float).eps)
    sim=np.empty_like(u);inversion_checks=[];analytic=[]
    for j,model in enumerate(fits["selected"]):
        dist=frozen(model)
        if model["family"]=="NIG":
            # SciPy's adaptive inverse-CDF approximation, requested u-error 1e-12.
            # Its accuracy is checked against the original CDF and direct PPF.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore",RuntimeWarning)
                inv=NumericalInversePolynomial(dist,center=float(dist.mean()),u_resolution=1e-12)
            sim[:,j]=inv.ppf(u[:,j])
            check_u=np.r_[np.geomspace(1e-7,.01,15),np.linspace(.02,.98,25),1-np.geomspace(1e-7,.01,15)]
            approx=inv.ppf(check_u)
            u_error=float(np.max(abs(dist.cdf(approx)-check_u)))
            x_error=float(np.max(abs(approx-dist.ppf(check_u))))
            assert u_error<1e-9 and x_error<1e-6
            inversion_checks.append(dict(stock=names[j],max_cdf_error=u_error,max_return_error=x_error))
        else:sim[:,j]=dist.ppf(u[:,j])
        assert np.isfinite(sim[:,j]).all()
        # Analytic single-stock marginal tail provides an independent check.
        cutoff=float(dist.ppf(.05))
        tail_mean=integrate.quad(lambda x:x*dist.pdf(x),-np.inf,cutoff,epsabs=1e-10)[0]/.05
        analytic.append(dict(stock=names[j],VaR95_per_share=-prices[-1,j]*cutoff,
                             ES95_per_share=-prices[-1,j]*tail_mean))
    current=shares*prices[-1]
    # Future price = last_price * (1+return), so stock P&L = current_value*return.
    pnl=sim*current
    mask_a=np.array(books)=="A";mask_b=~mask_a
    book_a=pnl[:,mask_a].sum(axis=1);book_b=pnl[:,mask_b].sum(axis=1)
    total=pnl.sum(axis=1)
    assert np.allclose(total,book_a+book_b,rtol=1e-13,atol=1e-9)
    arrays=[pnl[:,j] for j in range(d)]+[book_a,book_b,total]
    labels=names+["Book A","Book B","Total"]
    values=list(current)+[float(current[mask_a].sum()),float(current[mask_b].sum()),float(current.sum())]
    rows=[]
    # 20 scenario batches provide Monte Carlo error estimates, not parameter CIs.
    for i,(label,a,value) in enumerate(zip(labels,arrays,values)):
        var,es=risk(a)
        batch=np.array([risk(chunk) for chunk in np.array_split(a,20)])
        mcse=batch.std(axis=0,ddof=1)/np.sqrt(20)
        row=dict(name=label,book=books[i] if i<d else label,shares=float(shares[i]) if i<d else "",
                 last_price=float(prices[-1,i]) if i<d else "",current_value=float(value),
                 mean_pnl=float(a.mean()),VaR95=var,ES95=es,VaR95_percent=100*var/value,
                 ES95_percent=100*es/value,VaR_MCSE=float(mcse[0]),ES_MCSE=float(mcse[1]))
        assert es>=var
        if i<d:
            av=analytic[i]["VaR95_per_share"]*shares[i];ae=analytic[i]["ES95_per_share"]*shares[i]
            row.update(analytic_VaR95=float(av),analytic_ES95=float(ae))
            assert abs(var-av)<6*mcse[0]+.01 and abs(es-ae)<6*mcse[1]+.01
        rows.append(row)
    sum_stock_var=sum(row["VaR95"] for row in rows[:d]);sum_stock_es=sum(row["ES95"] for row in rows[:d])
    sum_book_var=sum(row["VaR95"] for row in rows[d:d+2]);sum_book_es=sum(row["ES95"] for row in rows[d:d+2])
    result=dict(nsim=nsim,seed=seed,tail_probability=.05,copula=cop["chosen"],
                copula_nu=cop["nu"] if cop["chosen"]=="Student t" else None,
                alternative_t_copula_nu=cop["nu"],
                rows=rows,inversion_checks=inversion_checks,negative_price_scenarios=int(np.count_nonzero(sim < -1)),
                diversification=dict(sum_stock_VaR95=sum_stock_var,sum_stock_ES95=sum_stock_es,
                    sum_book_VaR95=sum_book_var,sum_book_ES95=sum_book_es,
                    stock_to_total_VaR_reduction=1-rows[-1]["VaR95"]/sum_stock_var,
                    stock_to_total_ES_reduction=1-rows[-1]["ES95"]/sum_stock_es,
                    book_to_total_VaR_reduction=1-rows[-1]["VaR95"]/sum_book_var,
                    book_to_total_ES_reduction=1-rows[-1]["ES95"]/sum_book_es),
                lowest_return=float(sim.min()),highest_return=float(sim.max()))
    save_json("problem3_risk_results.json",result)
    fields=list(rows[0])
    save_csv("problem3_risk_results.csv",[{k:r.get(k,"") for k in fields} for r in rows])
    np.savez_compressed(HERE/"problem3_simulated_pnl.npz",pnl=pnl,book_a=book_a,book_b=book_b,total=total)
    print("RISK",json.dumps(result,indent=2),flush=True)


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage",choices=["all","fit","copula","simulate"],default="all")
    parser.add_argument("--draws",type=int,default=200000);parser.add_argument("--seed",type=int,default=54503)
    args=parser.parse_args()
    if args.stage in ("all","fit"):marginal_stage()
    if args.stage in ("all","copula"):copula_stage()
    if args.stage in ("all","simulate"):simulation_stage(args.draws,args.seed)
