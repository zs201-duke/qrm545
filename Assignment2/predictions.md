# Predictions I made before fitting the models

I wrote these notes after running `python analysis.py prepare`. At that point I
had only looked at the plots, pair counts, and descriptive statistics. I had not
run any of the model fits yet.

## Problem 1

- I expect the complete-case correlation matrix to be PSD because every entry
  comes from the same 81 rows. The pairwise matrix is the risky one: its entries
  are based on different groups of days, so they may not fit together as one
  valid correlation matrix.
- IDX is almost a weighted combination of the four stocks. That should make the
  smallest eigenvalue very close to zero. Because the matrix is already close
  to singular, even a fairly small mismatch in the pairwise estimates could
  push that eigenvalue below zero and cause Cholesky to fail.
- My first guess is that the correlations involving D will be the noisiest.
  D has only 96 observations, and the C-D pair has just 83 common days.

## Problem 2

- The final 50 days or so are clearly more volatile than the earlier part of
  the sample. My predicted VaR order, from low to high, is: historical, fitted
  t, equal-weight Normal, EW Normal with lambda 0.97, and EW Normal with lambda
  0.94. I am least sure about the first three because they look close. I am much
  more confident that 0.94 will be the largest and 0.97 will come next.
- For lambda 0.94, the effective sample size is 32.33 days and the half-life is
  11.20 days. For 0.97, they are 65.67 and 22.76 days. Those choices put 95.5%
  and 78.2% of the total weight, respectively, on the last 50 days.
- The full sample has excess kurtosis of 2.17. I do not think one stationary
  Normal distribution is a good explanation. A mix of a calm regime and a
  high-volatility regime could create that kurtosis even if returns were Normal
  within each regime.

## Problem 3

- Both bonds have very large negative skewness and excess kurtosis, and the
  default losses sit apart from the non-default outcomes. A Normal VaR will
  miss that shape.
- A defaults in 4.06% of the scenarios, but at least one bond defaults in 7.82%.
  My prediction is that diversification will increase 5% VaR because it moves
  default losses across the 5% cutoff. I still expect diversification to lower
  ES because it reduces the size of the losses in the worst scenarios.

## Problem 4

- Based on the moments, I would use a Normal margin for X1 and t margins for X2
  and X3. One observation has a big effect on X2: after removing it, skewness
  changes from -0.62 to 0.06 and excess kurtosis falls from 7.12 to 1.72. Even
  then, the remaining data still look heavier-tailed than Normal.
- Under independence, each 2.5% corner should contain only 0.625 joint days on
  average. The actual counts are 6-7 in the lower corners and 8-12 in the upper
  corners. That is a large difference, and the rank plots also bunch up in the
  corners. I expect the t copula to beat the Gaussian copula.

## Problem 5

- If the two stocks share a positive industry shock that the market factor does
  not capture, treating the residuals as independent should understate P1 VaR
  and overstate P2 VaR. The covariance term enters P1 variance as
  `+2 Cov(eA,eB)` and P2 variance as `-2 Cov(eA,eB)`.
