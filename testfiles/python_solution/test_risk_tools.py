"""Small independent examples to test boundaries beyond the course fixtures."""
import unittest

import numpy as np
import pandas as pd

from risk_tools import (calculate_returns, chol_psd, ew_covariance, fit_nig_moments,
                        higham_psd, missing_covariance, near_psd, simulate_normal,
                        simulate_pca)


class NumericalBoundaries(unittest.TestCase):
    def test_pairwise_uses_each_pairs_own_sample(self):
        x = [[1, 2], [2, np.nan], [3, 6]]
        np.testing.assert_allclose(missing_covariance(x), [[2, 4], [4, 8]])
        np.testing.assert_allclose(missing_covariance(x, pairwise=True), [[1, 4], [4, 8]])
        with self.assertRaises(ValueError):
            missing_covariance([[1, np.nan], [np.nan, 2]])

    def test_weighted_center_and_latest_row(self):
        # Weights 1/3, 2/3 give mean 3 and variance 2, without a Bessel correction.
        np.testing.assert_allclose(ew_covariance([[1], [4]], .5), [[2]])
        with self.assertRaises(ValueError):
            ew_covariance([[1], [4]], 1)

    def test_singular_cholesky_and_indefinite_repair(self):
        singular = np.array([[1., 1.], [1., 1.]])
        root = chol_psd(singular)
        np.testing.assert_allclose(root @ root.T, singular)
        bad = np.array([[1., 2.], [2., 1.]])
        with self.assertRaises(ValueError):
            chol_psd(bad)
        for repair in (near_psd, higham_psd):
            target = repair(bad)
            np.testing.assert_allclose(target, singular, atol=1e-8)
            samples, _ = simulate_normal(bad, n=20, repair=repair)
            self.assertTrue(np.isfinite(samples).all())

    def test_pca_minimal_component_selection(self):
        _, target, count, fraction = simulate_pca(np.diag([99., 1.]), n=20, explained=.99)
        self.assertEqual(count, 1)
        self.assertAlmostEqual(fraction, .99)
        np.testing.assert_allclose(target, np.diag([99., 0.]))

    def test_returns_keep_dates_and_drop_first_row(self):
        prices = pd.DataFrame({"Date": ["2020-01-01", "2020-01-02", "2020-01-03"],
                               "asset": [100., 110., 99.]})
        result = calculate_returns(prices)
        self.assertEqual(result.Date.tolist(), prices.Date.tolist()[1:])
        np.testing.assert_allclose(result.asset, [.1, -.1])
        np.testing.assert_allclose(calculate_returns(prices, True).asset, np.log([1.1, .9]))

    def test_nig_rejects_infeasible_moments(self):
        with self.assertRaises(ValueError):
            fit_nig_moments(np.arange(10.))


if __name__ == "__main__":
    unittest.main()
