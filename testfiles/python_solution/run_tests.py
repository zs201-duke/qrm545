"""Compute all 25 requested outputs, then independently compare with fixtures.

Run from any directory: python3 /path/to/python_solution/run_tests.py
Reference files are only read by the validation step, except where Tests.xlsx
explicitly prescribes a previous reference output as the next test's input.
"""
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import pandas as pd
import scipy
from scipy import stats

from risk_tools import (
    calculate_returns, chol_psd, correlation_from_covariance, ew_covariance,
    fit_nig_mle, fit_nig_moments, fit_normal, fit_t, fit_t_regression,
    higham_psd, missing_covariance, near_psd, nig_distribution,
    simulate_normal, simulate_pca, t_aicc,
)

HERE = Path(__file__).resolve().parent
DATA = HERE.parent / "data"
OUTPUT = HERE / "results"
SAMPLE_SIZE = 100_000
SEED = 1234


def filename(test):
    # Actual corpus naming differs from Excel's generic formula for groups 6/7.
    return f"testout_{test}.csv" if int(test.split('.')[0]) <= 5 else f"testout{test.replace('.', '_')}.csv"


def matrix(name):
    return pd.read_csv(DATA / name).to_numpy(dtype=float)


def as_frame(value):
    if isinstance(value, pd.DataFrame):
        return value
    if isinstance(value, dict):
        return pd.DataFrame([value])
    return pd.DataFrame(value, columns=[f"x{i + 1}" for i in range(value.shape[1])])


def main():
    OUTPUT.mkdir(exist_ok=True)
    source_files = [HERE.parent / "Tests.xlsx", *sorted(DATA.glob("*.csv"))]
    hashes = {str(p.relative_to(HERE.parent)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files}
    results, simulations, diagnostics = {}, {}, {}
    x = matrix("test1.csv")
    for test, pairwise, correlation in [("1.1", False, False), ("1.2", False, True),
                                         ("1.3", True, False), ("1.4", True, True)]:
        results[test] = missing_covariance(x, pairwise=pairwise, correlation=correlation)

    x = matrix("test2.csv")
    results["2.1"] = ew_covariance(x, .97)
    results["2.2"] = correlation_from_covariance(ew_covariance(x, .94))
    sd = np.sqrt(np.diag(results["2.1"]))
    results["2.3"] = results["2.2"] * np.outer(sd, sd)

    for test, input_name, repair in [
        ("3.1", "testout_1.3.csv", near_psd), ("3.2", "testout_1.4.csv", near_psd),
        ("3.3", "testout_1.3.csv", higham_psd), ("3.4", "testout_1.4.csv", higham_psd),
    ]:
        original = matrix(input_name)
        repaired = repair(original)
        np.testing.assert_allclose(np.diag(repaired), np.diag(original), atol=1e-10)
        assert np.linalg.eigvalsh(repaired)[0] >= -1e-8
        results[test] = repaired
    chol_input = matrix("testout_3.1.csv")
    results["4.1"] = chol_psd(chol_input)
    np.testing.assert_allclose(results["4.1"] @ results["4.1"].T, chol_input, atol=1e-8)
    # Also exercise the full dependency chain on our own computed matrices.
    for repair in (near_psd, higham_psd):
        own = repair(results["1.3"])
        np.testing.assert_allclose(chol_psd(own) @ chol_psd(own).T, own, atol=1e-8)

    for test, name, repair in [("5.1", "test5_1.csv", near_psd),
                               ("5.2", "test5_2.csv", near_psd),
                               ("5.3", "test5_3.csv", near_psd),
                               ("5.4", "test5_3.csv", higham_psd)]:
        original = matrix(name)
        sample, target = simulate_normal(original, SAMPLE_SIZE, SEED, repair)
        results[test] = np.cov(sample, rowvar=False)
        simulations[test] = (sample, target, original)
    original = matrix("test5_2.csv")
    sample, target, count, fraction = simulate_pca(original, SAMPLE_SIZE, .99, SEED)
    results["5.5"] = np.cov(sample, rowvar=False)
    simulations["5.5"] = (sample, target, original)
    diagnostics["pca"] = {"components": count, "explained_variance": fraction,
                           "target": "rank-truncated covariance (not full original covariance)"}
    assert fraction >= .99

    prices = pd.read_csv(DATA / "test6.csv")
    results["6.1"] = calculate_returns(prices)
    results["6.2"] = calculate_returns(prices, logarithmic=True)
    np.testing.assert_allclose(np.expm1(results["6.2"].iloc[:, 1:]), results["6.1"].iloc[:, 1:], atol=1e-14)
    results["7.1"] = fit_normal(matrix("test7_1.csv")[:, 0])
    t_data = matrix("test7_2.csv")[:, 0]
    results["7.2"], diagnostics["t_fit"] = fit_t(t_data)
    regression = pd.read_csv(DATA / "test7_3.csv")
    results["7.3"], diagnostics["t_regression"] = fit_t_regression(
        regression.y, regression.drop(columns="y"))
    results["7.4"] = {"AICC": t_aicc(t_data, results["7.2"])}
    nig_data = matrix("test7_5.csv")[:, 0]
    results["7.5"] = fit_nig_moments(nig_data)
    results["7.6"] = fit_nig_mle(nig_data)
    mm, mle = nig_distribution(results["7.5"]), nig_distribution(results["7.6"])
    sample_moments = [nig_data.mean(), nig_data.var(ddof=1), stats.skew(nig_data), stats.kurtosis(nig_data)]
    np.testing.assert_allclose(mm.stats(moments="mvsk"), sample_moments, atol=1e-10)
    diagnostics["nig"] = {"moments_loglikelihood": float(mm.logpdf(nig_data).sum()),
                           "mle_loglikelihood": float(mle.logpdf(nig_data).sum())}
    assert diagnostics["nig"]["mle_loglikelihood"] >= diagnostics["nig"]["moments_loglikelihood"]

    checks = []
    for test, value in results.items():
        actual = as_frame(value)
        name = filename(test)
        actual.to_csv(OUTPUT / name, index=False, float_format="%.17g")
        reference = pd.read_csv(DATA / name)
        assert list(actual.columns) == list(reference.columns) and actual.shape == reference.shape
        if "Date" in actual:
            assert actual.Date.equals(reference.Date)
        a, b = actual.select_dtypes("number").to_numpy(), reference.select_dtypes("number").to_numpy()
        assert np.isfinite(a).all()
        error = float(np.max(np.abs(a - b)))
        row = {"test": test, "output": name, "max_abs_reference_error": error}
        if test in simulations:
            sample, target, original = simulations[test]
            variance = np.diag(target)
            se = np.sqrt((np.outer(variance, variance) + target**2) / (SAMPLE_SIZE - 1))
            target_z = float(np.max(np.abs(a - target) / se))
            reference_z = float(np.max(np.abs(a - b) / (np.sqrt(2) * se)))
            mean_z = float(np.max(np.abs(sample.mean(axis=0)) / np.sqrt(variance / SAMPLE_SIZE)))
            relative_error = float(np.linalg.norm(a - target) / np.linalg.norm(target))
            row.update(check="Monte Carlo: 6 SE and 2% relative Frobenius error",
                       target_max_covariance_z=target_z, reference_max_covariance_z=reference_z,
                       mean_max_z=mean_z, target_relative_frobenius_error=relative_error,
                       original_relative_frobenius_error=float(np.linalg.norm(a - original) / np.linalg.norm(original)))
            passed = max(target_z, reference_z, mean_z) < 6 and relative_error < .02
        else:
            # Numerical optimizers in Julia and SciPy need not terminate identically.
            rtol, atol = (1e-4, 1e-7) if test in {"7.2", "7.3", "7.6"} else (1e-8, 1e-9)
            passed = np.allclose(a, b, rtol=rtol, atol=atol)
            row.update(check=f"allclose: rtol={rtol:g}, atol={atol:g}")
        row["status"] = "PASS" if passed else "FAIL"
        checks.append(row)

    summary = pd.DataFrame(checks)
    summary.to_csv(OUTPUT / "validation_summary.csv", index=False)
    diagnostics.update(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                       pandas=pd.__version__, seed=SEED, simulations_per_test=SAMPLE_SIZE,
                       source_sha256=hashes, checks=checks)
    (OUTPUT / "diagnostics.json").write_text(json.dumps(diagnostics, indent=2), encoding="utf-8")
    for p in source_files:
        assert hashlib.sha256(p.read_bytes()).hexdigest() == hashes[str(p.relative_to(HERE.parent))]
    print(summary[["test", "status", "max_abs_reference_error"]].to_string(index=False))
    print(f"\n{sum(summary.status == 'PASS')}/{len(summary)} passed. Results: {OUTPUT}")
    if not (summary.status == "PASS").all():
        raise SystemExit(1)


if __name__ == "__main__":
    main()
