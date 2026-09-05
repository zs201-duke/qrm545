"""Build the written answers from computed results; no fitted values are retyped.

Requires only ReportLab and Pillow, after analysis.py has produced JSON and PNGs.
Uses the included, licensed DejaVu Sans fonts for portable Greek math labels.
The same content is exported as Markdown for convenient reading and editing.
"""
from pathlib import Path
from xml.sax.saxutils import escape
import json
import math
import re
import reportlab
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak

BASE = Path(__file__).resolve().parent
R = json.loads((BASE / "results/results.json").read_text())
P1, P2, P3, P4, P5 = [R[f"problem{i}"] for i in range(1, 6)]
OLS, NORMAL, T = P2["models"]
AR2, AR3 = P5["models"][1:3]
OUT = BASE / "output/pdf/Assignment1_Report.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)

fontdir = BASE / "fonts"
pdfmetrics.registerFont(TTFont("Vera", str(fontdir / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("VeraBold", str(fontdir / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="VeraBold", italic="Vera", boldItalic="VeraBold")
INK = colors.black
BLUE = colors.black
LIGHT = colors.HexColor("#f3f3f3")
styles = {
    "body": ParagraphStyle("body", fontName="Vera", fontSize=10, leading=14.5, textColor=INK, spaceAfter=8),
    "small": ParagraphStyle("small", fontName="Vera", fontSize=9, leading=12, textColor=INK, spaceAfter=7),
    "h1": ParagraphStyle("h1", fontName="VeraBold", fontSize=13, leading=18, textColor=INK, spaceAfter=10, keepWithNext=True),
    "h2": ParagraphStyle("h2", fontName="VeraBold", fontSize=10.5, leading=15, textColor=INK, spaceBefore=6, spaceAfter=7, keepWithNext=True),
    "eq": ParagraphStyle("eq", fontName="Vera", fontSize=10, leading=16, leftIndent=8, spaceAfter=9, textColor=INK),
    "cell": ParagraphStyle("cell", fontName="Vera", fontSize=9, leading=12, textColor=INK),
}
story, md = [], []


def plain(text):
    text = text.replace("<br/>", "\n").replace("<b>", "**").replace("</b>", "**")
    text = re.sub(r"<sub>(.*?)</sub>", r"_\1", text)
    text = re.sub(r"<super>(.*?)</super>", r"^\1", text)
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def p(text, style="body"):
    story.append(Paragraph(text, styles[style]))
    md.append(plain(text) + "\n")


def h(text, level=1):
    story.append(Paragraph(text, styles[f"h{level}"]))
    md.append("#" * level + " " + text + "\n")


def page(title):
    # Keep each set of answers and its tables together on a page.
    if story:
        story.append(PageBreak())
    h(title)


def table(headers, rows, widths=None):
    def cell(v): return Paragraph(str(v), styles["cell"])
    tab = Table([[cell("<b>"+str(v)+"</b>") for v in headers]] + [[cell(v) for v in row] for row in rows],
                colWidths=widths, repeatRows=1, hAlign="LEFT", splitByRow=0)
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), LIGHT),
        ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#bbbbbb")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING", (0,0), (-1,-1), 7), ("RIGHTPADDING", (0,0), (-1,-1), 7)]))
    story.extend([tab, Spacer(1,10)])
    md.append("| " + " | ".join(map(str,headers)) + " |")
    md.append("| " + " | ".join(["---"]*len(headers)) + " |")
    md.extend("| " + " | ".join(plain(str(v)).replace("\n", " ") for v in row) + " |" for row in rows)
    md.append("")


def fig(name, caption, width=508, maxheight=290):
    from PIL import Image as PILImage
    path=BASE/"figures"/name
    with PILImage.open(path) as im: w, hh=im.size
    height=width*hh/w
    if height>maxheight: width*=maxheight/height; height=maxheight
    story.append(Image(str(path),width=width,height=height))
    story.append(Spacer(1,5))
    story.append(Paragraph(caption,styles["small"]))
    md.append(f"![{caption}](figures/{name})\n")


def f(v, digits=6): return f"{v:.{digits}f}"


page("Assignment 1")
p("FinTech 545 - Quantitative Risk Management", "small")
p("For each problem, I first look at the data and make a prediction, then fit the models and compare the results with my prediction. The calculations use the five CSV files supplied with the assignment.")
h("1. Reading the shape of a sample",2)
p(f"I used the {P1['n']} observations in problem1.csv to calculate the first four moments. The variance uses n - 1. For skewness and excess kurtosis, I used the bias-corrected estimates. I also report the uncorrected values below. Here, m<sub>r</sub> = (1/n) Σ(x<sub>i</sub> - x̄)<super>r</super>.")
table(["Statistic", "Value"],[
    ["Mean", f(P1['mean'],9)], ["Sample variance, denominator n - 1", f(P1['variance_unbiased'],10)],
    ["Bias-corrected skewness",f(P1['skewness_bias_corrected'])],
    ["Bias-corrected excess kurtosis",f(P1['excess_kurtosis_bias_corrected'])],
    ["Uncorrected standardized skewness",f(P1['skewness_moment'])],
    ["Uncorrected excess kurtosis",f(P1['excess_kurtosis_moment'])],
    ["Central third moment m3 (not standardized)",f"{P1['central_moment3_n']:.9e}"],
    ["Central fourth moment m4 (not standardized)",f"{P1['central_moment4_n']:.9e}"]],[343,165])
h("1(a) Predict: candidate distributions",2)
p("The skewness is negative, so the sample has a longer left tail. The positive excess kurtosis suggests heavier tails than a Normal distribution. Based on these two features, I think a negatively skewed <b>Normal Inverse Gaussian (NIG)</b> is a reasonable choice from Week 1 because it allows both skewness and heavy tails.")
p("I would rule out the <b>Normal</b> as a good match because its skewness and excess kurtosis are both zero. The usual <b>Student t</b> can explain heavy tails, but it is symmetric and cannot explain negative population skewness when that moment exists. The <b>lognormal</b> has positive skewness, which is the opposite of this sample. The skewed t and generalized hyperbolic families briefly mentioned in the notes could also be possible, but NIG is the main candidate among the four distributions covered in detail.")
p("These conclusions are based on sample moments, so they do not prove which distribution generated the data. For example, a sample from a symmetric distribution can still have nonzero skewness. Before fitting, I expect the Normal model to underestimate the left tail, giving more than 10 observations below its 1% quantile.")

page("1. Fit and explanation")
h("1(b) Fit: match the sample mean and variance",2)
p(f"I fit the Normal by setting μ = x̄ = {f(P1['mean'],9)} and σ² = s² = {f(P1['variance_unbiased'],10)}. The standard deviation is {f(P1['normal_sd'],9)}. I then calculate its 1% quantile:")
p(f"q<sub>0.01</sub> = μ + σ Φ<super>-1</super>(0.01) = <b>{f(P1['normal_q01'],9)}</b>.","eq")
table(["Quantity", "Result"],[
    ["Observed number strictly below the Normal 1% quantile",str(P1['observed_below_q01'])],
    ["Expected number under the fitted model: 1,000 × 0.01",f(P1['expected_below_q01'],0)],
    ["Observed fraction below that cutoff",f"{100*P1['observed_below_q01']/P1['n']:.2f}%"],
    ["Empirical 1% quantile (linear interpolation)",f(P1['empirical_q01'],9)]],[378,130])
fig("p1_normal.png","Figure 1. The sample and the fitted Normal, including the left-tail probabilities.",maxheight=212)
h("1(c) Reconcile: where the Normal is wrong",2)
p(f"There are <b>{P1['observed_below_q01']}</b> observations below this cutoff, compared with <b>{P1['expected_below_q01']:.0f}</b> expected under the Normal model. That is {P1['observed_below_q01']/P1['expected_below_q01']:.1f} times the expected count. This agrees with my prediction: the fitted Normal assigns too little probability to large negative values.")
p("The empirical 1% quantile is more negative than the Normal 1% quantile. Therefore, using the Normal would underestimate the size of an extreme negative outcome at this probability level. The histogram also shows a more concentrated center and a heavier left tail than the Normal curve. Matching the mean and variance does not capture these differences in shape.")
p("The count of 10 is the number implied by the fitted model. I use the comparison as a check of the tail fit, rather than as a formal hypothesis test.")

page("2. A regression whose errors are not Normal")
h("2(a) Predict from the scatter",2)
fig("p2_prefit.png","Figure 2. The original 200 observations; no fitted line is included in this preliminary plot.",maxheight=245)
p("The scatter shows a clear positive, roughly linear relationship. Most points are fairly close to a line, but a few are much farther above or below it. I do not see an obvious increase in spread as x increases. I would expect a Student t error because it can allow these larger errors while keeping most observations near the line. The plot alone is not enough to confirm the distribution.")
h("2(b) Predict the effect on the slope and its standard error",2)
p("This appears to violate <b>assumption 7: the errors are normally distributed</b>, from Week 2. I expect the OLS slope to remain close to the main trend, although large residuals may move it somewhat. Non-normality alone does not make the slope biased if E[ε | X] = 0.")
p("For the standard error, I expect the large residuals to make the estimate more sensitive to individual observations. However, I would not automatically say that the standard error is too small or too large. With uncorrelated errors, constant finite variance, and E[ε | X] = 0, the usual OLS variance formula σ²(X′X)<super>-1</super> still applies without normal errors. What becomes less reliable is using the usual exact small-sample t tests and confidence intervals.")


page("2. Fit: OLS, Normal MLE, and Student t MLE")
p("I fit y<sub>i</sub> = α + βx<sub>i</sub> + ε<sub>i</sub> with OLS, Normal MLE, and Student t MLE. The error location is set to zero because the intercept already accounts for location. For the t model, ε = sT<sub>ν</sub>. Its scale s is different from its standard deviation.")
table(["Method", "α", "β", "Error scale", "ν"], [
    [m['model'],f(m['alpha']),f(m['beta']),f(m['error_scale']),"-" if m['error_df'] is None else f(m['error_df'])] for m in P2['models']
],[145,89,89,97,88])
p(f"The OLS standard errors are <b>SE(α̂) = {f(OLS['se_alpha'])}</b> and <b>SE(β̂) = {f(OLS['se_beta'])}</b>. OLS estimates the residual SD using sqrt(SSE/(n - 2)), giving {f(OLS['error_scale'])}. Normal MLE uses sqrt(SSE/n), giving {f(NORMAL['error_scale'])}. The slopes and intercepts are identical because maximizing the Normal likelihood gives the same coefficient estimates as minimizing squared errors.")
p(f"The fitted t has ν = {f(T['error_df'])} and scale s = {f(T['error_scale'])}. Using the formula from Week 1, its error SD is s sqrt(ν/(ν - 2)) = {f(P2['t_error_sd'])}. Its variance exists because ν &gt; 2, but its fourth moment is not finite because ν &lt; 4.")
h("Likelihood and model selection",2)
p("Normal: ℓ = -(n/2) log(2πσ²) - SSE/(2σ²).<br/>Student t: ℓ = Σ [log f<sub>Tν</sub>((y<sub>i</sub> - α - βx<sub>i</sub>)/s) - log s].", "eq")
p("For the t model, I maximize the log likelihood over the intercept, slope, scale, and degrees of freedom. I tried five starting values for the degrees of freedom, and they gave the same fitted result.")
p("AICc = -2ℓ + 2k + 2k(k + 1)/(n - k - 1), with n = 200.", "eq")
table(["Model / likelihood", "k", "Log likelihood", "AICc"],[
    ["OLS evaluated at Normal MLE scale",3,f(OLS['loglik']),f(OLS['aicc'])],
    ["Normal MLE",3,f(NORMAL['loglik']),f(NORMAL['aicc'])],
    ["Student t MLE",4,f(T['loglik']),f(T['aicc'])]
],[250,38,110,110])
p(f"I count k = 3 parameters for the Normal model (α, β, σ) and k = 4 for the t model (α, β, s, ν). For OLS, I evaluate AICc using the Normal likelihood at its MLE scale, so its AICc is the same as Normal MLE. The <b>t model has the lower AICc</b> by {NORMAL['aicc']-T['aicc']:.6f}, so I choose it.")

page("2. Comparing the results")
h("2(c-d) Slopes and error distributions",2)
p(f"The OLS and Normal-MLE slopes are {f(OLS['beta'])}, while the t slope is {f(T['beta'])}. The difference is {f(P2['slope_difference_t_minus_ols'])}, or about {100*P2['slope_difference_t_minus_ols']/OLS['beta']:.2f}% of the OLS slope. This is small relative to the OLS slope standard error, so the result agrees with my prediction that the slopes would stay close.")
p("The main problem with the Normal model is the <b>distribution of errors around the line</b>, rather than the line itself. It needs a larger scale to account for the large residuals. This makes it too spread out around the center, yet its far tails are still too thin. The t model fits a tighter center and allows more extreme errors. This explains why AICc can strongly prefer the t model even when the slopes are similar.")
fig("p2_fits.png","Figure 3. Fitted lines and error distributions.",maxheight=202)
h("2(e) Error quantiles and a capital buffer",2)
table(["One-sided percentile", "Normal error", "Student t error", "Wider"],[[f"{100*q['p']:g}%",f(q['normal']),f(q['student_t']),"Normal" if q['normal']>q['student_t'] else "Student t"] for q in P2['quantiles']],[156,120,120,112])
p("I interpret 95% and 99.5% as the one-sided quantiles F<super>-1</super>(0.95) and F<super>-1</super>(0.995). At 95%, the Normal quantile is larger because its fitted scale is larger. At 99.5%, the heavier tail of the t distribution becomes more important, so its quantile is larger. Since both errors are symmetric, the corresponding lower-tail values have the same magnitudes and negative signs.")
p(f"For a capital buffer covering a 0.5% adverse error, I would use the t value of <b>{P2['quantiles'][1]['student_t']:.6f}</b>, compared with {P2['quantiles'][1]['normal']:.6f} for the Normal. The t model fits better and allows for the more extreme outcomes that matter here. This number is for the error; a threshold for y would also include the predicted value α + βx. The fitted quantile still has estimation uncertainty.")

page("3. Pearson and Spearman correlation")
p(f"I plotted all six pairs in problem3.csv before calculating the correlations. There are {P3['n']} observations. Pearson measures a linear relationship, while Spearman uses ranks to measure whether the variables tend to increase or decrease together.")
fig("p3_pairs.png","Figure 4. All six distinct pairs, in their original units.",maxheight=330)
h("3(a) Pair-by-pair predictions",2)
table(["Pair", "Prediction and visual reason"],[
    ["x1 / x2","I expect the largest gap here. The points mostly increase together but follow a curve. Spearman should be near +1 and Pearson lower."],
    ["x1 / x3","Both should be positive and fairly close. The points follow an upward, roughly linear pattern."],
    ["x1 / x4","Both should be near zero. There is no clear pattern."],
    ["x2 / x3","Both should be positive, with Spearman higher because the pattern is curved. I expect a smaller gap than x1/x2."],
    ["x2 / x4","Both should be near zero. Even for large positive or negative x2, x4 shows no clear direction."],
    ["x3 / x4","Both should be near zero because the points have no clear direction."]],[75,433])

page("3. Correlation results")
h("3(b) Pearson matrix",2)
table(["", "x1", "x2", "x3", "x4"],[[f"x{i+1}"]+[f(v) for v in row] for i,row in enumerate(P3['pearson'])],[68,110,110,110,110])
h("Spearman matrix",2)
table(["", "x1", "x2", "x3", "x4"],[[f"x{i+1}"]+[f(v) for v in row] for i,row in enumerate(P3['spearman'])],[68,110,110,110,110])
p(f"The largest gap is for <b>x1 and x2</b>. Pearson is {P3['largest_gap']['pearson']:.6f}, Spearman is {P3['largest_gap']['spearman']:.6f}, and the absolute difference is <b>{P3['largest_gap']['absolute_gap']:.6f}</b>. This matches my prediction. The x2/x3 gap is smaller ({P3['pairs'][3]['absolute_gap']:.6f}), and the x1/x3 gap is {P3['pairs'][1]['absolute_gap']:.6f}. Both measures are near zero for the three pairs involving x4.")
h("3(c) Why the correlations differ",2)
p("For x1 and x2, the points follow a curve that looks roughly cubic. As x1 increases, x2 generally increases, but the relationship is not a straight line. Pearson therefore gives a lower value. Spearman only uses the ordering of values, so it captures the strong increasing pattern more clearly.")
p("I would use <b>Spearman</b> to describe how strongly these two series move in the same direction. It is close to one but not exactly one because some observations change order, especially near the flat middle part of the curve.")
p("Pearson is not wrong. It answers a different question: how strong is the <b>linear relationship</b> in the original values? It is useful when working with linear regression or covariance. Also, the near-zero correlations with x4 do not prove that x4 is independent of the other series.")

page("4. Conditional distributions")
h("4(a) Partition the covariance matrix",2)
p("I use block 1 for x1, which is observed, and block 2 for x2, which is being predicted. This is the reverse of the conditioning direction in the Week 2 example. The sample covariance matrix, using n - 1, is:")
table(["Σ", "Block 1: x1", "Block 2: x2"],[["Block 1: x1",f(P4['covariance'][0][0]),f(P4['covariance'][0][1])],["Block 2: x2",f(P4['covariance'][1][0]),f(P4['covariance'][1][1])]],[160,174,174])
p("v<sub>2|1</sub> = Var(x2 | x1 = a) = Σ<sub>22</sub> - Σ<sub>21</sub>Σ<sub>11</sub><super>-1</super>Σ<sub>12</sub>.","eq")
p(f"Numerically, v<sub>2|1</sub> = {P4['covariance'][1][1]:.6f} - {P4['covariance'][1][0]:.6f}² / {P4['covariance'][0][0]:.6f} = <b>{P4['conditional_variance']:.6f}</b>. The ratio of conditional to unconditional variance is:")
p("r = (Σ<sub>22</sub> - Σ<sub>21</sub>Σ<sub>11</sub><super>-1</super>Σ<sub>12</sub>)/Σ<sub>22</sub> = 1 - ρ².","eq")
p(f"The remaining variance factor is <b>{P4['variance_remaining']:.6f}</b>. In other words, learning x1 reduces the variance of x2 by {100*(1-P4['variance_remaining']):.2f}% under the Normal model. If uncertainty means standard deviation instead, the remaining factor is sqrt(r) = {math.sqrt(P4['variance_remaining']):.6f}, a reduction of {100*(1-math.sqrt(P4['variance_remaining'])):.2f}%.")
h("4(b) Does the observed x1 value change the factor?",2)
p("<b>No.</b> Under the multivariate Normal, the conditional variance formula only contains the covariance blocks. It does not contain the observed value a. Therefore, before checking the scatter, I expect the Normal model to give the same band width for every x1.")
h("4(c) Conditional mean and band",2)
p("m(a) = E[x2 | x1 = a] = μ<sub>2</sub> + Σ<sub>21</sub>Σ<sub>11</sub><super>-1</super>(a - μ<sub>1</sub>).","eq")
p(f"The sample means are μ̂<sub>1</sub> = {P4['mean'][0]:.6f} and μ̂<sub>2</sub> = {P4['mean'][1]:.6f}. The coefficient Σ<sub>21</sub>/Σ<sub>11</sub> = {P4['slope']:.6f} is the OLS slope when regressing x2 on x1 with an intercept. The fitted line is <b>m̂(a) = {P4['intercept']:.6f} + {P4['slope']:.6f}a</b>.")
p(f"I draw the 95% band as m̂(a) ± Φ<super>-1</super>(0.975) sqrt(v̂<sub>2|1</sub>), which gives <b>m̂(a) ± {P4['half_width']:.6f}</b>. This band is for individual x2 observations around the line, not a confidence interval for the estimated mean. I use the estimated parameters directly, without adding an adjustment for their uncertainty.")

page("4. Checking the band")
fig("p4_conditional.png","Figure 5. The conditional mean, the 95% band, and coverage in each group.",maxheight=185)
h("4(d-e) Overall and conditional coverage",2)
p(f"Overall, <b>{P4['inside']} out of {P4['n']} observations</b> are inside the band, giving <b>{100*P4['coverage']:.2f}% coverage</b>. For the three groups, I use z = |x1 - x̄1| / s1. The groups are z ≤ 1, 1 &lt; z ≤ 2, and z &gt; 2, where s1 is the sample standard deviation.")
table(["Bucket", "Inside / n", "Coverage", "Residual SD"],[[b['bucket'],f"{b['inside']} / {b['n']}",f"{100*b['coverage']:.2f}%",f(b['residual_sd'])] for b in P4['buckets']],[192,100,100,116])
h("4(f) What the coverage tells us",2)
p("Coverage is close to 95% near the mean of x1 but lower in the other two groups. The residual SD also increases from about 1.08 to about 1.58-1.60. This suggests that the spread of x2 around the line changes with x1. The <b>constant conditional variance</b> implied by the multivariate Normal is not a good description of this sample.")
p("Coverage does not decrease in every group: the last group has 90.20%, above the middle group's 85.79%. It has only 51 observations, so a few points can affect the percentage. The main pattern is lower coverage outside the center.")
p("The coefficient Σ̂<sub>21</sub>/Σ̂<sub>11</sub> still equals the OLS slope without normality. The line remains the best least-squares straight-line fit. If the conditional mean is linear, changing variance alone does not invalidate it. However, the covariance matrix cannot prove that the true conditional mean is linear.")
p("We cannot keep the claim that the same variance and 95% band work equally well for every x1. The covariance formula still gives the variance left after the linear fit, but not necessarily the conditional variance at each x1. A better band needs to allow for changing spread and possibly a different error shape.")

page("5. Identifying an AR or MA order")
fig("p5_prefit.png","Figure 6. The series in file order and its ACF/PACF through lag 30. Shading is the lecture's pointwise ±1.96/sqrt(n) band.",width=475,maxheight=424)
h("5(a-b) Prediction from the plots",2)
p(f"I predict <b>AR(2)</b>. The series moves around a fairly stable level without an obvious trend. The ACF starts at {P5['acf'][1]:.5f}, then turns negative and gradually becomes small. The PACF has two large early values, {P5['pacf'][1]:.5f} and {P5['pacf'][2]:.5f}. Lag 3 is only {P5['pacf'][3]:.5f}, and most later values are also small.")
p(f"The rule from Week 2 is that an AR(p) has a decaying ACF and a PACF that cuts off after lag p. An MA(q) has the opposite pattern. I use the significance band <b>±1.96/sqrt({P5['n']}) = ±{P5['band']:.5f}</b> shown in the plot.")
p("The PACF does not cut off perfectly in this sample: lags 9 and 21 are also outside the band. Since the plot checks many lags, a few extra spikes can occur by chance. The first two lags show the clearest pattern, so my prediction is still AR(2).")

page("5. Model results")
h("5(c-d) Six fits on the same sample",2)
p("I fit all six models using the same 500 observations and Gaussian maximum likelihood in statsmodels. Each model estimates a constant mean and an innovation variance along with its lag coefficients, so k equals the order plus two. Using the same sample and fitting method lets me compare their AICc values.")
best_aicc=min(m['aicc'] for m in P5['models'])
table(["Model", "k", "Log likelihood", "AICc", "ΔAICc"],[[m['model'],m['k'],f(m['loglik']),f(m['aicc']),f(m['aicc']-best_aicc)] for m in P5['models']],[85,40,134,130,119])
p(f"<b>{P5['selected']} has the lowest AICc, {best_aicc:.6f}</b>, so it is selected. This matches my prediction. AR(3) and MA(3) are within two AICc points, though, so the result supports AR(2) without showing that it is the only reasonable model.")
h("5(e) Comparing AR(2) and AR(3)",2)
table(["Parameter", "AR(2)", "AR(3)"],[
    ["Unconditional mean μ",f(AR2['params']['const']),f(AR3['params']['const'])],
    ["First AR coefficient",f(AR2['params']['ar.L1']),f(AR3['params']['ar.L1'])],
    ["Second AR coefficient",f(AR2['params']['ar.L2']),f(AR3['params']['ar.L2'])],
    ["Third AR coefficient","-",f(AR3['params']['ar.L3'])],
    ["Innovation variance",f(AR2['params']['sigma2']),f(AR3['params']['sigma2'])]
],[250,129,129])
gain=2*(AR3['loglik']-AR2['loglik'])
penalty=(2*AR3['k']+2*AR3['k']*(AR3['k']+1)/(P5['n']-AR3['k']-1))-(2*AR2['k']+2*AR2['k']*(AR2['k']+1)/(P5['n']-AR2['k']-1))
p(f"The third AR coefficient is small: {AR3['params']['ar.L3']:.6f}, with an estimated SE of {AR3['standard_errors']['ar.L3']:.6f}. AR(3) improves log likelihood by only {AR3['loglik']-AR2['loglik']:.6f}, reducing the -2ℓ part of AICc by {gain:.6f}. The extra parameter increases the penalty by {penalty:.6f}. Overall, AICc rises by <b>{AR3['aicc']-AR2['aicc']:.6f}</b>, so the small improvement in fit is not enough to justify the larger model.")
p(f"R² does not penalize extra parameters. To compare it fairly, I also fit AR(2) and AR(3) by OLS on the same 497 usable response rows. R² increases slightly from {P5['common_sample_ols']['AR(2)']['r_squared']:.8f} to {P5['common_sample_ols']['AR(3)']['r_squared']:.8f}. Adding a lag cannot make the minimized squared error larger on the same rows, so R² would not prefer the smaller model. These OLS values are a separate illustration; the AICc table uses the maximum-likelihood fits.")

page("6. Code and references")
h("Run the complete analysis",2)
p("The folder includes the PDF, Python code, data, and a README. To reproduce the results, use Python 3.11 or newer and run these commands from the Assignment1 folder:")
p("python -m pip install -r requirements.txt<br/>python analysis.py --stage all<br/>python build_report.py", "eq")
p("The original predictions are saved in predictions.md. The analysis script creates the figures and numerical results, and build_report.py uses those results to produce this PDF and the Markdown version.")
p("The data folder contains the five original CSV files. The results folder contains the model tables, correlation matrices, coverage counts, and a JSON file with the unrounded results. The figures folder contains the plots. README.md gives the setup instructions and explains the main calculation choices.")
h("Calculation choices",2)
p("I use n - 1 for sample variance and covariance, and the bias-corrected options for skewness and excess kurtosis. The Normal-MLE error variance uses SSE/n, while OLS uses SSE/(n - 2). AICc includes the fitted variance and any shape parameters in k. The time-series constant reported by the software is the unconditional mean, not the intercept in the AR recurrence equation. Further details are in README.md.")
h("Verification",2)
p("I checked that the models converged, the OLS and Normal-MLE coefficients agreed, and the conditional slope matched a direct OLS fit. I also checked the coverage counts and the AICc calculations. Re-running the analysis produced the same results.")
h("Sources used",2)
p("Dominic Pazzula, <b>Week 01 - Univariate Statistics</b>, supplied course PDF: sections 3-4 (pp. 5-8), sections 5.1-5.5 (pp. 9-14), and section 6 (p. 15). These support moments, shape screening, and the Normal, lognormal, t, and NIG comparisons.","small")
p("Dominic Pazzula, <b>Week 02 - Multivariate Statistics and Regression</b>, supplied course PDF: sections 1.3-1.4 (pp. 3-5), section 2.4 (p. 8), sections 3.1-3.3 (pp. 9-11), sections 4.1-4.3 (pp. 12-13), section 5.3 (p. 15), and sections 6.1-6.5 (pp. 16-22). These support the correlation, conditioning, regression, AICc, and time-series methods.","small")
p("<b>Assignment 1 - Univariate and Multivariate Statistics</b>, pp. 1-4, and the supplied files problem1.csv through problem5.csv.", "small")


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("Vera",9); canvas.setFillColor(colors.black)
    canvas.drawCentredString(306,27,str(doc.page))
    canvas.restoreState()


doc=SimpleDocTemplate(str(OUT),pagesize=(612,792),rightMargin=46,leftMargin=46,
    topMargin=42,bottomMargin=52,title="Assignment 1 - Univariate and Multivariate Statistics",
    author="",subject="Predict, fit, and reconcile the five supplied datasets")
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(BASE/"Assignment1_Answers.md").write_text("\n".join(md),encoding="utf-8")
print(OUT)
