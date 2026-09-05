# Assignment 1 - Univariate and Multivariate Statistics

The completed written report is `output/pdf/Assignment1_Report.pdf`.
`Assignment1_Answers.md` contains the same report content in readable Markdown.
The five source datasets are included unchanged in `data/`, making this folder
self-contained. Course inputs originally live in `../Assignments/Assignment1/`.

## Reproduce everything

Use Python **3.11 or newer** (the calculations were verified with 3.13.7).
From this folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python analysis.py --stage all
python build_report.py
```

On Windows activate with `.venv\Scripts\activate` instead.
On an already configured environment, only the last two commands are needed.
The calculations do not require network access after dependency installation.
Paths are resolved relative to each script, so the scripts also work when called
from another directory. Figures use the noninteractive Agg backend.

To inspect the stages individually:

```bash
python analysis.py --stage prepare
# Inspect preliminary.json, p2_prefit.png, p3_pairs.png, and p5_prefit.png.
# Original pre-fit judgments are already preserved in predictions.md.
python analysis.py --stage fit
python build_report.py
```

`prepare` does not fit the requested models. It computes the permitted initial
moments, covariance, ACF/PACF and scatter plots. The initial predictions were
written after inspecting these diagnostics and **before the fit stage ran**.
The fit stage requires that prediction record; rerunning does not rewrite it.

## Files

- `analysis.py`: all computations and six figure files, with explanatory comments.
- `build_report.py`: creates the PDF and Markdown report directly from JSON results.
- `predictions.md`: preserved pre-fit analytical predictions.
- `data/problem1.csv` through `problem5.csv`: original numeric inputs, no edits.
- `results/preliminary.json`: moments, initial covariance, ACF, and PACF.
- `results/results.json`: every full-precision result and analytical package versions.
- `results/p2_models.csv`: regression parameters, OLS SEs, likelihoods, and AICc.
- `results/p3_pearson.csv`, `p3_spearman.csv`: both complete correlation matrices.
- `results/p4_coverage.csv`: bucket counts, coverage, and residual spread diagnostics.
- `results/p5_models.csv`: all six AR/MA likelihoods and AICc values.
- `figures/`: pre-fit and fitted plots embedded in the report.
- `fonts/`: DejaVu Sans regular/bold with their redistribution license, included
  so mathematical symbols render consistently without system-font dependencies.
- `output/pdf/Assignment1_Report.pdf`: written answers for all subquestions.
- `Assignment1_Answers.md`: the same answers in Markdown; modify `build_report.py`
  if edits should persist when regenerating both report formats.

## Statistical conventions

1. **Moments:** mean, unbiased sample variance (`ddof=1`), adjusted skewness
   (`scipy.stats.skew(..., bias=False)`), and Fisher excess kurtosis
   (`kurtosis(..., fisher=True, bias=False)`). Uncorrected central moments and
   standardized shape moments are also exported. For uncorrected central moments
   m_r = mean((x - mean(x))**r), g1 = m3/m2**1.5, g2 = m4/m2**2 - 3.
   The corrections are G1 = sqrt(n*(n-1))/(n-2) * g1 and
   G2 = (n-1)/((n-2)*(n-3)) * ((n+1)*g2 + 6).
   These conventional corrections do not make shape estimators exactly unbiased
   for every possible non-Normal population.
2. **Problem 1 Normal:** matches mean and unbiased sample variance. Counts use
   strict `< q01`. The empirical quantile uses linear interpolation.
3. **OLS versus Normal MLE:** the exact Normal-MLE coefficients equal OLS.
   OLS residual SD uses SSE/(n-2); the Normal-MLE variance uses SSE/n. OLS SEs are
   the conventional homoskedastic SEs. An optional HC3 slope SE is in the JSON;
   it is not a test proving heteroskedasticity or an automatic cure for heavy tails.
4. **Student t regression:** error location fixed at zero, intercept estimated,
   scale s and degrees of freedom nu jointly estimated with the slope. Scale is
   not SD; SD is s*sqrt(nu/(nu-2)) when nu>2. Five deterministic starting values
   are used. Positive parameters are optimized on log scales with wide numerical
   bounds; nu is allowed below 2. The solution is well inside the bounds.
5. **AICc:** -2*loglik + 2*k + 2*k*(k+1)/(n-k-1). The Gaussian regression has
   k=3; t regression has k=4. OLS is not a separate density model, so its AICc
   is evaluated at the Gaussian MLE scale and matches Normal MLE.
6. **Error quantiles:** 95% and 99.5% refer to one-sided CDF percentiles, not
   endpoints of central intervals. Errors are symmetric about zero.
7. **Correlations:** Pearson uses values; Spearman uses average ranks for ties.
   Pair gaps are absolute differences over the six off-diagonal pairs.
8. **Conditional band:** block 1 is observed x1, block 2 is predicted x2. Use
   n-1 sample covariance and the Schur complement, with a Gaussian 1.959964
   multiplier. The plug-in band covers conditional observations, not estimated
   means. This is in-sample coverage without a parameter-estimation adjustment.
   Buckets use |x1-mean(x1)|/sd(x1), with boundaries <=1, (1,2], and >2.
9. **Time series:** preserve file order, no differencing, fit a constant mean.
   ACF uses unadjusted autocovariances; PACF uses `method='ywm'`.
   Both plots use the lecture's +/-1.96/sqrt(n) pointwise identification band.
   All AR/MA models use statsmodels ARIMA exact stationary Gaussian state-space
   MLE on the same full 500 observations, with zero likelihood burn. The fitted
   `const` is the unconditional mean, not the AR recurrence intercept.
   Count lag parameters, mean, and innovation variance. AR(2)/AR(3) R-squared
   values come from a separate nested OLS comparison on identical 497 response
   rows, not from incomparable samples or from the exact-likelihood model fits.

## Checks performed

The scripts assert correct column names, finite observations, optimizer
convergence, Gaussian-MLE/OLS coefficient agreement, covariance-formula/OLS
conditional-mean agreement, the identity Schur complement = SSE/(n-1), complete
coverage buckets, symmetric correlation matrices, and agreement between manual
and statsmodels ARMA AICc. The five t starts attain the same optimum. Numerical
rounding occurs only in the report; full-precision values remain in JSON/CSV.
The final PDF was rendered and visually inspected.

The analysis used the system scientific Python environment (versions recorded in
JSON). PDF generation used ReportLab 4.4.9 from the bundled runtime. The pinned
requirements collect the packages into one reproducible environment; installing
that fresh environment was not needed for this run.

## 中文阅读提示

英文 PDF 已覆盖所有题目，按“预测—拟合—解释差异”组织。重点包括：

- 第 1 题：负偏、厚尾；正态 1% 阈值下实际 26 个，预期 10 个。
- 第 2 题：t 模型 AICc 更低，但斜率仍接近 OLS；非正态本身不必然
  使 OLS 有偏，也不必然使标准误偏小。95% 分位正态更宽，99.5% 分位 t 更宽。
- 第 3 题：x1/x2 的差异最大；Spearman 描述单调关系，Pearson 描述线性关系。
- 第 4 题：整体 93.5% 覆盖掩盖条件覆盖差异；固定宽度正态区间有问题，
  但协方差算出的系数仍然是 OLS 系数。最外组覆盖率没有继续单调下降。
- 第 5 题：ACF/PACF 预测 AR(2)，AICc 也选 AR(2)，但与 AR(3)、MA(3)
  差距不大；不能把选择结果当作确定的真实过程。

此目录已具备题目要求的 PDF、代码、README。尚未进行 Canvas 的 `done`
回复，也未向远程仓库推送。请阅读并理解报告内容后自行完成课程提交步骤。
