"""Create the self-contained Word write-up for Midterm Problem 3."""
from pathlib import Path
import json
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

HERE = Path(__file__).resolve().parent
R = json.loads((HERE / "problem3_risk_results.json").read_text())
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
doc.core_properties.title = "Midterm Problem 3 Copula Portfolio Risk"
doc.core_properties.subject = "Marginal distribution fitting copulas and portfolio risk"
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
    doc.add_heading(f"Problem 3 Part {part}", level=1)
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


F=json.loads((HERE/"problem3_marginal_fits.json").read_text())
C=json.loads((HERE/"problem3_copula_fit.json").read_text())
names=F["names"]
models={(m["stock"],m["family"]):m for m in F["models"]}
chosen={m["stock"]:m for m in F["selected"]}
stock_rows=R["rows"][:10]
book_a,book_b,total=R["rows"][-3:]

# Page numbering is useful for the multi-part write-up and code appendices.
footer=sec.footer.paragraphs[0]
footer.alignment=WD_ALIGN_PARAGRAPH.RIGHT
footer.add_run("Page ")
field=OxmlElement("w:fldSimple");field.set(qn("w:instr"),"PAGE");footer._p.append(field)
for run in footer.runs:run.font.size=Pt(9)


def new_page(title):
    heading=doc.add_heading(title,level=1)
    heading.paragraph_format.page_break_before=True


def code_block(code):
    for line in code.strip("\n").splitlines():
        para=doc.add_paragraph()
        para.paragraph_format.space_after=Pt(0)
        para.paragraph_format.line_spacing=Pt(11.5)
        run=para.add_run(line or " ")
        run.font.name="DejaVu Sans Mono";run.font.size=Pt(9)
        fonts=run._element.get_or_add_rPr().rFonts
        for kind in ("ascii","hAnsi","cs"):fonts.set(qn("w:"+kind),"DejaVu Sans Mono")


# Problem 3(a): methods, all normal fits, and parameter interpretation.
doc.add_paragraph("Midterm Problem 3 Copula Portfolio Risk",style="Title")
p("I use the 1,001 daily prices for S1 through S10 in problem3.csv and the share counts and books in "
  "problem3_holdings.csv. The resulting 1,000 arithmetic-return observations determine the fitted "
  "marginals and dependence model. Positions are valued at the final prices dated November 3, 2025. "
  "All risk amounts below are one-day absolute losses in dollars.")
question("a","For each stock, fit a normal, a Student's t, and a normal inverse Gaussian distribution "
         "to its returns. Report the fitted parameters. Which distribution fits each stock best? "
         "Justify your choice.",25)
p("I transform each stock's prices into arithmetic returns, preserving all 1,000 observations:")
eq(sub("r","i,t")," = ",frac([sub("P","i,t")],[sub("P","i,t−1")])," − 1")
p("I fit each family by maximum likelihood, maximizing the sum of log densities over the same return "
  "sample. I retain the fitted locations and means; the question does not ask for zero-mean returns. "
  "Optimization is performed on standardized data to improve numerical conditioning, with parameters "
  "then converted back to decimal-return units. Multiple starting values and local refinement reduce "
  "sensitivity to the starting guess.")
doc.add_heading("Normal fitted parameters",level=2)
p("For the normal model, μ is the mean and σ is the standard deviation. The normal MLE uses the "
  "sample mean and variance denominator n = 1,000, not the n − 1 unbiased sample-variance denominator.")
table(["Stock","Normal μ","Normal σ"],
      [[name,f'{models[name,"Normal"]["parameters"]["mu"]:.9f}',
        f'{models[name,"Normal"]["parameters"]["sigma"]:.9f}'] for name in names],
      [1.0,2.97,2.97],size=10)
doc.add_heading("Distribution notation used in the parameter tables",level=2)
p("The Student's t parameters are degrees of freedom ν, location μ, and scale s, with return r = μ + sTν. "
  "The scale is not the standard deviation: Var(r) = s²ν/(ν − 2), when ν > 2. The NIG parameters follow "
  "the Week 01 notation NIG(α, β, δ, μ), where α > |β| and δ > 0. Its location μ is generally not its mean.")

# Problem 3(a): all t and NIG parameters, including numerical-limit caveats.
new_page("Problem 3 Part a Fitted t and NIG Parameters")
doc.add_heading("Student t fitted parameters",level=2)
table(["Stock","Degrees of freedom ν","Location μ","Scale s"],
      [[name,f'{models[name,"Student t"]["parameters"]["nu"]:.6g}',
        f'{models[name,"Student t"]["parameters"]["mu"]:.9f}',
        f'{models[name,"Student t"]["parameters"]["scale"]:.9f}'] for name in names],
      [.65,2.0,2.145,2.145],size=10)
p("S1, S4, and S7 reach ν ≈ 1,000,002, an effectively normal numerical limit. Their finite ν values "
  "are weakly identified. Other t estimates are interior; ν > 2 ensures finite variance.")
doc.add_heading("Normal inverse Gaussian fitted parameters",level=2)
table(["Stock","Tail α","Asymmetry β","Scale δ","Location μ"],
      [[name+('*' if models[name,"NIG"]["near_normal_limit"] else ''),
        f'{models[name,"NIG"]["parameters"]["alpha"]:.7g}',
        f'{models[name,"NIG"]["parameters"]["beta"]:.7g}',
        f'{models[name,"NIG"]["parameters"]["delta"]:.9f}',
        f'{models[name,"NIG"]["parameters"]["mu"]:.9f}'] for name in names],
      [.6,1.585,1.585,1.585,1.585],size=9.5)
p("* The starred NIG alternatives are near-normal, weakly identified numerical fits; compensating "
  "parameters explain their large locations. Their excess kurtoses are 0.0028, 0.0024 and 0.0033. "
  "The selected S3/S6/S9 NIG fits are interior and not near these limits.")
p("Numerical constraints: 0.001 ≤ a ≤ 100,000 and |b/a| ≤ tanh(3), with a = αδ and b = βδ. "
  "Normal-limit shape parameters should not be interpreted precisely.")
eq("γ = ",root([sup(["α"],"2")," − ",sup(["β"],"2")]),";     E[r] = μ + ",frac(["δβ"],["γ"]))

# Problem 3(a): information criteria and justification for every chosen family.
new_page("Problem 3 Part a Distribution Selection")
p("I select the lowest corrected Akaike information criterion, AICc, and report BIC as a second check. "
  "Normal, t, and NIG models estimate k = 2, 3, and 4 parameters, respectively. Since all fits use the "
  "same observations and units, their likelihoods and information criteria are comparable.")
eq("AICc = −2ℓ + 2k + ",frac(["2k(k + 1)"],["n − k − 1"]),";    BIC = −2ℓ + k ln(n)")
selection_rows=[]
for name in names:
    ms=[models[name,fam] for fam in ("Normal","Student t","NIG")]
    bs=sorted(ms,key=lambda m:m["BIC"])
    selection_rows.append([name,*[f'{m["AICc"]:.3f}' for m in ms],chosen[name]["family"],
                           f'{bs[1]["BIC"]-bs[0]["BIC"]:.3f}'])
table(["Stock","Normal AICc","t AICc","NIG AICc","Selected","BIC margin"],
      selection_rows,[.55,1.31,1.31,1.31,1.35,1.11],size=9.5)
p("BIC margin is the next-best BIC minus the selected model's BIC; a positive margin favors the "
  "selected model. BIC agrees with AICc for all ten stocks. Complete log likelihoods, AICc, BIC, and "
  "unrounded parameters are retained in problem3_marginal_fits.csv.")
doc.add_heading("Interpretation of the selected families",level=2)
p("S1, S4, and S7: normal. Their sample skewnesses are approximately −0.040, −0.035, and −0.041; "
  "sample excess kurtoses are −0.027, −0.127, and −0.118. A t fit collapses toward the normal limit. "
  "NIG adds only a very small likelihood improvement, insufficient to pay for two extra parameters. "
  "Normal is the parsimonious choice rather than a conclusion that every possible tail property is known.")
p("S2, S5, S8, and S10: Student's t. Their selected degrees of freedom are 4.858, 6.289, 3.483, and "
  "4.121. The sample excess kurtoses are about 5.51, 2.75, 6.57, and 5.62, which support heavier tails "
  "than normal. The t model beats both alternatives after the parameter penalty. S8's low degrees of "
  "freedom indicate especially heavy fitted tails. The sample skew of S10 is negative, but sample "
  "asymmetry alone does not guarantee that the four-parameter NIG is the better overall fit.")
p("S3, S6, and S9: NIG. Their sample skewnesses are approximately −1.323, −1.204, and −1.085, with "
  "substantial positive excess kurtosis. The fitted NIG asymmetry parameters are negative. NIG can "
  "represent both the left-skewed shape and heavy tails, whereas the symmetric t cannot represent "
  "the asymmetry. AICc improves over the next-best family by 43.18, 48.66, and 28.75, respectively, "
  "so the additional parameter is well supported in these samples.")
p("These are relative in-sample model choices among the three specified families. Matching a sample "
  "moment is only a diagnostic; the likelihood comparison and parameter penalty determine the choice.")

# Problem 3(b): fixed selected margins, same rank correlation, both copulas.
new_page("Problem 3 Part b Copula Selection")
p("Question (20 points): Using the distributions you chose in part (a), fit a Gaussian copula and a "
  "Student's t copula. Which one fits better? Justify your choice.","Question")
p("I freeze the ten selected marginal fits and transform each observed return using its own fitted "
  "CDF. This gives the uniform-scale observations needed to fit a copula. I use the same uniform "
  "matrix and the same correlation estimate for both copula families.")
eq(sub("u","ti")," = ",sub("F","i"),"(",sub("r","ti"),");    ",sub("R","ij")," = sin(",frac(["π",sub("τ","ij")],["2"]),")")
p("Here τij is Kendall's rank correlation. Its sine transform is exact for elliptical copulas, "
  "including both Gaussian and t. Strictly monotone marginal transforms preserve the ranks, so τ can "
  "be computed from the returns. The resulting 10 × 10 latent correlation matrix is positive definite: "
  f'its smallest eigenvalue is {C["original_min_eigenvalue"]:.8f}. No PSD repair or ridge is needed. '
  "The full matrix is saved in problem3_copula_correlation.csv.")
p("For the Gaussian copula, I transform uniforms to normal scores and compute the joint normal log "
  "density minus the sum of the univariate normal log densities. For a candidate t-copula ν, the same "
  "density-ratio construction uses t scores and a multivariate t with scale matrix R:")
eq(sub("ℓ","t"),"(ν) = ",sub("Σ","t"),"[ln ",sub("f","R,ν"),"(",sub("y","t"),") − ",sub("Σ","i"),"ln ",sub("f","ν"),"(",sub("y","ti"),")]")
eq(sub("y","ti")," = ",sup([sub("T","ν")],"−1"),"(",sub("u","ti"),")")
p("I profile the t-copula likelihood in 1/ν. The course's initial upper bound ν = 100 was reached, "
  "so I extended the search toward the Gaussian limit. The refined estimate is approximately "
  f'ν = {C["nu"]:,.2f}. Such a large value describes an almost Gaussian copula; it is separate from '
  "the much smaller degrees of freedom in the four selected t marginals.")
table(["Copula","ν","Log likelihood","k","AICc","BIC"],
      [[s["family"],"—" if s["family"]=="Gaussian" else f'{C["nu"]:.2f}',
        f'{s["loglik"]:.6f}',s["k"],f'{s["AICc"]:.6f}',f'{s["BIC"]:.6f}'] for s in C["scores"]],
      [1.0,.8,1.35,.4,1.695,1.695],size=9.5)
p("Following Week 05, k counts only copula parameters remaining after the common R is fixed: zero "
  "for Gaussian and one for t. The 45 correlation entries and all marginal fits are shared by both "
  "models. The t gains only 0.005536 in log likelihood. Gaussian has the lower AICc by 1.992936 and "
  "the lower BIC by 6.896684, so I select the Gaussian copula. The small AICc gap indicates a modest "
  "complexity preference; BIC makes the stronger choice. There is no support for materially heavier "
  "joint tails in this comparison.")
p("A Gaussian copula does not require Gaussian stock returns. The fitted t and NIG marginal tails "
  "remain in the simulation. Gaussian tail dependence is asymptotically zero, but positive finite-level "
  "dependence remains. I use information criteria rather than a naive likelihood-ratio chi-square test "
  "because the Gaussian model is the t copula's boundary at ν tending to infinity.")

# Problem 3(c): input valuations and the full joint simulation construction.
new_page("Problem 3 Part c Valuation and Simulation Method")
p("Question (30 points): Using the copula you chose in part (b), simulate the portfolio with at least "
  "5,000 draws. Calculate the absolute VaR and ES at the 95% level, in dollars, for each stock, each "
  "book, and the total portfolio. Present the results in a table. Discuss the results.","Question")
p("I use 200,000 joint draws, seed 54503, which provides 10,000 observations in the 5% loss tail. "
  "Current position value is share count times the last price. Book A contains S1–S5; Book B contains "
  "S6–S10. The values below use the unrounded prices; displayed prices are rounded for readability.")
table(["Stock","Book","Shares","Last price $","Position value $"],
      [[s["name"],s["book"],f'{s["shares"]:.0f}',f'{s["last_price"]:.6f}',f'{s["current_value"]:,.2f}'] for s in stock_rows]
      +[["Book A","A","","",f'{book_a["current_value"]:,.2f}'],
        ["Book B","B","","",f'{book_b["current_value"]:,.2f}'],
        ["Total","","","",f'{total["current_value"]:,.2f}']],
      [.7,.55,.75,2.0,2.94],size=10)
p("For each draw, I generate a correlated standard normal vector with correlation R using its "
  "Cholesky factor. Applying the standard normal CDF gives dependent uniforms. I then apply each "
  "stock's selected inverse CDF, so the final return vector has the chosen mixed marginal families.")
eq("Z ∼ N(0,R);    ",sub("U","i")," = Φ(",sub("Z","i"),");    ",sub("r","i")," = ",sup([sub("F","i")],"−1"),"(",sub("U","i"),")")
p("I reprice every stock under arithmetic returns and aggregate the resulting P&Ls within each shared "
  "scenario. The book or portfolio quantile is calculated only after aggregation; stand-alone VaRs "
  "and ES values are not added to obtain portfolio risk.")
eq(sub("P","i,1")," = ",sub("P","i,0"),"(1 + ",sub("r","i"),");    Δ",sub("V","i")," = ",sub("h","i"),sub("P","i,0"),sub("r","i"))
eq(sub("VaR","95%")," = −",sub("q","0.05"),"(ΔV);    ",sub("ES","95%")," = −mean(worst 5% of ΔV)")
p("Absolute risk uses the actual P&L distribution relative to today's value. I retain fitted expected "
  "returns; I do not subtract the mean P&L or apply an absolute-value operator to every observation. "
  "Empirical VaR uses linear quantile interpolation, while ES averages exactly the 10,000 worst draws.")

# Problem 3(c): requested 13-row risk table, interpretation, and uncertainty.
new_page("Problem 3 Part c Dollar VaR and ES Results")
p("All amounts below are one-day 95% absolute dollar risk from the same 200,000 Gaussian-copula "
  "scenarios. A positive number represents a loss. Each stock row covers the entire holding of that "
  "stock, rather than a single share.")
table(["Position","Book","Current value $","VaR 95% $","ES 95% $"],
      [[s["name"],s["book"] if s["name"].startswith("S") else "—",f'{s["current_value"]:,.2f}',
        f'{s["VaR95"]:,.2f}',f'{s["ES95"]:,.2f}'] for s in R["rows"]],
      [1.0,.55,2.09,1.65,1.65],size=10)
p(f'Book B is riskier than Book A in dollars and as a percentage of its value: Book A VaR/ES are '
  f'{book_a["VaR95_percent"]:.3f}% / {book_a["ES95_percent"]:.3f}%, versus '
  f'{book_b["VaR95_percent"]:.3f}% / {book_b["ES95_percent"]:.3f}% for Book B. '
  "Book B has a larger current value and substantial exposure to S9, the largest position. S9 also has "
  "a negatively skewed, heavy-tailed NIG fit and the largest stand-alone stock VaR and ES. Stand-alone "
  "risk is not the same as a marginal risk contribution.")
p(f'Diversification matters. The sum of stock VaRs is ${R["diversification"]["sum_stock_VaR95"]:,.2f}, '
  f'compared with total VaR of ${total["VaR95"]:,.2f}; the corresponding ES amounts are '
  f'${R["diversification"]["sum_stock_ES95"]:,.2f} and ${total["ES95"]:,.2f}. '
  "These reductions are approximately 31.36% and 33.80%. Combining the two books reduces risk "
  "relative to adding book risks by 15.22% for VaR and 16.22% for ES. ES subadditivity is consistent "
  "with this result; VaR is also lower here, although VaR is not generally subadditive.")
p("Average latent correlations are 0.546 within Book A, 0.530 within Book B, and 0.285 between books. "
  "Lower cross-book dependence provides additional diversification. Copula correlations need not equal "
  "Pearson correlations of the final nonnormal returns.")
p("Every ES exceeds its VaR because it averages losses beyond the threshold. Total ES of $10,668.84 "
  "is about 39.2% above total VaR of $7,664.45. VaR is a cutoff, not a maximum loss. Mixed t and NIG "
  "margins preserve heavy, skewed stock tails under Gaussian dependence.")
doc.add_heading("Numerical precision and validation",level=2)
p("Twenty scenario batches give approximate Monte Carlo standard errors for total VaR/ES of "
  f'${total["VaR_MCSE"]:.2f}/${total["ES_MCSE"]:.2f}. Cents support reproducibility, not cent-level accuracy. '
  "These errors exclude parameter and model uncertainty. Stock risks agree with marginal calculations "
  "within two simulation standard errors. P&Ls reconcile in every draw; no return is below −100%.")

# Code appendix: labeled extracts are backed by the complete executable file.
new_page("Problem 3 Code for Marginal and Copula Fitting")
p("The complete runnable file is problem3_analysis.py. Its sections are labeled Problem 3(a), "
  "Problem 3(b), and Problem 3(c). Run python3 problem3_analysis.py from any directory; it locates "
  "the input files relative to itself. The following excerpts show the calculations behind the answers. "
  "The helper functions shown by name are defined in the full script.")
code_block('''# Problem 3(a): arithmetic returns and marginal MLE.
names, prices, ret, shares, books, dates = load_data()
for j, stock in enumerate(names):
    x = ret[:, j]
    center, unit = x.mean(), x.std(ddof=0)
    z = (x - center) / unit
    normal = stats.norm(center, unit)
    (nu, m, s), _ = fit_t(z)
    student = stats.t(nu, loc=center+unit*m, scale=unit*s)
    (a, b, m, s), _ = fit_nig(z)
    nig = stats.norminvgauss(a, b, loc=center+unit*m,
                            scale=unit*s)
    # fit_t and fit_nig optimize the sum of log densities
    # with multiple starts, constraints and local refinement.
    scores = []
    for dist, k in [(normal, 2), (student, 3), (nig, 4)]:
        ll = dist.logpdf(x).sum()
        scores.append(information_criteria(ll, k, len(x)))
    best = np.argmin([s["AICc"] for s in scores])

# Problem 3(b): selected marginal CDFs and common R.
u = np.column_stack([frozen(m).cdf(ret[:, j])
                     for j, m in enumerate(selected)])
tau = np.eye(10)
for i in range(10):
    for j in range(i):
        tau[i, j] = tau[j, i] = stats.kendalltau(
            ret[:, i], ret[:, j]).statistic
r = np.sin(np.pi * tau / 2)
assert np.linalg.eigvalsh(r).min() > 0

# Gaussian copula log density: joint minus marginal logs.
z = stats.norm.ppf(u)
ll_gauss = (stats.multivariate_normal(cov=r).logpdf(z).sum()
            - stats.norm.logpdf(z).sum())

# t copula likelihood for each candidate nu, same u and R.
def t_loglik(nu):
    y = stats.t.ppf(u, nu)
    joint = stats.multivariate_t(shape=r, df=nu).logpdf(y)
    return joint.sum() - stats.t.logpdf(y, nu).sum()
# The full script profiles in 1/nu, refines the maximum,
# extends a reached nu=100 boundary, and compares AICc/BIC.
''')

new_page("Problem 3 Code for Portfolio Simulation")
code_block('''# Problem 3(c): Gaussian copula selected by part (b).
nsim, seed = 200000, 54503
rng = np.random.default_rng(seed)
z = rng.standard_normal((nsim, 10)) @ np.linalg.cholesky(r).T
u = stats.norm.cdf(z)
sim = np.empty_like(u)
for j, model in enumerate(selected):
    dist = frozen(model)
    if model["family"] == "NIG":
        inv = NumericalInversePolynomial(
            dist, center=float(dist.mean()), u_resolution=1e-12)
        sim[:, j] = inv.ppf(u[:, j])
    else:
        sim[:, j] = dist.ppf(u[:, j])

# Reprice every position at the final price in the file.
current = shares * prices[-1]
pnl = sim * current
is_a = np.array(books) == "A"
book_a = pnl[:, is_a].sum(axis=1)
book_b = pnl[:, ~is_a].sum(axis=1)
total = pnl.sum(axis=1)
assert np.allclose(total, book_a + book_b)

# Absolute VaR and ES: retain fitted means and negate losses.
def risk95(pnl):
    k = int(0.05 * len(pnl))
    var = -np.quantile(pnl, 0.05, method="linear")
    es = -np.partition(pnl, k-1)[:k].mean()
    return var, es

for j, stock in enumerate(names):
    print(stock, risk95(pnl[:, j]))
print("Book A", risk95(book_a))
print("Book B", risk95(book_b))
print("Total", risk95(total))
''')
doc.add_heading("Sources and reproducibility",level=2)
p("The analysis follows Week 01 for normal, t and NIG distributions; Week 02 for MLE, AICc and BIC; "
  "Week 04 for arithmetic-return repricing and absolute VaR; and Week 05 for Gaussian/t copulas and ES. "
  "The script uses NumPy 2.3.3 and SciPy 1.16.2 for numerical calculations; it saves parameter tables, "
  "copula scores and correlation, simulated P&Ls, and the 13-row risk report.")
p("Implementation references: SciPy 1.16.2 norminvgauss documentation confirms a = αδ, b = βδ, "
  "loc = μ and scale = δ. NumericalInversePolynomial documentation describes the adaptive inverse-CDF "
  "method used for the three selected NIG margins. On a test grid, the largest CDF round-trip error "
  "was 1.5 × 10⁻¹² and the largest difference from direct NIG quantiles was 1.3 × 10⁻⁷ in return units.")
for url in [
    "https://docs.scipy.org/doc/scipy-1.16.2/reference/generated/scipy.stats.norminvgauss.html",
    "https://docs.scipy.org/doc/scipy-1.16.2/reference/generated/scipy.stats.sampling.NumericalInversePolynomial.html",
]:
    para=p(url)
    for run in para.runs:run.font.size=Pt(8)

doc.save(HERE/"Problem3_Answers.docx")
print(HERE/"Problem3_Answers.docx")
