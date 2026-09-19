# Tests 1.1–7.6: Final Implementation and Validation Report

All **25 tests** specified in `../Tests.xlsx`, from Test 1.1 through Test 7.6,
were implemented in Python. Each test produced a CSV output and passed the
applicable numerical or statistical comparison against the course reference
files in `../data/`. Six additional boundary tests also passed.

The original workbook, Julia source files, input datasets, and reference outputs
remain unchanged. Tests 8.1 and later are outside this report's scope.

## Reproduction

The implementation requires Python 3.11 or later, NumPy, pandas, and SciPy.
Validation used Python 3.13.7. Dependency versions are recorded in
`requirements.txt` and `results/diagnostics.json`.

Run these commands from this directory:

```bash
python3 -m pip install -r requirements.txt
python3 run_tests.py
python3 -m unittest discover -s . -p 'test_risk_tools.py' -v
```

Skip the installation command if the dependencies are already installed.
Alternatively, run the following from the repository root:

```bash
python3 testfiles/python_solution/run_tests.py
python3 -m unittest discover -s testfiles/python_solution -p 'test_risk_tools.py' -v
```

Input paths are resolved relative to the script, independently of the working
directory. A failed validation returns a nonzero exit code. Rerunning the script
updates this solution's results without overwriting the course reference files.

## Deliverables

- `risk_tools.py`: reusable numerical algorithms.
- `run_tests.py`: execution of all 25 tests, CSV export, reference comparisons, and mathematical checks.
- `test_risk_tools.py`: independent boundary tests using small examples.
- `results/testout*.csv`: 25 computed outputs with the same column names, ordering, and dimensions as the reference files.
- `results/validation_summary.csv`: each test's status, error measurements, and acceptance criteria.
- `results/diagnostics.json`: optimizer diagnostics, simulation errors, software versions, and SHA-256 hashes of the original files.

## Methods and Conventions

| Test | Implementation and conventions |
| --- | --- |
| 1.1–1.2 | Remove rows containing any missing values, then calculate sample covariance or Pearson correlation. |
| 1.3–1.4 | Select complete observations separately for each variable pair. Covariance uses the pair's observation count minus one as its denominator. |
| 2.1 | Use λ=0.97, assign the greatest weight to the latest row, normalize weights, and center on the weighted mean without an unbiasedness correction. |
| 2.2 | Standardize the EW covariance matrix with λ=0.94 into a correlation matrix. |
| 2.3 | Combine EW standard deviations with λ=0.97 and EW correlations with λ=0.94 using D × R × D. |
| 3.1–3.2 | Convert to correlation, truncate negative eigenvalues, normalize the diagonal, and restore the original variances. |
| 3.3–3.4 | Apply Higham alternating projections with Dykstra correction and a unit diagonal, then restore the original variances. |
| 4.1 | Compute a lower triangular Cholesky factor that supports positive semidefinite matrices and zero pivots. Verify that L Lᵀ reconstructs the input. |
| 5.1–5.2 | Generate 100,000 zero-mean Normal observations for each positive definite or positive semidefinite covariance input. |
| 5.3–5.4 | Repair the indefinite covariance input using near_psd or Higham, respectively, before generating 100,000 observations. |
| 5.5 | Retain the fewest leading principal components explaining at least 99% of total variance, then simulate 100,000 observations. |
| 6.1–6.2 | Calculate arithmetic returns Pₜ/Pₜ₋₁−1 and log returns log(Pₜ/Pₜ₋₁), retaining each return's ending date. |
| 7.1 | Estimate the sample mean and sample standard deviation (ddof=1), matching the course implementation. |
| 7.2 | Fit a location-scale Student t distribution by maximum likelihood with ν≥2.0001, three starting points, and an analytic gradient. |
| 7.3 | Jointly estimate the intercept, three regression coefficients, error scale, and degrees of freedom under t errors with error location fixed at zero. |
| 7.4 | Calculate AICc=−2LL+2k+2k(k+1)/(n−k−1), with k=3. |
| 7.5 | Fit NIG parameters by matching the sample mean, sample variance (ddof=1), unadjusted skewness, and unadjusted excess kurtosis, following Julia StatsBase conventions. |
| 7.6 | Fit the NIG distribution by SciPy maximum likelihood and convert (a,b,loc,scale) into (μ,α,β,δ). |

Every output was computed from the specified input rather than copied from its
reference answer. Tests 3 and 4 use earlier reference outputs as inputs where
explicitly required by the workbook. The independently computed dependency chain
from Test 1.3 through PSD repair and Cholesky reconstruction was also checked.

## Distribution and Regression Results

Values below are rounded for presentation; the CSV files retain full precision.

| Test | Estimated parameters or result |
| --- | --- |
| 7.1 | μ=0.046771958, σ=0.051789726 |
| 7.2 | μ=0.050100336, σ=0.044955079, ν=4.092925522 |
| 7.3 | Intercept=0.049587882, B1=1.177763237, B2=1.826955288, B3=3.056412308; σ=0.050626304, ν=4.661908802 |
| 7.4 | AICc=−279.054620985 |
| 7.5 | μ=0.023943331, α=52.947062531, β=−12.245376486, δ=0.057458901 |
| 7.6 | μ=0.019659521, α=46.923580335, β=−8.232654649, δ=0.052607862 |

For the Student t fits, σ denotes the scale parameter; the standard deviation is
σ√(ν/(ν−2)). Both t optimizations converged from all three starting points to
essentially identical objective values.

The NIG parameter conversion is α=a/scale, β=b/scale, μ=loc, and δ=scale.
The method-of-moments fit reproduces the four specified sample moment estimates.
The maximum-likelihood fit achieves a log likelihood of 1974.544444, compared
with 1974.105624 for the moment fit. These results reflect the different
objectives of the two estimation methods.

## Validation Results

All 25 requested tests passed. Deterministic comparisons use
`rtol=1e-8, atol=1e-9`. Optimized parameter comparisons in Tests 7.2, 7.3, and 7.6
allow `rtol=1e-4, atol=1e-7` to accommodate differences in optimizer termination.
The observed maximum absolute parameter differences were approximately 1.5e-8
for the t fits and 1.5e-12 for the NIG MLE fit.

The six additional tests cover pairwise missing-data selection, exponential
weighting and centering, singular Cholesky decomposition and indefinite matrix
repair, minimal PCA component selection, return/date alignment, and rejection
of infeasible NIG moment estimates. All six passed.

### Monte Carlo comparisons

Simulations use NumPy `default_rng(1234)`. Python and Julia produce different
random sequences even when given the same integer seed. Consequently, simulated
covariance matrices are compared using statistical tolerances. Samples are not
rescaled to force agreement with the target covariance.

For Gaussian observations, the standard error of sample covariance element
(i,j) is `sqrt((Σii*Σjj + Σij²)/(N−1))`. Validation requires each simulated
covariance element to lie within six standard errors of its target, and each
difference from the independent Julia reference simulation to lie within six
combined standard errors. Sample means must also lie within six standard errors
of zero. Relative Frobenius covariance error must be below 2%.
These thresholds were specified before evaluating the results.

| Test | Target covariance | Relative Frobenius error | Status |
| --- | --- | ---: | --- |
| 5.1 | Original positive definite input | 0.5525% | PASS |
| 5.2 | Original positive semidefinite input | 0.7200% | PASS |
| 5.3 | Covariance repaired with near_psd | 0.3899% | PASS |
| 5.4 | Covariance repaired with Higham | 0.3876% | PASS |
| 5.5 | Covariance reconstructed from retained principal components | 0.7604% | PASS |

PCA retained two components, explaining 99.751311% of total variance. Its target
covariance excludes discarded components, so a difference from the complete
input covariance is expected. Tests 5.3 and 5.4 similarly target repaired
covariances because the original indefinite input is not a valid covariance
matrix. Errors relative to the original input matrices are also recorded in
`validation_summary.csv`.

## Source File Clarifications

1. The workbook's actual filename is `Tests.xlsx`.
2. Some output names generated by Excel formulas for Groups 6 and 7 differ from
   the actual reference filenames. This implementation follows the existing CSV
   names, such as `testout6_1.csv` and `testout7_2.csv`.
3. The Test 2.3 comment in `test_setup.jl` reverses the decay parameters, while
   its executable code agrees with the workbook: λ=0.97 for variances and
   λ=0.94 for correlations. The implementation follows that convention.
4. The workbook describes Test 5.4's input as PSD, but its specified input,
   `test5_3.csv`, is indefinite and requires Higham repair.
