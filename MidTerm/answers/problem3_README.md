# Midterm Problem 3

`Problem3_Answers.docx` contains the detailed answer, with parts 3(a), 3(b), and 3(c) restated and code excerpts labeled by part. `problem3_analysis.py` is the complete executable calculation code.

## Run the complete analysis

Requires Python 3, NumPy, and SciPy. The calculations were run with Python 3.13, NumPy 2.3.3, and SciPy 1.16.2.

```sh
python3 problem3_analysis.py
```

Paths are relative to the script, so the command can run from any working directory. The original price and holdings files are unchanged. To rerun one stage after its prerequisite JSON exists:

```sh
python3 problem3_analysis.py --stage fit
python3 problem3_analysis.py --stage copula
python3 problem3_analysis.py --stage simulate --draws 200000 --seed 54503
```

## Numerical conventions

- Arithmetic returns: 1,001 prices produce 1,000 returns.
- Marginals: constrained maximum likelihood using normal, location-scale Student t, and NIG; select by AICc and confirm with BIC. Normal MLE variance uses n. Fitted means are retained.
- t marginals: degrees of freedom are constrained above 2 to keep variance finite. Near-normal S1/S4/S7 alternatives reach the approximately 1,000,002 upper boundary. These are numerical representatives of a normal limit, not precisely identified finite tail parameters.
- NIG: report the course's alpha, beta, delta, mu, with SciPy a=alpha*delta, b=beta*delta, loc=mu, scale=delta. Numerical bounds are a in [0.001,100000] and abs(b/a)<=tanh(3). All selected NIG fits are interior; discarded S1/S4/S7 NIG alternatives are near-normal and weakly identified.
- Copulas: use the same selected marginal CDF observations and Kendall-derived latent correlation matrix for both models. After fixing their common correlation matrix, count zero additional parameters for Gaussian and one for Student t, following Week05. An optimum at the initial nu=100 upper bound triggers an extended search toward the Gaussian limit.
- Simulation: 200,000 Gaussian-copula scenarios, seed 54503. Selected NIG inverse CDFs use SciPy's adaptive `NumericalInversePolynomial` at requested probability resolution 1e-12, validated against direct CDF/quantile calculations. No return demeaning is applied.
- Absolute risk: VaR=-q_0.05(P&L), ES=minus the mean of the worst 10,000 P&Ls. Linear empirical quantile interpolation is used. Aggregate positions within each shared scenario before calculating book and total risk.
- Precision: results are Monte Carlo estimates conditional on fitted models. Reported cents identify a reproducible run; total VaR/ES Monte Carlo standard errors are approximately $28.41/$44.47. These exclude parameter and model uncertainty.

## Output files

- `problem3_marginal_fits.csv` and `.json`: all 30 fitted models, parameters, likelihoods, AICc/BIC, selection and numerical-limit notes.
- `problem3_sample_diagnostics.csv`: return shape diagnostics and selected families.
- `problem3_returns.csv`: all 1,000 return observations.
- `problem3_copula_fit.json`, `problem3_copula_comparison.csv`, `problem3_copula_profile.csv`, and `problem3_copula_correlation.csv`: both family fits, profile search, and shared dependence matrix.
- `problem3_risk_results.csv` and `.json`: all ten holdings, two books, and total, including latest values and 95% dollar VaR/ES. JSON also records inverse-CDF checks and diversification measures.
- `problem3_simulated_pnl.npz`: stock, book and total P&L scenarios used in the report.
- `problem3_fit_validation.json`: selected nonnormal fits independently checked against SciPy's generic fit routines; likelihood differences are below 4e-8.

The complete script verifies input structure, covariance positive definiteness, density-ratio likelihoods, P&L aggregation, and marginal analytic versus simulated risk. Original-input SHA-256 hashes are stored in the marginal fit JSON. The Word report was rendered and visually inspected.

## Sources

Course foundation: Week01 distribution families and NIG notation; Week02 MLE and information criteria; Week04 arithmetic returns and VaR; Week05 copula fitting, model comparison and ES.

Implementation references:

- https://docs.scipy.org/doc/scipy-1.16.2/reference/generated/scipy.stats.norminvgauss.html
- https://docs.scipy.org/doc/scipy-1.16.2/reference/generated/scipy.stats.sampling.NumericalInversePolynomial.html
