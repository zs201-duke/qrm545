"""Create the self-contained Word write-up for Midterm Problem 2."""
from pathlib import Path
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "problem2_results.json").read_text())
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Inches(8.5), Inches(11)
sec.top_margin = sec.bottom_margin = Inches(.72)
sec.left_margin = sec.right_margin = Inches(.78)
styles = doc.styles
for name in ["Normal", "Title", "Subtitle", "Heading 1", "Heading 2"]:
    styles[name].font.name = "Calibri"
    styles[name].font.color.rgb = RGBColor(0, 0, 0)
styles["Normal"].font.size = Pt(11)
styles["Normal"].paragraph_format.line_spacing = 1.07
styles["Normal"].paragraph_format.space_after = Pt(7)
styles["Title"].font.size = Pt(20)
styles["Title"].paragraph_format.space_after = Pt(9)
styles["Heading 1"].font.size = Pt(14)
styles["Heading 1"].paragraph_format.space_before = Pt(9)
styles["Heading 1"].paragraph_format.space_after = Pt(6)
styles["Heading 2"].font.size = Pt(11)
styles["Heading 2"].paragraph_format.space_before = Pt(7)
styles["Heading 2"].paragraph_format.space_after = Pt(4)
for border in list(doc.styles.element.xpath(".//w:pBdr")):
    border.getparent().remove(border)
doc.core_properties.title = "Midterm Problem 2 VaR and ES"
doc.core_properties.subject = "One day normal stock return VaR and Expected Shortfall"
doc.core_properties.author = ""


def p(text, bold_lead=None):
    para = doc.add_paragraph()
    if bold_lead and text.startswith(bold_lead):
        para.add_run(bold_lead).bold = True
        para.add_run(text[len(bold_lead):])
    else:
        para.add_run(text)
    return para


def question(part, text, points):
    doc.add_heading(f"Problem 2 Part {part}", level=1)
    p(f"Question ({points} points): {text}", "Question")


def mr(text):
    run = OxmlElement("m:r")
    props = OxmlElement("w:rPr")
    fonts = OxmlElement("w:rFonts")
    fonts.set(qn("w:ascii"), "Cambria Math")
    fonts.set(qn("w:hAnsi"), "Cambria Math")
    props.append(fonts)
    run.append(props)
    t = OxmlElement("m:t")
    t.set(qn("xml:space"), "preserve")
    t.text = text
    run.append(t)
    return run


def seq(*items):
    return [mr(item) if isinstance(item, str) else item for item in items]


def sub(base, index):
    el = OxmlElement("m:sSub")
    e, s = OxmlElement("m:e"), OxmlElement("m:sub")
    e.append(mr(base) if isinstance(base,str) else base); s.append(mr(index))
    el.extend([e, s])
    return el


def sigma_hat():
    el = OxmlElement("m:acc")
    props = OxmlElement("m:accPr")
    char = OxmlElement("m:chr"); char.set(qn("m:val"), "̂")
    props.append(char); el.append(props)
    e = OxmlElement("m:e"); e.append(mr("Σ")); el.append(e)
    return el


def sup(contents, power):
    el = OxmlElement("m:sSup")
    e, s = OxmlElement("m:e"), OxmlElement("m:sup")
    e.extend(seq(*contents)); s.append(mr(power))
    el.extend([e, s])
    return el


def frac(numerator, denominator):
    el = OxmlElement("m:f")
    n, d = OxmlElement("m:num"), OxmlElement("m:den")
    n.extend(seq(*numerator)); d.extend(seq(*denominator))
    el.extend([n, d])
    return el


def root(contents):
    el = OxmlElement("m:rad")
    props = OxmlElement("m:radPr")
    hide = OxmlElement("m:degHide"); hide.set(qn("m:val"), "1")
    props.append(hide); el.append(props)
    deg, e = OxmlElement("m:deg"), OxmlElement("m:e")
    e.extend(seq(*contents)); el.extend([deg, e])
    return el


def eq(*contents):
    para = doc.add_paragraph()
    para.paragraph_format.space_before = Pt(2)
    para.paragraph_format.space_after = Pt(8)
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    om = OxmlElement("m:oMathPara")
    math = OxmlElement("m:oMath")
    math.extend(seq(*contents)); om.append(math); para._p.append(om)
    return para


def table(headers, rows, widths=None, size=10):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    if widths is None:
        widths = [6.94/len(headers)]*len(headers)
    for c,w in zip(t.columns,widths): c.width = Inches(w)
    for c,txt in zip(t.rows[0].cells,headers): c.text = str(txt)
    for row in rows:
        cells=t.add_row().cells
        for c,txt in zip(cells,row): c.text=str(txt)
    for ir,row in enumerate(t.rows):
        pr=row._tr.get_or_add_trPr()
        no_split=OxmlElement("w:cantSplit");pr.append(no_split)
        if ir == 0:
            repeat=OxmlElement("w:tblHeader");pr.append(repeat)
        for j,c in enumerate(row.cells):
            c.width=Inches(widths[j]); c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcpr=c._tc.get_or_add_tcPr()
            shade=OxmlElement("w:shd")
            shade.set(qn("w:fill"),"E8EDF2" if ir==0 else "FFFFFF")
            tcpr.append(shade)
            margins=OxmlElement("w:tcMar")
            for side in ["top","left","bottom","right"]:
                el=OxmlElement("w:"+side);el.set(qn("w:w"),"65");el.set(qn("w:type"),"dxa");margins.append(el)
            tcpr.append(margins)
            borders=OxmlElement("w:tcBorders")
            for side in ["top","left","bottom","right"]:
                el=OxmlElement("w:"+side);el.set(qn("w:val"),"single");el.set(qn("w:sz"),"4");el.set(qn("w:color"),"D9D9D9");borders.append(el)
            tcpr.append(borders)
            for para in c.paragraphs:
                para.alignment=WD_ALIGN_PARAGRAPH.CENTER
                para.paragraph_format.space_after=Pt(0)
                para.paragraph_format.line_spacing=1.0
                for run in para.runs:
                    run.font.size=Pt(size)
                    run.bold=(ir==0)
    doc.add_paragraph().paragraph_format.space_after=Pt(0)
    return t


def matrix(title, data, fmt=".8f", multiplier=1):
    doc.add_heading(title,level=2)
    table(["Series",*R["labels"]],
          [[label,*[format(v*multiplier,fmt) for v in row]] for label,row in zip(R["labels"],data)],
          [.58]+[1.272]*5,size=9.5)


def eigenrow(values, digits=8):
    table(["Eigenvalue 1","Eigenvalue 2","Eigenvalue 3","Eigenvalue 4","Eigenvalue 5"],
          [[format(0 if abs(v)<1e-12 else v,f".{digits}f") for v in values]],size=9.5)


# Problem 2(a): price transformation, regression model, and normal VaR.
doc.add_paragraph("Midterm Problem 2 VaR and ES",style="Title")
p("Using the 501 daily prices in problem2.csv, I calculate one-day VaR and ES for 100 XYZ shares. "
  "All reported percentages are positive losses relative to the current position value.")
question("a","What is your VaR at the 95% and 99% levels, in percent? Explain your method.",10)
p("I first convert the chronologically ordered prices into 500 arithmetic returns for each stock. "
  "The first price is only the starting value; it does not provide a separate return observation.")
eq(sub("r","i,t")," = ",frac([sub("P","i,t")],[sub("P","i,t−1")])," − 1")
p("I fit the stated regression by ordinary least squares with an intercept. Following the normal OLS "
  "model in Week 05, I model the SPY return and the error jointly as normal with zero covariance; "
  "the error has mean zero. The fitted coefficients are treated as fixed, and the next SPY return "
  "is random rather than a known conditioning value.")
eq(sub("r","XYZ")," = α + β",sub("r","SPY")," + ε")
table(["Fitted quantity","Value"],[
    ["Intercept α",f'{R["alpha"]:.12f}'],
    ["Market coefficient β",f'{R["beta"]:.10f}'],
    ["SPY mean daily return",f'{R["spy_mean"]:.12f}'],
    ["SPY daily return variance",f'{R["spy_variance"]:.12f}'],
    ["Residual daily variance",f'{R["residual_variance"]:.12f}'],
],[3.5,3.44],size=10)
p("The variances use sample denominator 499. The affine normal model gives these XYZ moments:")
eq(sub("μ","XYZ")," = α + β",sub("μ","SPY")," ≈ 0")
eq(sup([sub("σ","XYZ")],"2")," = ",sup(["β"],"2"),sup([sub("σ","SPY")],"2")," + ",sup([sub("σ","ε")],"2")," = 0.000384298563680")
p("Thus XYZ's daily standard deviation is 0.019603534469, or 1.96035345%. Both market and residual "
  "risk are included. Its fitted mean is numerically zero without discarding the intercept.")
p("For confidence c, let p = 1 − c and zp = Φ⁻¹(p). The course defines positive-loss VaR as the "
  "negative lower-tail return quantile:")
eq(sub("VaR","c")," = −",sub("μ","XYZ")," − ",sub("σ","XYZ"),sub("z","p"))
table(["Confidence","Lower-tail p","Normal quantile zp","VaR as percent"],[
    ["95%","0.05","−1.644853627",f'{R["results"][0]["var_percent"]:.6f}%'],
    ["99%","0.01","−2.326347874",f'{R["results"][1]["var_percent"]:.6f}%'],
],[1.1,1.3,2.2,2.34],size=10)
p("Therefore, the one-day VaR is 3.224494% at 95% confidence and 4.560464% at 99% confidence. "
  "Under the fitted model, losses exceed these thresholds on approximately 5% and 1% of days, respectively.")

# Problem 2(b): expected shortfall and interpretation of the 100-share holding.
question("b","What is your ES at the 95% and 99% levels, in percent? Explain your method.",10)
doc.paragraphs[-2].paragraph_format.page_break_before = True
p("Expected Shortfall is the average loss in the tail beyond the corresponding VaR threshold. "
  "It measures the severity of losses on the worst p fraction of days, rather than only the "
  "threshold at which those days begin. For the continuous normal return distribution and the "
  "course's positive-loss convention:")
eq(sub("ES","c")," = −E[",sub("r","XYZ")," | ",sub("r","XYZ")," ≤ −",sub("VaR","c"),"]")
p("For a normal return with mean μ and standard deviation σ, averaging the normal left tail gives "
  "the Week 05 closed-form expression below. Here φ is the standard normal density, Φ is the "
  "standard normal CDF, and p = 1 − c:")
eq(sub("ES","c")," = −μ + σ ",frac(["φ(",sub("z","p"),")"],["p"]),";    ",sub("z","p")," = ",sup(["Φ"],"−1"),"(p)")
table(["Confidence","Tail probability","Normal ES multiplier","ES as percent"],[
    ["95%","0.05",f'{R["results"][0]["normal_es_multiplier"]:.9f}',f'{R["results"][0]["es_percent"]:.6f}%'],
    ["99%","0.01",f'{R["results"][1]["normal_es_multiplier"]:.9f}',f'{R["results"][1]["es_percent"]:.6f}%'],
],[1.1,1.3,2.2,2.34],size=10)
p("Substituting the fitted mean of essentially zero and the standard deviation 0.019603534469 gives:")
eq(sub("ES","95%")," = 0.019603534469 × 2.062712807 = 0.040436461622 = 4.043646%")
eq(sub("ES","99%")," = 0.019603534469 × 2.665214220 = 0.052247618836 = 5.224762%")
p("The 95% ES means an average loss of 4.043646% among the worst 5% of daily outcomes. The 99% "
  "ES means an average loss of 5.224762% among the worst 1%. Each ES exceeds its corresponding "
  "VaR because it averages losses beyond that threshold. Neither measure is a maximum possible loss.")
doc.add_heading("Why the number of shares does not change percent risk",level=2)
p(f'The final XYZ price is ${R["last_xyz_price"]:.8f}, so 100 shares are worth '
  f"${R['position_value']:,.8f}. Dividing the position's P&L by its current value cancels the share count:")
eq(frac(["100",sub("P","0"),sub("r","XYZ")],["100",sub("P","0")])," = ",sub("r","XYZ"))
p("Therefore the stock-return percentages are also the position's percentage VaR and ES. For scale, "
  "the 95% and 99% ES correspond to approximately $301.33 and $389.34 on this holding.")
doc.add_heading("Estimation convention and checks",level=2)
p("I use the sample covariance of SPY returns and fitted residuals, with denominator n − 1, matching "
  "the Week 05 OLS simulation example. This reproduces the sample variance of XYZ returns exactly. "
  "The regression error-variance estimator SSE/(n − 2), used for coefficient inference, and Gaussian "
  "MLE's SSE/n are different conventions. No annualization or parameter-uncertainty adjustment is applied.")
p("The residual mean and covariance with SPY are numerically zero. A separate two-million-draw "
  "market-and-error simulation agrees within 0.01 percentage point. Reported answers use analytic formulas.")
p("Course references: Week 02, Ordinary Least Squares; Week 04, Arithmetic Returns and Value at Risk; "
  "Week 05, Model Based Simulation and The Normal Case of Expected Shortfall. Data: MidTerm/problem2.csv.")

# Appendix: actual runnable calculation code, labeled by problem and part.
doc.add_heading("Problem 2 Calculation Code",level=1).paragraph_format.page_break_before = True
p("The following code reproduces the reported percentages. Save it beside problem2_analysis.py in "
  "MidTerm/answers and run it with Python 3 and NumPy. The full analysis script additionally saves "
  "returns, results, and numerical checks.")
code = '''from pathlib import Path
import csv
import numpy as np
from statistics import NormalDist

# Problem 2(a): turn 501 prices into 500 arithmetic returns.
path = Path(__file__).resolve().parent.parent / "problem2.csv"
with path.open(newline="") as f:
    rows = sorted(csv.DictReader(f), key=lambda row: row["Date"])
prices = np.array([[float(row["SPY"]), float(row["XYZ"])]
                   for row in rows])
returns = prices[1:] / prices[:-1] - 1.0
spy, xyz = returns.T

# Problem 2(a): OLS regression with intercept and residuals.
X = np.column_stack([np.ones(len(spy)), spy])
alpha, beta = np.linalg.lstsq(X, xyz, rcond=None)[0]
error = xyz - alpha - beta * spy
mu = alpha + beta * spy.mean()
sigma = np.sqrt(beta**2 * spy.var(ddof=1)
                + error.var(ddof=1))
normal = NormalDist()

# Problem 2(a): VaR is the negative lower return quantile.
for confidence in (0.95, 0.99):
    p = 1.0 - confidence
    z = normal.inv_cdf(p)
    var = -mu - sigma * z
    print(f"VaR {confidence:.0%}: {100 * var:.6f}%")

# Problem 2(b): ES is minus the conditional left-tail mean.
for confidence in (0.95, 0.99):
    p = 1.0 - confidence
    z = normal.inv_cdf(p)
    es = -mu + sigma * normal.pdf(z) / p
    print(f"ES  {confidence:.0%}: {100 * es:.6f}%")
'''
for line in code.splitlines():
    para=doc.add_paragraph()
    para.paragraph_format.space_after=Pt(0)
    para.paragraph_format.line_spacing=Pt(12)
    run=para.add_run(line or " ");run.font.name="Consolas";run.font.size=Pt(9.5)
    run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"),"Consolas")
    run._element.rPr.rFonts.set(qn("w:hAnsi"),"Consolas")

doc.save(HERE / "Problem2_Answers.docx")
print(HERE / "Problem2_Answers.docx")
