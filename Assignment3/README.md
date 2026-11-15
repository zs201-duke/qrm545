# FinTech 545 - Assignment 3

The written submission is `output/pdf/Assignment3_Report.pdf`. An editable
matching version is `Assignment3_Answers.md`. Every subquestion in Problems
1-5 is answered using the required **Predict - Fit - Reconcile** structure.

## Contents

- `analysis.py`: diagnostics, five problem analyses, plots and saved estimates.
- `options.py`: my own GBSM formula, Greeks, IV inversion and binomial trees.
- `risklib.py`: moments, distribution fitting, OLS, AICc, VaR/ES and portfolios.
- `build_report.py`: report generation from the saved results.
- `predictions.md`: predictions saved before the later fitting stage.
- `data/`: the seven provided CSV inputs, copied unchanged from the course repo.
- `figures/`: all figures referenced in the written response.
- `results/`: full-precision JSON, quote CSVs, provenance and verification logs.
- `tests/test_finance.py`: nine independent numerical and economic checks.
- `fonts/`: portable DejaVu report fonts and their license.
- `COURSE_NOTES_zh.md`: Chinese explanations and Week 1-8 course mapping.
- `source_manifest.json`: reviewed lecture sources and input file hashes.

## Setup

Python 3.11 or later is recommended. From the repository root:

```bash
cd Assignment3
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

No Julia, Quarto, TeX, option-pricing package or market-data download is needed.
The report includes its fonts. This submission was analyzed with Python 3.13
and built using the bundled Python/ReportLab runtime. Versions are recorded in
`results/environment.json`.

## Reproduce all results

```bash
python analysis.py prepare
# predictions.md already contains the preserved pre-fit predictions.
# Read the diagnostic outputs and that file before continuing.
python analysis.py fit
python -m unittest discover -s tests -v
python build_report.py
```

The scripts resolve paths from their own location, so they also work when
invoked as `python Assignment3/analysis.py fit` from the repository root.
Preparation computes only the diagnostics permitted in the prediction parts:
parity, exercise thresholds, initial Greeks, sample moments, CAPM regressions
and residual-factor correlations. It does not invert IV, run a dividend tree,
fit the return distributions, optimize portfolios or fit FF3/Carhart4.

Fitting requires the preparation result and predictions file to exist, verifies
input data SHA-256 hashes, and records the prediction hash in
`results/fit_provenance.json`. Rerunning prepare changes its run timestamp; it
does not alter the preserved prediction text. The original fitting provenance
is also kept in `results/original_fit_provenance.json`.

The default run uses N=400 for reported dividend-tree prices and Greeks,
one million ten-day paths **per distribution**, and 500 whole-month bootstrap
replicates. It also computes neighboring convergence points through 600/605.
The analysis generally takes about a minute or two on a current laptop;
speed and peak memory depend on hardware. The four-channel exact dividend
subtree implementation gets expensive as N grows; it uses no interpolation.

Individual problems can be rerun, for example:

```bash
python analysis.py fit --problem 1
python analysis.py fit --problem 2 --steps 400
python analysis.py fit --problem 3 --nsim 1000000 --seed 5452026
python analysis.py fit --problem 4 --bootstrap 500 --seed 5452026
python analysis.py fit --problem 5
```

Keep the default parameters to reproduce the submitted PDF's numerical
discussion. Custom parameters create sensitivity results, but some explanatory
sentences in the report intentionally refer to the submitted default run.

## Conventions that affect the answers

- Arithmetic daily returns are `P[t]/P[t-1]-1`. Sample variances use `ddof=1`.
  Distribution MLE uses its likelihood convention, with Normal variance divided
  by n. Skewness and excess kurtosis use finite-sample correction.
- GBSM uses continuously compounded rates and cost of carry. Problem 1 uses
  `T=35/365`, `r=0.0425`, `b=r-0.006`. Each bid/mid/ask is checked for price
  bounds; there are nine invalid bid inversions, all reported explicitly.
- Vega is dollars per 1.0 decimal volatility. A one-cent price change gives
  `0.01/vega` decimal volatility, or `1/vega` percentage points.
- Dividend-tree dates must land exactly on steps. Each cash jump starts new
  independent subtrees at `max(S-D,0)`. Exercise on both sides of the jump is
  allowed. There is no adjusted-spot or interpolation approximation inside the
  dividend tree. The floor affects only economically negligible remote states
  here; European cash-dividend put-call parity is checked numerically.
- American-minus-European premiums are calculated on the **same tree** to avoid
  confusing discretization error with the exercise premium. No-dividend
  European prices are also reported from exact GBSM as instructed.
- Theta is signed change per model year of elapsed time. The Problem 3 time
  change is `10/255`. Stock holdings do not create an invented financing leg.
- All Problem 3 paths contain ten separately sampled iid daily returns, which
  are compounded. Fitted Normal and t locations are set to zero for simulation;
  t scale is not its standard deviation. No risk-neutral drift is added to
  physical return scenarios. IV remains unchanged when positions are repriced.
- Delta-normal uses the sample daily SD, sqrt(10) scaling and dollar delta.
  It omits theta. Delta-gamma and delta-gamma-theta comparisons use the very same
  terminal stock scenarios as full revaluation.
- VaR/ES are positive for losses. Empirical VaR uses the inverse empirical CDF.
  Primary empirical ES averages exactly alpha probability mass, including a
  fractional boundary observation when alpha*n is not an integer. For 240
  monthly returns at 1%, it uses 2 + 0.4 observations divided by 2.4. The PDF and
  results also give the classroom shortcut, mean of all observations at or
  below the interpolated quantile (three full months at 1%).
- Problem 4 uses a nominal monthly risk-free return `0.03/12`, and reports
  monthly VaR/ES. Portfolio means and covariances use the full monthly sample.
  Annualized Sharpe uses sqrt(12). Bootstrap samples whole monthly rows.
- Factor CSV column headers are stripped; both factors and RF are divided by
  100. Fund returns are already decimals. Mkt-RF is not reduced by RF again.
  Regressions use fund **excess** returns and one identical matched date sample.
- OLS SEs use residual variance `SSE/(n-p)`. AICc uses Gaussian MLE variance
  `SSE/n` and counts intercept, slopes and variance (k=3,5,6). HC3 SE/t
  diagnostics supplement the conventional results; they are not HAC estimates.
- The latest ten years of factors means 2014-10-01 to 2024-09-30, as the supplied
  files end in 2024. Expected total returns include average RF. Main annual
  expected returns use 255 times the expected daily arithmetic return;
  compounded alternatives and realized CAGR are labeled separately.
- Momentum stress uses the worst Mom day in the **entire** supplied history,
  1939-09-05 at -18.44%, with other factor shocks zero. It isolates beta_Mom
  exposure rather than adding drift, alpha or residual shocks.

## Checks and limitations

```bash
python -m unittest discover -s tests -v
```

The tests include a separate exhaustive-path implementation of a small
two-dividend tree, independent numerical Greek checks, parity and bounds,
American dominance, convergence to GBSM, discrete ES coherence, an independent
direct Sharpe search, and frontier endpoint feasibility. All nine pass.
Full run logs are in `results/fit_console.txt` and `results/tests.txt`.

MC standard errors measure simulation noise, not fitted-parameter or model
uncertainty. N=400 tree results retain lattice error and piecewise-linear
finite-difference gamma behavior; neighboring grids are reported rather than
claiming six-decimal pricing accuracy. Historical 1% ES has very few loss
months. Bootstrap uncertainty is conditional on the observed history and iid
month resampling, and cannot invent unseen crashes. Fund regressions use an
older period than the prescribed latest factor window; that comparison is not
a real-time forecast from 2001.

## Submission

Place this complete `Assignment3` directory in the intended code repository.
The PDF is the written response, and code plus this README supply the code
component. The assignment also instructs the student to reply **done.** in
Canvas after finishing. These scripts do not submit to Canvas or push Git.
