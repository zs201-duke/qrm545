# Predictions recorded before the model-fitting stage

These are analysis-stage predictions, written after `analysis.py prepare` and
before any implied-volatility inversion, dividend-tree pricing, distribution
fit, simulation, portfolio optimization, FF3 or four-factor regression. The
CAPM regressions in Problem 5 and the Greeks in Problem 3 are explicitly part
of their prediction questions. The preparation timestamp and input hashes are
in `results/prefit.json`; `fit_provenance.json` records this file's hash.

## Problem 1

The parity diagnostic flags only K=175: call minus put exceeds the theoretical
forward difference by $0.888179, above the required $0.47 combined-spread band.
At least one of the two quotes, or its contract metadata, is inconsistent.
Parity alone cannot identify which leg is wrong. It should create a call/put
IV separation at that strike. If parity holds exactly, subtracting the two
GBSM prices removes volatility: the call and put must imply the same volatility
because each price is strictly increasing in volatility.

Deep ITM and deep OTM contracts have low vega. Their IVs should be least reliable
for a fixed dollar quote error. Calls at 215, 220 and 225 have the identical
$0.05/$0.10 bid/ask despite progressively more remote strikes. A $0.075 mid
maintained by a price floor can manufacture a rising IV wing; I expect that
wing to be predominantly a quote-resolution artifact. Deep ITM bids may also
fall below discounted intrinsic value and have no positive IV.

## Problem 2

The strike-financing thresholds are $0.891948 for the first dividend and
$0.224495 for the second. The $0.25 first dividend fails the condition; the
$1.50 second dividend passes. Passing only permits exercise when sufficiently
ITM; it does not mean every holder should exercise.

Both European and American calls should lose value with dividends; both puts
should gain. The call early-exercise premium should increase from zero. The
put premium should decrease because the downward jump makes it valuable to
wait and retain the put. The second dividend should have a smaller absolute
American-call sensitivity per dollar: an owner can exercise immediately before
it, while no analogous escape is worthwhile before the first dividend.

## Problem 3

The last stock price is $99.12. Aggregate (delta, gamma, annual theta) is:

| Book | Delta | Gamma | Theta |
|---|---:|---:|---:|
| CoveredCall | 69.916054 | -3.792522 | 1477.776381 |
| ShortStraddle | -0.888844 | -8.092138 | 3313.354940 |
| RiskReversal | 61.388729 | 0.535962 | 18.588445 |
| HedgedShortCall | -0.444422 | -4.046069 | 1868.117622 |

For missed absolute tail risk I predict ShortStraddle, HedgedShortCall,
CoveredCall, then RiskReversal. The first two are almost delta neutral but short
gamma, so delta normal should severely understate their risk. Their missing
quadratic downside is roughly proportional to the large negative gammas.
CoveredCall should also be understated: negative gamma increases downside
losses, though positive theta partly offsets them. RiskReversal's local gamma
is small and positive, so I expect modest overstatement, especially at 5%; the
1% wing could disagree because local Greeks need not remain valid far away.

All four have positive theta, so all should gain if the stock stays fixed for
ten days. The gain in RiskReversal should be small. The two nearly hedged,
short-gamma books should have ES/VaR well above the zero-mean normal's 1.254 at
5%, because losses are driven by squared moves. ABC has near-zero sample skew
(0.0191) and positive excess kurtosis (2.4639); I expect a t fit to beat normal
on AICc. Its effect should be larger on ES and on 1% risk than on 5% VaR.

## Problem 4

PUTW has the highest annual Sharpe (0.7834) and striking negative skew (-6.5665)
and excess kurtosis (61.1418). June 2008 lost 16.7197% and accounts for 45.95%
of its centered sum of squares. Deleting that month increases Sharpe to 1.2717,
but the remaining skew (-4.5008) and kurtosis (40.7441) still reveal insurance
selling. The observation is economically material, not a reason to delete it.

I expect PUTW to dominate the long-only tangency portfolio, plausibly taking
50-80% of the capital, although the covariance can shift that weight. I expect
historical 1% ES to be much larger than the matched normal ES. With just 240
months there are only 2.4 months of probability mass in the 1% tail, so the
empirical number will itself be imprecise.

Monthly mean standard errors are 0.3180%, 0.0869%, 0.6020%, and 0.1068% for
EQ, BOND, STK and PUTW. Excess monthly means are small relative to those errors;
unconstrained weights should be fragile, and a cap should provide more
defensible exposure control than trusting an exact estimated tangency weight.

## Problem 5

Over the matched sample FUND1 has annual excess Sharpe 0.8479 versus 0.7500
for FUND2. CAPM daily alpha is 4.4066 bp (t=3.2043) for FUND1 and 2.4491 bp
(t=1.8349) for FUND2. On this restricted evidence FUND1 looks more skilled.

However, FUND1's CAPM residual correlations with SMB, HML and Mom are -0.0612,
0.2052 and 0.8015. I expect momentum to explain most of the apparent alpha,
with HML adding some explanation. The residual correlations are marginal
diagnostics, not partial regression coefficients; SMB need not be negative.

FUND2's corresponding correlations are 0.3295, -0.1206 and 0.0530. Size should
improve its fit, but momentum should add little. I expect FUND2's alpha to be
more persistent than FUND1's when the full factors are added; the direction
of its exact alpha change also depends on sample factor premia, not only on
residual correlations. These predictions will be reconciled without rewriting
them after the final regressions.
