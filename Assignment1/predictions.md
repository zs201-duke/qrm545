# Predictions recorded before model fitting

These statements were written after running only `analysis.py --stage prepare`
and inspecting its permitted diagnostics. The later fitted results do not revise
this record. They are analytical predictions for this solution, not a claim about
the student's personal prior beliefs.

## 1. Sample shape

The mean is 0.00110439, the unbiased variance is 0.0000962482,
bias-corrected skewness is -0.66984, and excess kurtosis is 2.35761.
Negative skew and positive excess kurtosis favor a negatively skewed Normal
Inverse Gaussian (NIG). A Normal cannot reproduce either shape moment; a
symmetric Student t cannot reproduce the negative skew; the ordinary lognormal
has positive, not negative, population skew. These are shape-based exclusions,
not formal finite-sample impossibility statements. Two sample moments do not
identify a family. I expect a moment-matched Normal to understate the lower-tail
probability and to produce more than 10 observations below its nominal 1%
quantile among the 1,000 observations. Moments alone cannot guarantee this
specific quantile result.

## 2. Regression

The scatter shows a clear positive, roughly linear trend, with most points close
to a narrow central strip and several unusually large vertical deviations on
both sides. There is no obvious fan-shaped spread. I predict a symmetric,
heavy-tailed error family such as Student t rather than Normal; a scatter alone
cannot establish the exact family or independence of errors.

This targets assumption 7 (normal errors) in Week 2, section 3.1. I expect
the OLS and t slopes to stay fairly close, although individual outliers can move
OLS. Non-normality alone does not cause slope bias when E[error | x] = 0.
I expect the estimated residual variance and hence conventional slope standard
error to be sensitive to those large deviations. I do not predict a guaranteed
upward or downward standard-error bias: under independent, homoskedastic errors
with finite variance, the usual OLS covariance formula remains valid without
normality. Exact small-sample normal/t-based inference is what is lost.

## 3. Pairwise relationships

- x1/x2: strongest expected disagreement. The relation is almost monotone but
  visibly cubic-like rather than a straight line. Spearman should be close to
  +1, with Pearson noticeably lower.
- x1/x3: broad, approximately linear upward cloud; both should be moderately
  to strongly positive and reasonably close.
- x1/x4: no evident trend; both should be near zero.
- x2/x3: positive but curved and compressed horizontally near zero; Spearman
  should exceed Pearson, with some gap, likely smaller than for x1/x2.
- x2/x4: no evident trend despite the unusual x2 scale; both near zero.
- x3/x4: no evident trend; both near zero.

## 4. Conditional variance

Use block 1 for x1 (observed), block 2 for x2 (predicted), reversing the direction
of conditioning in the lecture example. The covariance matrix is
[[1.09987522, 1.69690216], [1.69690216, 4.10474896]].
Under the multivariate Normal, Var(x2 | x1) = Sigma22 -
Sigma21 Sigma11^{-1} Sigma12 = 1.48674568. The fraction of variance remaining
is this expression divided by Sigma22 = 0.36220137: a 63.7799% variance
reduction. In standard-deviation units the remaining fraction is sqrt(0.36220137).
No observed value of x1 occurs in the conditional covariance formula, so the
Gaussian model predicts constant conditional uncertainty for all x1.
This is a model implication, not an empirical finding about the actual data.

## 5. Time series

I commit to AR(2). The series fluctuates around a stable-looking level, without
an obvious deterministic trend. The ACF has an initial positive spike, a
negative excursion, and then decays rather than cleanly cutting off. The PACF
has strong lags 1 and 2 (0.46163 and -0.30312); lag 3 is -0.01473 and most
later lags are small. The rule from Week 2, section 6.1, is that AR(p) has a
decaying ACF and a PACF that cuts off after p; MA(q) reverses the roles.
The plotted significance band is +/-1.96/sqrt(500) = +/-0.08765.
PACF lags 9 and 21 exceed that pointwise band, so 'cutoff' is approximate in
this finite sample. Isolated late spikes do not outweigh the early two-lag
signature, and examining 30 pointwise bands creates multiple-testing noise.
