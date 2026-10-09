"""S6 report and A3: cost of quality.

Usage: python -m analytics.s6_cost_of_quality.report
"""
import warnings

import numpy as np
import pandas as pd

from analytics.s6_cost_of_quality.s6_cost import LENGTH, compute
from analytics.style import style as S

HEADER = ("Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant. January 2024 to December 2025; US dollars.<br>"
          "Sources: cost of quality lines from accounting, scrap transactions, NCRs, complaints, CMM reports, calibration records, labor rates, ERP lots.<br>"
          "Management summary; DMAIC project with A3.")
LINE_ORDER = ["scrap", "customer credit", "sorting and containment", "rework labor", "return freight", "re-inspection"]
LINE_LABEL = {"scrap": "Scrap", "customer credit": "Customer credits", "sorting and containment": "Sorting and containment", "rework labor": "Rework labor, booked", "return freight": "Return freight",
              "re-inspection": "Re-inspection"}
PEAKS = (("2024-05", "2024-06"), ("2025-05", "2025-06"))
EST = "Rework left on production jobs, estimate"


def tbl(head, rows, total=()):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join(f'<tr{" class=total" if n in total else ""}>' + "".join(f'<td class="{"num" if i else ""}">{v}</td>' for i, v in enumerate(r)) + "</tr>" for n, r in enumerate(rows))
    return f'<table class="data"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def cap(text):
    return f'<div class="caption">{text}</div>'


def usd(x, d=0):
    return f"${x:,.{d}f}"


def month(p):
    return pd.Timestamp(p + "-01").strftime("%B %Y")


def figure_failure(r, name, h=3.6):
    fl, t = r["failure_lines"], r["totals"].set_index("period")
    f, ax = S.fig(h=h, w=9.2, grid="x")
    labels = [LINE_LABEL[k] for k in LINE_ORDER] + [EST]
    y = np.arange(len(labels))[::-1]
    for year, off, color in ((2025, 0.2, S.BRAND_BLUE), (2024, -0.2, S.LIGHT_BLUE)):
        v = fl[fl["year"] == year].set_index("cost_line")["amount"]
        vals = [float(v[k]) for k in LINE_ORDER] + [float(t.loc[str(year), "rework_estimate"])]
        bars = ax.barh(y + off, S.sig(np.array(vals) / 1000), height=0.38, color=color, label=str(year))
        bars[-1].set_hatch("///")
        bars[-1].set_edgecolor("white")
        if year == 2025:
            bars[0].set_color(S.AMBER)
            for yy, val in zip(y + off, vals):
                ax.annotate(f"{val / 1000:,.0f}", (val / 1000, yy), textcoords="offset points", xytext=(4, 0), va="center", fontsize=8.5, color=S.DARK_GREY)
    ax.set_yticks(y)
    ax.set_yticklabels(labels)
    ax.set_xlabel("$ thousand")
    ax.set_title("Failure cost by line, 2025 and 2024")
    ax.legend(frameon=False, loc="lower right")
    f.tight_layout()
    return S.save(f, name, "Failure cost by line in 2025 and 2024, with scrap as the scrap report shows it and the rework estimate")


def figure_monthly(r, name="s6_fig2_monthly", h=3.9):
    m = r["monthly"]
    f, ax = S.fig(h=h, w=9.4)
    x = np.arange(len(m))
    base = np.zeros(len(m))
    for col, color, label in (("failure", S.BRAND_BLUE, "Failure, as booked"), ("appraisal", S.ACCENT, "Appraisal"), ("prevention", S.AMBER, "Prevention")):
        v = S.sig(m[col].to_numpy() / 1000)
        ax.bar(x, v, bottom=base, color=color, width=0.78, label=label)
        base = base + v
    periods = list(m["period"])
    for a, b in PEAKS:
        i, j = periods.index(a), periods.index(b)
        ax.annotate("May and June", ((i + j) / 2, float(base[i:j + 1].max()) + 6), ha="center", fontsize=8.5, color=S.DARK_GREY)
    ax.set_xticks(x[::3])
    ax.set_xticklabels([pd.Timestamp(p + "-01").strftime("%b %Y") for p in periods[::3]], fontsize=9)
    ax.set_ylim(0, float(base.max()) + 40)
    ax.set_ylabel("$ thousand")
    ax.set_title("Cost of quality by month, as booked")
    ax.legend(frameon=False, ncols=3, loc="upper left", fontsize=9)
    f.tight_layout()
    return S.save(f, name, "Monthly cost of quality as booked by category, January 2024 to December 2025")


def build():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = compute()
    t = r["totals"].set_index("period")
    a, b, w = t.loc["2025"], t.loc["2024"], t.loc["24 months"]
    rec, rw, fl, tr = r["reconciliation"], r["rework"].set_index("year"), r["failure_lines"], r["traced"]
    s3, s4, esc = r["s3"].set_index("period"), r["s4"], r["s4_escapes"].set_index("year")
    cr = r["cmm_rate"]
    part = r["s2_part"]

    def ratio(x, booked):
        return f"{(x.failure_booked if booked else x.failure) / x.prevention:.1f} : {x.appraisal / x.prevention:.1f} : 1"

    body = "<h2 id='f1'>1. Totals and shares</h2>"
    body += (f"<p>Cost of quality in 2025 is {usd(a.total_booked)} as booked, {100 * a.booked_over_revenue:.1f}% of revenue of {usd(a.revenue)}. With the rework left on production jobs estimated from hours over standard it is "
             f"{usd(a.total)}, {100 * a.over_revenue:.1f}%. In 2024 the figures were {100 * b.booked_over_revenue:.1f}% as booked and {100 * b.over_revenue:.1f}% with the estimate. "
             f"Failure is {100 * a.failure_booked_share:.1f}% of the booked total, appraisal {100 * a.appraisal_booked_share:.1f}% and prevention {100 * a.prevention_booked_share:.1f}%.</p>")

    def row(label, f_):
        return [label, f_(a), f_(b), f_(w)]
    rows = [row("Revenue (quantity shipped at unit price)", lambda x: usd(x.revenue)), row("Scrap report (scrap transactions)", lambda x: usd(x.scrap_report)),
            row("Failure, as booked", lambda x: usd(x.failure_booked)), row("Appraisal", lambda x: usd(x.appraisal)), row("Prevention", lambda x: usd(x.prevention)),
            row("Total, as booked", lambda x: usd(x.total_booked)), row("Total over revenue, as booked", lambda x: f"{100 * x.booked_over_revenue:.2f}%"),
            row("Shares of the booked total: failure; appraisal; prevention", lambda x: f"{100 * x.failure_booked_share:.1f}%; {100 * x.appraisal_booked_share:.1f}%; {100 * x.prevention_booked_share:.1f}%"),
            row("Failure : appraisal : prevention, as booked", lambda x: ratio(x, True)),
            row(EST, lambda x: usd(x.rework_estimate)), row("Failure, with the estimate", lambda x: usd(x.failure)), row("Total, with the estimate", lambda x: usd(x.total)),
            row("Total over revenue, with the estimate", lambda x: f"{100 * x.over_revenue:.2f}%"),
            row("Shares with the estimate: failure; appraisal; prevention", lambda x: f"{100 * x.failure_share:.1f}%; {100 * x.appraisal_share:.1f}%; {100 * x.prevention_share:.1f}%"),
            row("Failure : appraisal : prevention, with the estimate", lambda x: ratio(x, False))]
    body += tbl(["", "2025", "2024", "24 months"], rows, total=(5, 11))
    body += cap("Table 1. Cost of quality by category, as booked and with the estimate of rework left on production jobs.")

    body += "<h2 id='f2'>2. Reconciliation to the source tables</h2>"
    y = 2025
    tot_b = a.total_booked
    traced = sum(tr[y].values())
    nrw = rw.loc[y]
    body += (f"<p>Every failure line of 2025 traces to its source record with no difference: {usd(tr[y]['failure'])} of {usd(a.failure_booked)}. Of appraisal, {usd(tr[y]['appraisal'])} of {usd(a.appraisal)} traces "
             f"(CMM time to the CMM reports, laboratory calibration to the calibration events); inspection labor and the technician's calibration time are booked from timesheets that are not in the exports. "
             f"No prevention line traces: training, SPC software and supplier audit travel are booked from invoices. In all, {usd(traced)} of {usd(tot_b)} as booked is traced, {100 * traced / tot_b:.1f}%. "
             f"The estimate of rework left on production jobs: the {int(nrw.unbooked_ncrs)} NCRs of 2025 with a rework disposition and no hours on the rework code sit on {int(nrw.unbooked_lots)} production lots that ran {nrw.estimated_hours:,.0f} hours over standard, "
             f"valued at the machinist rate.</p>")

    def rec_rows(year):
        out = []
        for x in rec[rec["year"] == year].itertuples():
            traced_ = x.source_amount == x.source_amount
            out.append([x.cost_line[0].upper() + x.cost_line[1:], x.cost_group, f"{x.lines:,}", usd(x.line_amount, 2), x.source, f"{x.source_records:,}" if traced_ else "", usd(x.source_amount, 2) if traced_ else "",
                        usd(abs(x.difference), 2) if traced_ else ""])
        return out
    head = ["Line", "Category", "Cost lines", "Amount", "Source", "Source records", "Source amount", "Difference"]
    body += tbl(head, rec_rows(2025))
    body += cap(f"Table 2. Cost lines of 2025 against their source tables. CMM time is booked at {cr['hours_per_report']:.2f} hours per report and {usd(cr['rate'], 2)} an hour; lines with no source table in the exports are "
                f"booked but not traceable and carry no difference. Cost lines whose NCR or complaint is not found in its table: {r['sources_not_found']}.")

    body += "<h2 id='f3'>3. Rework as booked and the estimate</h2>"
    body += (f"<p>Accounting books rework from the rework labor code: {usd(nrw.booked_amount)} on {int(nrw.booked_ncrs)} NCRs in 2025. {int(nrw.unbooked_ncrs)} of the {int(nrw.rework_ncrs)} rework NCRs carry no hours on that code; "
             f"the estimate for them is {usd(nrw.estimated_amount)}, which raises rework from {usd(nrw.booked_amount)} to {usd(nrw.booked_amount + nrw.estimated_amount)}. "
             f"In 2024, {int(rw.loc[2024].unbooked_ncrs)} of {int(rw.loc[2024].rework_ncrs)} carried none ({int(rw.loc[2024].unbooked_lots)} lots) and the estimate is {usd(rw.loc[2024].estimated_amount)}.</p>")
    body += tbl(["Year", "Rework NCRs", "With hours on the rework code", "Hours booked", "Amount booked", "Without hours on the code", "Their lots", "Hours over standard on their lots", "Estimate at the machinist rate"],
                [[yy, int(x.rework_ncrs), int(x.booked_ncrs), f"{x.booked_hours:,.0f}", usd(x.booked_amount), int(x.unbooked_ncrs), int(x.unbooked_lots), f"{x.estimated_hours:,.0f}", usd(x.estimated_amount)] for yy, x in ((2025, rw.loc[2025]), (2024, rw.loc[2024]))])
    body += cap("Table 3. Rework labor as booked beside the estimate from production hours over standard on lots with a rework NCR and no booked rework hours.")

    body += "<h2 id='f4'>4. Failure cost against the scrap report</h2>"
    body += (f"<p>The scrap report understates failure cost: failure cost in 2025 is {a.failure_booked_over_scrap:.2f} times the scrap report as booked and {a.failure_over_scrap:.2f} times with the estimate "
             f"({b.failure_booked_over_scrap:.2f} and {b.failure_over_scrap:.2f} in 2024). The report shows {usd(a.scrap_report)}; customer credits, sorting and containment, rework labor, return freight and re-inspection add "
             f"{usd(a.failure_booked - a.scrap_report)} as booked.</p>")
    body += figure_failure(r, "s6_fig1_failure_lines") + cap("Figure 1. Failure cost by line. The 2025 scrap bar is the amount on the scrap report; the hatched bars are the estimate of rework left on production jobs.")

    body += "<h2 id='f5'>5. Monthly trend</h2>"
    fm = r["failure_monthly"].set_index("period")
    mm = r["monthly"].set_index("period")
    f14 = r["f14_scrap_monthly"]
    parts = []
    for p0, p1 in PEAKS:
        sel = fm.loc[[p0, p1]]
        parts.append((p0[:4], float(mm.loc[[p0, p1], "failure"].sum()), float(sel["customer credit"].sum()), float(sel["sorting and containment"].sum()), float(sel["scrap"].sum()), f14.get(p0, 0.0) + f14.get(p1, 0.0)))
    mean25 = float(mm[mm.index.str.startswith("2025")]["failure"].mean())
    mean24 = float(mm[mm.index.str.startswith("2024")]["failure"].mean())
    p24, p25 = parts
    body += (f"<p>Failure cost as booked averages {usd(mean25)} a month in 2025 against {usd(mean24)} in 2024; appraisal and prevention are level. May and June are the highest pair of months in both years: "
             f"{usd(p25[1])} in 2025 and {usd(p24[1])} in 2024. The peaks are in customer credits ({usd(p25[2])} and {usd(p24[2])}) and in sorting and containment ({usd(p25[3])} and {usd(p24[3])}), not in scrap "
             f"({usd(p25[4])} and {usd(p24[4])}); F-14 scrap in May and June 2025 was {usd(p25[5])}.</p>")
    body += figure_monthly(r) + cap("Figure 2. Cost of quality by month and category as booked, 24 full months from January 2024; the estimate of rework left on production jobs is not in the monthly series.")

    body += "<h2 id='f6'>6. Cost attributable to the findings of S2, S3 and S4</h2>"
    f25 = fl[fl["year"] == 2025].set_index("cost_line")
    f24 = fl[fl["year"] == 2024].set_index("cost_line")
    att25, att24 = float(f25["attributed"].sum()), float(f24["attributed"].sum())
    s2 = r["s2"]
    len25 = float(s2[(s2["cited"] == "the length") & (s2["period_year"] == 2025)]["amount"].sum())
    oth25 = float(s2[(s2["cited"] != "the length") & (s2["period_year"] == 2025)]["amount"].sum())
    saved_h = s4["table_hours"] - s4["switched_hours"]
    e25 = esc.loc[2025]
    body += (f"<p>The findings of S2, S3 and S4 account for {usd(att25)} of {usd(a.failure)} of failure cost in 2025 (with the estimate), {100 * att25 / a.failure:.1f}%. The remaining failure cost sits in lines the studies did not address: "
             f"customer credits outside S-017 ({usd(f25.loc['customer credit', 'remaining'])}), scrap outside F-14 ({usd(f25.loc['scrap', 'remaining'])}) and sorting and containment outside the two "
             f"({usd(f25.loc['sorting and containment', 'remaining'])}).</p>")
    body += (f"<p>The milled length {LENGTH} (S2): {usd(len25)} in 2025 from NCRs citing the length, which understates it, since {r['s2_rework'][2025]['without_hours']} of its {r['s2_rework'][2025]['ncrs']} rework NCRs carries no booked hours "
             f"and the other NCR lines on part {part} ({usd(oth25)} in 2025, citing {', '.join(r['s2_other'])} or no characteristic) are not added. "
             f"F-14 scrap (S3): {usd(r['s3_by_year'][2025])} in 2025; {usd(s3.loc['before', 'per_month'])} a month on the {int(s3.loc['before', 'lots'])} lots before the K20 insert and {usd(s3.loc['after', 'per_month'])} a month on the "
             f"{int(s3.loc['after', 'lots'])} lots since. S-017 escapes (S4): {int(e25.complaints)} complaints in 2025 with {usd(e25.credit)} in credits, {usd(e25.containment)} in containment and {usd(e25.freight)} in return freight.</p>")
    rows = [[LINE_LABEL[k], usd(f25.loc[k, "amount"]), f25.loc[k, "finding"], usd(f25.loc[k, "attributed"]), usd(f25.loc[k, "remaining"]), usd(f24.loc[k, "amount"]), usd(f24.loc[k, "attributed"])] for k in LINE_ORDER]
    rows.append([EST, usd(a.rework_estimate), "", usd(0), usd(a.rework_estimate), usd(b.rework_estimate), usd(0)])
    rows.append(["Failure, with the estimate", usd(a.failure), "", usd(att25), usd(a.failure - att25), usd(b.failure), usd(att24)])
    body += tbl(["Failure line", "2025", "Study finding on the line", "2025 under the findings", "2025 remaining", "2024", "2024 under the findings"], rows, total=(len(rows) - 1,))
    body += cap(f"Table 4. Failure cost by line with the amount under the findings of S2 (the length {LENGTH}), S3 (F-14 scrap) and S4 (S-017 escapes): {100 * att25 / a.failure:.1f}% of failure cost in 2025 and {100 * att24 / b.failure:.1f}% in 2024.")
    body += (f"<p>Receiving inspection under the Z1.4 switching rules (S4) is a cost avoided in appraisal, not a failure cost: at {s4['minutes_per_piece']:.2f} minutes per sampled piece, {saved_h:,.0f} hours and "
             f"{usd(saved_h * s4['cost_per_hour'])} over the 24 months.</p>")
    body += tbl(["Receiving inspection, 24 months", "Sample pieces", "Hours", "Cost"],
                [["Z1.4 table on every lot", f"{s4['table_pieces']:,.0f}", f"{s4['table_hours']:,.0f}", usd(s4["table_hours"] * s4["cost_per_hour"])],
                 ["Z1.4 with the switching rules applied", f"{s4['switched_pieces']:,.0f}", f"{s4['switched_hours']:,.0f}", usd(s4["switched_hours"] * s4["cost_per_hour"])],
                 ["Difference", f"{s4['table_pieces'] - s4['switched_pieces']:,.0f}", f"{saved_h:,.0f}", usd(saved_h * s4["cost_per_hour"])]], total=(2,))
    body += cap(f"Table 5. Receiving inspection hours at {s4['minutes_per_piece']:.2f} minutes per piece and {usd(s4['cost_per_hour'], 2)} an hour, from the receiving inspectors' {s4['booked_hours']:,.0f} booked hours over {s4['pieces_taken']:,.0f} pieces.")

    body += "<h2 id='f7'>7. Prevention</h2>"
    body += (f"<p>Prevention is the smallest category: {usd(a.prevention)} in 2025, {100 * a.prevention_booked_share:.1f}% of the booked total and {100 * a.prevention_share:.1f}% with the estimate, down from "
             f"{100 * b.prevention_booked_share:.1f}% and {100 * b.prevention_share:.1f}% in 2024. Failure to appraisal to prevention is {ratio(a, True)} as booked and {ratio(a, False)} with the estimate "
             f"({ratio(b, True)} and {ratio(b, False)} in 2024).</p>")

    body += "<h2 id='rec'>Recommendation</h2><ul>"
    body += ("<li>Book rework and sorting hours against the NCR, not the production job, so that failure cost is captured without an estimate.</li>"
             "<li>Carry the cost of quality by category on the monthly quality review, on the booked basis, with the scrap report shown as a component and not as the total.</li>"
             "<li>Give re-inspection its own labor code; it is now identified only by the NCR reference on inspection labor lines.</li></ul>")
    body += "<h2 id='method'>Method and data</h2>"
    body += (f"<p class='note'>Cost lines: {int(r['by_line']['lines'].sum()):,} lines of the accounting ledger over the 24 months, grouped as failure, appraisal and prevention; re-inspection is the inspection labor booked against NCRs and is counted as failure. "
             "Reconciliation: each line against the record it derives from, by count and amount; scrap against the scrap transactions, rework, re-inspection and sorting against NCR hours at the labor rate of the year, "
             "credits, containment and freight against complaints, CMM time against the count of CMM reports, laboratory calibration against the count of laboratory calibration events. "
             "Estimate: hours over standard on the production lots of rework NCRs with no hours on the rework code, at the machinist rate; it is an estimate and is shown apart from the booked figures everywhere. "
             "Revenue: quantity shipped at unit price by ship date. Scrap report: the sum of scrap transactions. Monthly series: 24 full months, January 2024 to December 2025, as booked. "
             "Attribution: cost lines whose NCR cites the length; scrap transactions on F-14 lots; complaints for plating defects on accepted S-017 lots. Amounts are measured costs for the period; none is annualized.</p>")

    body += "<h2 id='app'>Appendix</h2>"
    body += tbl(head, rec_rows(2024)) + cap("Table A1. Cost lines of 2024 against their source tables.")
    bl = r["by_line"]
    rows = []
    for (g, line), d in bl.groupby(["cost_group", "cost_line"], sort=True):
        d = d.set_index("period_year")
        rows.append([line[0].upper() + line[1:], g] + [v for yy in (2025, 2024) for v in (f"{int(d.loc[yy, 'lines']):,}", usd(d.loc[yy, "amount"]), f"{d.loc[yy, 'hours']:,.0f}" if d.loc[yy, "hours"] > 0 else "")])
    body += tbl(["Line", "Category", "2025 lines", "2025 amount", "2025 hours", "2024 lines", "2024 amount", "2024 hours"], rows) + cap("Table A2. Cost lines by category and year.")
    body += tbl(["Month", "Failure, as booked", "Appraisal", "Prevention", "Total, as booked"],
                [[month(x.period), usd(x.failure), usd(x.appraisal), usd(x.prevention), usd(x.failure + x.appraisal + x.prevention)] for x in r["monthly"].itertuples()])
    body += cap("Table A3. Cost of quality by month and category, as booked.")
    rows = []
    for (cited, line), d in s2.groupby(["cited", "cost_line"], sort=True):
        d = d.set_index("period_year")
        rows.append([cited[0].upper() + cited[1:], LINE_LABEL[line]] + [v for yy in (2025, 2024) for v in ((f"{int(d.loc[yy, 'lines'])}", usd(d.loc[yy, "amount"])) if yy in d.index else ("", ""))])
    body += tbl(["NCR cites", "Line", "2025 lines", "2025 amount", "2024 lines", "2024 amount"], rows) + cap(f"Table A4. Cost lines from NCRs on part {part}.")
    body += tbl(["Year", "Complaints", "Credits", "Containment", "Return freight", "Total"],
                [[yy, int(x.complaints), usd(x.credit), usd(x.containment), usd(x.freight), usd(x.credit + x.containment + x.freight)] for yy, x in ((2025, esc.loc[2025]), (2024, esc.loc[2024]))])
    body += cap("Table A5. Complaints for plating defects on accepted S-017 lots.")

    toc = [("f1", "Totals"), ("f2", "Reconciliation"), ("f3", "Rework"), ("f4", "Scrap report"), ("f5", "Monthly trend"), ("f6", "Attributable"), ("f7", "Prevention"), ("rec", "Recommendation"), ("method", "Method"), ("app", "Appendix")]
    (S.DOCS / "reports").mkdir(parents=True, exist_ok=True)
    (S.DOCS / "reports" / "s6_cost_of_quality.html").write_text(S.report_shell("S6. Cost of quality, January 2024 to December 2025", "Study report", HEADER, body, toc), encoding="utf8", newline="\n")

    left = [f"<section><h2>Background and problem</h2><p>Cost of quality in 2025 is {usd(a.total_booked)} as booked, {100 * a.booked_over_revenue:.1f}% of revenue ({100 * a.over_revenue:.1f}% with rework left on production jobs estimated). "
            f"The monthly scrap report shows {usd(a.scrap_report)}; failure cost as booked is {a.failure_booked_over_scrap:.2f} times that.</p></section>",
            f"<section><h2>Current condition</h2>{figure_failure(r, 's6_a3_failure_lines', 2.9)}<div class='caption'>Failure cost by line; the 2025 scrap bar is the scrap report, the hatched bars the estimate.</div>"
            + tbl(["", "2025", "2024"], [["Total as booked; over revenue", f"{usd(a.total_booked)}; {100 * a.booked_over_revenue:.1f}%", f"{usd(b.total_booked)}; {100 * b.booked_over_revenue:.1f}%"],
                                        ["Total with the estimate; over revenue", f"{usd(a.total)}; {100 * a.over_revenue:.1f}%", f"{usd(b.total)}; {100 * b.over_revenue:.1f}%"],
                                        ["Failure over the scrap report: as booked; with the estimate", f"{a.failure_booked_over_scrap:.2f}; {a.failure_over_scrap:.2f}", f"{b.failure_booked_over_scrap:.2f}; {b.failure_over_scrap:.2f}"],
                                        ["Failure : appraisal : prevention, as booked", ratio(a, True), ratio(b, True)]]) + "</section>",
            "<section><h2>Target</h2><p>Failure cost reported on a booked basis with no estimate line required, reviewed monthly.</p></section>"]
    right = [f"<section><h2>Analysis</h2>"
             + tbl(["2025", "Booked", "Traced to a source table"], [["Failure", usd(a.failure_booked), usd(tr[y]["failure"])], ["Appraisal", usd(a.appraisal), usd(tr[y]["appraisal"])], ["Prevention", usd(a.prevention), usd(tr[y]["prevention"])],
                                                                    [EST, "", f"{usd(a.rework_estimate)} on {int(nrw.unbooked_ncrs)} NCRs"]])
             + f"<ul><li>Every failure line traces to its scrap transaction, NCR or complaint with no difference; inspection labor, technician calibration time and the prevention lines are booked from timesheets and invoices that are not in the exports.</li>"
             f"<li>{int(nrw.unbooked_ncrs)} of {int(nrw.rework_ncrs)} rework NCRs in 2025 carry no hours on the rework code; their {int(nrw.unbooked_lots)} lots ran {nrw.estimated_hours:,.0f} hours over standard.</li>"
             f"<li>The findings of S2, S3 and S4 account for {usd(att25)} of {usd(a.failure)} of failure cost (with the estimate), {100 * att25 / a.failure:.1f}%: the length {LENGTH} {usd(len25)}, F-14 scrap {usd(r['s3_by_year'][2025])}, "
             f"S-017 escapes {usd(e25.credit + e25.containment + e25.freight)}.</li>"
             f"<li>The rest sits in customer credits outside S-017, scrap outside F-14 and sorting and containment outside the two.</li>"
             f"<li>Cost avoided in appraisal under the Z1.4 switching rules: {saved_h:,.0f} receiving hours, {usd(saved_h * s4['cost_per_hour'])} over 24 months.</li></ul></section>",
             "<section><h2>Countermeasures</h2>"
             + tbl(["Action", "Owner", "When"], [["Rework and sorting hours booked against the NCR, not the production job", "Production manager and controller", "March 2026"],
                                                 ["Cost of quality by category on the monthly quality review, booked basis, with the scrap report as a component", "Quality manager", "from the February 2026 review"],
                                                 ["A labor code for re-inspection, apart from inspection labor", "Controller", "March 2026"]]) + "</section>",
             f"<section><h2>Expected results</h2><p>Rework NCRs without booked hours from {int(nrw.unbooked_ncrs)} of {int(nrw.rework_ncrs)} in 2025 to none, so that the estimate line ({usd(a.rework_estimate)} in 2025) closes into booked rework. "
             f"Measured to date: F-14 scrap at {usd(s3.loc['after', 'per_month'])} a month since the K20 insert, from {usd(s3.loc['before', 'per_month'])}.</p></section>",
             "<section><h2>Follow-up</h2><p>The count of rework NCRs without hours and the four categories as booked, each month on the quality review. The cost lines traced again to their source tables at the end of 2026.</p></section>"]
    (S.DOCS / "a3").mkdir(parents=True, exist_ok=True)
    (S.DOCS / "a3" / "s6_cost_of_quality.html").write_text(S.a3_shell("Cost of quality", "S6 A3", HEADER.split("<br>")[0] + "<br>Management summary; DMAIC project.", "\n".join(left), "\n".join(right)), encoding="utf8", newline="\n")
    return S.DOCS / "reports" / "s6_cost_of_quality.html"


if __name__ == "__main__":
    print(build())
