"""S1 report: measurement system analysis.

Usage: python -m analytics.s1_msa.report
"""
import warnings

import numpy as np
import pandas as pd

from analytics.s1_msa.s1_msa import YEAR, compute
from analytics.style import style as S

HEADER = ("Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant. January 2024 to December 2025; lengths in mm.<br>"
          "Sources: gauge study and attribute study worksheets, SPC module, CMM software, calibration system.<br>"
          "PPAP element 7, measurement system analysis studies; AS9102 supporting data.")


def tbl(head, rows, cls="data"):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f'<td class="{"num" if i else ""}">{v}</td>' for i, v in enumerate(r)) + "</tr>" for r in rows)
    return f'<table class="{cls}"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def cap(text):
    return f'<div class="caption">{text}</div>'


def components_table(g):
    rows = []
    for x in g["components"].itertuples():
        rows.append([x.Source, f"{x.VarComp:.9f}", f"{x.pct_contribution:.2f}", f"{x.StdDev:.6f}", f"{x.study_var:.6f}", f"{x.pct_study_var:.2f}", f"{x.pct_tolerance:.2f}",
                     f"{x.sd_lower:.4f} to {x.sd_upper:.4f}" if x.sd_lower == x.sd_lower and x.sd_upper == x.sd_upper else ""])
    return tbl(["Source", "VarComp", "%Contribution (of VarComp)", "StdDev (SD)", "Study Var (6 x SD)", "%Study Var (%SV)", "%Tolerance (SV/Toler)", "StdDev 95% interval"], rows)


def anova_table(g):
    rows = [[x.Source, x.DF, f"{x.SS:.7f}", f"{x.MS:.8f}" if x.MS == x.MS else "", f"{x.F:.3f}" if x.F == x.F else "", f"{x.P:.3f}" if x.P == x.P else ""] for x in g["anova"].itertuples()]
    return tbl(["Source", "DF", "SS", "MS", "F", "P"], rows)


def figure_gauges(gauge):
    f, ax = S.fig(h=6.8, w=9.6, ncols=2, nrows=2)
    colors = [S.BRAND_BLUE, S.AMBER, S.ACCENT]
    for j, (key, title) in enumerate((("bore", "Bore gauge"), ("air", "Air gauge"))):
        t = gauge[key]["worksheet"]
        ops = sorted(t["operator"].unique())
        m = t.groupby(["operator", "part"])["reading"].mean().unstack(0)
        for o, c in zip(ops, colors):
            ax[0, j].plot(m.index, S.sig(m[o]), marker="o", ms=3.5, lw=1.4, color=c, label=o)
        ax[0, j].set_title(f"{title}: mean by part")
        ax[0, j].set_xlabel("Part")
        ax[0, j].set_xticks(range(1, 11))
        ax[0, j].legend(frameon=False, ncol=3, loc="lower center", fontsize=9)
        rng = t.groupby(["operator", "part"])["reading"].agg(lambda s: s.max() - s.min())
        rbar = float(rng.mean())
        x0 = 0
        for o, c in zip(ops, colors):
            v = rng[o]
            ax[1, j].plot(np.arange(x0 + 1, x0 + len(v) + 1), S.sig(v), marker="o", ms=3.5, lw=1.2, color=c)
            x0 += len(v)
        ax[1, j].axhline(float(S.sig(rbar)), color=S.DARK_GREY, lw=1)
        ax[1, j].axhline(float(S.sig(2.574 * rbar)), color=S.RED, lw=1, ls="--")
        ax[1, j].set_title(f"{title}: range by operator")
        ax[1, j].set_xlabel("Parts 1 to 10 for each operator in turn")
        ax[1, j].set_xticks([])
    ax[0, 0].set_ylabel("mm")
    ax[1, 0].set_ylabel("mm")
    lo = min(a.get_ylim()[0] for a in ax[0])
    hi = max(a.get_ylim()[1] for a in ax[0])
    top = max(a.get_ylim()[1] for a in ax[1])
    for a in ax[0]:
        a.set_ylim(lo - 0.22 * (hi - lo), hi)
    for a in ax[1]:
        a.set_ylim(0, top)
    f.tight_layout()
    return S.save(f, "s1_fig1_gauge_studies", "Operator by part interaction and range charts for the bore gauge and the air gauge")


def figure_bias(bias):
    f, ax = S.fig()
    pts = bias["all_points"]
    out = set(bias["points"]["calibration_id"])
    for cid, g in pts.groupby("calibration_id", sort=False):
        marked = cid in out
        ax.plot(S.sig(g["reference_value"]), S.sig(g["as_found_error"]), marker="o", ms=4, lw=1.6 if marked else 1.0, color=S.RED if marked else S.LIGHT_BLUE,
                label=f"{str(g['done_date'].iloc[0])[:10]}" + (", found out of tolerance" if marked else ""))
    tol = float(pts["tolerance"].iloc[0])
    ax.axhline(tol, color=S.DARK_GREY, lw=1, ls="--")
    ax.axhline(0, color="#DDDDDD", lw=1)
    ax.set_xlabel("Reference value, mm")
    ax.set_ylabel("As-found error, mm")
    ax.set_title("Bore gauge: as-found error at the check points, five calibrations")
    ax.set_ylim(-0.0003, 0.0082)
    ax.legend(frameon=False, ncol=3, fontsize=9, loc="upper left")
    f.tight_layout()
    return S.save(f, "s1_fig2_bias_linearity", "As-found error of the bore gauge against reference value at five calibrations")


def figure_operators(prod, study_ops):
    f, ax = S.fig(h=4.6, w=6.2)
    e = prod["by_operator"].set_index("operator_id")["random_effect"]
    b = prod["match_by_operator"].set_index("operator_id")
    lim = 0.0062
    ax.plot([-lim, lim], [-lim, lim], color="#DDDDDD", lw=1)
    for o in e.index:
        st_ = o in study_ops
        ax.errorbar(float(S.sig(e[o])), float(S.sig(b.loc[o, "mean"])), yerr=[[float(S.sig(b.loc[o, "mean"] - b.loc[o, "lower"]))], [float(S.sig(b.loc[o, "upper"] - b.loc[o, "mean"]))]],
                    fmt="o", ms=7, color=S.AMBER if st_ else S.BRAND_BLUE, ecolor=S.GREY, capsize=2)
        offsets = [(9, -12), (-46, 9), (9, -14), (-46, 9), (10, -12), (-50, -5), (-16, 17), (10, -9)]
        ax.annotate(o, (float(S.sig(e[o])), float(S.sig(b.loc[o, "mean"]))), textcoords="offset points", xytext=offsets[list(e.sort_values().index).index(o) % 8], fontsize=9, color=S.DARK_GREY)
    ax.plot([], [], "o", color=S.AMBER, label="In the gauge study")
    ax.plot([], [], "o", color=S.BRAND_BLUE, label="Other F-21 machinists")
    ax.legend(frameon=False, loc="upper left")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_xlabel("Operator effect in the SPC record, mm (mixed model)")
    ax.set_ylabel("Bore gauge minus CMM, mm (matched pieces)")
    ax.set_title(f"Each machinist in two records, {YEAR}")
    f.tight_layout()
    return S.save(f, "s1_fig3_operator_effects", "Operator effect from the SPC record against bias to the CMM, one point per machinist")


def figure_attribute(at):
    f, ax = S.fig(h=3.4, w=6.6)
    d = at["by_inspector"]
    x = np.arange(len(d))
    for k, (col, ci, c, label) in enumerate((("within", "within_ci", S.BRAND_BLUE, "Within inspector"), ("reference", "reference_ci", S.ACCENT, "Against the reference"))):
        v = 100 * d[col].to_numpy()
        lo = v - 100 * np.array([c_[0] for c_ in d[ci]])
        hi = 100 * np.array([c_[1] for c_ in d[ci]]) - v
        ax.errorbar(x + (k - 0.5) * 0.22, S.sig(v), yerr=[S.sig(lo), S.sig(hi)], fmt="o", ms=7, color=c, ecolor=S.GREY, capsize=3, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels(d["inspector"])
    ax.set_ylim(50, 100)
    ax.set_ylabel("% of 50 parts")
    ax.set_title("Attribute agreement by inspector, with 95% intervals")
    ax.legend(frameon=False, loc="lower right")
    f.tight_layout()
    return S.save(f, "s1_fig4_attribute_agreement", "Within-inspector agreement and agreement with the reference by inspector")


def build():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = compute()
    b, a = r["gauge"]["bore"], r["gauge"]["air"]
    bias, at, prod = r["bias"], r["attribute"], r["production"]
    comp = b["components"].set_index("Source")
    acomp = a["components"].set_index("Source")
    y = prod["by_year"].set_index("year")
    y25, y24 = y.loc[YEAR], y.loc[YEAR - 1]
    study_ops = set(b["by_operator"]["operator"])
    rec = bias["records"]
    bad = rec[rec["largest_error"] > rec["tolerance"]].iloc[0]
    good = rec[rec["largest_error"] <= rec["tolerance"]]
    days_late = (pd.Timestamp(bad["done_date"]) - pd.Timestamp(bad["due_date"])).days
    ma = prod["match_all"]
    mi = prod["match_by_interval"]
    late_row = mi[[pd.Timestamp(x) == pd.Timestamp(bad["due_date"]) + pd.Timedelta(days=1) for x in mi["from"]]].iloc[0]
    bo = prod["match_by_operator"]
    eff = prod["by_operator"].set_index("operator_id")["random_effect"]
    corr = float(np.corrcoef(eff.reindex(bo["operator_id"]).to_numpy(), bo["mean"].to_numpy())[0, 1])
    ins = at["by_inspector"].set_index("inspector")
    strict = ins["reject_share"].idxmax()
    ar_b = b["average_range"]
    op_int = b["intervals"]["Operator"]

    body = "<h2 id='f1'>1. The bore gauge</h2>"
    body += (f"<p>The two-point bore gauge consumes {b['pct_tolerance']:.1f}% of the {b['tolerance']:.3f} mm tolerance on the F-21 critical bore, with {b['ndc']} distinct categories. "
             f"Reproducibility is the larger component at {comp.loc['Reproducibility', 'pct_tolerance']:.1f}% of tolerance against {comp.loc['Repeatability', 'pct_tolerance']:.1f}% for repeatability; "
             f"the operator term alone is {comp.loc['Operator', 'pct_tolerance']:.1f}%.</p>")
    body += components_table(b) + cap(f"Table 1. Bore gauge {b['header']['gauge'].split(' ')[0]}, gauge R&R variance components: {b['operators']} operators, {b['parts']} parts, {b['trials']} trials, "
                                      f"{b['readings']} readings, study {b['header']['study_id']} of {b['header']['study_date']}. Number of distinct categories = {b['ndc']}.")
    body += (f"<p>The study on file from 2022 gave 19.4% by the average and range method. The same method on this worksheet gives {ar_b['pct_tolerance']:.1f}%. "
             f"The method accounts for {round(b['pct_tolerance'], 1) - round(ar_b['pct_tolerance'], 1):.1f} points of the move from 19.4% to {b['pct_tolerance']:.0f}%.</p>")
    body += tbl(["", "Method", "GRR, % of tolerance", "ndc"],
                [["Study on file, GRR-2022-031 of 2022-11-08", "average and range", "19.4", "not stated"],
                 ["Bore gauge, this study", "ANOVA", f"{b['pct_tolerance']:.1f}", b["ndc"]],
                 ["Bore gauge, this study", "average and range", f"{ar_b['pct_tolerance']:.1f}", ar_b["ndc"]],
                 ["Air gauge, this study", "ANOVA", f"{a['pct_tolerance']:.1f}", a["ndc"]]])
    body += cap("Table 2. The gauge R&R on file and the two gauges in this study, on the same tolerance.")
    body += figure_gauges(r["gauge"])
    body += cap("Figure 1. Mean reading by part for each operator (top) and range of the three trials by operator with its mean and upper limit (bottom); bore gauge left, air gauge right, same ten parts.")

    body += "<h2 id='f2'>2. The air gauge on the same parts</h2>"
    body += (f"<p>On the same ten parts with the same three operators the air gauge consumes {a['pct_tolerance']:.1f}% of tolerance, with {a['ndc']} distinct categories. "
             f"Its operator term is {acomp.loc['Operator', 'pct_tolerance']:.1f}% of tolerance. The two studies give the same part-to-part sd, {b['part_sd']:.4f} and {a['part_sd']:.4f} mm.</p>")
    body += components_table(a) + cap(f"Table 3. Air gauge {a['header']['gauge'].split(' ')[0]}, gauge R&R variance components: {a['readings']} readings, study {a['header']['study_id']} of "
                                      f"{a['header']['study_date']}. Number of distinct categories = {a['ndc']}.")

    body += "<h2 id='f3'>3. Operator reproducibility in the study and in the production record</h2>"
    body += (f"<p>The study's three operators give an operator sd of {b['operator_sd']:.4f} mm with a 95% interval of {op_int[0]:.4f} to {op_int[1]:.4f}; "
             f"the {YEAR} production record ({int(y25.operators)} machinists, {int(y25.subgroups):,} subgroups) gives {y25.operator_sd:.4f} with an interval of "
             f"{y25.operator_sd_lower:.4f} to {y25.operator_sd_upper:.4f}. The {YEAR - 1} record gives {y24.operator_sd:.4f}.</p>")
    body += tbl(["", "Study", f"{YEAR - 1} record", f"{YEAR} record"],
                [["Operators", "3", int(y24.operators), int(y25.operators)],
                 ["Lots; subgroups; readings", f"1 part number; {b['readings']} readings", f"{int(y24.lots)}; {int(y24.subgroups):,}; {int(y24.readings):,}", f"{int(y25.lots)}; {int(y25.subgroups):,}; {int(y25.readings):,}"],
                 ["Operator sd, mm (95% interval)", f"{b['operator_sd']:.4f} ({op_int[0]:.4f} to {op_int[1]:.4f})", f"{y24.operator_sd:.4f} ({y24.operator_sd_lower:.4f} to {y24.operator_sd_upper:.4f})",
                  f"{y25.operator_sd:.4f} ({y25.operator_sd_lower:.4f} to {y25.operator_sd_upper:.4f})"],
                 ["Ratio to the study", "", f"{y24.ratio_to_study:.2f}", f"{y25.ratio_to_study:.2f}"]])
    body += cap("Table 4. Operator component of the bore gauge in the study and in the SPC record on the F-21 bore.")

    body += "<h2 id='f4'>4. Measurement share of the bore's apparent variance</h2>"
    body += (f"<p>{100 * y25.share_study:.0f}% of the bore's apparent variance in {YEAR} was measurement on the study's gauge variance, and {100 * y25.share_production:.0f}% with the production operator component "
             f"in place of the study's. The process sd net of measurement is {y25.process_sd_production:.4f} to {y25.process_sd_study:.4f} mm against an apparent {y25.total_sd:.4f} mm. "
             f"The capability of the bore is restated in S2.</p>")
    body += tbl(["", str(YEAR - 1), str(YEAR)],
                [["Readings", f"{int(y24.readings):,}", f"{int(y25.readings):,}"],
                 ["Apparent sd of all readings, mm", f"{y24.total_sd:.4f}", f"{y25.total_sd:.4f}"],
                 [f"Measurement share on the study's gauge variance (GRR sd {b['grr_sd']:.4f})", f"{100 * y24.share_study:.1f}%", f"{100 * y25.share_study:.1f}%"],
                 ["Measurement share with the production operator component", f"{100 * y24.share_production:.1f}%", f"{100 * y25.share_production:.1f}%"],
                 ["Process sd net of measurement, on the study's gauge variance, mm", f"{y24.process_sd_study:.4f}", f"{y25.process_sd_study:.4f}"],
                 ["Process sd net of measurement, with the production operator component, mm", f"{y24.process_sd_production:.4f}", f"{y25.process_sd_production:.4f}"]])
    body += cap("Table 5. Measurement share of the variance of the bore readings in the SPC record, by year.")

    body += "<h2 id='f5'>5. Bias and linearity from the calibration records</h2>"
    body += (f"<p>The calibration of {str(bad['done_date'])[:10]} found the bore gauge {bad['bias_mid_range']:.4f} mm high at mid-range, outside its {bad['tolerance']:.4f} mm tolerance, "
             f"with bias rising {bad['slope']:.5f} mm per mm of reference value (p = {bad["slope_p"]:.4f}). It was done {days_late} days past due, and {int(y25.past_due_subgroups)} subgroups on the bore "
             f"were taken in that window. The other four calibrations found at most {good['largest_error'].max():.4f} mm and no slope. "
             f"The air gauge stayed within {bias['air']['largest_error'].max():.4f} mm at every point in {len(bias['air'])} calibrations.</p>")
    body += tbl(["Done", "Due", "Result", "Bias at mid-range", "Largest error", "Slope, mm per mm (95% interval)", "p"],
                [[str(x.done_date)[:10], str(x.due_date)[:10], x.result, f"{x.bias_mid_range:.4f}", f"{x.largest_error:.4f}", f"{x.slope:.6f} ({x.slope_lower:.6f} to {x.slope_upper:.6f})", f"{x.slope_p:.3f}"]
                 for x in rec.itertuples()])
    body += cap(f"Table 6. Bore gauge as-found error at five calibrations, five check points each; tolerance {bad['tolerance']:.4f} mm.")
    body += tbl(["Reference value", "As-found error", "As-left error"], [[f"{x.reference_value:.2f}", f"{x.as_found_error:.4f}", f"{x.as_left_error:.4f}"] for x in bias["points"].itertuples()])
    body += cap(f"Table 7. Check points of the calibration of {str(bad['done_date'])[:10]}, as found and as left after adjustment.")
    body += figure_bias(bias)
    body += cap("Figure 2. As-found error against reference value at each calibration; the dashed line is the tolerance.")

    body += "<h2 id='f6'>6. Bias against the CMM</h2>"
    body += (f"<p>On {int(ma.pieces)} pieces measured by both, the bore gauge reads {ma['mean']:.4f} mm above the CMM ({ma.lower:.4f} to {ma.upper:.4f}). "
             f"In the past-due window it reads {late_row['mean']:.4f} mm above on {int(late_row.pieces)} pieces ({late_row.lower:.4f} to {late_row.upper:.4f}). "
             f"By machinist the bias runs from {bo['mean'].min():.4f} to {bo['mean'].max():+.4f} mm, and the two records agree on who reads high and who reads low (r = {corr:.2f} over {len(bo)} machinists).</p>")
    yrs = prod["match_by_year"].set_index("recorded_year")
    rows = [["All matched pieces", int(ma.pieces), f"{ma['mean']:+.4f} ({ma.lower:+.4f} to {ma.upper:+.4f})", f"{ma.sd:.4f}"]]
    for yy in yrs.index:
        v = yrs.loc[yy]
        rows.append([str(yy), int(v.pieces), f"{v['mean']:+.4f} ({v.lower:+.4f} to {v.upper:+.4f})", f"{v.sd:.4f}"])
    rows.append([f"Past due, {late_row['from']} to {late_row['to']}", int(late_row.pieces), f"{late_row['mean']:+.4f} ({late_row.lower:+.4f} to {late_row.upper:+.4f})", f"{late_row.sd:.4f}"])
    body += tbl(["Period", "Pieces", "Bore gauge minus CMM, mm (95% interval)", "sd"], rows) + cap("Table 8. Bore gauge reading minus CMM result on pieces matched by serial.")
    body += tbl(["Machinist", "In the study", "Subgroups", "Operator effect, SPC record", "Pieces matched", "Bore gauge minus CMM (95% interval)"],
                [[x.operator_id, "yes" if x.operator_id in study_ops else "", int(prod["by_operator"].set_index("operator_id").loc[x.operator_id, "count"]), f"{eff[x.operator_id]:+.4f}", int(x.pieces),
                  f"{x.mean:+.4f} ({x.lower:+.4f} to {x.upper:+.4f})"] for x in bo.itertuples()])
    body += cap(f"Table 9. Each F-21 machinist in {YEAR}: operator effect from the SPC record (mixed model) and bias to the CMM on matched pieces, mm.")
    body += figure_operators(prod, study_ops)
    body += cap("Figure 3. Operator effect from the SPC record against bore gauge minus CMM on matched pieces, one point per machinist with the 95% interval of the bias; the line is equality.")

    body += "<h2 id='f7'>7. Attribute agreement on the cosmetic surface</h2>"
    others = [i for i in ins.index if i != strict]
    body += (f"<p>All six calls agree on {at['between_matched']} of {at['parts']} parts ({100 * at['between']:.0f}%), and Fleiss' kappa is {at['kappa']:.2f} ({at['kappa_ci'][0]:.2f} to {at['kappa_ci'][1]:.2f}). "
             f"{strict} rejects {100 * ins.loc[strict, 'reject_share']:.0f}% of its calls against the reference's {100 * at['reference_reject_share']:.0f}% and repeats its own call on "
             f"{100 * ins.loc[strict, 'within']:.0f}% of parts: consistent and stricter. {others[0]} and {others[1]} repeat their own call on {100 * ins.loc[others[0], 'within']:.0f}% and "
             f"{100 * ins.loc[others[1], 'within']:.0f}% of parts.</p>")
    body += tbl(["Inspector", "Within inspector, matched of 50", "% (95% interval)", "Against the reference, both trials", "% (95% interval)", "Reject share of calls", "Rejects of reference-accept", "Accepts of reference-reject"],
                [[x.inspector, x.within_matched, f"{100 * x.within:.0f} ({100 * x.within_ci[0]:.0f} to {100 * x.within_ci[1]:.0f})", x.reference_matched,
                  f"{100 * x.reference:.0f} ({100 * x.reference_ci[0]:.0f} to {100 * x.reference_ci[1]:.0f})", f"{100 * x.reject_share:.0f}%", x.false_rejects, x.false_accepts] for x in at["by_inspector"].itertuples()])
    body += cap(f"Table 10. Attribute agreement by inspector: {at['parts']} parts, 2 trials, study {at['header']['study_id']} of {at['header']['study_date']}; the last two columns count calls of 100.")
    body += tbl(["Measure", "Matched of 50", "% (95% interval)"],
                [["Between inspectors: all six calls agree", at["between_matched"], f"{100 * at['between']:.0f} ({100 * at['between_ci'][0]:.0f} to {100 * at['between_ci'][1]:.0f})"],
                 ["All six calls match the reference", at["all_reference_matched"], f"{100 * at['all_reference']:.0f} ({100 * at['all_reference_ci'][0]:.0f} to {100 * at['all_reference_ci'][1]:.0f})"],
                 ["Fleiss' kappa, six calls per part", "", f"{at['kappa']:.2f} ({at['kappa_ci'][0]:.2f} to {at['kappa_ci'][1]:.2f})"]])
    body += cap("Table 11. Agreement between inspectors and with the reference.")
    body += figure_attribute(at)
    body += cap("Figure 4. Parts on which each inspector repeated the call, and parts on which both trials matched the reference.")

    body += "<h2 id='rec'>Recommendation</h2><ul>"
    body += (f"<li>Measure the F-21 critical bore on the air gauge in production and at final ({a['header']['gauge'].split(' ')[0]} or its equivalent), and withdraw the two-point bore gauge from critical characteristics.</li>"
             "<li>Restate the capability of the bore on the air gauge history once it accrues; S2 gives the restatement on the existing record meanwhile.</li>"
             "<li>Set the calibration interval of the bore gauge family so that the condition found in February 2025 is caught: the record shows a linearity slope at the first calibration done past due.</li>"
             f"<li>Define the cosmetic acceptance standard with boundary samples and repeat the attribute study against them, with the calls of {strict} as the reference candidate for the stricter standard "
             "if the customer's requirement supports it.</li></ul>")

    body += "<h2 id='method'>Method and data</h2>"
    body += (f"<p class='note'>Gauge R&R: AIAG MSA 4th edition, crossed study, ANOVA method; the operator by part interaction is kept when its p-value is 0.25 or below "
             f"(p = {b['interaction_p']:.3f} for the bore gauge, kept; p = {a['interaction_p']:.3f} for the air gauge, pooled). Study variation is 6 sd; at 5.15 sd the bore gauge is "
             f"{b['pct_tolerance_515']:.1f}% of tolerance and the air gauge {a['pct_tolerance_515']:.1f}%. Intervals on the standard deviations are Satterthwaite approximations. "
             "Operator component in the SPC record: mixed model on subgroup means with lot fixed and operator random, REML; interval from chi-square on operators minus one. "
             "Measurement share: gauge variance over the variance of all readings about nominal; the production figure replaces the study's operator variance with the record's. "
             "Bias and linearity: as-found error at the check points of each calibration, regressed on reference value. "
             f"Bias against the CMM: pieces matched on lot and serial, the bore gauge reading of the piece minus the CMM result; {int(ma.pieces)} pieces. "
             f"CMM features reach the characteristics master by the id in the report ({100 * prod['mapping'].set_index('map_method').loc['id in the report', 'share']:.1f}%) or the mapping table "
             f"({100 * prod['mapping'].set_index('map_method').loc['mapping table', 'share']:.1f}%); the rest are not in the master. "
             "Attribute agreement: Jeffreys intervals on the percentages; Fleiss' kappa over six calls per part, interval by bootstrap over parts (2,000 resamples). "
             "Readings are used as recorded.</p>")

    body += "<h2 id='app'>Appendix</h2>"
    body += anova_table(b) + cap("Table A1. Bore gauge, two-way ANOVA table with interaction.")
    body += anova_table(a) + cap("Table A2. Air gauge, two-way ANOVA table with interaction.")
    body += tbl(["Calibration", "Due", "Done", "Result", "Past due", "Bias at mid-range", "Mean bias", "Largest error", "Slope", "p", "R-sq"],
                [[x.calibration_id, str(x.due_date)[:10], str(x.done_date)[:10], x.result, "yes" if x.past_due else "", f"{x.bias_mid_range:.4f}", f"{x.mean_bias:.5f}", f"{x.largest_error:.4f}",
                  f"{x.slope:.6f}", f"{x.slope_p:.4f}", f"{x.r_squared:.3f}"] for x in rec.itertuples()])
    body += cap("Table A3. Bore gauge calibration records.")
    body += tbl(["Period", "Pieces", "Bore gauge minus CMM, mm (95% interval)", "sd"],
                [[f"{x['from']} to {x['to']}", int(x.pieces), f"{x['mean']:+.4f} ({x.lower:+.4f} to {x.upper:+.4f})", f"{x.sd:.4f}"] for _, x in mi.iterrows()])
    mv = prod["match_variance"]
    body += cap(f"Table A4. Bore gauge minus CMM between calibration events, with the window past due split out. The variance of the difference on the {mv['pieces']} pieces of {YEAR} is "
                f"{100 * mv['share']:.1f}% of the year's variance of readings; it includes the CMM's own error.")
    body += tbl(["How mapped", "Features", "Share"], [[x.map_method, f"{x.features:,}", f"{100 * x.share:.1f}%"] for x in prod["mapping"].itertuples()])
    body += cap("Table A5. CMM features by how they reach the characteristics master.")

    toc = [("f1", "Bore gauge"), ("f2", "Air gauge"), ("f3", "Operators"), ("f4", "Measurement share"), ("f5", "Bias and linearity"), ("f6", "Bias to the CMM"), ("f7", "Attribute agreement"),
           ("rec", "Recommendation"), ("method", "Method"), ("app", "Appendix")]
    html = S.shell("S1. Measurement system analysis", "Study report", HEADER, body, toc)
    out = S.DOCS / "reports"
    out.mkdir(parents=True, exist_ok=True)
    (out / "s1_msa.html").write_text(html, encoding="utf8", newline="\n")
    return out / "s1_msa.html"


if __name__ == "__main__":
    print(build())
