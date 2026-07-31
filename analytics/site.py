"""README.md and docs/index.html: the study table with each study's finding, the coverage line, the customer package mapping, the data sources and the links.

Usage: python -m analytics.site
The finding of each study is composed from the sentences of its report under docs/reports, so the reports are built first.
"""
import csv
import html
import re
from pathlib import Path

from analytics.data import query
from analytics.style.style import DOCS, shell

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
SHOP = "Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant."
SCOPE = "Six quality engineering studies and a quality dashboard on the shop's records from January 2024 to December 2025."


def report_text(stem, section, k=0):
    s = (DOCS / "reports" / f"{stem}.html").read_text(encoding="utf8")
    body = re.search(rf"<h2 id='{section}'>.*?</h2>(.*?)(?=<h2 id=|$)", s, flags=re.S).group(1)
    items = re.findall(r"<p>(.*?)</p>|<li>(.*?)</li>", body, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", "".join(items[k])))).strip()


def grab(pattern, text):
    m = re.search(pattern, text)
    assert m, (pattern, text)
    return m.groups()


def _s1():
    bore, ndc_b = grab(r"consumes ([\d.]+%) of the .* with (\d+) distinct", report_text("s1_msa", "f1"))
    air, ndc_a = grab(r"air gauge consumes ([\d.]+%) of tolerance, with (\d+) distinct", report_text("s1_msa", "f2"))
    study, n, prod = grab(r"operator sd of ([\d.]+) mm .*production record \((\d+) machinists, .*\) gives ([\d.]+)", report_text("s1_msa", "f3"))
    share, = grab(r"^(\d+%) of the bore's apparent variance", report_text("s1_msa", "f4"))
    pieces, bias, lo, hi = grab(r"On ([\d,]+) pieces measured by both, the bore gauge reads ([\d.]+) mm above the CMM \(([\d.]+) to ([\d.]+)\)", report_text("s1_msa", "f6"))
    return (f"The bore gauge consumes {bore} of tolerance (ndc {ndc_b}) and the air gauge {air} (ndc {ndc_a}); {share} of the apparent process variation on the bore in 2025 was measurement; "
            f"the production history gives an operator sd of {prod} mm over {n} machinists against the study's {study}; bore-gauge bias against the CMM on {pieces} matched pieces is {bias} mm ({lo} to {hi}).")


def _s2():
    n, k, m6, j = grab(r"Of (\d+) critical characteristics the shop reports as capable, (\d+) are not capable on the 2025 record; of (\d+) reported marginal, (\d+) are capable", report_text("s2_capability", "f1"))
    lo, hi, inside = grab(r"95% interval of ([\d.]+) to ([\d.]+) either side on the reported capable calls\. (\d+) of the", report_text("s2_capability", "f2"))
    b, c, d = grab(r"Cpk ([\d.]+) on the shop's 25 readings, ([\d.]+) on the year's subgroups and ([\d.]+) on every piece", report_text("s2_capability", "f3"))
    return (f"Of {n} critical characteristics the shop reports as capable, {k} are not when the calculation uses the pooled within-subgroup standard deviation, the fitted distribution for bounded "
            f"characteristics and all 2025 subgroups; {j} of {m6} reported as marginal are capable; the reported values carry a sampling interval of ±{lo} to ±{hi} at 25 subgroups and {inside} of the "
            f"capable calls lie inside it; the medical bore gives Cpk {b} on the shop's 25 readings, {c} on the year's subgroups and {d} on every piece.")


def _s3():
    share, = grab(r"carried (\d+%) of the family's scrap pieces", report_text("s3_root_cause", "f1"))
    p, = grab(r"MT-04 odds ratio is [\d.]+ \([\d.]+ to [\d.]+, p = ([\d.]+)\)", report_text("s3_root_cause", "f4"))
    var, = grab(r"explains ([\d.]+%) of the between-lot scrap variance", report_text("s3_root_cause", "f5"))
    a, b, lots, since, all_ = grab(r"fell from ([\d.]+%) to ([\d.]+%) on the (\d+) lots of the confirmation window .* stands at ([\d.]+%) on all (\d+) lots since", report_text("s3_root_cause", "f7"))
    assert "did not move" in report_text("s3_root_cause", "f7")
    return (f"MT-04 accounted for {share} of scrap on the family; controlling for bar-lot hardness and insert grade the machine effect is not significant (p = {p}); hardness above 32 HRC with the standard "
            f"insert explains {var} of the between-lot scrap variance; the insert change cut the family's scrap rate from {a} to {b} on the next {lots} lots (p < 0.001) and {since} on all {all_} since, "
            f"with the control family unchanged.")


def _s4():
    c0, z, share = grab(r"same LTPD as the Z1.4 plan \(([\d.]+%) against ([\d.]+%) on lots of 501 to 1,200.*\) at (\d+%) of the sample pieces", report_text("s4_sampling", "f2"))
    pa, pc = grab(r"current plan passes (\d+%) of lots above 2.5% defective and the c=0 plan (\d+%)", report_text("s4_sampling", "f4"))
    rz, lots, rc = grab(r"current plan rejects (\d+) of (\d+) lots and the c=0 plan (\d+)", report_text("s4_sampling", "f4"))
    k, total = grab(r"^(\d+) of (\d+) suppliers have a defect rate whose 95% interval lies above 1%", report_text("s4_sampling", "f6"))
    assert "Two of the five worst" in report_text("s4_sampling", "f6")
    qualify, hours = grab(r"\((\d+) suppliers qualify\), saving [\d,]+ sample pieces and ([\d,]+) hours in 24 months", report_text("s4_sampling", "rec"))
    return (f"The c=0 plan gives the same consumer protection at the LTPD as the current plan ({c0} against {z} on lots of 501 to 1,200) at {share} of the sample pieces and rejects {rc} of {lots} S-017 lots "
            f"over 24 months against the current plan's {rz}; the Z1.4 switching rules, never applied in the record, would have moved {qualify} of {total} suppliers to reduced inspection and saved {hours} "
            f"receiving hours; evaluated on S-017's lot history the current plan accepts {pa} of lots above 2.5% defective and the c=0 plan {pc}; {k} of {total} suppliers have defect-rate intervals lying "
            f"entirely above 1%; 2 of the five worst suppliers on the published scorecard have fewer than five lots.")


def _s5():
    effect, = grab(r"interact: effect (-?[\d.]+) µm \(p < 0.001\)", report_text("s5_doe", "f2"))
    lo_r, hi_r = grab(r"feed effect is ([+-][\d.]+) µm at the 0.4 mm radius and ([+-][\d.]+) µm at 0.8 mm", report_text("s5_doe", "f3"))
    pred, lo, hi, before = grab(r"predicts Ra ([\d.]+) µm \(([\d.]+) to ([\d.]+)\) against ([\d.]+) µm at the settings before", report_text("s5_doe", "f5"))
    assert "4 of 4 inside the interval" in report_text("s5_doe", "f5")
    lots, mean = grab(r"The (\d+) lots run since .* average ([\d.]+) µm", report_text("s5_doe", "f7"))
    return (f"Feed and insert nose radius interact (effect {effect} µm, p < 0.001); at 0.8 mm radius the feed effect reverses ({lo_r} µm at 0.4 mm, {hi_r} µm at 0.8 mm); the chosen settings reduce Ra from "
            f"{before} to {pred} µm, confirmed on four runs inside the prediction interval ({lo} to {hi}); the next {lots} production lots hold {float(mean):.2f} µm.")


def _s6():
    booked, est = grab(r"as booked, ([\d.]+%) of revenue.* it is \$[\d,]+, ([\d.]+%)\.", report_text("s6_cost_of_quality", "f1"))
    ratio, = grab(r"failure cost in 2025 is ([\d.]+) times the scrap report as booked", report_text("s6_cost_of_quality", "f4"))
    prev, = grab(r"in 2025, ([\d.]+%) of the booked total", report_text("s6_cost_of_quality", "f7"))
    share, = grab(r"\(with the estimate\), ([\d.]+%)\.", report_text("s6_cost_of_quality", "f6"))
    return (f"Cost of quality is {booked} of 2025 revenue as booked and {est} with rework left on production jobs estimated; failure costs are {ratio} times the scrap report as booked; prevention is {prev} "
            f"of the booked total; the non-capable length, the F-14 scrap and the plating escapes account for {share} of failure cost.")


# study, file stem, title, question, the finding composed from the report, whether the study has an A3
STUDIES = [
    ("S1", "s1_msa", "Measurement system analysis", "How much of the tolerance on the critical bore do the gauges consume?", _s1, False),
    ("S2", "s2_capability", "Process capability", "Are the characteristics the shop reports as capable capable?", _s2, False),
    ("S3", "s3_root_cause", "Root cause of scrap on family F-14", "What drives scrap on family F-14?", _s3, True),
    ("S4", "s4_sampling", "Acceptance sampling and supplier quality", "What does the receiving plan protect against, and which suppliers run above 1%?", _s4, False),
    ("S5", "s5_doe", "Designed experiment on surface finish", "Which settings bring the surface finish inside its limit?", _s5, True),
    ("S6", "s6_cost_of_quality", "Cost of quality", "What does quality cost beyond the scrap report?", _s6, True),
]
SYSTEMS = [("erp", "ERP"), ("qms", "QMS with SPC module"), ("cmm", "CMM and vision software"), ("calibration", "Calibration system"), ("accounting", "Accounting"), ("studies", "Study worksheets")]
GRAIN = {"customers": "customer", "employees": "employee", "jobs": "lot", "machines": "machine", "material_certs": "bar lot", "parts": "part", "routings": "part and operation",
         "scrap_transactions": "scrap transaction", "audit_findings": "audit finding", "capa": "corrective action", "capability_reports": "capability report", "characteristics": "part and characteristic",
         "complaints": "complaint", "final_inspection": "lot", "ncrs": "nonconformance", "receiving_inspection": "receiving lot", "spc_subgroups": "subgroup", "suppliers": "supplier",
         "cmm_features": "report and feature", "cmm_reports": "CMM report", "calibrations": "calibration event", "gauges": "gauge", "cost_of_quality_lines": "cost line", "labor_rates": "role and year",
         "attribute_agreement_cosmetic": "inspector, part and trial", "doe_surface_finish": "run", "gauge_rr_air_gauge": "operator, part and trial", "gauge_rr_bore_gauge": "operator, part and trial"}
PIPELINE = ("`pipeline/load` loads the CSV exports under `data/raw` into DuckDB with dlt, one table per file. The dbt project under `pipeline/dbt` builds the staging models (one per export, typed), the "
            "intermediate models (the process history of each characteristic with lot, machine, operator, gauge, bar lot and calibration status; the CMM feature mapping and the serial match; lot outcomes; "
            "receiving outcomes with the Z1.4 table values; cost lines with their source records) and the marts, with schema tests on keys, ranges and relationships in every layer. The scripts under "
            "`analytics/` read the marts and the study worksheets under `data/raw/studies` and write each study's report, A3 and figures under `docs/`, the dashboard and this file.")
RUN = """```
python -m venv .venv
.venv\\Scripts\\activate            # Windows; on Linux or macOS: source .venv/bin/activate
pip install -e .
python -m pipeline.load.load_exports
cd pipeline/dbt
dbt build --profiles-dir .
cd ../..
python -m analytics.build_all
```"""


def element(stem):
    s = (DOCS / "reports" / f"{stem}.html").read_text(encoding="utf8")
    meta = re.search(r'<div class="meta">(.*?)</div>', s, flags=re.S).group(1)
    return html.unescape(meta.split("<br>")[-1]).strip().rstrip(".")


def links(stem, a3, prefix="docs/"):
    out = [(f"{prefix}reports/{stem}.html", "report")]
    if a3:
        out.append((f"{prefix}a3/{stem}.html", "A3"))
    return out


def batch_id():
    with open(RAW / "erp" / "export_batch.csv", newline="", encoding="utf8") as f:
        return next(csv.DictReader(f))["export_batch_id"]


def records(path, worksheet):
    if worksheet:                                       # header rows, a blank line, then the table
        return len(path.read_text(encoding="utf8").split("\n\n", 1)[1].splitlines()) - 1
    with open(path, newline="", encoding="utf8") as f:
        return sum(1 for _ in csv.reader(f)) - 1


def sources():
    rows = []
    for folder, name in SYSTEMS:
        for p in sorted((RAW / folder).glob("*.csv")):
            if p.stem != "export_batch":
                rows.append([name, f"data/raw/{folder}/{p.name}", GRAIN[p.stem], f"{records(p, folder == 'studies'):,}"])
    return rows


def coverage():
    c = query("""select (select count(*) from marts.mart_lot_outcomes) as lots,
                        (select count(*) from marts.mart_spc_history where subgroup_size = 5) as subgroups,
                        (select count(*) from marts.mart_spc_history where subgroup_size = 1) as pieces,
                        (select count(*) from staging.stg_cmm__cmm_reports) as cmm,
                        (select count(*) from marts.mart_receiving_lots) as receiving""").iloc[0]
    readings = 5 * int(c.subgroups) + int(c.pieces)
    return (f"Every figure in the studies is computed on all records in the period: {int(c.lots):,} lots, {int(c.subgroups):,} subgroups of five and {int(c.pieces):,} single-piece records "
            f"({readings:,} readings), {int(c.cmm):,} CMM reports, {int(c.receiving):,} receiving lots, January 2024 to December 2025; the gauge, attribute and designed-experiment studies are the shop's "
            f"worksheets as recorded.")


INTRO = ("Measurement systems, capability, root cause, acceptance sampling, a designed experiment and cost of quality on a precision machining shop, January 2024 to December 2025, "
         "computed on the shop's complete quality record and set beside the figures the shop reports.")
INCLUDED = [
    "Six connected studies, each delivered as a client report, with an A3 for each improvement project: gauge R&R, bias, linearity and attribute agreement; process capability restated on every "
    "subgroup; root cause of scrap on one part family; acceptance sampling and the supplier scorecard; a designed experiment on surface finish; cost of quality reconciled to its source tables. "
    "Each study is mapped to the PPAP element or AS9102 form it supports.",
    "One quality dashboard: capability as reported beside capability as restated, PPM by program, NCRs by cause and detection point, the supplier scorecard with intervals, cost of quality by "
    "category, gauge calibration status, SPC alarms.",
    "A data pipeline from raw system exports to analysis-ready marts: DuckDB, dbt with schema tests, one build command that regenerates every table, figure and page byte-identically.",
]
CONTEXT = [
    "The shop is a precision machining supplier: about 150 employees, IATF 16949 and AS9100, one plant, about 600 active part numbers across 40 families on Swiss, multi-axis turning, milling and "
    "grinding, for automotive, aerospace, medical and industrial programs. Critical characteristics run on SPC in the QMS module; CMM reports, receiving inspection, NCRs, complaints and "
    "calibration each live in their own system; accounting books quality cost on its own lines.",
    "The shop's quality reporting rested on three documents: the monthly scrap report, the capability reports its engineers file with customer packages from the last 25 subgroups, and a quarterly "
    "supplier scorecard ranked on lot acceptance. In 2025 those documents said that 49 of the 56 critical characteristics with a report were capable, that one machine accounted for most of the "
    "scrap on the F-14 family, that the plating supplier S-017 was accepted at receiving on every lot while its defects reached customers as complaints, and that quality cost the shop about "
    "$560,000 a year. The engineering staff ran the studies the customers required, on worksheets, in a statistics package; the two years of SPC subgroups, CMM reports, receiving results and NCRs "
    "behind those worksheets were used for nothing beyond the control charts that produced them.",
    "The engagement computed each of those figures again on the whole record and compared the two: the gauge studies against the production history on the same bore, the 25-subgroup capability "
    "reports against every 2025 subgroup, the machine Pareto against a model that controls for bar-lot hardness and insert grade, the receiving plan against the supplier's actual lot quality, the "
    "scrap report against every failure line in the ledger. Where the shop's figure held, the report says so; where it did not, the report gives the restated figure, the reason, and what to do. "
    "The studies below are the result, in the order they were built.",
]
METHODS = [
    "Quality engineering statistics: gauge R&R by the AIAG ANOVA method with variance components, % of tolerance and ndc; bias and linearity from calibration records; attribute agreement with "
    "Fleiss' kappa; stability by Western Electric rules 1 to 4 before capability; Cp, Cpk, Pp and Ppk with bootstrap intervals; distribution fitting by Anderson-Darling and the percentile method "
    "for bounded characteristics; the sampling interval a 25-subgroup study carries; ANOVA and quasi-likelihood binomial regression with controls for root cause; two-proportion score tests with a "
    "control family; Z1.4 and zero-acceptance sampling plans on binomial and hypergeometric OC curves, AOQ and switching rules, evaluated against the supplier's actual lot-quality distribution; "
    "Jeffreys intervals on supplier rates; a 2^(4-1) designed experiment with alias resolution, a reduced model, prediction intervals and confirmation runs; cost of quality assembled from cost "
    "lines and reconciled line by line to the source tables.",
    "Data engineering: raw system exports loaded to DuckDB; a dbt project with schema tests on every mart (249 nodes and tests); one build command that regenerates every table, figure and page "
    "byte-identically from the committed inputs; two executions from a clean tree give byte-identical outputs.",
    "Population against sample: every study computes the shop's own figure on its own sample first and then the same quantity on all records, in one table, so the difference is measured rather "
    "than asserted.",
    "Framing: the improvement projects are written as DMAIC projects with an A3 each. Every report describes the findings and what to do, in the form a client receives at the end of an engagement.",
]
RECORD = ("The record carries what these systems carry in practice: digit preference and readings pulled inside a limit on hand gauges, subgroups entered in a batch at the end of a shift, gauge "
          "ids not updated after a gauge went out of service, CMM feature names that do not match the characteristics master, NCR cause codes as the opener entered them, receiving samples below "
          "the table value, duplicated complaint entries, and rework hours left on the production job. The analyses work with the record as it stands and say so where it limits a finding.")
AUTHOR = "Brian Davis. Data engineering and applied analytics/ML for manufacturers. Other work: [github.com/brimsystems](https://github.com/brimsystems?tab=repositories)."


def current_periods():
    """The current month and week as the dashboard header states them."""
    meta = (DOCS / "dashboard" / "index.html").read_text(encoding="utf8")
    month = re.search(r"(\w+ \d{4}) \(current month\)", meta).group(1)
    name, day = re.search(r"week of (\w+) (\d+), \d{4} \(current week", meta).groups()
    return month, f"{int(day)} {name}"


def readme(findings):
    month, week = current_periods()
    lines = ["# mfg-quality-engineering", "", INTRO, "", "![Quality dashboard](docs/readme/dashboard.png)", "", "## What is included", ""]
    lines += [f"- {x}" for x in INCLUDED]
    lines += ["", "## Business context", ""]
    for x in CONTEXT:
        lines += [x, ""]
    lines += ["## Studies", "", "| Study | Question | Finding | PPAP or AS9102 element | Deliverable |", "|---|---|---|---|---|"]
    for (s, stem, title, question, _, a3), finding in zip(STUDIES, findings):
        lines.append(f"| {s}. {title} | {question} | {finding} | {element(stem)} | " + ", ".join(f"[{t}]({u})" for u, t in links(stem, a3)) + " |")
    lines += ["", "| Study | PPAP or AS9102 element | Deliverable |", "|---|---|---|"]
    for s, stem, title, _, _, a3 in STUDIES:
        lines.append(f"| {s}. {title} | {element(stem)} | " + ", ".join(f"[{t}]({u})" for u, t in links(stem, a3)) + " |")
    lines += ["", "**Dashboard.** [docs/dashboard/index.html](docs/dashboard/index.html). Index of deliverables: [docs/index.html](docs/index.html). "
              f"{month} is the current month and the week of {week} the current week; every panel carries a one-line definition in the reports' wording.", "", "## Methods", ""]
    for x in METHODS:
        lines += [x, ""]
    lines += ["## Data", "", coverage(), "", RECORD, "", f"Export batch {batch_id()}, as at 31 December 2025.", "", "| System | Export | Grain | Records |", "|---|---|---|---|"]
    lines += ["| " + " | ".join(r) + " |" for r in sources()]
    lines += ["", PIPELINE, "", "## How to run", "", "Python 3.12 or later, from a clean clone:", "", RUN, "", "## Author", "", AUTHOR, ""]
    (ROOT / "README.md").write_text("\n".join(lines), encoding="utf8", newline="\n")


def index(findings):
    def tbl(head, rows):
        h = "".join(f"<th>{c}</th>" for c in head)
        b = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in r) + "</tr>" for r in rows)
        return f'<div style="overflow-x:auto"><table class="data"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'

    def anchors(stem, a3):
        return ", ".join(f'<a href="{u}">{t}</a>' for u, t in links(stem, a3, ""))
    body = "<h2>Studies</h2>" + tbl(["Study", "Question", "Finding", "Deliverable"],
                                    [[f"{s}. {title}", question, html.escape(finding), anchors(stem, a3)] for (s, stem, title, question, _, a3), finding in zip(STUDIES, findings)])
    body += '<p>Dashboard: <a href="dashboard/index.html">quality dashboard</a>.</p>'
    body += f"<p>{html.escape(coverage())}</p>"
    body += "<h2>Customer package mapping</h2>" + tbl(["Study", "PPAP or AS9102 element", "Deliverable"], [[f"{s}. {title}", html.escape(element(stem)), anchors(stem, a3)] for s, stem, title, _, _, a3 in STUDIES])
    meta = f"{SHOP} January 2024 to December 2025.<br>Sources: ERP, QMS with its SPC module, CMM software, calibration system and accounting exports (batch {batch_id()}); the shop's study worksheets."
    (DOCS / "index.html").write_text(shell("Quality engineering studies", "Index of deliverables", meta, body), encoding="utf8", newline="\n")


def main():
    findings = [spec() for _, _, _, _, spec, _ in STUDIES]
    readme(findings)
    index(findings)
    print("wrote README.md and docs/index.html")


if __name__ == "__main__":
    main()
