"""Independent identities and boundary examples for Tests 8.1–13.9."""
import unittest

import numpy as np
import pandas as pd
from scipy import integrate, stats

from advanced_risk import (
    aggregate_risk, american_greeks, american_option, copula_information_criteria,
    distribution_risk, empirical_risk, expost_attribution, fix_correlation,
    fit_multivariate_t, gaussian_copula_loglike, gbsm, kendall_correlation,
    maximum_sharpe, profile_nu, risk_parity, simulate_copula, tail_dependence_t,
)


class AdvancedIdentities(unittest.TestCase):
    def test_analytic_es_against_numerical_integration(self):
        for distribution in (stats.norm(loc=.02, scale=.1), stats.t(5, loc=.02, scale=.1)):
            var, es = distribution_risk(distribution)
            expected = -integrate.quad(lambda x: x*distribution.pdf(x), -np.inf, -var)[0]/.05
            self.assertAlmostEqual(es, expected, places=10)
            self.assertGreater(es, var)

    def test_empirical_tail_order_and_translation(self):
        x = np.arange(-20., 20.)
        self.assertEqual(empirical_risk(x), (19., 19.5))
        np.testing.assert_allclose(empirical_risk(x+10), np.array(empirical_risk(x))-10)
        with self.assertRaises(ValueError):
            empirical_risk([1., 2.])

    def test_portfolio_aggregation_and_percentages(self):
        r = np.column_stack([np.linspace(-.1, .1, 100), np.linspace(-.1, .1, 100)])
        table = aggregate_risk(r, ["A", "B"], [100., 200.])
        np.testing.assert_allclose(table.loc[2, ["VaR95", "ES95"]].astype(float),
                                   table.loc[:1, ["VaR95", "ES95"]].sum())
        np.testing.assert_allclose(table.VaR95_Pct, table.VaR95 / [100, 200, 300])

    def test_diagonal_risk_budgets_have_closed_form(self):
        cov = np.diag([.04, .09, .16])
        budget = np.array([1., 2., .5])
        expected = np.sqrt(budget / np.diag(cov))
        expected /= expected.sum()
        np.testing.assert_allclose(risk_parity(cov, budget), expected, atol=1e-8)
        with self.assertRaises(ValueError):
            risk_parity(cov, [1, 0, 1])

    def test_sharpe_closed_form_and_binding_limits(self):
        cov = np.diag([.04, .09, .16])
        means, rf = np.array([.08, .12, .15]), .03
        expected = np.linalg.solve(cov, means-rf)
        expected /= expected.sum()
        np.testing.assert_allclose(maximum_sharpe(cov, means, rf), expected, atol=1e-7)
        constrained = maximum_sharpe(cov, means, rf, .2, .4)
        self.assertAlmostEqual(constrained.sum(), 1)
        self.assertTrue(np.all(constrained >= .2-1e-10))
        self.assertTrue(np.all(constrained <= .4+1e-10))
        with self.assertRaises(ValueError):
            maximum_sharpe(cov, means, rf, .4, .5)

    def test_zero_return_attribution_limits(self):
        zero = pd.DataFrame(np.zeros((10, 2)), columns=["A", "B"])
        table = expost_attribution([.3, .7], zero, zero, np.eye(2))
        np.testing.assert_allclose(table.iloc[:, 1:].to_numpy(), 0)
        returns = pd.DataFrame({"A": [.1, -.05, .02], "B": [-.05, .03, .01]})
        table = expost_attribution([.3, .7], returns, returns, np.eye(2))
        compounded = np.array([.3, .7]) @ (1+returns).prod().to_numpy()-1
        self.assertAlmostEqual(table.Portfolio.iloc[0], compounded)
        self.assertAlmostEqual(table.loc[1, ["A", "B", "Alpha"]].sum(), compounded)

    def test_european_put_call_parity_and_vega(self):
        s, k, t, r, q, sigma = 100., 105., .8, .04, .02, .3
        call = gbsm(True, s, k, t, r, r-q, sigma)
        put = gbsm(False, s, k, t, r, r-q, sigma)
        self.assertAlmostEqual(call["Value"]-put["Value"], s*np.exp(-q*t)-k*np.exp(-r*t))
        h = 1e-5
        fd = (gbsm(True, s, k, t, r, r-q, sigma+h)["Value"]
              - gbsm(True, s, k, t, r, r-q, sigma-h)["Value"])/(2*h)
        self.assertAlmostEqual(call["Vega"], fd, places=6)

    def test_one_step_american_tree(self):
        s, k, t, r, sigma = 100., 100., 1., .05, .2
        u, d = np.exp(sigma), np.exp(-sigma)
        p = (np.exp(r)-d)/(u-d)
        expected = np.exp(-r)*(p*max(s*u-k, 0)+(1-p)*max(s*d-k, 0))
        self.assertAlmostEqual(american_option(True, s, k, t, r, r, sigma, 1), expected)
        self.assertAlmostEqual(american_option(False, 80, 100, 0, r, r, sigma, 0), 20)

    def test_dividend_tree_against_explicit_two_step_branches(self):
        s, k, r, sigma, dividend = 100., 100., .04, .2, 3.
        dt = .5
        u, d = np.exp(sigma*np.sqrt(dt)), np.exp(-sigma*np.sqrt(dt))
        p, discount = (np.exp(r*dt)-d)/(u-d), np.exp(-r*dt)
        for call in (True, False):
            sign = 1 if call else -1
            nodes = []
            for before in (s*d, s*u):
                after = before-dividend
                hold = discount*(p*max(sign*(after*u-k), 0)+(1-p)*max(sign*(after*d-k), 0))
                nodes.append(max(hold, sign*(before-k), sign*(after-k), 0))
            expected = max(sign*(s-k), discount*((1-p)*nodes[0]+p*nodes[1]), 0)
            actual = american_option(call, s, k, 1., r, r, sigma, 2, [dividend], [1])
            self.assertAlmostEqual(actual, expected, places=12)

    def test_american_no_dividend_and_rho_convention(self):
        args = (True, 100., 100., .5, .04, .04, .2)
        analytic = gbsm(*args)["Value"]
        tree = american_option(*args, steps=500)
        self.assertLess(abs(tree-analytic), .01)
        zero_cash = american_option(*args, steps=20, dividends=[0.], dividend_steps=[10])
        self.assertAlmostEqual(zero_cash, american_option(*args, steps=20), places=12)
        greek = american_greeks(*args, steps=100)
        self.assertAlmostEqual(greek["Rho"], -.5*greek["Value"], places=6)

    def test_kendall_invariance_and_pd_repair(self):
        rng = np.random.default_rng(77)
        x = rng.normal(size=(100, 3))
        np.testing.assert_allclose(kendall_correlation(x), kendall_correlation(np.exp(x)))
        repaired = fix_correlation(np.ones((3, 3)))
        self.assertGreater(np.linalg.eigvalsh(repaired)[0], 0)
        np.testing.assert_allclose(np.diag(repaired), 1)

    def test_profile_and_scale_covariance_relation(self):
        nu, ll = profile_nu(lambda nu: -(1/nu-.2)**2)
        self.assertLess(abs(nu-5), .001)
        self.assertLess(abs(ll), 1e-8)
        x = np.random.default_rng(77).normal(size=(50, 2))*.02
        mean, scale, nu, ll = fit_multivariate_t(x)
        np.testing.assert_allclose(mean, x.mean(axis=0))
        np.testing.assert_allclose(np.diag(scale)*nu/(nu-2), x.var(axis=0, ddof=1))
        self.assertTrue(np.isfinite(ll))

    def test_gaussian_independence_and_tail_dependence(self):
        u = np.random.default_rng(55).uniform(.001, .999, size=(100, 3))
        self.assertAlmostEqual(gaussian_copula_loglike(u, np.eye(3)), 0, places=10)
        self.assertGreater(tail_dependence_t(.5, 4), tail_dependence_t(.1, 4))
        self.assertGreater(tail_dependence_t(.5, 4), tail_dependence_t(.5, 50))
        aicc, bic = copula_information_criteria(10., 1, 100)
        self.assertAlmostEqual(aicc, -18+4/98)
        self.assertAlmostEqual(bic, np.log(100)-20)

    def test_copula_uniform_margins_and_reproducibility(self):
        corr = np.array([[1., .4], [.4, 1.]])
        for nu in (None, 5.):
            u = simulate_copula(corr, 20_000, seed=44, nu=nu)
            np.testing.assert_array_equal(u, simulate_copula(corr, 20_000, seed=44, nu=nu))
            for column in u.T:
                self.assertLess(stats.kstest(column, "uniform").statistic, .02)
            tau = stats.kendalltau(u[:, 0], u[:, 1]).statistic
            self.assertLess(abs(tau-2*np.arcsin(.4)/np.pi), .02)


if __name__ == "__main__":
    unittest.main()
