"""Midterm Problem 1: missing-data correlations, Higham repair, and covariance.

Run with Python 3 and NumPy. Paths are relative to this script, so execution
does not depend on the working directory. Blank cells remain missing values.
"""
from pathlib import Path
import csv
import hashlib
import json
from statistics import correlation, variance
import numpy as np

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "problem1.csv"


def higham_nearest_correlation(a, tolerance=1e-14, max_iterations=10000):
    """Unweighted Frobenius nearest correlation via Higham and Dykstra.

    PSD projection clips eigenvalues. Unit-diagonal projection resets diagonal
    entries to one. Dykstra's correction is essential to nearestness. No ridge
    or positive-definite floor is added: the requested solution may be singular.
    """
    y = np.array(a, dtype=float, copy=True)
    correction = np.zeros_like(y)
    x_previous = y.copy()
    for iteration in range(1, max_iterations + 1):
        y_previous = y.copy()
        r = y - correction
        eigenvalues, eigenvectors = np.linalg.eigh((r + r.T) / 2)
        x = (eigenvectors * np.maximum(eigenvalues, 0)) @ eigenvectors.T
        correction = x - r
        y = (x + x.T) / 2
        np.fill_diagonal(y, 1.0)
        residual = max(
            np.linalg.norm(x - x_previous, "fro") / np.linalg.norm(x, "fro"),
            np.linalg.norm(y - y_previous, "fro") / np.linalg.norm(y, "fro"),
            np.linalg.norm(y - x, "fro") / np.linalg.norm(y, "fro"),
        )
        if residual < tolerance and np.linalg.eigvalsh(y)[0] >= -10 * tolerance:
            return y, iteration, residual, correction
        x_previous = x.copy()
    raise RuntimeError("Higham iteration failed to converge")


def save_matrix(name, matrix, labels):
    with (HERE / name).open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(["series", *labels])
        for label, row in zip(labels, matrix):
            writer.writerow([label, *row])


def main():
    with SOURCE.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.reader(stream)
        labels = next(reader)
        data = np.array([[float(v) if v.strip() else np.nan for v in row]
                         for row in reader])
    assert labels == ["x1", "x2", "x3", "x4", "x5"]
    assert data.shape == (50, 5)
    observed = np.isfinite(data)

    # Problem 1(1): pairwise Pearson correlation on overlapping observations.
    # Both pair-specific means and both pair-specific SDs use the SAME rows.
    pair_counts = np.zeros((5, 5), dtype=int)
    correlations = np.eye(5)
    for i in range(5):
        for j in range(i, 5):
            mask = observed[:, i] & observed[:, j]
            pair_counts[i, j] = pair_counts[j, i] = int(mask.sum())
            value = np.corrcoef(data[mask, i], data[mask, j])[0, 1]
            correlations[i, j] = correlations[j, i] = value
            if i != j:
                independent = correlation(data[mask, i].tolist(), data[mask, j].tolist())
                assert abs(value - independent) < 1e-14
    np.fill_diagonal(correlations, 1.0)

    # Problem 1(2): full available sample variance for each series, ddof=1.
    counts = observed.sum(axis=0)
    means = np.nanmean(data, axis=0)
    variances = np.nanvar(data, axis=0, ddof=1)
    for i in range(5):
        assert abs(variances[i] - variance(data[observed[:, i], i].tolist())) < 1e-16

    # Problem 1(3): eigenvalues characterize PSD of a real symmetric matrix.
    original_eigenvalues, eigenvectors = np.linalg.eigh(correlations)
    negative_direction = eigenvectors[:, 0]
    quadratic_form = float(negative_direction @ correlations @ negative_direction)

    # Problem 1(4): nearest PSD correlation, W=I, fixed unit diagonal.
    repaired, iterations, residual, dual_psd = higham_nearest_correlation(correlations)
    repaired_eigenvalues = np.linalg.eigvalsh(repaired)
    changes = []
    for i in range(5):
        for j in range(i + 1, 5):
            difference = repaired[i, j] - correlations[i, j]
            changes.append(dict(pair=f"{labels[i]} / {labels[j]}",
                                original=float(correlations[i, j]),
                                repaired=float(repaired[i, j]),
                                change=float(difference), absolute_change=float(abs(difference))))
    changes.sort(key=lambda row: row["absolute_change"], reverse=True)

    # Independent optimality certificate for the convex nearest-matrix problem.
    # S=dual_psd >=0; Y>=0; stationarity and trace(SY)=0 give the KKT conditions.
    diagonal_multiplier = np.diag(dual_psd - repaired + correlations)
    stationarity = repaired - correlations + np.diag(diagonal_multiplier) - dual_psd
    kkt_stationarity = float(np.linalg.norm(stationarity, "fro"))
    kkt_complementarity = float(np.trace(dual_psd @ repaired))
    assert repaired_eigenvalues[0] > -1e-12
    assert np.linalg.eigvalsh(dual_psd)[0] > -1e-12
    assert kkt_stationarity < 1e-12 and abs(kkt_complementarity) < 1e-12
    assert np.max(abs(np.diag(repaired) - 1)) == 0
    tighter, _, _, _ = higham_nearest_correlation(correlations, tolerance=1e-15)
    assert np.max(abs(tighter - repaired)) < 1e-12

    # Problem 1(5): combine repaired dependence with FULL-SAMPLE variances.
    stds = np.sqrt(variances)
    covariance = repaired * np.outer(stds, stds)
    covariance_eigenvalues = np.linalg.eigvalsh(covariance)
    assert np.max(abs(np.diag(covariance) - variances)) < 1e-16
    assert covariance_eigenvalues[0] > -1e-14
    assert np.max(abs(covariance / np.outer(stds, stds) - repaired)) < 1e-14

    result = dict(source=str(SOURCE), source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  labels=labels, shape=list(data.shape), observations=counts.tolist(),
                  missing=(50-counts).tolist(), full_sample_means=means.tolist(),
                  pair_counts=pair_counts.tolist(), correlation=correlations.tolist(),
                  variances=variances.tolist(), standard_deviations=stds.tolist(),
                  original_eigenvalues=original_eigenvalues.tolist(),
                  negative_direction=negative_direction.tolist(), negative_quadratic_form=quadratic_form,
                  higham_correlation=repaired.tolist(), higham_eigenvalues=repaired_eigenvalues.tolist(),
                  higham_iterations=iterations, higham_relative_residual=residual,
                  frobenius_distance=float(np.linalg.norm(repaired-correlations, "fro")),
                  squared_frobenius_distance=float(np.sum((repaired-correlations)**2)),
                  changes=changes, covariance=covariance.tolist(),
                  covariance_eigenvalues=covariance_eigenvalues.tolist(),
                  validation=dict(kkt_stationarity=kkt_stationarity,
                                  kkt_complementarity=kkt_complementarity,
                                  tighter_run_max_difference=float(np.max(abs(tighter-repaired)))))
    (HERE / "problem1_results.json").write_text(json.dumps(result, indent=2))
    save_matrix("problem1_pairwise_correlation.csv", correlations, labels)
    save_matrix("problem1_pair_counts.csv", pair_counts, labels)
    save_matrix("problem1_higham_correlation.csv", repaired, labels)
    save_matrix("problem1_covariance.csv", covariance, labels)
    with (HERE / "problem1_variances.csv").open("w", newline="") as stream:
        writer=csv.writer(stream)
        writer.writerow(["series", "observations", "sample_variance", "sample_standard_deviation"])
        writer.writerows(zip(labels, counts, variances, stds))
    np.set_printoptions(precision=12, suppress=True, linewidth=140)
    for key in ("observations", "pair_counts", "correlation", "variances", "original_eigenvalues",
                "higham_correlation", "higham_eigenvalues", "covariance", "covariance_eigenvalues"):
        print(key, "\n", np.array(result[key]))
    print("iterations",iterations,"relative residual",residual)
    print("Frobenius distance",result["frobenius_distance"])
    print("changes",json.dumps(changes,indent=2))
    print("validation",result["validation"])


if __name__ == "__main__":
    main()
