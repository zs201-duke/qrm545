"""Create the self-contained Word write-up for Midterm Problem 1."""
from pathlib import Path
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "problem1_results.json").read_text())
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
doc.core_properties.title = "Midterm Problem 1 Correlation and Covariance"
doc.core_properties.subject = "Pairwise correlation, full-sample variance, Higham repair and covariance"
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
    doc.add_heading(f"Problem 1 Part {part}", level=1)
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


# Problem 1(1): restatement, pairwise estimator, and both relevant matrices.
doc.add_paragraph("Midterm Problem 1 Correlation and Covariance",style="Title")
p("Using problem1.csv, analyze 50 days of returns for x1 through x5, treating every blank cell as missing. "
  "The pairwise correlation matrix has a negative eigenvalue. Higham's method repairs the dependence "
  "matrix, and combining it with each series's full available-sample variance produces a valid covariance matrix.")
question(1,"Calculate the pairwise correlation matrix.",5)
p("For each pair i and j, I use only the days on which both returns are observed. Let Sij be that set "
  "of days. The two means and both sums of squared deviations in the Pearson correlation are calculated "
  "on Sij. Thus, an observation can contribute to one pair even when another series is missing that day. "
  "Missing returns are neither filled with zero nor removed from unrelated pairs.")
eq(sub("r","ij")," = ",frac(
    [sub("Σ","t∈Sij"),"(",sub("x","ti")," − ",sub("x̄","i,Sij"),")(",sub("x","tj")," − ",sub("x̄","j,Sij"),")"],
    [root([sub("Σ","t∈Sij"),sup(["(",sub("x","ti")," − ",sub("x̄","i,Sij"),")"],"2"),
           sub("Σ","t∈Sij"),sup(["(",sub("x","tj")," − ",sub("x̄","j,Sij"),")"],"2")])]))
matrix("Pairwise correlation matrix C",R["correlation"])
matrix("Number of overlapping observations for each pair",R["pair_counts"],fmt=".0f")
p("The diagonal is 1 because each series is perfectly correlated with itself. The off-diagonal estimates "
  "use between 28 and 36 overlapping observations. Each diagonal count is the full number of observations "
  "available for that series. All reported matrices use the order x1, x2, x3, x4, x5.")

# Problem 1(2) and Problem 1(3): sample variances and PSD diagnosis.
doc.add_page_break()
question(2,"Calculate the variance of each series, using every observation that series has.",3)
p("For each series, I use all of its nonmissing returns, regardless of whether other series were observed "
  "on those dates. The mean is also computed from that series's full available sample. Following the "
  "course's sample-variance convention, I divide by ni − 1, rather than ni.")
eq(sup([sub("s","i")],"2")," = ",frac(
    [sub("Σ","t∈Si"),sup(["(",sub("x","ti")," − ",sub("x̄","i"),")"],"2")],
    [sub("n","i")," − 1"]))
table(["Series","Observed","Missing","Sample variance","Sample SD"],
      [[R["labels"][i],R["observations"][i],R["missing"][i],f'{R["variances"][i]:.12f}',
        f'{R["standard_deviations"][i]:.10f}'] for i in range(5)],
      [.6,.8,.8,2.45,2.29],size=10)
p("These variances are in squared decimal-return units and are not annualized. For example, x1's "
  "variance uses 41 observations and a denominator of 40. The five sample standard deviations are "
  "approximately 2.0151%, 2.1910%, 1.2293%, 2.9013%, and 1.6527%, respectively.")
question(3,"Is the correlation matrix positive semi-definite? Show how you know.",5)
p("No. A real symmetric matrix is positive semi-definite if and only if every eigenvalue is nonnegative. "
  "The eigenvalues of the unrounded pairwise correlation matrix, in ascending order, are:")
eigenrow(R["original_eigenvalues"])
p("The smallest eigenvalue is −0.0892786677. Its magnitude is far larger than floating-point roundoff, "
  "so the failure is substantive. As an additional check, a unit-length eigenvector for that eigenvalue is:")
eq("v ≈ (−0.28658054, −0.36525447, −0.15719738, −0.34247034, 0.80153840)′")
eq("v′Cv ≈ −0.08927867 < 0")
p("A negative quadratic form would imply a negative variance for some linear combination, which is "
  "incompatible with a valid correlation matrix. Pairwise deletion can cause this because different "
  "entries are estimated on different dates. Symmetry, a unit diagonal, and individual correlations "
  "between −1 and 1 do not guarantee joint consistency.")

# Problem 1(4): Higham objective, Dykstra algorithm, repaired matrix, changes.
doc.add_page_break()
question(4,"If it is not, use Higham's method to find the nearest positive semi-definite correlation "
         "matrix. Report the matrix and its eigenvalues. Which entries changed the most?",7)
p("I apply the unweighted Higham nearest-correlation algorithm from Week 03. Nearest means minimizing "
  "the Frobenius distance from C, subject to symmetry, nonnegative eigenvalues, and a unit diagonal. "
  "The weights are W = I; pairwise observation counts are not used as optimization weights.")
eq(sub("min","A"),"  ",frac(["1"],["2"]),sup([sub("‖A − C‖","F")],"2"))
p("Starting from Y0 = C and a zero Dykstra correction, each iteration subtracts the previous correction, "
  "projects onto the PSD cone by setting negative eigenvalues to zero, updates the correction, and "
  "projects onto the unit-diagonal set. Repeating both projections is necessary because either one "
  "can undo the other's constraint. The correction makes the solution nearest in the stated norm.")
p(f'The algorithm converged in {R["higham_iterations"]} iterations at a relative tolerance of 10⁻¹⁴. '
  "I checked the final eigenvalues and unit diagonal in addition to changes between iterations.")
matrix("Higham nearest correlation matrix A",R["higham_correlation"])
eigenrow(R["higham_eigenvalues"])
p("The computed smallest eigenvalue is approximately −1.0 × 10⁻¹⁴, numerically zero. The limiting solution "
  "is PSD and singular, with four positive eigenvalues. No positive-definite ridge is added. The Frobenius "
  f'distance is {R["frobenius_distance"]:.10f}; its square is {R["squared_frobenius_distance"]:.10f}. '
  "Eigenvalues are calculated before rounding the displayed matrix.")
doc.add_heading("Largest changes among distinct pairs",level=2)
table(["Pair","Original","Higham","Signed change"],
      [[c["pair"],f'{c["original"]:.8f}',f'{c["repaired"]:.8f}',f'{c["change"]:+.8f}']
       for c in R["changes"][:4]],[1.0,1.98,1.98,1.98],size=10)
p("The largest change is x2–x5, followed by x4–x5 and x1–x5; the symmetric entries change identically. "
  "All four correlations involving x5 decrease. The largest increase is x2–x4, by 0.01981412. "
  "Every diagonal entry remains exactly 1.")

# Problem 1(5): reconstruct covariance while preserving marginal variances.
doc.add_page_break()
question(5,"Combine your results into a covariance matrix. Report it.",5)
p("I combine the repaired correlation matrix A from Part 4 with the full available-sample variances "
  "from Part 2. Let D be the diagonal matrix of the five sample standard deviations. Then:")
eq("D = diag(",sub("s","1"),", ",sub("s","2"),", ",sub("s","3"),", ",sub("s","4"),", ",sub("s","5"),");   ", sigma_hat()," = DAD")
eq(sub(sigma_hat(),"ij")," = ",sub("A","ij"),sub("s","i"),sub("s","j"),";   ",sub(sigma_hat(),"ii")," = ",sup([sub("s","i")],"2"))
p("For readable entries, the following table reports the covariance matrix multiplied by 10,000. "
  "Equivalently, the covariance matrix itself is 10⁻⁴ times the displayed matrix. This also equals the "
  "covariance matrix if returns are expressed in percentage points rather than decimals.")
matrix("Covariance matrix multiplied by 10000",R["covariance"],multiplier=10000)
p("For example, the x1–x2 covariance is 0.34945220097 × 0.02015127471 × 0.02191041619 "
  "= 0.0001542911197. Thus the displayed entry 1.54291120 is interpreted as 1.54291120 × 10⁻⁴. "
  "The diagonal entries reproduce the five variances from Part 2, so the repair changes dependence "
  "without changing the estimated marginal variances.")
doc.add_heading("Why this covariance matrix is valid",level=2)
p("The reconstructed matrix is symmetric. Because D is diagonal and A is PSD, every vector w satisfies "
  "the following condition:")
eq("w′",sigma_hat(),"w = (Dw)′A(Dw) ≥ 0")
p("Its numerical eigenvalues, in ascending order and in decimal-return squared units, are approximately "
  "0, 0.0000946996642, 0.0002919794854, 0.0004623009506, and 0.0013031586541. The computed "
  "minimum is −3.2 × 10⁻¹⁸, which is roundoff. All other eigenvalues are positive.")
doc.add_heading("Calculation checks and course references",level=2)
p("The pairwise correlations and full-sample variances agree with independently calculated values using "
  "Python's standard statistical formulas. Tightening Higham's tolerance from 10⁻¹⁴ to 10⁻¹⁵ changes no "
  "matrix entry by more than 4.5 × 10⁻¹⁵. The PSD projection's dual matrix also satisfies stationarity "
  "and complementarity to less than 10⁻¹², supporting nearestness as well as feasibility. Calculations "
  "retain full precision; displayed matrices are rounded.")
p("Data: MidTerm/problem1.csv. Methods: Week 01, Estimating Moments from a Sample; Week 02, Covariance, "
  "Pearson Coefficient, and Positive Definiteness; Week 03, Missing Data, Covariance Matrix Generation "
  "Techniques, and Higham. All are within the supplied course materials.")
doc.save(HERE / "Problem1_Answers.docx")
print(HERE / "Problem1_Answers.docx")
