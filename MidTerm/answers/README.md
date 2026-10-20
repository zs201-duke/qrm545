# Midterm Problem 1

`Problem1_Answers.docx` is the written answer, with the original question restated for each numbered part. The write-up contains the pairwise correlations, overlap counts, marginal sample variances, eigenvalue diagnosis, Higham repair, largest changes, and reconstructed covariance matrix.

Run the labeled calculation code with Python 3 and NumPy:

```sh
python3 problem1_analysis.py
```

The script reads `../problem1.csv` without changing it. Comments identify Problem 1(1) through Problem 1(5). Output CSVs retain full numerical precision; `problem1_results.json` also records every correlation change, eigenvalues, convergence and optimality checks, and the source file's SHA-256 hash. No additional source data or network access is needed.

The covariance CSV is in squared decimal-return units. The Word document displays 10,000 times this matrix and explicitly labels that scaling. Correlation matrices are dimensionless. Variances use each series's full available sample with denominator n-1. Pairwise correlations use only the common nonmissing dates for that pair.

`build_problem1_writeup.py` rebuilds the Word document from the numerical JSON and requires python-docx. Calculations were checked using the course's Week01-Week03 methods, with independent standard-library correlation/variance calculations, a tighter Higham convergence run, and convex optimality residual checks. The final Word file was rendered and visually reviewed.
