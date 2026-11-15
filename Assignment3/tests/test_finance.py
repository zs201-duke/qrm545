"""Independent economic checks, not snapshots of this assignment's answers."""
import sys
from pathlib import Path
import unittest
from itertools import combinations
import json
import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from options import gbsm, greeks, implied_vol, crr_all
from risklib import risk, tangency, efficient_weights


def exhaustive_tree(spot, strike, T, r, vol, n, divs):
    """Independent non-recombining path-by-path implementation for small n.

    This deliberately does not use crr_all's segment/array rollback. It visits
    every up/down path and takes early exercise at every individual node.
    """
    dt=T/n; u=np.exp(vol*np.sqrt(dt)); p=(np.exp(r*dt)-1/u)/(u-1/u)
    def visit(s, j):
        pre=s
        s=max(s-divs.get(j,0.),0.)
        if j==n:
            return np.array([max(s-strike,0)]*2+[max(strike-s,0)]*2,float)
        cont=np.exp(-r*dt)*(p*visit(s*u,j+1)+(1-p)*visit(s/u,j+1))
        # Both sides of an instantaneous cash jump are legitimate stopping
        # times. For a put, exercising just AFTER the jump can dominate both
        # pre-jump exercise and waiting for the next CRR step.
        cont[1]=max(cont[1],pre-strike,s-strike,0.)
        cont[3]=max(cont[3],strike-pre,strike-s,0.)
        return cont
    return visit(spot,0)


class OptionChecks(unittest.TestCase):
    def test_gbsm_parity_and_price_bounds(self):
        for k in [50,100,150]:
            c=gbsm("Call",100,k,.5,.05,.03,.3)
            p=gbsm("Put",100,k,.5,.05,.03,.3)
            self.assertAlmostEqual(c-p,100*np.exp(-.02*.5)-k*np.exp(-.05*.5),places=11)
            self.assertGreaterEqual(c,gbsm("Call",100,k,.5,.05,.03,0))
            self.assertGreaterEqual(p,gbsm("Put",100,k,.5,.05,.03,0))

    def test_greeks_against_independent_finite_differences(self):
        s,k,T,r,b,v=101,100,.4,.045,.025,.32
        for kind in ("Call","Put"):
            g=greeks(kind,s,k,T,r,b,v)
            h=.01
            f=lambda S: gbsm(kind,S,k,T,r,b,v)
            self.assertAlmostEqual(g["delta"],(f(s+h)-f(s-h))/(2*h),places=7)
            self.assertAlmostEqual(g["gamma"],(f(s+h)+f(s-h)-2*f(s))/h**2,places=6)
            hv=1e-5;ht=1e-5
            self.assertAlmostEqual(g["vega"],(gbsm(kind,s,k,T,r,b,v+hv)-gbsm(kind,s,k,T,r,b,v-hv))/(2*hv),places=6)
            self.assertAlmostEqual(g["theta"],-(gbsm(kind,s,k,T+ht,r,b,v)-gbsm(kind,s,k,T-ht,r,b,v))/(2*ht),places=6)

    def test_implied_vol_roundtrip_and_invalid_quote(self):
        for kind in ("Call","Put"):
            price=gbsm(kind,100,107,.2,.04,.03,.34)
            iv,status=implied_vol(kind,price,100,107,.2,.04,.03)
            self.assertEqual(status,"ok");self.assertAlmostEqual(iv,.34,places=10)
        iv,status=implied_vol("Call",1.,100,50,.2,.04,.04)
        self.assertTrue(np.isnan(iv));self.assertIn("below",status)

    def test_tree_against_exhaustive_paths_with_two_dividends(self):
        args=(48.5,50.,.5,.045,.3,10)
        a=crr_all(*args,((.1,.25),(.4,1.5)))
        b=exhaustive_tree(*args,{2:.25,8:1.5})
        np.testing.assert_allclose(a,b,rtol=1e-12,atol=1e-12)

    def test_american_dominance_dividend_parity_and_monotonicity(self):
        args=(48.5,50.,.5,.045,.3,100)
        nodiv=crr_all(*args); div=crr_all(*args,((.1,.25),(.4,1.5)))
        self.assertAlmostEqual(nodiv[0],nodiv[1],places=10)
        for v in (nodiv,div):
            self.assertGreaterEqual(v[1],v[0]);self.assertGreaterEqual(v[3],v[2])
        pv=.25*np.exp(-.045*.1)+1.5*np.exp(-.045*.4)
        self.assertAlmostEqual(div[0]-div[2],48.5-pv-50*np.exp(-.045*.5),places=9)
        self.assertLess(div[1],nodiv[1]);self.assertGreater(div[3],nodiv[3])
        with self.assertRaises(ValueError): crr_all(*args[:5],101,((.1,.25),(.4,1.5)))

    def test_tree_converges_to_closed_form(self):
        tree=crr_all(100,100,.5,.05,.3,1000)
        for idx,kind in [(0,"Call"),(2,"Put")]:
            self.assertLess(abs(tree[idx]-gbsm(kind,100,100,.5,.05,.05,.3)),.003)


class RiskAndPortfolioChecks(unittest.TestCase):
    def test_exact_probability_mass_es_and_coherence(self):
        x=np.array([-10.,-4.,1.,3.,4.])
        # Worst 1.5 observations, not the worst 2 in full.
        self.assertAlmostEqual(risk(x,.3)["es"],8.)
        y=np.array([1.,-8.,-5.,2.,4.])
        self.assertLessEqual(risk(x+y,.3)["es"],risk(x,.3)["es"]+risk(y,.3)["es"]+1e-12)
        self.assertAlmostEqual(risk(x+2,.3)["es"],risk(x,.3)["es"]-2)

    def test_tangency_against_independent_direct_search(self):
        mu=np.array([.008,.003,.011,.006]);rf=.0025
        sd=np.array([.05,.014,.09,.017])
        cov=np.diag(sd**2)
        for mode in ["long_only","capped"]:
            w=tangency(mu,cov,rf,mode)
            bounds=[(0,1)]*4
            if mode=="capped":bounds[-1]=(0,.2)
            objective=lambda x: -(x@(mu-rf))/np.sqrt(x@cov@x)
            direct=minimize(objective,np.ones(4)/4 if mode=="long_only" else [.2,.4,.2,.2],
                method="SLSQP",constraints=[dict(type="eq",fun=lambda x:x.sum()-1)],
                bounds=bounds,options=dict(ftol=1e-12,maxiter=1000))
            self.assertTrue(direct.success)
            self.assertAlmostEqual(objective(w),direct.fun,places=8)
            np.testing.assert_allclose(w.sum(),1.,atol=1e-12)

    def test_frontier_constraints_and_endpoint(self):
        mu=np.array([.005,.008,.011]);cov=np.diag([.01,.02,.03])
        for target in [.006,.009,.011]:
            w=efficient_weights(mu,cov,target)
            self.assertAlmostEqual(w.sum(),1,places=10)
            self.assertAlmostEqual(w@mu,target,places=10)
            self.assertGreaterEqual(w.min(),-1e-9)


if __name__=="__main__":unittest.main()
