#!/usr/bin/env python3
"""Build the Assignment 2 PDF and a matching Markdown answer document.

All reported values are loaded from analysis.py's JSON output.  This script
requires ReportLab and Pillow; it does not rerun or alter any statistical fit.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


BASE = Path(__file__).resolve().parent
RESULTS = BASE / "results"
OUT = BASE / "output" / "pdf" / "Assignment2_Report.pdf"
OUT.parent.mkdir(parents=True, exist_ok=True)


def load(name):
    return json.loads((RESULTS / name).read_text(encoding="utf-8"))


P1P, P2P, P3P, P4P = [load(f"problem{i}_prepare.json") for i in range(1, 5)]
P1, P2, P3, P4, P5 = [load(f"problem{i}_fit.json") for i in range(1, 6)]

font_dir = BASE / "fonts"
pdfmetrics.registerFont(TTFont("Vera", str(font_dir / "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("VeraBold", str(font_dir / "DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("Vera", normal="Vera", bold="VeraBold", italic="Vera", boldItalic="VeraBold")

INK = colors.HexColor("#17212b")
NAVY = colors.HexColor("#173f5f")
LIGHT = colors.HexColor("#eef3f7")
GRID = colors.HexColor("#aeb9c2")
styles = {
    "body": ParagraphStyle("body", fontName="Vera", fontSize=9.5, leading=13.6, textColor=INK, spaceAfter=7),
    "small": ParagraphStyle("small", fontName="Vera", fontSize=8.2, leading=11.2, textColor=INK, spaceAfter=6),
    "title": ParagraphStyle("title", fontName="VeraBold", fontSize=20, leading=25, textColor=NAVY, spaceAfter=12),
    "h1": ParagraphStyle("h1", fontName="VeraBold", fontSize=13.5, leading=18, textColor=NAVY, spaceBefore=3, spaceAfter=8, keepWithNext=True),
    "h2": ParagraphStyle("h2", fontName="VeraBold", fontSize=10.5, leading=14.5, textColor=INK, spaceBefore=5, spaceAfter=6, keepWithNext=True),
    "cell": ParagraphStyle("cell", fontName="Vera", fontSize=7.9, leading=10.6, textColor=INK),
    "eq": ParagraphStyle("eq", fontName="Vera", fontSize=9.2, leading=14, leftIndent=12, textColor=INK, spaceAfter=7),
}

story = []
markdown = []


def md_plain(text):
    text = text.replace("<br/>", " ").replace("<b>", "**").replace("</b>", "**")
    text = re.sub(r"<sub>(.*?)</sub>", r"_\1", text)
    text = re.sub(r"<super>(.*?)</super>", r"^\1", text)
    return text.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")


def p(text, style="body"):
    story.append(Paragraph(text, styles[style]))
    markdown.append(md_plain(text) + "\n")


def h(text, level=1):
    story.append(Paragraph(text, styles[f"h{level}"]))
    markdown.append("#" * level + " " + text + "\n")


def new_page(title):
    if story:
        story.append(PageBreak())
    h(title, 1)


def table(headers, rows, widths=None):
    def cell(value, bold=False):
        value = str(value)
        return Paragraph(f"<b>{value}</b>" if bold else value, styles["cell"])

    data = [[cell(v, True) for v in headers]] + [[cell(v) for v in row] for row in rows]
    tab = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    tab.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT),
        ("GRID", (0, 0), (-1, -1), 0.35, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.extend([tab, Spacer(1, 8)])
    markdown.append("| " + " | ".join(map(str, headers)) + " |")
    markdown.append("| " + " | ".join(["---"] * len(headers)) + " |")
    markdown.extend("| " + " | ".join(md_plain(str(v)).replace("\n", " ") for v in row) + " |" for row in rows)
    markdown.append("")


def figure(filename, caption, width=495, max_height=280):
    path = BASE / "figures" / filename
    with PILImage.open(path) as im:
        px_w, px_h = im.size
    height = width * px_h / px_w
    if height > max_height:
        width *= max_height / height
        height = max_height
    story.append(Image(str(path), width=width, height=height))
    story.append(Spacer(1, 4))
    story.append(Paragraph(caption, styles["small"]))
    markdown.append(f"![{caption}](figures/{filename})\n")


def num(value, digits=4):
    return f"{value:.{digits}f}"


def money(value):
    sign = "-" if value < 0 else ""
    return f"{sign}${abs(value):,.0f}"


def matrix_rows(matrix, labels, digits=4):
    return [[labels[i]] + [f"{v:.{digits}f}" for v in row] for i, row in enumerate(matrix)]


# Cover and conventions
story.append(Paragraph("Assignment 2", styles["title"]))
p("FinTech 545 - Quantitative Risk Management")
p("Covariance, Value at Risk, expected shortfall, copulas, and model-based simulation", "small")
p("I followed the required Predict - Fit - Reconcile sequence. The predictions were recorded in predictions.md after descriptive plots and counts and before any model fitting. All VaR and ES values use the lower P&amp;L tail and are reported as positive losses; a negative VaR therefore means the stated percentile is still a gain.")
h("Conventions and course foundation", 2)
p("Arithmetic return is P<sub>t</sub>/P<sub>t-1</sub> - 1. Historical VaR is -q<sub>alpha</sub>(P&amp;L), and historical ES is the negative mean of observations at or below that empirical quantile. Sample variances use n - 1. Exponentially weighted variances use normalized finite-sample weights. Simulations use a fixed seed and 100,000 draws.")
p("The method choices follow the Week 3 material on PSD correlation matrices, exponentially weighted volatility, Rebonato-Jackel and Higham repairs; Week 4 on P&amp;L VaR and VaR non-subadditivity; and Week 5 on ES, OLS residual covariance, copulas, Kendall's tau, likelihood, and tail dependence.")


# Problem 1
new_page("1. Correlations from mismatched histories")
h("Predict", 2)
p(f"There are {P1P['complete_rows']} complete rows. Complete-case correlation is guaranteed PSD because it is a Gram matrix built from one common set of return vectors. Pairwise correlation can be non-PSD because different entries use different samples and need not be jointly consistent. Since IDX is nearly a fixed combination of A-D, the true matrix should have a very small eigenvalue. The matrix is therefore especially vulnerable to a small estimation inconsistency crossing zero. I predicted correlations involving D, especially C-D, would be least reliable because D has only 96 observations and C-D has only 83 paired days.")
counts = P1P["pair_counts"]
labels = P1P["variables"]
table(["Joint n"] + labels, [[r] + [counts[c][r] for c in labels] for r in labels], [72, 62, 62, 62, 62, 62])
h("Fit: correlations, eigenvalues, and Cholesky", 2)
table(["Matrix"] + labels, matrix_rows(P1["complete_correlation"], labels), [80, 68, 68, 68, 68, 68])
p("Complete-case correlation matrix", "small")
table(["Matrix"] + labels, matrix_rows(P1["pairwise_correlation"], labels), [80, 68, 68, 68, 68, 68])
p("Pairwise correlation matrix", "small")
table(["Estimator", "Eigenvalues, ascending", "Cholesky"], [
    ["Complete case", ", ".join(f"{x:.6f}" for x in P1["complete_eigenvalues"]), "succeeds" if P1["complete_cholesky"] else "fails"],
    ["Pairwise", ", ".join(f"{x:.6f}" for x in P1["pairwise_eigenvalues"]), "succeeds" if P1["pairwise_cholesky"] else "fails"],
], [94, 330, 75])
p(f"The complete-case minimum eigenvalue is {P1['complete_eigenvalues'][0]:.6f}; the near linear relation is visible but remains positive. Pairwise estimation pushes it to {P1['pairwise_eigenvalues'][0]:.6f}, so standard Cholesky factorization fails.")

new_page("1. Repair and reconciliation")
h("Pairwise covariance and tracking portfolio", 2)
p("I formed Sigma = D C<sub>pair</sub> D, where D contains each series' full-history standard deviation. For w = (-0.40, -0.30, -0.20, -0.10, 1), the computed variance is w' Sigma w.", "eq")
table(["A SD", "B SD", "C SD", "D SD", "IDX SD"], [[f"{P1['full_history_sd'][c]:.6f}" for c in labels]], [100] * 5)
p(f"The raw pairwise result is <b>{P1['tracking_variance_raw']:.9f}</b>. A negative variance is impossible. It directly violates PSD, whose definition requires x'Ax &gt;= 0 for every x. Here the tracking-portfolio vector supplies an explicit counterexample.")
h("PSD repairs", 2)
table(["Matrix", "Minimum eigenvalue", "Frobenius distance", "Tracking variance"], [
    ["Raw pairwise", f"{P1['pairwise_eigenvalues'][0]:.9f}", "0", f"{P1['tracking_variance_raw']:.9f}"],
    ["Rebonato-Jackel", f"{P1['rj_min_eigenvalue']:.3e}", f"{P1['rj_frobenius_distance']:.6f}", f"{P1['tracking_variance_rj']:.9f}"],
    ["Higham", f"{P1['higham_min_eigenvalue']:.3e}", f"{P1['higham_frobenius_distance']:.6f}", f"{P1['tracking_variance_higham']:.9f}"],
], [120, 120, 125, 130])
p("Both repaired minimum eigenvalues are numerical zero (the tiny negative Higham value is floating-point tolerance), and both tracking variances become nonnegative. Higham is closer in Frobenius norm because it solves the nearest-correlation problem iteratively; spectral clipping with diagonal rescaling is quicker but not the Frobenius optimum.")
h("What moved and why", 2)
table(["Entry", "Before", "After Higham", "Absolute change"], [[r["pair"], f"{r['before']:.6f}", f"{r['after']:.6f}", f"{r['absolute_change']:.6f}"] for r in P1["largest_higham_changes"][:5]], [105, 100, 120, 120])
p("My reliability prediction did not identify the largest moves: A-IDX moved most, followed by C-IDX and B-IDX. Higham was not given pair counts. It changes entries only as needed to restore global algebraic consistency while minimizing unweighted Frobenius distance. The near-basket relation makes correlations with IDX central to the negative direction, so the optimization changes those entries even when their pair counts are large.")
p(f"The Higham repair size is {P1['higham_frobenius_distance']:.6f}, while the complete-case versus pairwise estimator gap is {P1['estimator_gap_frobenius']:.6f}, about {P1['estimator_gap_frobenius']/P1['higham_frobenius_distance']:.1f} times larger. For these data, the choice of estimator matters much more than the choice of repair. Repair fixes feasibility; it does not erase sampling-design differences.")


# Problem 2
new_page("2. Volatility after a regime change")
h("Predict", 2)
figure("problem2_returns.png", "Figure 1. Demeaned arithmetic returns. The visibly higher volatility begins about 50 days from the end.", max_height=210)
p("Before fitting, I predicted the order from smallest to largest as historical, fitted t, equal-weight Normal, EW Normal with lambda 0.97, and EW Normal with lambda 0.94. The robust part of the prediction was that the two EW estimates would be largest and 0.94 would be highest, because it reacts fastest to the recent high-volatility regime. I expected the three full-history estimates to be close.")
table(["lambda", "Effective n", "Half-life (days)", "Weight on last 50 days"], [
    ["0.94", f"{P2P['lambda_0.94']['effective_sample_size']:.2f}", f"{P2P['lambda_0.94']['half_life']:.2f}", f"{100*P2P['lambda_0.94']['recent_50_weight']:.2f}%"],
    ["0.97", f"{P2P['lambda_0.97']['effective_sample_size']:.2f}", f"{P2P['lambda_0.97']['half_life']:.2f}", f"{100*P2P['lambda_0.97']['recent_50_weight']:.2f}%"],
], [100, 120, 135, 150])
mom = P2P["moments"]
p(f"The full sample has mean {mom['mean']:.2e}, variance {mom['variance']:.8f}, skewness {mom['skewness']:.4f}, and excess kurtosis {mom['excess_kurtosis']:.4f}. A stationary Normal population has zero skewness and excess kurtosis. The large positive excess kurtosis is more consistent with mixing calm and volatile regimes than with one Normal regime.")
h("Fit", 2)
e = P2["estimates"]
table(["Method", "Volatility / parameters", "5% VaR"], [
    ["Normal, equal weight", f"sigma={e['Normal_equal']['sigma']:.6f}", money(e['Normal_equal']['VaR'])],
    ["Normal EW, 0.97", f"sigma={e['EW_0.97']['sigma']:.6f}", money(e['EW_0.97']['VaR'])],
    ["Normal EW, 0.94", f"sigma={e['EW_0.94']['sigma']:.6f}", money(e['EW_0.94']['VaR'])],
    ["Student t MLE", f"nu={e['Student_t']['df']:.3f}, loc={e['Student_t']['loc']:.6f}, scale={e['Student_t']['scale']:.6f}", money(e['Student_t']['VaR'])],
    ["Historical", "full sample", money(e['Historical']['VaR'])],
], [132, 270, 95])

new_page("2. Reconciliation and use of lambda")
p("The fitted order from smallest to largest is t, equal-weight Normal, historical, EW 0.97, EW 0.94. The two EW positions matched my prediction. Historical simulation landed above the t and equal-weight Normal estimates, rather than below both. The realized 5% empirical quantile contains more moderately large losses than I inferred from the mixture shape; moment or tail-shape intuition alone does not determine one sample quantile.")
table(["Regime", "Days", "Sample SD"], [
    ["Earlier calm regime", "450", f"{P2['old_regime_sd']:.6f}"],
    ["Recent volatile regime", "50", f"{P2['new_regime_sd']:.6f}"],
], [180, 100, 140])
p(f"The recent SD is {P2['new_regime_sd']/P2['old_regime_sd']:.2f} times the earlier SD. A two-Normal mixture with these regime weights and SDs has theoretical excess kurtosis {P2['two_regime_normal_mixture_excess_kurtosis']:.3f}, close to the sample's {mom['excess_kurtosis']:.3f}. Thus the fitted t with nu={e['Student_t']['df']:.2f} is a compact unconditional description of regime mixing. It does not establish that returns are conditionally t within either regime.")
h("Is the EW gap signal or estimation noise?", 2)
p(f"The two EW VaRs differ by {money(P2['ew_var_gap'])}. Using sigma/sqrt(2 n_eff), their approximate VaR standard errors are {money(e['EW_0.94']['VaR_se'])} and {money(e['EW_0.97']['VaR_se'])}; the gap is only {P2['ew_gap_over_combined_se']:.2f} combined standard errors. It is therefore not clearly larger than estimation noise, even though the ordering is economically consistent with the regime change.")
p("<b>Opinion:</b> I would use lambda=0.94 for a trading limit because it responds quickly to a changed risk environment, while recognizing its noisier estimate. I would use lambda=0.97 for a capital number because it is more stable and less driven by a few days. Governance could supplement the slower capital estimate with a stressed floor so that stability does not ignore a lasting break.")


# Problem 3
new_page("3. When diversification raises VaR")
h("Predict", 2)
figure("problem3_pnl.png", "Figure 2. One-year P&L distributions. The log count scale makes the separated default-loss regions visible.", max_height=205)
table(["Series", "Mean", "Variance", "Skewness", "Excess kurtosis", "Return < -20%"], [
    ["A", f"{P3P['A_moments']['mean']:.4f}", f"{P3P['A_moments']['variance']:.5f}", f"{P3P['A_moments']['skewness']:.3f}", f"{P3P['A_moments']['excess_kurtosis']:.3f}", P3P['A_below_minus_20pct']],
    ["B", f"{P3P['B_moments']['mean']:.4f}", f"{P3P['B_moments']['variance']:.5f}", f"{P3P['B_moments']['skewness']:.3f}", f"{P3P['B_moments']['excess_kurtosis']:.3f}", P3P['B_below_minus_20pct']],
], [55, 70, 75, 75, 100, 100])
p(f"At least one bond loses more than 20% in {P3P['at_least_one_below_minus_20pct']} scenarios (7.82%), while both do so in only {P3P['both_below_minus_20pct']} scenarios. Each individual default rate is below 5%. I therefore predicted that at 5% the diversified position would have larger VaR, because its default mass crosses the percentile threshold, but smaller ES, because splitting the notional reduces average loss severity in the worst tail. The extreme negative skew and kurtosis imply a Normal VaR will smooth away the payoff discontinuity.")
h("Fit: 5% historical and Normal risk", 2)
rows = []
for label in ("$1m A", "$1m B", "$2m A", "$1m A + $1m B"):
    item = P3["alpha_5pct"][label]
    rows.append([label, money(item["historical"]["VaR"]), money(item["historical"]["ES"]), money(item["normal"]["VaR"])])
table(["Position", "Historical VaR", "Historical ES", "Normal VaR"], rows, [150, 115, 115, 110])
p("A negative 5% VaR for either single bond, and for $2m in A, means the empirical fifth percentile is still a gain. This is valid under the sign convention and is exactly why the quantile can jump when the default probability crosses 5%.")

new_page("3. Subadditivity and the 1% result")
h("Five-percent subadditivity", 2)
p(f"Historical VaR fails subadditivity: VaR(A)+VaR(B)-VaR(A+B) = {money(P3['alpha_5pct']['subadditivity']['VaR_A_plus_VaR_B_minus_VaR_AB'])}. The combination's VaR exceeds the sum by {money(-P3['alpha_5pct']['subadditivity']['VaR_A_plus_VaR_B_minus_VaR_AB'])}. Each marginal 5% quantile lies in the non-default profit cluster, but the combination has 7.82% probability of at least one default, putting its 5% quantile in a loss cluster.")
p(f"ES remains subadditive: ES(A)+ES(B)-ES(A+B) = {money(P3['alpha_5pct']['subadditivity']['ES_A_plus_ES_B_minus_ES_AB'])}, which is positive. ES averages the whole worst 5% rather than selecting the boundary point, so the severity reduction from splitting the investment is recognized.")
p(f"Normal VaR favors the diversified choice: {money(P3['alpha_5pct']['$1m A + $1m B']['normal']['VaR'])} versus {money(P3['alpha_5pct']['$2m A']['normal']['VaR'])} for concentrated A. It reaches the economically sensible diversification conclusion for average tail severity, but for the wrong 5% historical-VaR reason. Elliptical Normal risk is automatically subadditive and cannot represent the discrete probability mass crossing the VaR threshold.")
h("One-percent historical risk", 2)
rows = []
for label in ("$1m A", "$1m B", "$2m A", "$1m A + $1m B"):
    item = P3["alpha_1pct"][label]["historical"]
    rows.append([label, money(item["VaR"]), money(item["ES"])])
table(["Position", "Historical 1% VaR", "Historical 1% ES"], rows, [190, 145, 145])
p(f"At 1%, the concentrated A VaR is {money(P3['alpha_1pct']['$2m A']['historical']['VaR'])}, while the diversified VaR is {money(P3['alpha_1pct']['$1m A + $1m B']['historical']['VaR'])}. Diversification now lowers VaR. The 1% quantile lies inside the default-loss region for both choices, so loss severity, rather than whether default mass crosses the cutoff, determines the comparison. VaR's failure is threshold-specific; it appears when the chosen probability cuts between separated loss states.")


# Problem 4
new_page("4. Gaussian or t copula")
h("Predict: margins and rank tails", 2)
table(["Series", "Mean", "Variance", "Skewness", "Excess kurtosis", "Kurtosis without most extreme row"], [
    [c, f"{P4P['moments'][c]['mean']:.6f}", f"{P4P['moments'][c]['variance']:.7f}", f"{P4P['moments'][c]['skewness']:.3f}", f"{P4P['moments'][c]['excess_kurtosis']:.3f}", f"{P4P['single_observation_check'][c]['moments_without']['excess_kurtosis']:.3f}"] for c in ("X1", "X2", "X3")
], [48, 82, 88, 72, 90, 130])
p("I predicted a Normal margin for X1 and t margins for X2 and X3. Row 952 strongly affects X2: removing it changes skewness from -0.615 to 0.056 and excess kurtosis from 7.125 to 1.725. The residual heavy tails still favor t, while warning that one joint extreme has high influence.")
figure("problem4_rank_pairs.png", "Figure 3. Rank uniforms for all pairs. Dashed lines mark each outer 2.5%.", max_height=175)
table(["Pair", "Observed lower joint days", "Observed upper joint days", "Expected under independence"], [[r["pair"], r["lower_joint_count"], r["upper_joint_count"], f"{r['independence_expected']:.3f}"] for r in P4P["rank_tail_counts"]], [100, 130, 130, 135])
p("Every observed corner count is far above 0.625. The rank plots show positive association through the middle and a visibly stronger concentration in the corners. I therefore predicted that the t copula would win because it can produce common scale shocks and nonzero asymptotic tail dependence.")
h("Fit: margins", 2)
table(["Margin", "Normal AICc", "t AICc", "t df", "Selected"], [[c, f"{P4['margin_fits'][c]['normal']['AICc']:.2f}", f"{P4['margin_fits'][c]['t']['AICc']:.2f}", f"{P4['margin_fits'][c]['t']['df']:.2f}", P4['margin_fits'][c]['selected']] for c in ("X1", "X2", "X3")], [90, 100, 100, 80, 95])
p("AICc confirms the margin predictions: Normal for X1, t with nu=5.27 for X2, and t with nu=6.09 for X3. Each selected fitted CDF is then used to create the uniforms for copula fitting.")

new_page("4. Copula fit and simulated risk")
h("Kendall correlation and copula likelihood", 2)
table(["R"] + ["X1", "X2", "X3"], matrix_rows(P4["copula_fit"]["correlation_from_tau"], ["X1", "X2", "X3"]), [70, 95, 95, 95])
p("I used rho<sub>ij</sub> = sin(pi tau<sub>ij</sub>/2). The resulting R has minimum eigenvalue %.4f and requires no repair." % P4["copula_fit"]["min_correlation_eigenvalue"])
cf = P4["copula_fit"]
table(["Copula", "df", "Log likelihood", "AICc", "BIC"], [
    ["Gaussian", "-", f"{cf['gaussian']['loglik']:.3f}", f"{cf['gaussian']['AICc']:.3f}", f"{cf['gaussian']['BIC']:.3f}"],
    ["t", f"{cf['t']['df']:.3f}", f"{cf['t']['loglik']:.3f}", f"{cf['t']['AICc']:.3f}", f"{cf['t']['BIC']:.3f}"],
], [105, 65, 115, 105, 105])
p(f"The t copula wins by {cf['t']['loglik']-cf['gaussian']['loglik']:.3f} log-likelihood units, {cf['gaussian']['AICc']-cf['t']['AICc']:.3f} AICc points, and {cf['gaussian']['BIC']-cf['t']['BIC']:.3f} BIC points. This decisively agrees with the prediction.")
h("Portfolio risk for $1m in each asset", 2)
risk_rows = []
for model, label in (("historical", "Historical"), ("gaussian_copula", "Gaussian copula"), ("t_copula", "t copula")):
    rr = P4["risk"][model]
    risk_rows.append([label, money(rr["alpha_5pct"]["VaR"]), money(rr["alpha_5pct"]["ES"]), money(rr["alpha_1pct"]["VaR"]), money(rr["alpha_1pct"]["ES"])])
table(["Method", "5% VaR", "5% ES", "1% VaR", "1% ES"], risk_rows, [135, 88, 88, 88, 88])
p("Switching from Gaussian to t changes 5% VaR by only $900, 5% ES by $1,155, 1% VaR by $2,434, and 1% ES by $5,625. The largest movement is 1% ES because it averages the deepest joint losses, where t-copula tail dependence matters most. Five-percent VaR is a boundary quantile in a less extreme region; both copulas have the same Kendall-based correlation and similar central dependence, so it barely moves.")

new_page("4. Joint tails and what likelihood rewards")
h("Implied joint tail days per 1,000", 2)
observed = {r["pair"]: r for r in P4P["rank_tail_counts"]}
gauss = {r["pair"]: r for r in P4["simulated_joint_tail_counts_per_1000"]["gaussian"]}
tcop = {r["pair"]: r for r in P4["simulated_joint_tail_counts_per_1000"]["t"]}
tail_rows = []
for pair in ("X1-X2", "X1-X3", "X2-X3"):
    tail_rows.append([pair, f"{observed[pair]['lower_joint_count']} / {observed[pair]['upper_joint_count']}", f"{gauss[pair]['lower_per_1000']:.2f} / {gauss[pair]['upper_per_1000']:.2f}", f"{tcop[pair]['lower_per_1000']:.2f} / {tcop[pair]['upper_per_1000']:.2f}"])
table(["Pair", "Observed lower / upper", "Gaussian lower / upper", "t lower / upper"], tail_rows, [85, 135, 140, 140])
p("The t copula generally raises joint-corner frequencies and is closer to the overall observed concentration, although no symmetric copula reproduces every finite-sample asymmetry: for example, X1-X3 has 12 observed upper-tail days versus about 7.64 under t. This is a limitation of both fitted elliptical copulas.")
h("Daily log-likelihood contributions", 2)
total_gain = cf["t"]["loglik"] - cf["gaussian"]["loglik"]
central_gain = total_gain * P4["fraction_loglik_advantage_from_central_days"]
p(f"The mean daily contribution ell<sub>t</sub>-ell<sub>G</sub> is {P4['loglik_difference_per_day_mean']:.4f}. There are {P4['central_day_count']} days on which every fitted uniform is between 5% and 95%; those days contribute {central_gain:.3f}, or {100*P4['fraction_loglik_advantage_from_central_days']:.1f}% of the total {total_gain:.3f} log-likelihood advantage. Information criteria score the density on every observation, not only the few named tail events. A t copula can win partly by fitting the broad shape of dependence in the center and shoulders.")
h("Tail dependence", 2)
top = max(P4["tail_dependence"], key=lambda r: r["rho"])
p(f"The most correlated pair is {top['pair']} with rho={top['rho']:.4f}. For the fitted t copula, lambda = 2 T<sub>nu+1</sub>(-sqrt((nu+1)(1-rho)/(1+rho))) = <b>{top['t_tail_dependence']:.4f}</b>. The Gaussian copula coefficient is <b>0</b> for rho&lt;1. Thus Gaussian joint extremes can be frequent at a fixed 2.5% cutoff while still becoming asymptotically independent.")


# Problem 5
new_page("5. Model-based simulation and residual correlation")
h("Predict", 2)
p("With positive industry residual covariance, setting Cov(e<sub>A</sub>,e<sub>B</sub>) to zero removes +2 Cov(e<sub>A</sub>,e<sub>B</sub>) from P1 variance and removes -2 Cov(e<sub>A</sub>,e<sub>B</sub>) from P2 variance. I therefore predicted that the independence shortcut would understate P1 VaR and overstate P2 VaR.")
h("Fit: market regressions", 2)
reg = P5["regression"]
table(["Stock", "alpha", "beta", "Residual SD"], [[c, f"{reg[c]['alpha']:.6f}", f"{reg[c]['beta']:.4f}", f"{reg[c]['residual_sd']:.6f}"] for c in ("A", "B")], [90, 120, 105, 125])
p(f"The residual correlation is <b>{P5['residual_correlation']:.4f}</b>, confirming a large positive common component beyond the market. The market SD is {P5['market_sd']:.6f}. Expected returns are set to zero in the risk simulation, as instructed; alpha is reported as a regression diagnostic but not added to simulated returns.")
h("100,000-day simulation and delta-Normal VaR", 2)
table(["Portfolio", "Full residual covariance", "Residual correlation = 0", "Delta-Normal"], [[
    "P1: long A, long B", money(P5['risk']['P1_long_A_long_B']['full_residual_simulation_VaR']), money(P5['risk']['P1_long_A_long_B']['zero_residual_correlation_simulation_VaR']), money(P5['risk']['P1_long_A_long_B']['delta_normal_VaR'])], [
    "P2: long A, short B", money(P5['risk']['P2_long_A_short_B']['full_residual_simulation_VaR']), money(P5['risk']['P2_long_A_short_B']['zero_residual_correlation_simulation_VaR']), money(P5['risk']['P2_long_A_short_B']['delta_normal_VaR'])]], [150, 125, 125, 100])
p(f"The shortcut lowers P1 VaR by {money(P5['risk']['P1_long_A_long_B']['full_minus_zero'])} and raises P2 VaR by {money(-P5['risk']['P2_long_A_short_B']['full_minus_zero'])}, exactly as predicted. P2 is more exposed in absolute and percentage terms because its long-short market components largely cancel; residual covariance then determines whether the stock-specific parts hedge or reinforce. Removing positive residual covariance destroys that hedge.")
p(f"Full-covariance simulation and delta-Normal differ by only {money(abs(P5['risk']['P1_long_A_long_B']['full_minus_delta']))} for P1 and {money(abs(P5['risk']['P2_long_A_short_B']['full_minus_delta']))} for P2, which is ordinary Monte Carlo error. OLS makes residuals orthogonal to the market in sample, so beta beta' Var(MKT)+Sigma<sub>epsilon</sub> reconstructs the stock covariance; the maximum elementwise discrepancy is {P5['max_abs_sample_minus_implied_full']:.2e}. With jointly Normal market and errors, a linear portfolio is Normal, so factor simulation and direct delta-Normal use the same distribution. They would diverge with non-Normal factors or residuals, nonlinear positions, volatility dynamics, parameter uncertainty, or dependence not captured by a constant covariance matrix.")


# Code / reproducibility
new_page("6. Reproducibility and references")
h("Files and commands", 2)
p("The folder contains the assignment workflow, report builder, predictions, data, figures, and full-precision results. General calculations live in the installable qrm545 package, which separates reusable risk measures, covariance repairs, distribution fitting, and copula tools from the five problem-specific workflows.")
p("python3 -m pip install -r requirements.txt<br/>python3 -m pip install -e .<br/>MPLCONFIGDIR=.mplconfig python3 analysis.py prepare<br/># inspect figures and predictions.md<br/>MPLCONFIGDIR=.mplconfig python3 analysis.py fit<br/>python3 build_report.py<br/>python3 -m unittest discover -s tests -v", "eq")
p("Running prepare or fit overwrites only generated figures and JSON result files. The fixed random seeds make both 100,000-draw simulations reproducible. The README documents the environment, formulas, and output locations.")
h("Implementation checks", 2)
p("The qrm545 package has focused unit tests for risk measures, EW weights, covariance construction, both matrix repairs, Student t fitting, AICc, copula likelihoods, simulation, Kendall correlation, and tail dependence. I also reran the full assignment after the refactor and confirmed that every saved fitted result is unchanged.")
h("Course materials used", 2)
p("Dominic Pazzula, Week 03 - Monte Carlo and Covariance Estimation, supplied PDF and HTML slides: covariance construction, PSD diagnostics, effective sample size, half-life, volatility standard error, Rebonato-Jackel repair, and Higham nearest-correlation iteration.", "small")
p("Dominic Pazzula, Week 04 - Returns and Value at Risk, supplied PDF and HTML slides: arithmetic P&amp;L returns, empirical and Normal VaR, sign convention, and failure of VaR subadditivity for non-elliptical payoff distributions.", "small")
p("Dominic Pazzula, Week 05 - Expected Shortfall and Copulas, supplied PDF and HTML slides: ES, residual covariance in model-based simulation, marginal transformations, Kendall's tau, Gaussian and t copula likelihoods, simulation, information criteria, and t-copula tail dependence.", "small")
p("Assignment 2 - Covariance, VaR, and Copulas, supplied assignment PDF/QMD and problem1.csv through problem5.csv.", "small")


def add_page_number(canvas, doc):
    canvas.saveState()
    canvas.setFont("Vera", 8)
    canvas.setFillColor(colors.HexColor("#5f6d78"))
    canvas.drawString(54, 28, "QRM 545 - Assignment 2")
    canvas.drawRightString(558, 28, f"Page {doc.page}")
    canvas.restoreState()


doc = SimpleDocTemplate(
    str(OUT),
    pagesize=(612, 792),
    rightMargin=54,
    leftMargin=54,
    topMargin=50,
    bottomMargin=44,
    title="Assignment 2 - Covariance, VaR, and Copulas",
    author="QRM 545 student submission",
)
doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
markdown_path = BASE / "Assignment2_Answers.md"
if not markdown_path.exists():
    markdown_path.write_text("\n".join(markdown), encoding="utf-8")
print(f"Wrote {OUT}")
print(f"Kept existing Markdown answers at {markdown_path}")
