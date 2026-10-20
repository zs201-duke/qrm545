"""Small numerical checks for the public qrm545 API."""

from __future__ import annotations

import unittest

import numpy as np

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
    t_tail_dependence,
)


class RiskMeasureTests(unittest.TestCase):
    def test_moments_use_sample_variance(self):
        result = moments([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(result["n"], 4)
        self.assertAlmostEqual(result["mean"], 2.5)
        self.assertAlmostEqual(result["variance"], 5 / 3)

    def test_historical_risk_uses_positive_loss_sign(self):
        result = historical_risk([-4.0, -3.0, -2.0, -1.0, 10.0], alpha=0.20)
        self.assertAlmostEqual(result["quantile"], -3.2)
        self.assertAlmostEqual(result["VaR"], 3.2)
        self.assertAlmostEqual(result["ES"], 4.0)

    def test_ew_weights_are_normalized_and_newest_is_largest(self):
        weights = ew_weights(20, 0.94)
        self.assertAlmostEqual(float(weights.sum()), 1.0)
        self.assertTrue(np.all(np.diff(weights) > 0))

    def test_normal_risk_returns_consistent_summary(self):
        result = normal_risk([-2.0, -1.0, 0.0, 1.0, 2.0], alpha=0.05)
        self.assertAlmostEqual(result["mean"], 0.0)
        self.assertGreater(result["VaR"], 0.0)
        self.assertGreater(result["ES"], result["VaR"])


class CovarianceTests(unittest.TestCase):
    def setUp(self):
        self.non_psd = np.array([
            [1.0, 0.9, 0.9],
            [0.9, 1.0, -0.9],
            [0.9, -0.9, 1.0],
        ])

    def check_correlation(self, matrix):
        np.testing.assert_allclose(matrix, matrix.T, atol=1e-12)
        np.testing.assert_allclose(np.diag(matrix), 1.0, atol=1e-12)
        self.assertGreaterEqual(float(np.linalg.eigvalsh(matrix).min()), -2e-10)

    def test_spectral_repair_returns_a_correlation_matrix(self):
        self.check_correlation(nearest_corr_spectral(self.non_psd))

    def test_higham_repair_returns_a_correlation_matrix(self):
        repaired, iterations = nearest_corr_higham(self.non_psd)
        self.check_correlation(repaired)
        self.assertGreater(iterations, 0)

    def test_covariance_and_portfolio_variance(self):
        covariance = covariance_from_correlation(np.eye(2), [2.0, 3.0])
        np.testing.assert_allclose(covariance, np.diag([4.0, 9.0]))
        self.assertAlmostEqual(portfolio_variance(covariance, [1.0, -1.0]), 13.0)


class CopulaTests(unittest.TestCase):
    def test_gaussian_identity_has_zero_log_copula_density(self):
        uniforms = np.array([[0.1, 0.8], [0.4, 0.6], [0.9, 0.2]])
        contributions = gaussian_copula_log_contributions(uniforms, np.eye(2))
        np.testing.assert_allclose(contributions, 0.0, atol=1e-12)

    def test_kendall_transform_detects_monotone_pair(self):
        observations = np.column_stack([np.arange(10), np.arange(10)])
        tau, correlation = kendall_correlation(observations)
        self.assertAlmostEqual(tau[0, 1], 1.0)
        self.assertAlmostEqual(correlation[0, 1], 1.0)

    def test_simulators_return_open_unit_interval(self):
        correlation = np.array([[1.0, 0.4], [0.4, 1.0]])
        gaussian = simulate_gaussian_copula(correlation, 100, np.random.default_rng(1))
        student = simulate_t_copula(correlation, 5.0, 100, np.random.default_rng(1))
        self.assertEqual(gaussian.shape, (100, 2))
        self.assertEqual(student.shape, (100, 2))
        self.assertTrue(np.all((gaussian > 0) & (gaussian < 1)))
        self.assertTrue(np.all((student > 0) & (student < 1)))

    def test_t_tail_dependence_is_positive(self):
        coefficient = t_tail_dependence(0.5, 4.0)
        self.assertGreater(coefficient, 0.0)
        self.assertLess(coefficient, 1.0)


class InformationCriterionTests(unittest.TestCase):
    def test_aicc_formula(self):
        expected = 200 + 6 + 24 / 96
        self.assertAlmostEqual(aicc(-100.0, 3, 100), expected)

    def test_student_t_fit_returns_valid_parameters(self):
        rng = np.random.default_rng(8)
        sample = 0.001 + 0.01 * rng.standard_t(7.0, size=400)
        fitted = fit_student_t(sample)
        self.assertTrue(fitted["success"])
        self.assertGreater(fitted["df"], 2.0)
        self.assertGreater(fitted["scale"], 0.0)


if __name__ == "__main__":
    unittest.main()
