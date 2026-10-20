# QRM 545 Assignment 2

This folder has my code and write-up for Assignment 2. I kept the preliminary
work separate from the model fitting so that the predictions were actually
written down before I saw the fitted results.

## What's in the folder

- `analysis.py` does the calculations, model fitting, matrix repairs, and
  simulations.
- `qrm545/` is a reusable Python package with the general risk functions. It is
  separate from the assignment-specific data loading and plots.
- `tests/` checks the public library functions on small examples.
- `predictions.md` contains the notes I made before fitting anything.
- `Assignment2_Answers.md` is the Markdown version of my written answers.
- `build_report.py` creates `output/pdf/Assignment2_Report.pdf` from the saved
  results.
- `data/` has the five CSV files used in the assignment.
- `figures/` has the three plots used for the prediction sections.
- `results/` has the full-precision results in JSON format.

## Setup

I used Python 3.13, although Python 3.11 or newer should work. From this folder,
install the packages with:

```bash
python3 -m pip install -r requirements.txt
python3 -m pip install -e .
```

On macOS I also used a local Matplotlib cache folder:

```bash
mkdir -p .mplconfig
```

## Running the analysis

First run the preliminary stage:

```bash
MPLCONFIGDIR=.mplconfig python3 analysis.py prepare
```

That command creates the return plots, pair counts, and descriptive statistics.
I used those outputs to write `predictions.md`.

Once the predictions are in place, run the fits and simulations:

```bash
MPLCONFIGDIR=.mplconfig python3 analysis.py fit
```

Finally, rebuild the PDF with:

```bash
python3 build_report.py
```

The PDF will be saved as `output/pdf/Assignment2_Report.pdf`. The builder leaves
the edited `Assignment2_Answers.md` file alone, so rerunning it will not undo
wording changes in the Markdown submission.

## Reusable Python library

The calculations that could be useful in another assignment are in the
installable `qrm545` package rather than being buried inside `analysis.py`. The
package is split into four modules:

- `qrm545.risk` has moments, EW weights, historical risk, and Normal risk.
- `qrm545.covariance` has covariance construction, portfolio variance, and the
  Rebonato-Jackel and Higham repairs.
- `qrm545.distributions` has Student t MLE and AICc.
- `qrm545.copulas` has Kendall correlation, Gaussian and t log densities,
  simulators, and the t tail-dependence coefficient.

After running `python3 -m pip install -e .`, the functions can be used from a
different script or notebook. For example:

```python
from qrm545 import ew_weights, historical_risk, nearest_corr_higham

weights = ew_weights(250, 0.97)
risk = historical_risk(portfolio_pnl, alpha=0.05)
repaired_correlation, iterations = nearest_corr_higham(raw_correlation)
```

Run the library tests with:

```bash
python3 -m unittest discover -s tests -v
```

## Choices I made in the code

- Returns are arithmetic returns: `P[t] / P[t-1] - 1`.
- I calculate VaR as `-quantile(P&L, alpha)`. ES is the negative average of the
  P&L observations at or below that quantile. This means VaR can be negative
  when the fifth percentile is still a profit.
- Sample variances and covariances use `n - 1`. I use the finite-sample
  corrections available in SciPy for skewness and excess kurtosis.
- The exponentially weighted calculations use normalized weights over the
  available sample, with the largest weight on the newest return.
- The Rebonato-Jackel repair clips negative eigenvalues and then rescales the
  matrix to have ones on the diagonal. The Higham repair uses alternating
  projections with Dykstra's correction.
- I compare Normal and Student t margins with AICc. The Normal has two fitted
  parameters, while the t has three.
- For the copulas, I estimate correlation from Kendall's tau using
  `rho = sin(pi * tau / 2)`. Once that matrix is fixed, only the t copula has an
  extra fitted parameter: its degrees of freedom.
- Both simulation problems use 100,000 draws and fixed random seeds, so the
  results should reproduce exactly.

The t optimizer tries several starting degrees of freedom. I also clip copula
uniforms slightly away from zero and one before applying inverse CDFs. In
Problem 5, I report the regression intercepts but leave them out of the risk
simulation because the question tells us to assume zero expected returns.
