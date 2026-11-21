# Tests 1.1–13.9: Final Implementation and Validation Report

All **50 tests** specified in `../Tests.xlsx`, from Test 1.1 through Test 13.9,
were implemented in Python. Each test produced a CSV output and passed the
applicable numerical or statistical comparison against the course reference
files in `../data/`. **Twenty independent tests** of mathematical identities and
boundary behavior also passed. The latest extension covers all 25 tests from
8.1 through 13.9. PASS refers to the explicitly documented validation rules in
this implementation, not an external instructor grading system.

The original workbook, Julia source files, input datasets, and reference outputs
remain unchanged. Functions compute results from the supplied inputs; reference
outputs are used for validation, not substituted for computed answers.

## Reproduction

The implementation requires Python 3.11 or later, NumPy, pandas, and SciPy.
Dependency versions are recorded in `requirements.txt`. The Python and package
versions for each run are recorded in `results/diagnostics.json` and
`results/advanced_diagnostics.json`.

Run these commands from this directory:

```bash
python3 -m pip install -r requirements.txt
python3 run_all_tests.py
```

Skip the installation command if the dependencies are already installed.
Alternatively, run the following from the repository root:

```bash
python3 testfiles/python_solution/run_all_tests.py
```

To run only Tests 8.1–13.9, use `python3 run_advanced_tests.py` from this directory.
The original `python3 run_tests.py` still runs Tests 1.1–7.6.
The combined entry point also runs all 20 independent unit tests.

Input paths are resolved relative to the script, independently of the working
directory. A failed validation returns a nonzero exit code. Rerunning the script
updates this solution's results without overwriting the course reference files.

## Deliverables

- `risk_tools.py`: reusable algorithms for Tests 1.1–7.6 and marginal distribution fitting.
- `advanced_risk.py`: reusable risk measures, portfolio optimization, attribution, option pricing, and copula algorithms for Tests 8.1–13.9.
- `run_tests.py` and `run_advanced_tests.py`: compute and validate the first and second groups of 25 tests, respectively.
- `run_all_tests.py`: one entry point for all 50 workbook tests and 20 independent tests.
- `test_risk_tools.py` and `test_advanced_risk.py`: independent mathematical and boundary tests.
- `results/testout*.csv`: 50 computed outputs matching the reference column names, ordering, and dimensions.
- `results/all_validation_summary.csv`: combined statuses, error measurements, and acceptance criteria for all 50 workbook tests.
- `results/validation_summary.csv` and `results/advanced_validation_summary.csv`: validation details for the two groups.
- `results/diagnostics.json` and `results/advanced_diagnostics.json`: fit diagnostics, simulation errors, software versions, and SHA-256 hashes of the original files.

## Methods and Conventions: Tests 1.1–7.6

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

## Validation Results: Tests 1.1–7.6

All 25 tests in this group passed. Deterministic comparisons use
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

## Methods and Results: Tests 8.1–13.9

### Tests 8.1–8.6: Value at Risk and Expected Shortfall

All risk measures use a 5% lower-tail probability (95% confidence). Absolute risk
is the negative return quantile or negative tail mean. Risk measured relative to
the mean adds the fitted distribution mean, or the simulated sample mean for
simulation tests. Positive numbers therefore denote losses.

`distribution_risk` computes analytic Normal and location-scale Student t VaR
and ES. `empirical_risk` sorts the observations and follows the course's
order-statistic convention: average the observations at one-based indices
floor(Nα) and ceil(Nα), then average all observations at or below that threshold
for ES. It does not substitute NumPy's default interpolated percentile.

| Test | Method | Absolute risk | Risk relative to mean |
| --- | --- | ---: | ---: |
| 8.1 | Normal VaR | 0.038414561 | 0.085186518 |
| 8.2 | Student t VaR | 0.045115232 | 0.095215568 |
| 8.3 | Student t simulated VaR | 0.041309788 | 0.092566277 |
| 8.4 | Normal ES | 0.060055373 | 0.106827331 |
| 8.5 | Student t ES | 0.092156371 | 0.142256707 |
| 8.6 | Student t simulated ES | 0.092746855 | 0.143325756 |

Tests 8.3 and 8.6 each use 10,000 observations, with fixed seeds 8 and 86.
Their differences from both the analytical target and the Julia simulations are
checked statistically. The fitted distribution is recalculated from the original
`test7_2.csv` input. Analytic ES integrates the entire tail; the Julia reference
numerical integration starts at its 1e-12 quantile, explaining tiny ES differences.

### Test 9.1: Gaussian Copula Portfolio Risk

The portfolio file specifies 100 shares of A at 20 and 100 shares of B at 30,
giving position values of 2,000 and 3,000. A receives a Normal margin and B a
fitted t margin. Following this test's reference procedure, the Gaussian copula
uses the Spearman correlation of marginal probability transforms directly.
This differs from the Kendall transformation used in Test 13.

`simulate_copula` generates 100,000 dependent observations with seed 1234.
`aggregate_risk` calculates each position's P&L and sums P&L across positions
before computing portfolio risk. Portfolio VaR is not the sum of individual VaRs.

| Position | VaR95 | ES95 | VaR95 / current value | ES95 / current value |
| --- | ---: | ---: | ---: | ---: |
| A | 94.441218 | 119.498116 | 0.047220609 | 0.059749058 |
| B | 117.629808 | 171.383335 | 0.039209936 | 0.057127778 |
| Total | 166.587867 | 226.503415 | 0.033317573 | 0.045300683 |

### Tests 10.1–10.4: Portfolio Optimization

`risk_parity` solves the convex risk-budget objective
`0.5 xᵀΣx − Σᵢ bᵢ log(xᵢ)`, then normalizes weights to sum to one. It verifies
that each share of portfolio variance, `wᵢ(Σw)ᵢ/(wᵀΣw)`, equals the normalized
risk budget. Test 10.1 uses equal shares; Test 10.2 gives X5 half the budget of
each other asset.

`maximum_sharpe` maximizes `(wᵀμ − 0.04)/sqrt(wᵀΣw)` subject to full investment
and the specified bounds. Both tests use `test5_2.csv`, as required by the Excel
workbook. Test 10.3 permits zero weights, matching the reference optimizer's
nonnegative constraint. Test 10.4 imposes 0.1 ≤ wᵢ ≤ 0.5.

| Test | X1 | X2 | X3 | X4 | X5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 10.1 | 0.035464 | 0.025806 | 0.056469 | 0.265920 | 0.616341 |
| 10.2 | 0.050242 | 0.036560 | 0.080399 | 0.378608 | 0.454191 |
| 10.3 | 0 | 0 | 0 | 0.121311 | 0.878689 |
| 10.4 | 0.1 | 0.1 | 0.1 | 0.5 | 0.2 |

The reference-generation script instead reads `test5_3.csv` for Tests 10.3 and
10.4. Both inputs were solved independently to investigate this discrepancy.
For these data, the optimal weights agree within approximately 1.4e-8; the
reported outputs use the workbook's specified input. The Sharpe ratios need not
agree across different covariance inputs. The Julia weights also contain tiny
constraint violations near −1e-8; Python weights satisfy the nonnegative bounds.

### Tests 11.1–11.2: Ex-Post Attribution

`expost_attribution` updates buy-and-hold weights after each period, computes
factor exposures from those weights and the supplied betas, and treats the
unexplained portfolio return as Alpha. Carino linking allocates the compounded
portfolio return across factors and Alpha. Volatility attribution uses each
component's covariance with portfolio returns divided by portfolio volatility.

| Test | Compounded portfolio return | Portfolio standard deviation |
| --- | ---: | ---: |
| 11.1 | 0.081098 | 0.014787 |
| 11.2 | 0.105249 | 0.012239 |

The output CSVs include the complete TotalReturn, Return Attribution, and Vol
Attribution rows. Attributed returns reconcile to total compounded return, and
component volatilities reconcile to portfolio volatility. A negative component
volatility is valid and indicates a negative covariance contribution. Zero-return
periods use the continuous limit log(1+r)/r → 1.

### Tests 12.1–12.3: Option Pricing and Greeks

`gbsm` supplies European option values and analytic Greeks. `american_option`
uses a Cox–Ross–Rubinstein tree with early-exercise comparisons at each node.
Continuous-dividend American options use 500 steps. For discrete dividends,
the tree restarts after subtracting the cash dividend at each ex-dividend date;
pre-dividend exercise is compared with continuation. Test 12.3 uses two steps
per day, so 250 days correspond to 500 steps and dividend days 75/150 correspond
to steps 150/300. The day-count denominator is read from each input row.

| ID | European value (12.1) | American continuous-dividend value (12.2) |
| --- | ---: | ---: |
| 1 | 3.260824 | 3.259347 |
| 2 | 2.646281 | 2.692775 |
| 3 | 22.043329 | 22.050266 |
| 4 | 20.449083 | 21.019233 |

The small call difference in row 1 is finite-tree approximation error; without
dividends, its American value converges to the European value as the tree is
refined. In Test 12.3, the discrete-dividend Call and Put values are **14.503386**
and **11.779632**, respectively.

The Greeks deliberately retain the reference conventions:

- Test 12.1 Rho changes the interest rate while holding dividend yield fixed;
  Theta is calendar-time decay, −∂V/∂T.
- Test 12.2 Rho holds carry `b` fixed while changing the discount rate;
  its column labeled Theta is **+∂V/∂T**. These columns are therefore not directly
  comparable to their Test 12.1 counterparts.
- Test 12.2 uses centered finite differences, with step
  `eps^(1/3) × max(abs(parameter), 1)`. Gamma uses a separate spot bump of 1.5.
- Vega is per unit change in volatility, Rho per unit change in rate, and Theta
  per year. No division by 100 or by the number of days is applied.

### Tests 13.1–13.9: Multivariate t and Copulas

`kendall_correlation` applies `ρ=sin(π τ/2)` to pairwise Kendall correlations,
repairs indefiniteness if needed, and adds a small ridge when required for
positive definiteness. `fit_multivariate_t` follows the course's rank-based
profile procedure: hold the sample mean and standard deviations fixed, use the
Kendall correlation matrix, and set `S = D R D × (ν−2)/ν`.
The returned S is a **scale matrix**, with covariance `νS/(ν−2)`.
This procedure is not an unconstrained joint MLE over all mean and scale entries.

`profile_nu` evaluates 200 equally spaced values of 1/ν on [0.01, 0.49], then
200 values between the best grid point's neighbors. Thus the actual degrees of
freedom range is approximately [2.0408, 100]. Test 13.4 gives
**ν=5.823530882**, with log likelihood **3811.275358**.

For the copulas, each return series receives its own fitted t margin. Gaussian
and t copula log likelihoods subtract the sum of transformed marginal log
densities from the joint log density. Both use the same Kendall correlation R;
only the t copula adds a profiled ν. Its estimate is **5.946515745**.

| Copula | Log likelihood | Incremental parameter count | AICc | BIC |
| --- | ---: | ---: | ---: | ---: |
| Gaussian | 98.650447 | 0 | −197.300894 | −197.300894 |
| T | 128.698689 | 1 | −255.381248 | −251.875916 |

Both criteria select the t copula. The parameter counts follow the exercise's
conditional comparison, holding the common estimated margins and R fixed; they
are not counts of every parameter in the complete joint return model.

Test 13.8 uses `2 t_(ν+1)(−sqrt((ν+1)(1−ρ)/(1+ρ)))` for lower-tail dependence.
All ten pairwise values are positive, ranging approximately from 0.081732 to
0.130838. For these nonsingular correlations, the Gaussian copula's asymptotic
tail dependence is zero.

Test 13.9 generates 100,000 observations with seed 13 and a shared chi-square
shock per multivariate observation. The common shock is essential to the t
copula's joint tails. The resulting portfolio VaR95 is **163.911588** and ES95 is
**230.357272**, or **1.639116%** and **2.303573%** of the 10,000 current value.
All five position rows and the portfolio total are included in `testout13_9.csv`.

## Validation Results: Tests 8.1–13.9

All **25/25** new tests passed: 21 deterministic comparisons and four simulation
comparisons. Labels, row/column dimensions, and identifier columns are checked
as well as numeric values. None of the new computation functions reads a
reference-output file. Reference comparisons occur after results are computed.

Deterministic tolerances are `rtol=1e-8, atol=1e-8`, with these exceptions:

| Tests | Relative tolerance | Absolute tolerance | Reason |
| --- | ---: | ---: | --- |
| 10.1–10.4 | 1e-5 | 5e-7 | Constrained optimizer termination and tiny reference bound violations |
| 12.2 | 1e-5 | 5e-6 | Numerical differentiation of a finite tree |
| 13.5–13.8 | 1e-7 | 1e-6 | Marginal MLE and inverse-CDF engine differences |

The largest observed absolute discrepancy among the new deterministic results
is approximately **8.2e-8**. The tolerances were specified before the first
validation run and were not increased to make a failing comparison pass.

### Simulation uncertainty

Monte Carlo results cannot be expected to equal Julia outputs digit for digit.
The four new simulation tests require every numeric result to be within **six
combined asymptotic standard errors** of its reference. For equal-size independent
samples from the same fitted model, the combined SE is estimated as √2 times the
Python sample's SE. These are approximate statistical checks, not deterministic
equality guarantees or formal simultaneous confidence intervals.

For q equal to the lower-tail return quantile and f(q) its density, the VaR
influence function is `(1{x≤q}−α)/f(q)`. The ES influence function is
`−(min(x−q,0)−mean(min(x−q,0)))/α`. The sample standard deviation of the influence
function divided by √N estimates the standard error. Mean-relative measures add
the mean's influence function `x−mean(x)`. Fitted densities are used for known
margins; a Gaussian KDE estimates the aggregate portfolio P&L density for VaR.
These errors measure simulation uncertainty conditional on the fitted model,
not the uncertainty in estimating that model from historical data.

| Test | Simulated observations | Largest reference discrepancy in combined SE | Status |
| --- | ---: | ---: | --- |
| 8.3 | 10,000 | 2.7081 | PASS |
| 8.6 | 10,000 | 0.2950 | PASS |
| 9.1 | 100,000 | 2.7060 | PASS |
| 13.9 | 100,000 | 2.4839 | PASS |

Tests 8.3 and 8.6 additionally pass comparisons with the analytical t risk
measures. Full standard-error arrays, fixed seeds, and comparisons are saved in
`advanced_diagnostics.json`. For context, the largest raw difference in Test 9.1
is 4.522789 in dollar ES; the largest in Test 13.9 is 1.785325. Their PASS statuses
refer to statistical consistency, not exact numerical matching.

The 14 new independent tests verify analytic ES against numerical integration,
empirical quantile indexing, P&L aggregation, closed-form risk budgets and Sharpe
weights, attribution reconciliation and zero-return limits, put-call parity,
finite-difference Vega, explicit one/two-step trees, dividend transitions,
American Greek conventions, Kendall invariance, profile/scale relationships,
copula independence, information criteria, tail dependence, and simulated uniform
margins. Together with the six existing tests, all **20** pass.

## Source File Clarifications

1. The workbook's actual filename is `Tests.xlsx`.
2. Some output names generated by Excel formulas for Groups 6 through 12 differ from
   the actual reference filenames. This implementation follows the existing CSV
   names, such as `testout6_1.csv` and `testout7_2.csv`.
3. The Test 2.3 comment in `test_setup.jl` reverses the decay parameters, while
   its executable code agrees with the workbook: λ=0.97 for variances and
   λ=0.94 for correlations. The implementation follows that convention.
4. The workbook describes Test 5.4's input as PSD, but its specified input,
   `test5_3.csv`, is indefinite and requires Higham repair.
5. Tests 10.3/10.4 name `test5_2.csv` in Excel but use `test5_3.csv` in the
   reference-generation script. The outputs follow Excel, with the alternative
   input comparison documented above. The Test 10.3 label says w>0, while the
   reference constraints and optimal solution allow zero weights.
6. The Test 11.2 input list misspells the weights filename as
   `test_11_2_weights.csv`; the supplied file is `test11_2_weights.csv`.
7. Test 12.2's Rho and Theta use the reference script's partial-derivative
   conventions detailed above. Test 12.3 requests option values only.
