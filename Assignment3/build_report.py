"""Build the English PDF submission and its matching editable Markdown.

Uses only saved JSON results and the local figures. No analysis is rerun here.
Run with Python containing reportlab and Pillow; see README.md.
"""
from pathlib import Path
import json
import math
import re
from xml.sax.saxutils import escape
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, TableStyle,
                               Spacer, Image, PageBreak, KeepTogether)

ROOT=Path(__file__).resolve().parent
OUT=ROOT/"output/pdf/Assignment3_Report.pdf"
OUT.parent.mkdir(parents=True,exist_ok=True)
load=lambda n:json.loads((ROOT/"results"/n).read_text())
PRE=load("prefit.json")
P1,P2,P3,P4,P5=[load(f"p{i}.json") for i in range(1,6)]
pdfmetrics.registerFont(TTFont("DV",str(ROOT/"fonts/DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB",str(ROOT/"fonts/DejaVuSans-Bold.ttf")))
pdfmetrics.registerFontFamily("DV",normal="DV",bold="DVB",italic="DV",boldItalic="DVB")
NAVY=colors.HexColor("#153C56"); INK=colors.HexColor("#172B3A")
LIGHT=colors.HexColor("#EDF3F7"); GRID=colors.HexColor("#C2CDD5")
styles={
    "title":ParagraphStyle("title",fontName="DVB",fontSize=24,leading=29,textColor=NAVY,spaceAfter=12),
    "h1":ParagraphStyle("h1",fontName="DVB",fontSize=15,leading=20,textColor=NAVY,spaceAfter=10,keepWithNext=True),
    "h2":ParagraphStyle("h2",fontName="DVB",fontSize=10.3,leading=14,textColor=NAVY,spaceBefore=8,spaceAfter=5,keepWithNext=True),
    "body":ParagraphStyle("body",fontName="DV",fontSize=9.15,leading=13.25,textColor=INK,spaceAfter=7),
    "small":ParagraphStyle("small",fontName="DV",fontSize=8,leading=11.4,textColor=INK,spaceAfter=6),
    "cell":ParagraphStyle("cell",fontName="DV",fontSize=7.3,leading=10,textColor=INK),
    "eq":ParagraphStyle("eq",fontName="DV",fontSize=9,leading=14,textColor=NAVY,leftIndent=10,spaceAfter=8),
}
story=[];md=[]


def plain(s):
    s=s.replace("<b>","**").replace("</b>","**").replace("<br/>"," ")
    s=re.sub(r"<sub>(.*?)</sub>",r"_\1",s)
    s=re.sub(r"<super>(.*?)</super>",r"^\1",s)
    return s.replace("&amp;","&").replace("&lt;","<").replace("&gt;",">")


def p(s,style="body"):
    story.append(Paragraph(s,styles[style]));md.append(plain(s)+"\n")


def h(s):
    story.append(Paragraph(s,styles["h2"]));md.append("## "+s+"\n")


def page(s):
    story.append(PageBreak());story.append(Paragraph(s,styles["h1"]));md.append("# "+s+"\n")


def table(head,rows,widths=None):
    if widths is None:widths=[500/len(head)]*len(head)
    else: widths=[500*w/sum(widths) for w in widths]
    cells=[[Paragraph("<b>"+str(v)+"</b>",styles["cell"]) for v in head]]
    cells += [[Paragraph(str(v),styles["cell"]) for v in row] for row in rows]
    t=Table(cells,colWidths=widths,repeatRows=1,hAlign="LEFT")
    t.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),LIGHT),("LINEBELOW",(0,0),(-1,0),.7,NAVY),
        ("LINEBELOW",(0,-1),(-1,-1),.5,GRID),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#F7F9FB")]),
        ("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),5),
        ("RIGHTPADDING",(0,0),(-1,-1),5),("TOPPADDING",(0,0),(-1,-1),4),
        ("BOTTOMPADDING",(0,0),(-1,-1),4),
    ]))
    story.extend([t,Spacer(1,8)])
    md.append("| "+" | ".join(map(plain,map(str,head)))+" |")
    md.append("| "+" | ".join(["---"]*len(head))+" |")
    md.extend("| "+" | ".join(plain(str(v)) for v in row)+" |" for row in rows)
    md.append("")


def figure(name,caption,maxh=310):
    path=ROOT/"figures"/name
    with PILImage.open(path) as im:w0,h0=im.size
    w=500;hh=w*h0/w0
    if hh>maxh:w*=maxh/hh;hh=maxh
    story.append(KeepTogether([Image(str(path),width=w,height=hh),Spacer(1,4),Paragraph(caption,styles["small"])]))
    md.append(f"![{plain(caption)}](figures/{name})\n")


def num(x,n=4):return "N/A" if x is None else f"{x:.{n}f}"
def pct(x,n=3):return f"{x*100:.{n}f}%"
def money(x,n=2):return f"{'-' if x<0 else ''}${abs(x):,.{n}f}"
def bp(x):return f"{x*10000:.4f}"
books=list(P3["greeks"])
short={"CoveredCall":"Covered call","ShortStraddle":"Short straddle","RiskReversal":"Risk reversal","HedgedShortCall":"Hedged short call"}
modes={"unconstrained":"Unconstrained","long_only":"Long only","capped":"PUTW ≤ 20%"}


story.append(Paragraph("Assignment 3",styles["title"]))
md.append("# Assignment 3\n")
p("FinTech 545 - Quantitative Risk Management", "h1")
p("Options, Option Risk, and Portfolio Construction", "h2")
p("Prepared 14 November 2026. All prices and factor histories are the supplied assignment data; no live market inputs are substituted.")
h("Method and reporting conventions")
p("The responses follow Predict, Fit, Reconcile, with each letter of the assignment identified. Predictions were saved in predictions.md after the permitted diagnostics and before the subsequent fits. The preparation timestamp, input hashes and prediction hash are saved with the results.")
p("Returns are arithmetic. Sample variance and covariance use n - 1; skewness and excess kurtosis use finite-sample corrections. Maximum-likelihood Normal variance uses n. AICc = -2ℓ + 2k + 2k(k+1)/(n-k-1). Regression k includes every coefficient, the intercept and residual variance. Conventional OLS standard errors are primary; HC3 diagnostics are also saved.")
p("VaR<sub>α</sub> = -q<sub>α</sub>(P&amp;L), and ES is the negative average of the worst α probability mass. A negative risk number denotes a gain. Historical VaR uses the inverse empirical CDF; for a fractional tail count, ES weights the boundary observation fractionally. Problem 4 also reports the classroom tail-observation convention so the finite-sample difference is explicit.")
p("Problem 1 uses 35/365 years and continuous yield q = 0.006. Problem 3 uses 255 trading days per year, a 10-day holding period, unchanged IVs and no cash financing leg. Theta is signed dV/dt per model year. Problem 4 uses monthly r<sub>f</sub> = 0.03/12; means annualize by 12 and volatility by √12. Problem 5 annualizes daily arithmetic means by 255, with compounded comparisons labeled separately.")
h("Course foundation reviewed")
table(["Week","Concepts applied or checked"],[
    ["1","Moments, mean standard errors, Normal versus Student t and scale versus standard deviation."],
    ["2","OLS, coefficient uncertainty, residual diagnostics, MLE and AICc parameter counts."],
    ["3","Monte Carlo precision, covariance estimation and preservation of dependence when resampling."],
    ["4","Arithmetic compounding, delta-normal risk and full revaluation over multiple days."],
    ["5","Positive-loss ES, coherence and the different sensitivity of VaR and ES to heavy tails."],
    ["6","Generalized BSM, put-call parity, IV inversion and CRR risk-neutral probabilities."],
    ["7","American exercise, discrete-dividend recursion, Greeks, tangency portfolios and factor models."],
    ["8","Uncertainty in optimized weights and expected returns constructed from factor exposures."],
],[35,465])
p("Sources: Dominic Pazzula, Week01/week01.qmd through Week08/week08.qmd, plus all seven available slide sources in Week02/slides through Week08/slides. Week 1 has lecture notes/PDF but no separate slide deck in this checkout. Relevant implementation references were library/gbsm.jl and Week07/Project/bt_american.jl. The supplied Assignment 3 PDF defines the questions. A source manifest and Chinese study guide accompany the code.","small")


page("1. Implied Volatility from a Dirty Chain")
h("Predict - (a) parity at every strike")
p("With continuous dividends, C - P = S exp(-qT) - K exp(-rT). I define the signed gap g = C<sub>mid</sub> - P<sub>mid</sub> - [S exp(-qT) - K exp(-rT)], and use the question's conservative band B = (C<sub>ask</sub> - C<sub>bid</sub>) + (P<sub>ask</sub> - P<sub>bid</sub>). A strike is flagged only if |g| &gt; B.")
table(["Strike","Parity gap ($)","Band ($)","Flag"],[[num(r["strike"],0),num(r["gap"],6),num(r["band"],3),"YES" if r["flag"] else "No"] for r in PRE["p1"]["parity"]],[65,160,145,70])
p("Only K = 175 is flagged: +$0.888179 against $0.470. The quoted call is expensive relative to the put and the dividend-adjusted stock/strike legs. At least one quote or its metadata is inconsistent; parity alone does not say which leg is wrong. Under frictionless stock and funding assumptions the executable option spread also leaves a positive discrepancy, because even the full-spread band is breached.")
h("Predict - (b) equality of implied volatilities")
p("For any common σ, GBSM has C(σ) - P(σ) equal to the parity term, which is independent of σ. If the observed mids satisfy parity exactly and σ<sub>C</sub> prices the call, then P(σ<sub>C</sub>) = C<sub>mid</sub> - parity term = P<sub>mid</sub>. Positive vega makes the inverse unique, so σ<sub>P</sub> = σ<sub>C</sub>. A gap inside the spread band is only approximate consistency; it does not force numerically identical mid IVs.")
h("Predict - (c) inversion reliability")
p("The inverse sensitivity is dσ/dV = 1/vega. Both far ITM and far OTM quotes have low vega, so rounding and spread errors become large IV errors. Calls at K = 215, 220 and 225 all quote $0.05/$0.10, hence a constant $0.075 mid. I predicted a false upward IV wing from that price floor. Deep ITM bids can fall below discounted intrinsic value and fail inversion altogether.")

for kind in ("Call","Put"):
    page(f"1. Fit - (d)-(e) {kind.lower()} implied volatilities and vega")
    p("I implement GBSM with b = r - q and solve V(σ) - quote = 0 using a bracketed root search. Each bid, mid and ask is checked against its no-arbitrage bounds before inversion. All IV columns below are annual percentages. Vega is dollars per 1.0 change in σ; the last column is the local IV change in percentage points for a $0.01 price increase.")
    table(["K","Bid IV (%)","Mid IV (%)","Ask IV (%)","Vega","pp / $0.01"],
        [[num(r["strike"],0),num(None if r["iv_bid"] is None else 100*r["iv_bid"],3),num(100*r["iv_mid"],3),num(100*r["iv_ask"],3),num(r["vega"],4),num(r["vol_points_per_cent"],4)] for r in P1 if r["type"]==kind],
        [40,91,91,91,91,96])
    if kind=="Call":
        p("The K = 140, 145, 150 and 155 call bids are below L<sub>C</sub> = max(0, S exp(-qT) - K exp(-rT)), so no nonnegative volatility can reproduce them. Their mids and asks still invert. This is a bound violation by the bid, not a numerical root-finder failure.")
        p("The one-cent approximation is Δσ ≈ 0.01/vega in decimal volatility, or Δσ<sub>pp</sub> ≈ 1/vega. It is local: when vega changes sharply across a spread, the full bid-to-ask IV range is more informative. A complete machine-readable table with quote prices and inversion diagnostics is saved in results/p1_quotes.csv.")
    else:
        p("The K = 205, 210, 215, 220 and 225 put bids violate L<sub>P</sub> = max(0, K exp(-rT) - S exp(-qT)). Every mid and every ask in the chain has an IV; exactly nine bids do not. The deep ITM K = 225 put has vega only 0.2716 and a one-cent local IV change of 3.6815 points, illustrating how unstable inversion can be despite a large option price.")
        p("N/A means a quote below the discounted intrinsic lower bound. It is not a missing quote or a volatility estimate of zero. The IV band in the chart is therefore unfilled wherever a bid has no admissible inverse.")

page("1. Reconcile - the two data problems")
figure("p1_iv_smile.png","Call and put mid IVs with bid/ask inversion bands. Missing bid inverses are retained as missing.",maxh=285)
h("(f) The parity outlier in volatility units")
c=next(r for r in P1 if r["type"]=="Call" and r["strike"]==175)
pu=next(r for r in P1 if r["type"]=="Put" and r["strike"]==175)
gap=next(r["gap"] for r in PRE["p1"]["parity"] if r["strike"]==175)
p(f"At K = 175, call mid IV is {pct(c['iv_mid'],4)} and put mid IV is {pct(pu['iv_mid'],4)}, a {100*(c['iv_mid']-pu['iv_mid']):.4f}-point difference. Linearizing at the call's vega {c['vega']:.4f} gives g/vega = {100*gap/c['vega']:.4f} vol points; using the put's vega {pu['vega']:.4f} gives {100*gap/pu['vega']:.4f}. The actual gap lies between these estimates, as vega changes over this finite IV interval. The chart shows a downward put outlier, although the parity test itself identifies only relative inconsistency.")
h("(g) The call wing above 210")
p("Call mid IV rises from 22.067% at 210 to 23.823%, 26.689% and 29.447% at 215, 220 and 225. The corresponding one-cent sensitivities are 0.443, 0.482 and 0.519 vol points, and the bid/ask IV ranges are 22.562-24.827%, 25.314-27.781% and 27.965-30.623%. Inverting the same small quote at increasingly remote strikes mechanically requires more volatility. The upturn is mainly evidence about quote floors and resolution, not reliable evidence of market pricing of upside tail risk. Wide IV ranges alone do not establish the cause; the identical bids, asks and mids provide the additional diagnosis.")
p("Parity did not flag those strikes because the dollar discrepancy is small relative to the deep ITM put's wide dollar spread. A large discrepancy measured in IV points need not be large in dollars when vega is low. Parity is a cross-contract price-consistency check; it is not a test of quote informativeness.")
h("(h) The usable shape")
p("Excluding K = 175's inconsistent pair and the floor-dominated call wing, IV declines from roughly 39% at low strikes to about 22% at high strikes. The broad shape is a downside skew or smirk, rather than a symmetric smile. Downside puts command higher implied volatility, consistent with demand for downside protection and a priced left tail. This is an interpretation of option prices, not a claim that an IV curve alone identifies physical crash probabilities.")


page("2. American Options and Discrete Dividends")
h("Predict - (a) exercise condition")
table(["Dividend time","Cash D","K[1 - exp(-r(T-t))]","Conclusion"],[["0.10",money(.25),money(PRE["p2"]["thresholds"][0],6),"Fails: no call exercise incentive"],["0.40",money(1.5),money(PRE["p2"]["thresholds"][1],6),"Passes: exercise can be optimal if ITM"]],[80,65,170,185])
p("The first dividend is below its strike-financing threshold, while the second exceeds it substantially. Passing is a permission for sufficiently high stock prices, not a rule to exercise every call. Remaining optionality still has to be compared with intrinsic value.")
h("Predict - (b) directions")
p("I predicted both call values would decrease, both put values would increase, the American call premium would increase from zero, and the American put premium would shrink. The call holder can recover some dividend exposure through optimal exercise before the large second dividend. The put holder benefits from waiting for the downward cash jump, reducing the value of exercising early.")
h("Fit - (c) prices and present-value adjustment")
p("The CRR inputs are Δt = T/N, u = exp(σ√Δt), d = 1/u, p = [exp(rΔt)-d]/(u-d), with discount exp(-rΔt). Every dividend date is exactly on the grid. At each cash jump, independent subtrees begin at S-D and American values are compared with intrinsic at pre-dividend S. Distinct histories never recombine after a dividend. Exercise immediately after a dividend is also allowed by the next subtree's root.")
table(["Option","No dividend","With cash dividends","GBSM PV adjustment"],[
    ["European call",money(P2["gbsm_no_div"][0],6),money(P2["with_div"][0],6),money(P2["gbsm_pv_adjusted"][0],6)],
    ["American call",money(P2["no_div"][1],6),money(P2["with_div"][1],6),"Not an American formula"],
    ["European put",money(P2["gbsm_no_div"][1],6),money(P2["with_div"][2],6),money(P2["gbsm_pv_adjusted"][1],6)],
    ["American put",money(P2["no_div"][3],6),money(P2["with_div"][3],6),"Not an American formula"],
],[110,115,130,145])
p(f"The European no-dividend entries use GBSM; American entries and all cash-dividend entries use N = {P2['N']}. PV(dividends) = {money(P2['pv_dividends'],6)}, giving adjusted spot {money(48.5-P2['pv_dividends'],6)}. Subtracting the cash PV before using GBSM understates both European tree prices by about $0.102. It approximates the forward level but does not reproduce multiplicative volatility between deterministic dollar jumps. It also cannot price optimal exercise.")

page("2. Fit - (d) convergence")
table(["N","Call, no div.","Put, no div.","Call, cash div.","Put, cash div."],[[r["N"],num(r["no_div"][1],6),num(r["no_div"][3],6),num(r["with_div"][1],6),num(r["with_div"][3],6)] for r in P2["convergence"]],[40,115,115,115,115])
figure("p2_convergence.png","American values oscillate with the lattice; neighboring multiples of five are both retained.",maxh=200)
p("For example, N = 100 and 105 give cash-dividend calls of $3.472648 and $3.465115, and puts of $5.379319 and $5.368243. At 600/605 the calls are $3.467478/$3.468410 and puts $5.370331/$5.370594. Convergence is oscillatory, so one subsequence can give false confidence. The reported N = 400 base prices should be read as approximately $3.468 for the American call and $5.370 for the put; six printed decimals identify the computation, not six-decimal continuum accuracy.")

page("2. Fit and reconcile - sensitivities and exercise")
h("Fit - (e) central finite-difference Greeks at N = 400")
p("For each American price V(S), delta = [V(S+h)-V(S-h)]/(2h), and gamma = [V(S+h)+V(S-h)-2V(S)]/h². The grid and dividend dates remain fixed for all bumps.","eq")
table(["Spot bump h","Call delta","Call gamma","Put delta","Put gamma"],[[num(r["bump"],3),num(r["call_delta"],6),num(r["call_gamma"],6),num(r["put_delta"],6),num(r["put_gamma"],6)] for r in P2["finite_differences"]])
h("Fit - (f) sensitivity to each dividend amount")
p("Entries are dollars of option value per additional dollar of the specified dividend. They are central differences, holding dividend dates fixed. Both cash-amount bumps are reported to expose numerical sensitivity.")
rows=[]
for d in P2["dividend_sensitivity"]:
    for e in d["estimates"]:
        rows.append([f"D{d['dividend']} at {d['time']:.2f}",num(e["bump"],3)]+[num(v,6) for v in e["values"]])
table(["Dividend","Bump","Euro call","Amer. call","Euro put","Amer. put"],rows,[95,45,90,90,90,90])
h("Reconcile - (g) premiums and the exercise boundary")
nd=P2["no_div"];dv=P2["with_div"]
table(["Premium American - European","No dividends","Cash dividends"],[
    ["Call, matched tree",money(nd[1]-nd[0],6),money(dv[1]-dv[0],6)],
    ["Put, matched tree",money(nd[3]-nd[2],6),money(dv[3]-dv[2],6)],
],[260,120,120])
p("The call premium rises from zero to $0.293551, while the put premium falls from $0.127866 to $0.085781, consistent with the predictions. Matched-tree premiums isolate the exercise right from lattice error. Relative to exact GBSM instead, the no-dividend put premium is $0.130259 and the finite-N call difference is $0.002393; that tiny call difference is discretization error, since the true no-dividend call premium is zero.")
p(f"Immediately before D2, exercise is optimal above pre-dividend stock price S* ≈ {money(P2['second_dividend_exercise_boundary'],5)} on the same remaining CRR lattice. I solve S* - 50 = C<sub>A</sub>(S* - 1.50, 50, 0.10). There are no later dividends, so C<sub>A</sub> equals the European call in the continuum; replacing the remaining tree by GBSM gives {money(P2['second_dividend_continuous_boundary'],5)}, an independent boundary check.")
page("2. Reconcile - the finite-difference Greeks")
h("(h) Why gamma does not settle")
p("Gamma is the unstable Greek. Call gamma drops from about 0.0415 at h = 1 to essentially zero at h = 0.001; put gamma also changes markedly. At fixed N, terminal payoffs, discounted sums and maxima make the price piecewise linear in spot. Inside one linear segment its second derivative is zero; a bump crossing one or more kinks produces a nonzero, sometimes sharply varying quotient. Shrinking h at fixed N therefore does not converge reliably to the smooth model's gamma. This is a lattice-resolution issue in addition to ordinary floating-point cancellation; use joint grid refinement and a bump large enough to span lattice features.")
h("Reconcile - (i) the two call dividend sensitivities")
p("The American call loses about $0.468 per additional dollar of D1, but only $0.108 per dollar of D2. Before D1 the dividend is too small to justify giving up the option, so the call remains exposed to the cash drop. Before D2, sufficiently ITM holders exercise and avoid that option-value loss. This exercise right limits the second-dividend sensitivity. The European call cannot exercise and has much closer sensitivities, about -0.435 and -0.380; timing and exercise both matter.")


page("3. VaR of an Option Book - predictions and fit")
h("Predict - (a) aggregate Greeks and ranking")
p(f"ABC closes at {money(P3['spot'])} on {PRE['p3']['date']}. Options initially have 30/255 years left, and each option represents one share. The quantities below already include all positive and negative holdings. Theta is dollars per model year; gamma is dollars per squared dollar of spot change.")
table(["Book","Current value ($)","Delta","Gamma","Theta / year"],[[short[b],num(g["value"],3),num(g["delta"],6),num(g["gamma"],6),num(g["theta"],3)] for b,g in P3["greeks"].items()],[125,105,90,90,90])
p("I ranked the expected missed absolute tail risk: ShortStraddle, HedgedShortCall, CoveredCall, then RiskReversal. The first two are almost delta neutral but strongly short gamma, so delta normal should severely understate risk. The covered call is also short gamma, with positive theta offsetting some loss. RiskReversal has small positive local gamma; I predicted modest overstatement at 5%, with less confidence in the far tail where local gamma may change sign.")
h("Predict - (b) no-move P&amp;L and tail ratios")
p("All four initial thetas are positive, so I predicted positive ten-day P&amp;L at unchanged spot, smallest for RiskReversal. For the nearly hedged short-gamma books, a squared-move loss should give ES/VaR substantially above the zero-mean normal's 1.254 at 5%. At 1% the zero-mean normal benchmark is 1.146, not 1.25; nonzero mean shifts either ratio.")
h("Fit - (c) moments and distribution choice")
m=P3["moments"]
table(["Observations","Mean","Variance","SD","Skew","Excess kurtosis"],[[m["n"],num(m["mean"],8),num(m["variance"],8),pct(m["sd"],4),num(m["skew"],5),num(m["excess_kurtosis"],5)]])
table(["Daily model","Location μ","Scale","Implied SD","ν","AICc"],[[name,num(f["mu"],8),num(f["scale"],8),num(f["sd"],8),num(f.get("df"),5),num(f["aicc"],4)] for name,f in P3["fitted"].items()],[80,92,92,92,65,79])
p("Student t wins by about 28.42 AICc units. Its scale 0.013506 is not its standard deviation; SD = scale × √[ν/(ν-2)] ≈ 0.016694. The sample is nearly symmetric but fat tailed, agreeing with the prefit prediction. Both distributions are fitted with a free location, then reset to exactly zero population mean for risk simulation, as required. No sample-mean drift is carried into the scenarios.")

page("3. Fit - (d)-(e) ten-day risk")
p("Delta-normal uses σ<sub>P</sub> = |δ| S<sub>0</sub> s<sub>daily</sub>√10, VaR = -z<sub>α</sub>σ<sub>P</sub>, and ES = φ(z<sub>α</sub>)σ<sub>P</sub>/α, with zero drift and no theta adjustment. Using dollar sensitivities avoids dividing by a negative or small book value. The daily sample SD is 1.667428%.")
table(["Book","DN VaR 5%","DN ES 5%","DN VaR 1%","DN ES 1%"],[[short[b]]+[num(P3["delta_normal"][b][a][k],2) for a,k in [("0.05","var"),("0.05","es"),("0.01","var"),("0.01","es")]] for b in books],[140,90,90,90,90])
p(f"Full revaluation uses {P3['nsim']:,} independent ten-day paths per model, with seeds {P3['seed']} and {P3['seed']+1}. Daily returns are iid draws from the fitted zero-location Normal or t. I compound S<sub>10</sub> = S<sub>0</sub> × ∏(1+r<sub>j</sub>), hold IV fixed, reduce expiry from 30 to 20 trading days and reprice each position. I do not multiply a one-day Student t draw by √10; the sum or product of independent t draws is not itself a t with the same degrees of freedom.")
for model in ("Normal","StudentT"):
    h(f"{model}: full revaluation; all dollar P&L")
    table(["Book","Mean","VaR 5%","ES 5%","VaR 1%","ES 1%"],[[short[b],num(P3["simulation"][model][b]["mean"],2)]+[num(P3["simulation"][model][b]["full"][a][k],2) for a,k in [("0.05","var"),("0.05","es"),("0.01","var"),("0.01","es")]] for b in books],[130,65,76,76,76,77])
p("All simulated daily returns exceeded -100%, so no sampled path needed truncation or rejection. The unbounded arithmetic-return families do assign a small theoretical probability to impossible negative prices; that model limitation is not repaired by changing the requested sampling rule. Means and tail losses are Monte Carlo estimates. Across twenty independent batches, 1% ES standard errors range from roughly $1-$2 under Normal and $1.5-$3 under t. Parameter uncertainty and model error are additional and are not included in those simulation standard errors.")

page("3. Fit - (f) full P&amp;L versus delta only")
figure("p3_book_pnl.png","Every panel uses the same stock price grid and ten fewer days to expiry. Positive P&amp;L is a gain.",maxh=400)
p("The covered call loses approximately like stock on the downside and gives up upside through the short call. The short straddle and hedged short call can lose on large moves in either direction, despite almost-flat delta lines at today's spot. RiskReversal has appreciable directional exposure; its nonlinear put wing becomes important as the stock falls. The vertical displacement at unchanged spot is time decay, which the delta-only line omits.")
h("Reconcile - no-move gains versus simulated mean")
table(["Book","Spot fixed: actual P&amp;L","Initial Θ × 10/255","Normal mean","t mean"],[[short[b],num(P3["no_move"][b],2),num(P3["greeks"][b]["theta"]*10/255,2),num(P3["simulation"]["Normal"][b]["mean"],2),num(P3["simulation"]["StudentT"][b]["mean"],2)] for b in books],[130,120,100,75,75])
p("The actual no-move gains agree in sign with all four predictions. They differ from Θ × Δt because theta itself changes over the ten-day interval. Positive expected underlying return was not assumed; option time decay can generate positive mean book P&amp;L even when E[S<sub>10</sub>-S<sub>0</sub>] = 0.")

page("3. Reconcile - (g) what gamma repairs and misses")
p("The nearly hedged books have DN 5% VaR of only $7.64 and $3.82. Their Normal full-revaluation values are $314.80 and $149.10. Delta normal sees only δΔS, so it misses the negative ½Γ(ΔS)² term and positive ΘΔt. These books are not protected against large moves merely because their initial delta is small.")
p("I evaluated both δΔS + ½Γ(ΔS)² and δΔS + ½Γ(ΔS)² + Θ(10/255) on exactly the same terminal-price scenarios used for full revaluation. The next table gives the three 5% comparisons; the following table gives the harder 1% ES comparison. All entries are dollars.")
table(["Model / book","Full VaR 5%","ΔΓ VaR 5%","ΔΓΘ VaR 5%","Full ES 5%","ΔΓΘ ES 5%"],[[f"{'N' if model=='Normal' else 't'} / {short[b]}",num(s["full"]["0.05"]["var"],2),num(s["delta_gamma"]["0.05"]["var"],2),num(s["delta_gamma_theta"]["0.05"]["var"],2),num(s["full"]["0.05"]["es"],2),num(s["delta_gamma_theta"]["0.05"]["es"],2)] for model in ("Normal","StudentT") for b,s in P3["simulation"][model].items()],[160,68,68,68,68,68])
table(["Book","Normal full ES 1%","Normal ΔΓΘ ES 1%","t full ES 1%","t ΔΓΘ ES 1%"],[[short[b]]+[num(P3["simulation"][model][b][method]["0.01"]["es"],2) for model,method in [("Normal","full"),("Normal","delta_gamma_theta"),("StudentT","full"),("StudentT","delta_gamma_theta")]] for b in books],[140,90,90,90,90])
p("Gamma improves the near-flat delta diagnosis but does not reproduce the full values. Adding gamma without theta overstates losses by discarding the time-decay gain. Even with theta, the local expansion freezes all Greeks, omits higher orders and omits time/spot cross effects. RiskReversal illustrates the limitation sharply: positive gamma at today's spot does not protect the far put wing, so its 1% ES is understated by the local expansion. This is the weakness anticipated in the prediction, and why the 5% overstatement prediction should not be extrapolated to all tail measures.")
h("Reconcile - (h) compensation for short gamma")
p("The short-gamma books' simulated means are positive but much smaller than their no-move gains. Implied volatilities are around 27-29%, versus approximately 26.63% annualized realized daily volatility, allowing time decay to exceed the expected gamma cost in this model. The positive mean pays for convex losses on large moves, including jumps and unhedged tail moves; it is an insurance premium, not a free return. A larger realized variance or a volatility jump could reverse it.")

page("3. Reconcile - (i)-(j) distributional risk and a flat book")
table(["Book","Normal ES/VaR 5%","t ES/VaR 5%","t ΔVaR 5%","t ΔES 1%"],[[short[b],num(P3["simulation"]["Normal"][b]["full"]["0.05"]["es"]/P3["simulation"]["Normal"][b]["full"]["0.05"]["var"],3),num(P3["simulation"]["StudentT"][b]["full"]["0.05"]["es"]/P3["simulation"]["StudentT"][b]["full"]["0.05"]["var"],3),num(P3["simulation"]["StudentT"][b]["full"]["0.05"]["var"]-P3["simulation"]["Normal"][b]["full"]["0.05"]["var"],2),num(P3["simulation"]["StudentT"][b]["full"]["0.01"]["es"]-P3["simulation"]["Normal"][b]["full"]["0.01"]["es"],2)] for b in books],[135,100,100,80,85])
p("The short straddle and hedged short call have the largest ES/VaR ratios, about 1.53/1.56 under Normal and 1.61/1.65 under t. This agrees with the nonlinear-tail prediction even when the underlying return model itself is Normal. Nonlinear pricing changes the shape of the P&amp;L distribution.")
p("Switching to t changes CoveredCall and RiskReversal 5% VaR by less than ten cents in this run, within simulation error. It increases ShortStraddle and HedgedShortCall 5% VaR by about $6.76 and $3.38. The corresponding 1% ES increases are about $77.92, $69.20, $95.90 and $47.95 for CoveredCall, RiskReversal, ShortStraddle and HedgedShortCall, respectively. Relative 1% ES increases are greatest in the two short-gamma books, around 13%; squared-move losses put more weight on extremes. The short straddle has the largest absolute increase.")
p("The fitted models have almost identical daily SDs but different tail shapes. Around the 5% one-sided quantile the central mass and tail reallocation largely offset, and ten-day aggregation further reduces central differences. ES averages beyond that threshold, and 1% risk reaches farther into the region where the t density dominates. Therefore a small 5% VaR change is not evidence that the model choice is immaterial.")
p("Relative to Normal full revaluation, the predicted ranking of missed absolute 5% VaR is confirmed: $307.16 for ShortStraddle, $145.28 for HedgedShortCall, $76.58 for CoveredCall, versus a $37.94 overstatement for RiskReversal. In the t 1% tail, however, RiskReversal's DN VaR and ES understate the full values. The part missed by a simple sign-of-gamma argument is the changing gamma in the remote put wing and the heavier underlying tail.")
h("(j) Two sentences to the risk manager")
p("The book is approximately delta neutral today (delta -0.444 shares), but it remains short gamma and exposed to theta, volatility changes and large moves in either direction. Its ten-day 5% VaR is about $152 and 1% ES about $414 under the fitted t full-revaluation model, so calling it flat materially understates its risk.")


page("4. A Sharpe Ratio That Sells Insurance")
h("Predict - (a) moments, Sharpe and the influential month")
p("The file has 240 monthly total-return observations. I use monthly rf = 0.25%, annual Sharpe = √12 × (mean - rf)/SD, and excess kurtosis. Means and SDs in the table are monthly; variance is in decimal-return squared units.")
table(["Asset","Mean","Variance","SD","Skew","Excess kurt.","Ann. SR"],[[a,pct(s["mean"]),num(s["variance"],7),pct(s["sd"]),num(s["skew"],3),num(s["excess_kurtosis"],3),num(s["sharpe"],4)] for a,s in PRE["p4"].items()],[45,65,80,65,75,85,85])
p("PUTW stands out: high Sharpe accompanies -6.57 skew and 61.14 excess kurtosis. June 2008 lost 16.7197% and contributes 45.95% of its centered sum of squares. Removing this single month changes its monthly mean from 0.6243% to 0.6969%, SD from 1.6551% to 1.2172%, and annual Sharpe from 0.7834 to 1.2717. Skew and excess kurtosis remain -4.50 and 40.74 after removal. The tail structure is not explained away by one observation, and deleting the bad month would make the strategy look artificially safer.")
h("Predict - (b) portfolio concentration and normal ES")
p("Before optimization I expected PUTW to take a dominant 50-80% weight, and expected the resulting historical 1% ES to greatly exceed a matched Normal ES. Its many smooth premium months conceal infrequent large insurance payouts. With only 240 observations the 1% tail contains 2.4 months of probability mass, so the empirical estimate is also imprecise.")
h("Fit - (c) three maximum-Sharpe portfolios")
p("All risky-asset weights sum to one. The unconstrained solution is proportional to Σ<super>-1</super>(μ-rf·1). For the other two, I minimize a convex quadratic variance after fixing excess return in rescaled holdings, then normalize; the 20% cap becomes a linear inequality. No risk-free asset is included in the four-asset weight table.")
table(["Portfolio","EQ","BOND","STK","PUTW","Ann. SR"],[[modes[mode]]+[pct(w,3) for w in q["weights"]]+[num(q["annual_sharpe"],4)] for mode,q in P4["portfolios"].items()],[110,78,78,78,78,78])
p("The long-only optimizer assigns PUTW 73.013%, within the predicted range, and nearly eliminates EQ. The unconstrained portfolio shorts EQ by 4.387% and holds PUTW at 77.468%. Imposing the cap forces PUTW to 20%, increases BOND to 63.621% and lowers estimated Sharpe from 0.8153 to 0.5902. The precise decimals describe fitted weights rather than confidence in their stability.")

page("4. Fit - the frontier and tail risk")
figure("p4_frontier.png","The upper long-only frontier is traced by minimum variance at each target return. CML uses the long-only tangency Sharpe.",maxh=275)
h("(d) Monthly VaR and ES, in percent of portfolio capital")
table(["Portfolio / model","VaR 5%","ES 5%","VaR 1%","ES 1%"],[[f"{modes[mode]} / {label}"]+[pct(q["risk"][a][method][k],3) for a,k in [("0.05","var"),("0.05","es"),("0.01","var"),("0.01","es")]] for mode,q in P4["portfolios"].items() for method,label in [("historical","Historical"),("normal","Normal")]], [180,80,80,80,80])
p("The long-only historical 1% ES is 9.205%, versus 2.877% from the matched Normal, a factor of about 3.20. The cap reduces historical 1% ES to 5.491%, even though matched-Normal ES rises slightly to 2.998%. The cap helps in the observed crash tail, not necessarily at every quantile: its historical 5% VaR rises as the portfolio holds less of PUTW's frequent small gains. This is why reporting only one quantile can reverse the apparent comparison.")
p("Finite-sample ES convention: primary 1% ES averages the two worst months plus 0.4 of the third, divided by 2.4. The classroom shortcut instead averages all three observations at or below the interpolated quantile, giving 1% ES of 8.160%, 8.145% and 5.009% for unconstrained, long-only and capped portfolios. At 5% both conventions use twelve months and agree. The 1% difference is a small-sample convention effect; either calculation retains the insurance-tail conclusion.","small")

page("4. Reconcile - conditional exposure and input uncertainty")
h("Fit - (e) CAPM and stress beta")
table(["Regression","n","Alpha / month","t(alpha)","Beta","R²"],[[label,fit["n"],pct(fit["coefficients"][0],4),num(fit["t"][0],4),num(fit["coefficients"][1],5),num(fit["r2"],5)] for label,fit in [("All months",P4["capm"]),("EQ excess &lt; -5%",P4["stress_capm"])]],[130,35,105,80,75,75])
p("Full-sample alpha is 0.274481% per month (3.2938% arithmetically annualized), with conventional t = 3.0516; beta is 0.184786 and R² is 0.302554. In the 26 months when EQ excess return is below -5%, beta is 0.942847, about 5.10 times the full-sample estimate. The stress regression includes its own intercept; it is a conditional fit, not the same alpha estimated from the full sample. HC3 reduces the full-sample alpha t statistic to 2.1899, showing that standard-error assumptions also matter.")
h("Reconcile - (f) what the optimizer bought, and ES coherence")
p("It bought a concentrated short-put insurance exposure combined with cash-like premium months and a bond allocation. Sharpe depends only on the first two moments; it is unchanged if losses are rearranged into a much more negatively skewed distribution with the same mean and variance. Fully cash securing the strike avoids borrowing and margin leverage, but it does not remove the nonlinear loss when EQ falls below the strike.")
p("ES directly averages the severity of the worst losses. Monotonicity makes worsening losses in a tail state increase risk; positive homogeneity scales those losses with position size; translation invariance handles certain cash offsets; subadditivity gives a coherent diversification rule. These properties support meaningful aggregation, but do not make a fitted Normal ES correct for a non-Normal strategy. The empirical tail distribution, as well as the measure, must capture the insurance payout.")
h("Reconcile - (g) interpreting alpha")
p("A positive CAPM alpha is not convincing evidence of skill here. A single constant beta averages across calm months, when the short put has low market sensitivity, and crash months, when its delta approaches one and losses accelerate. The 0.185 versus 0.943 betas expose that state dependence. The intercept can therefore label compensation for selling downside convexity as alpha because the linear market model omitted the option payoff.")
h("Reconcile - (h) mean standard errors")
table(["Asset","Mean / month","SE(mean)","Approximate 95% interval"],[[a,pct(s["mean"],4),pct(s["se_mean"],4),f"[{pct(s['mean']-1.96*s['se_mean'],3)}, {pct(s['mean']+1.96*s['se_mean'],3)}]"] for a,s in PRE["p4"].items()],[65,100,100,235])
p("These are iid standard errors s/√240, not robust confidence guarantees for an insurance strategy. Subtracting a fixed rf does not change the SE. EQ, BOND and STK have excess-mean t ratios of only about 1.70, 0.95 and 1.45; PUTW's is 3.50 but its highly skewed tail makes a Gaussian interval a weak description of uncertainty. Twenty years of monthly observations still leave substantial uncertainty in the mean inputs the optimizer amplifies.")

page("4. Reconcile - resampling the tangency weights")
p("I resampled 500 sets of 240 whole months, preserving cross-asset dependence within each draw, then re-estimated means, covariance and maximum-Sharpe weights. The table gives marginal 5th-95th percentile weight intervals, not a joint confidence region. The seed is 5452036.")
table(["Portfolio","EQ interval","BOND interval","STK interval","PUTW interval"],[[modes[mode]]+[f"{pct(lo,1)} to {pct(hi,1)}" for lo,hi in zip(v["p05"],v["p95"])] for mode,v in P4["bootstrap"].items()],[100,100,100,100,100])
p("All long-only and capped bootstrap solves succeeded. For unconstrained tangency, 498 of 500 draws had a positive-budget tangency direction; the other two are explicitly excluded, so its interval is conditional on that direction existing. Negative excess-premium realizations can make the finite unconstrained budget-normalized tangency construction inappropriate.")
p("Long-only PUTW ranges from about 28.4% to 100%, and unconstrained PUTW from about 32.5% to 128.6%. This is large weight uncertainty despite the same 240-month sample size. I would trust the qualitative observation that Sharpe optimization favors PUTW and that a cap mechanically limits the exposure. I would not trust the exact 73.013% estimate, the small STK allocation, or the precise unconstrained short-EQ weight as stable investment prescriptions.")
p("The PUTW cap is active at 20% in most resamples; that stability comes from the constraint, not precise estimation. Rare bootstrap samples omit enough loss months to produce extremely different insurance-risk estimates, which is part of the economic concern rather than a numerical failure. The iid month bootstrap also does not capture serial dependence or unseen regimes; it is a sensitivity analysis of the available sample.")
figure("prefit_diagnostics.png","Diagnostics prepared before the later fits: ABC prices/returns, PUTW returns, and cumulative fund growth.",maxh=275)


page("5. Alpha or Factor Exposure? - predictions")
h("Predict - (a) excess performance and CAPM")
p(f"I join the two factor files by date, strip the trailing spaces from the momentum header, divide percentage factors and RF by 100, then join to the funds' decimal returns. All {P5['sample_n']} fund observations match, covering 1 October 1996 through 28 September 2001. Each dependent variable is fund return minus that day's RF; Mkt-RF is already an excess return and is not reduced by RF a second time.")
table(["Fund","Daily mean excess","Daily total SD","Daily excess SD","Annual excess SR","CAPM alpha bp/day","t(alpha)"],[[f,pct(s["excess_moments"]["mean"],5),pct(s["moments"]["sd"],4),pct(s["excess_moments"]["sd"],4),num(s["annual_sharpe"],4),bp(s["capm"]["coefficients"][0]),num(s["capm"]["t"][0],4)] for f,s in PRE["p5"]["funds"].items()],[55,80,75,75,70,80,65])
p("FUND1 initially looks more skilled: higher excess Sharpe and a larger CAPM alpha with a t statistic above three. FUND2's initial alpha is smaller and its conventional t statistic is below two. That conclusion is explicitly provisional because CAPM admits only one systematic factor.")
h("Predict - (b) correlations of CAPM residuals")
table(["Fund","Residual / SMB","Residual / HML","Residual / Mom"],[[f]+[num(s["residual_correlations"][q],5) for q in ("SMB","HML","Mom")] for f,s in PRE["p5"]["funds"].items()],[80,140,140,140])
p("I predicted FUND1's alpha would largely disappear when momentum was included: a residual-momentum correlation of 0.8015 is too large to call unexplained performance. HML also has a positive residual correlation. FUND2's residuals correlate with SMB at 0.3295 but only 0.0530 with momentum, suggesting improved fit from size exposure and little benefit from adding momentum. I expected its alpha to be more persistent than FUND1's, without asserting that a residual correlation alone determines the sign of its alpha change.")
h("Fit - (c) regression and information-criterion conventions")
p("I fit CAPM, FF3 and Carhart4 on exactly the same dates for each fund. The equations are excess fund return = alpha + the included factor betas × factor returns + residual. Coefficients and standard errors follow on the next pages. Alpha and its SE are shown in basis points per day; beta and beta SE are unitless. AICc uses Gaussian residual MLE variance, counting k = 3, 5 and 6 for CAPM, FF3 and Carhart4 respectively. Comparisons are within the same fund and sample.")

for fund in ("FUND1","FUND2"):
    page(f"5. Fit - (c) {fund} coefficients and model comparison")
    rows=[]
    for name,fit in P5["funds"][fund]["fits"].items():
        for i,param in enumerate(fit["names"]):
            coef=bp(fit["coefficients"][i]) if i==0 else num(fit["coefficients"][i],6)
            se=bp(fit["se"][i]) if i==0 else num(fit["se"][i],6)
            rows.append([name,param+(" (bp/day)" if i==0 else ""),coef,se,num(fit["t"][i],4)])
    table(["Model","Parameter","Coefficient","Conventional SE","t statistic"],rows,[75,135,100,110,80])
    table(["Model","R²","AICc","Alpha t","HC3 alpha t","Durbin-Watson"],[[name,num(fit["r2"],6),num(fit["aicc"],4),num(fit["t"][0],4),num(fit["hc3_t"][0],4),num(fit["durbin_watson"],4)] for name,fit in P5["funds"][fund]["fits"].items()],[80,70,110,75,80,85])
    if fund=="FUND1":
        p("FF3 lowers daily alpha from 4.4066 bp to 2.9631 bp but leaves an apparently significant intercept. Carhart4 lowers it to only 0.02938 bp, with t = 0.0421, and improves R² from 0.8452 to 0.9563. Its momentum beta is 0.39355. AICc falls by roughly 1588.71 relative to FF3, overwhelming the extra-parameter penalty. This strongly supports the predicted omitted-momentum explanation.")
        p("FUND1's CAPM/FF3 residuals have some positive serial correlation (DW around 1.64), while the four-factor DW is near two. Conventional and HC3 alpha t statistics both become essentially zero in Carhart4. HC3 handles heteroskedasticity rather than serial correlation; these diagnostics do not prove iid residuals, but the disappearance of alpha is not a borderline significance call.")
    else:
        p("FUND2's daily alpha rises from 2.4491 bp under CAPM to 2.7715 bp under FF3 and remains 2.7280 bp under Carhart4. Adding size improves R² from 0.5669 to 0.6148. The momentum coefficient is only 0.00583 with SE 0.01267, so Carhart4 adds little fit and loses to FF3 on AICc by 1.8063. The persistent alpha agrees with the prediction, and the slight increase is consistent with removing negative sample size-factor compensation.")
        p("Carhart4 alpha has conventional t = 2.1495 and HC3 t = 2.1507. That is modest statistical evidence, not proof of manager skill. The model can still omit systematic risks, fees may change, and significance in this historical sample need not persist. For selecting among the specified models, FF3 is adequate for FUND2, while Carhart4 remains a useful common attribution and stress framework for comparing the funds.")

page("5. Fit - (d)-(e) expected returns and momentum stress")
h("(d) Most recent ten years in the supplied factor files")
p("The factor files end on 30 September 2024. I use dates strictly after 30 September 2014 through that end date: 1 October 2014-30 September 2024, 2,516 joined factor observations. This is the requested latest ten years in the files, not the five-year fund regression window and not the ten years ending in 2026. These factor observations postdate the fund sample, so this calculation is a prescribed historical comparison, not an implementable 2001 out-of-sample forecast.")
table(["Factor","Recent daily mean","Annual arithmetic mean","Fund-sample daily mean"],[[f,pct(P5["recent_daily_factor_means"][f],5),pct(255*P5["recent_daily_factor_means"][f],3),pct(P5["sample_daily_factor_means"][f],5)] for f in ("Mkt-RF","SMB","HML","Mom","RF")],[80,140,140,140])
p("Using four-factor betas, expected daily total return without alpha is mean(RF) + Σ beta<sub>j</sub> mean(f<sub>j</sub>). The with-alpha version adds the fitted daily intercept. I then multiply by 255 for annual arithmetic expected return, consistent with the assignment's arithmetic-return default. Compounding the expected daily gross return is a separate convention shown below; it is not the expected log-growth rate.")
table(["Fund","Annual, no alpha","Annual, with alpha","Compounded, no alpha","Compounded, with alpha"],[[f,pct(v["annual_expected_without_alpha"],3),pct(v["annual_expected_with_alpha"],3),pct(v["compounded_expected_without_alpha"],3),pct(v["compounded_expected_with_alpha"],3)] for f,v in P5["funds"].items()],[60,110,110,110,110])
h("(e) Worst momentum day with other factors flat")
p(f"The most negative daily Mom observation in the entire provided factor history is {pct(P5['worst_momentum_return'],2)} on 5 September 1939. With the other factor shocks set to zero, the isolated return shock is beta<sub>Mom</sub> × (-0.1844). I exclude RF, alpha and residual shocks from this factor-only stress, and scale by each fund's sample daily total-return SD.")
table(["Fund","Mom beta","Factor shock","Loss on $10 million","Daily SD multiples"],[[f,num(v["fits"]["Carhart4"]["coefficients"][-1],6),pct(v["momentum_scenario_return"],4),money(v["momentum_scenario_loss"],2),num(v["momentum_scenario_sigma"],4)] for f,v in P5["funds"].items()],[60,80,100,155,105])
p("FUND1's 7.2571% factor loss is about 6.18 sample daily SDs. FUND2's is only 0.1076%, about 0.15 SDs. This is a deterministic exposure stress, not a probability statement or an all-factor historical replay; a momentum crash can be dangerous even if the fund's average-period Sharpe looked attractive.")

page("5. Reconcile - (f)-(h) paying for alpha")
h("(f) Explaining FUND1's alpha change")
p("FUND1's CAPM alpha disappears almost entirely in Carhart4, as predicted. During the fund sample the annual arithmetic premia were approximately 5.510% for market, -4.151% for SMB, 9.478% for HML and 19.937% for Mom. FUND1 held a substantial positive momentum beta and a positive value beta, so the strong sample premia paid returns that CAPM could misclassify as skill.")
p("An exact omitted-variable accounting also allows for the omitted factors' correlations with the market. Regress each omitted factor f on market: f = a<sub>f</sub> + b<sub>f</sub> M + residual. Then alpha<sub>CAPM</sub> = alpha<sub>4F</sub> + Σ beta<sub>f,4F</sub> a<sub>f</sub>. Here a<sub>f</sub> = mean(f) - b<sub>f</sub> mean(M). Simply multiplying beta by the raw factor mean would miss the portion absorbed into CAPM beta.","eq")
f1=P5["funds"]["FUND1"]
table(["Component","Contribution to CAPM alpha (bp/day)"],[["Four-factor alpha",bp(f1["fits"]["Carhart4"]["coefficients"][0])]]+[[f,bp(v["contribution_to_capm_alpha"])] for f,v in f1["omitted_factor_attribution"].items()]+[["Sum = CAPM alpha",bp(f1["fits"]["CAPM"]["coefficients"][0])]], [250,250])
p("The momentum term contributes 3.0199 bp/day and HML 1.3585 bp/day; SMB contributes approximately -0.0012 bp/day. Together with the four-factor alpha of 0.0294 bp/day, these recover 4.4066 bp/day. The identity reconciles the alpha change numerically, not only by noting that momentum beta is positive.")
h("(g) APT interpretation and opinion")
p("Under APT, expected excess returns compensate exposures to priced systematic risks. Alpha is the intercept left relative to the selected factor model, so a positive alpha may reflect skill, omitted factors, nonlinear exposure, changing betas or estimation error. It is not a model-free quantity, and statistical alpha alone does not prove an arbitrage.")
p("<b>Opinion:</b> I would not pay FUND1 an alpha fee on this evidence: its CAPM alpha is explained by value and momentum exposures, and its momentum stress is substantial. If choosing between these two for an alpha fee, I would prefer FUND2, conditional on fee terms, investability, further out-of-sample evidence and checking other systematic risks. I would use Carhart4 as the common screening model to avoid the omitted-momentum error, while acknowledging FF3 wins FUND2's within-sample AICc comparison. FUND2's roughly 2.15 alpha t statistic is suggestive, not a guarantee; the provided returns alone do not establish whether another quoted fee has already been deducted.")
page("5. Reconcile - (h) expected returns for an optimizer")
table(["Fund","Realized annual arithmetic","Realized CAGR","Factor expected, no alpha","Factor expected, with alpha"],[[f,pct(v["realized_annual_arithmetic"],3),pct(v["realized_cagr"],3),pct(v["annual_expected_without_alpha"],3),pct(v["annual_expected_with_alpha"],3)] for f,v in P5["funds"].items()],[60,115,105,110,110])
p("FUND1's realized annual arithmetic return is 20.900%, far above the 13.705% latest-factor-premia estimate; adding its negligible alpha changes little. The fund's favorable value/momentum regime did not persist in the later ten-year factor averages. FUND2 realized 13.605%, versus 6.892% without alpha and 13.848% with alpha, so its fitted intercept accounts for much of that gap under these assumptions.")
p("A factor model makes expected-return assumptions visible and separates exposure from fitted alpha. It does not eliminate uncertain betas, unstable factor premia, regime differences or the risk of assuming alpha persists. For an optimizer like Problem 4's, using long-horizon premia and carefully justified shrinkage can reduce reliance on noisy recent asset means, but weights still need sensitivity analysis and exposure constraints. A good in-sample factor fit is not permission to treat its expected-return inputs as known.")


page("6. Code, reproduction and verification")
p("All code, unchanged input CSVs, figures, predictions and full-precision JSON outputs are in Assignment3/. The README gives a clean-environment setup and the exact commands to reproduce the report. No external option-pricing package is used.")
table(["File","Purpose"],[
    ["analysis.py","Separate prepare/fit stages, all five empirical problems, plots and provenance."],
    ["options.py","Own generalized BSM, analytic Greeks, IV inversion and exact dividend-subtree CRR rollback."],
    ["risklib.py","Moments, MLE/AICc, OLS/HC3, empirical and Normal risk, tangency and active-set frontier."],
    ["build_report.py","Loads saved results and renders this PDF plus matching Markdown; does not refit models."],
    ["tests/test_finance.py","Nine economic/numerical checks including an independent exhaustive-path dividend tree."],
    ["predictions.md","Preserved prefit reasoning. The fit records its SHA-256 hash."],
    ["results/*.json and *.csv","Full-precision estimates, all quote diagnostics, Monte Carlo SEs and bootstrap intervals."],
    ["COURSE_NOTES_zh.md","Chinese course-to-assignment guide and explanations of common convention errors."],
],[130,370])
h("Validation performed")
p("Nine tests pass. They check analytic put-call parity and bounds, Greeks against independent finite differences, IV inversion and invalid-quote handling, a dividend tree against exhaustive path enumeration, American/European dominance and dividend parity, no-dividend tree convergence to GBSM, exact-mass ES coherence on a discrete example, tangency against an independent direct Sharpe search, and frontier constraints including endpoints. The exhaustive tree explicitly allows exercise both immediately before and immediately after a cash jump.")
p("The whole analysis was rerun after numerical fixes. All five problems have saved outputs, every requested letter has a written response, both return distributions use one million paths, and portfolio-weight uncertainty uses 500 bootstrap samples. The PDF was rendered and visually checked before delivery. Printed Monte Carlo and tree digits identify this run; they should not be interpreted as eliminating model or discretization uncertainty.")
h("Submission")
p("The PDF is the written response; the full Assignment3 folder supplies the graded code and README. After reviewing and placing the folder in the intended repository, the assignment instructs the student to reply “done.” in Canvas. No Canvas response or repository push is performed by these scripts.")


def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(GRID);canvas.setLineWidth(.4)
    canvas.line(54,42,558,42);canvas.setFont("DV",7.3);canvas.setFillColor(INK)
    canvas.drawString(54,29,"FINTECH 545  |  Assignment 3")
    canvas.drawRightString(558,29,str(doc.page));canvas.restoreState()


doc=SimpleDocTemplate(str(OUT),pagesize=(612,792),leftMargin=56,rightMargin=56,
                      topMargin=44,bottomMargin=55,title="FinTech 545 - Assignment 3",
                      author="",subject="Options, option risk and portfolio construction")
doc.build(story,onFirstPage=footer,onLaterPages=footer)
(ROOT/"Assignment3_Answers.md").write_text("\n".join(md)+"\n",encoding="utf-8")
print(OUT)
