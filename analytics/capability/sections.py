"""Process capability.

Built by its report under analytics.reports.
"""
import warnings

import numpy as np
import pandas as pd

from analytics import stats
from analytics.capability.study import R5, YEAR, compute, history
from analytics.style import style as S

HEADER = ("Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant. January 2024 to December 2025; lengths in mm.<br>"
          "Sources: SPC module, capability reports, characteristics master, NCRs, ERP lots.<br>"
          "PPAP element 10, initial process studies; AS9102 Form 3 supporting data.")
CATS = ["capable", "marginal", "not capable"]


def tbl(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f'<td class="{"num" if i else ""}">{v}</td>' for i, v in enumerate(r)) + "</tr>" for r in rows)
    return f'<table class="data"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def cap(text):
    return f'<div class="caption">{text}</div>'


def figure_interval(m):
    c = m[m["reported_category"] == "capable"].sort_values(["cpk_reported", "characteristic_id"]).reset_index(drop=True)
    f, ax = S.fig(h=4.6, w=9.6)
    x = np.arange(len(c))
    inside = c["within_interval_of_133"].to_numpy()
    ax.vlines(x, S.sig(c["cpk_reported"] - c["halfwidth"]), S.sig(c["cpk_reported"] + c["halfwidth"]), color=np.where(inside, S.AMBER, S.LIGHT_BLUE), lw=2)
    ax.plot(x, S.sig(c["cpk_reported"]), "o", ms=4, color=S.BRAND_BLUE, label="Reported Cpk with the 95% interval of a 25-subgroup report")
    low = np.minimum(c["cpk"], c["ppk"])
    ok = c["restated_capable"].to_numpy()
    ax.plot(x[ok], S.sig(low[ok]), "D", ms=4, color=S.GREEN, label="Restated (lower of Cpk and Ppk), capable")
    ax.plot(x[~ok], S.sig(low[~ok]), "D", ms=5, color=S.RED, label="Restated, not capable")
    bad = np.flatnonzero(~ok)
    for j, i in enumerate(bad):
        crowded = j + 1 < len(bad) and bad[j + 1] - i < 2
        ax.annotate(str(j + 1), (x[i], float(S.sig(low[i]))), textcoords="offset points", xytext=(-12, -9) if crowded else (6, -9), fontsize=8, color=S.RED)
    ax.axhline(1.33, color=S.DARK_GREY, lw=1, ls="--")
    ax.plot([], [], color=S.AMBER, lw=2, label="Interval reaches below 1.33")
    ax.set_xticks([])
    ax.set_xlabel(f"The {len(c)} critical characteristics reported capable, in order of the reported value")
    ax.set_ylabel("Cpk")
    ax.set_ylim(0.6, min(4.2, float((c["cpk_reported"] + c["halfwidth"]).max()) + 0.1))
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_title("Reported capable calls against the restatement")
    f.tight_layout()
    return S.save_conformed(f, "capability_fig1_reported_against_restated", "Reported Cpk with its sampling interval against the restated value for each reported capable call")


def figure_medical(t):
    f, ax = S.fig(h=2.9, w=7.4, grid="x")
    y = np.arange(len(t))[::-1]
    ax.errorbar(S.sig(t["cpk"]), y, xerr=[S.sig(t["cpk"] - t["lower"]), S.sig(t["upper"] - t["cpk"])], fmt="o", ms=7, color=S.BRAND_BLUE, ecolor=S.GREY, capsize=3)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{b} ({n:,} readings)" for b, n in zip(t["basis"], t["readings"])])
    ax.axvline(1.33, color=S.DARK_GREY, lw=1, ls="--")
    ax.set_xlabel("Cpk with 95% interval")
    ax.set_title("The medical bore three ways")
    f.tight_layout()
    return S.save_conformed(f, "capability_fig2_medical_bore", "Cpk of the medical bore on the shop's 25 readings, on subgroups and on every piece")


def figure_charts(study):
    f, ax = S.fig(h=6.6, w=9.6, ncols=2, nrows=2)
    for a, name in zip(ax.ravel(), ["turned diameter", "runout", "milled length", "Swiss diameter"]):
        g = history(study[name]["characteristic_id"])
        x = g[R5].to_numpy()
        means, sigma = x.mean(axis=1), np.sqrt(x.var(axis=1, ddof=1).mean()) / np.sqrt(5)
        centre = means.mean()
        r1, r2, r3, r4 = stats.western_electric(means, centre, sigma)
        sig_ = r1 | r2 | r3 | r4
        i = np.arange(1, len(means) + 1)
        a.plot(i, S.sig(means), lw=0.8, color=S.ACCENT)
        a.plot(i[sig_], S.sig(means[sig_]), "o", ms=3, color=S.RED)
        for k, c_, ls in ((0, S.DARK_GREY, "-"), (3, S.RED, "--"), (-3, S.RED, "--")):
            a.axhline(float(S.sig(centre + k * sigma)), color=c_, lw=0.9, ls=ls)
        a.set_title(f"{name[0].upper() + name[1:]}: {int(sig_.sum())} of {len(means)} points signal")
        a.ticklabel_format(axis="y", useOffset=False)
        a.set_xlabel(f"Subgroup, {YEAR}")
        a.set_ylabel("Subgroup mean, mm")
    f.tight_layout()
    return S.save_conformed(f, "capability_fig4_control_charts", "Subgroup means of the four named characteristics with centre, three-sigma limits and the points signalling rules 1 to 4")


def figure_sawtooth(study):
    d = study["Swiss diameter"]
    sw = d["swiss"]
    g = history(d["characteristic_id"])
    g = g[g["piece_no"] <= 3 * sw["reset_interval"]]
    f, ax = S.fig(h=3.6, w=8.2)
    ax.plot(g["piece_no"], S.sig(g["subgroup_mean"]), "o", ms=3.5, color=S.ACCENT, label=f"Subgroup means, {g['job_id'].nunique()} lots")
    centre = (d["capability"]["usl"] + d["capability"]["lsl"]) / 2
    p = np.arange(1, 3 * sw["reset_interval"] + 1)
    ax.plot(p, S.sig(centre + sw["start_offset"] + sw["slope_per_piece"] * ((p - 3) % sw["reset_interval"])), color=S.BRAND_BLUE, lw=1.4, label="Fitted drift and reset")
    for lim in (d["capability"]["usl"], d["capability"]["lsl"]):
        ax.axhline(lim, color=S.RED, lw=0.9, ls="--")
    ax.set_xlabel("Piece number in the lot")
    ax.set_ylabel("mm")
    ax.set_title("Swiss diameter over three tool lives")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    f.tight_layout()
    return S.save_conformed(f, "capability_fig3_swiss_sawtooth", "Subgroup means of the Swiss diameter against piece number over three tool lives with the fitted drift")


def figure_pileup(h):
    f, ax = S.fig(h=3.6, w=8.2)
    v = h[h["step"] >= -4]
    x = np.arange(len(v))
    ax.bar(x - 0.2, S.sig(v["observed"]), width=0.4, color=S.BRAND_BLUE, label="Recorded")
    ax.bar(x + 0.2, S.sig(v["expected"]), width=0.4, color=S.LIGHT_BLUE, label="Expected from the fitted distribution")
    ax.axvline(float(np.flatnonzero(v["step"].to_numpy() == 0)[0]) + 0.5, color=S.RED, lw=1, ls="--")
    ax.set_xticks(x)
    ax.set_xticklabels([("last step inside" if s == 0 else f"{-s} inside" if s < 0 else f"{s} outside") for s in v["step"]], fontsize=9)
    ax.set_yscale("log")
    ax.set_ylabel("Readings (log scale)")
    ax.set_title("Readings by resolution step at the limit")
    ax.legend(frameon=False)
    f.tight_layout()
    return S.save_conformed(f, "capability_fig5_pile_up", "Recorded and expected readings by resolution step either side of the limit")


def build():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = compute()
    st_, m, res, fl = r["study"], r["compared"], r["restated"], r["flinching"]
    capc = m[m["reported_category"] == "capable"]
    marg = m[m["reported_category"] == "marginal"]
    changed = capc[~capc["restated_capable"]]
    ct = pd.crosstab(m["reported_category"], m["restated_category"]).reindex(index=CATS, columns=CATS, fill_value=0)
    counts = res["restated_category"].value_counts().reindex(CATS, fill_value=0)
    five = capc[capc["subgroup_size"] == 5]
    causes = changed["cause"].value_counts()
    cause_text = ", ".join(f"{causes[k]} {label}" for k, label in (("drift", "drift within the tool life"), ("bounded", "are bounded characteristics computed as normal"),
                                                                  ("shifts", "shifts between subgroups"), ("selection", "a selection that leaves out subgroups"),
                                                                  ("sampling", "the sampling interval alone")) if k in causes.index)

    body = "<h2 id='f1'>1. The restatement across the critical characteristics</h2>"
    body += (f"<p>Of {len(capc)} critical characteristics the shop reports as capable, {len(changed)} are not capable on the {YEAR} record; of {len(marg)} reported marginal, "
             f"{int(marg['restated_capable'].sum())} are capable. Of the {len(res)} critical characteristics on SPC, {counts['capable']} are capable, {counts['marginal']} marginal and "
             f"{counts['not capable']} not capable. The nine: {cause_text}.</p>")
    body += tbl([f"Reported, latest {YEAR} report", "Restated capable", "Restated marginal", "Restated not capable", "Total"],
                [[k, ct.loc[k, "capable"], ct.loc[k, "marginal"], ct.loc[k, "not capable"], ct.loc[k].sum()] for k in CATS])
    body += cap(f"Table 1. The {len(m)} critical characteristics with a capability report in {YEAR}: category as reported (Cpk at or above 1.33 capable, from 1.0 marginal) against the restated category.")
    changed = changed.sort_values(["cpk_reported", "characteristic_id"]).reset_index(drop=True)
    body += tbl(["No.", "Characteristic", "Type", "Reported Cpk", "Restated Cpk", "Restated Ppk", "Method", "Cause", "Points signalling"],
                [[x.Index + 1, x.characteristic_id, x.characteristic_type, f"{x.cpk_reported:.2f}", f"{x.cpk:.2f}", f"{x.ppk:.2f}",
                  x.method + (f" ({x.fitted_distribution})" if isinstance(x.fitted_distribution, str) else ""), x.cause, f"{100 * x.rule_share:.0f}%"] for x in changed.itertuples()])
    body += cap("Table 2. The reported capable calls that are not capable when restated, numbered as in the chart of reported against restated capability.")

    body += "<h2 id='f2'>2. The sampling interval of a 25-subgroup report</h2>"
    body += (f"<p>A Cpk from 25 subgroups carries a 95% interval of {five['halfwidth'].min():.2f} to {five['halfwidth'].max():.2f} either side on the reported capable calls. "
             f"{int(capc['within_interval_of_133'].sum())} of the {len(capc)} capable calls have a reported value within that interval of 1.33.</p>")
    body += figure_interval(m)
    body += cap("Figure 1. Each reported capable call with the interval of its 25-subgroup report and the restated value; the nine not capable are numbered as in Table 2.")

    mb = st_["medical bore"]
    t3 = mb["three_ways"]["table"]
    body += "<h2 id='f3'>3. The medical bore three ways</h2>"
    body += (f"<p>The medical bore gives Cpk {t3['cpk'].iloc[0]:.2f} on the shop's 25 readings, {t3['cpk'].iloc[1]:.2f} on the year's subgroups and {t3['cpk'].iloc[2]:.2f} on every piece. "
             f"The 25-reading interval runs from {t3['lower'].iloc[0]:.2f} to {t3['upper'].iloc[0]:.2f}; every piece gives {t3['lower'].iloc[2]:.2f} to {t3['upper'].iloc[2]:.2f}. "
             f"The record holds {mb['three_ways']['readings']:,} readings for {mb['three_ways']['pieces_made']:,} pieces made.</p>")
    body += tbl(["Basis", "Readings", "Cpk (95% interval)", "Ppk"],
                [[x.basis + (f", {x.run}" if x.run else ""), f"{x.readings:,}", f"{x.cpk:.2f} ({x.lower:.2f} to {x.upper:.2f})", f"{x.ppk:.2f}"] for x in t3.itertuples()])
    body += cap(f"Table 3. Bore {mb['characteristic_id']} on part {mb['part_id']}, {YEAR}.")
    body += figure_medical(t3) + cap("Figure 2. The three estimates with their 95% intervals; the dashed line is 1.33.")

    def cap_rows():
        rows = []
        for name, d in st_.items():
            c = d["capability"]
            rows.append([f"{name[0].upper() + name[1:]}, {d['characteristic_id']}", f"{c['lsl']:.3f}" if np.isfinite(c["lsl"]) else "", f"{c['usl']:.3f}", f"{c['readings']:,}", f"{c['mean']:.4f}",
                         f"{c['sigma_within']:.5f}", f"{c['sigma_overall']:.5f}", f"{c['cp']:.2f}" if np.isfinite(c["cp"]) else "", f"{c['cpk']:.2f} ({c['cpk_lower']:.2f} to {c['cpk_upper']:.2f})",
                         f"{c['pp']:.2f}" if np.isfinite(c["pp"]) else "", f"{c['ppk']:.2f} ({c['ppk_lower']:.2f} to {c['ppk_upper']:.2f})", f"{c['ppm_within']:,.0f}", f"{c['ppm_overall']:,.0f}",
                         f"{d['reported']['cpk']:.2f}"])
        return rows
    td, ro, ln, sw = st_["turned diameter"], st_["runout"], st_["milled length"], st_["Swiss diameter"]
    body += "<h2 id='f4'>4. The turned diameter</h2>"
    body += (f"<p>The turned diameter is stable and capable: Cpk {td['capability']['cpk']:.2f} ({td['capability']['cpk_lower']:.2f} to {td['capability']['cpk_upper']:.2f}) and Ppk "
             f"{td['capability']['ppk']:.2f} on {td['capability']['subgroups']} subgroups, against {td['reported']['cpk']:.2f} on the shop's latest report. "
             f"{td['stability']['any_rule']} of {td['stability']['points']} points signal a rule.</p>")
    body += tbl(["Characteristic", "LSL", "USL", "Sample N", "Sample mean", "StDev (Within)", "StDev (Overall)", "Cp", "Cpk (95%)", "Pp", "Ppk (95%)", "PPM within", "PPM overall", "Reported Cpk"], cap_rows())
    body += cap(f"Table 4. Capability summary of the five study characteristics, {YEAR}; the runout row is the normal calculation against the upper limit, and its fit is Table 5.")

    f = ro["fit"]
    body += "<h2 id='f5'>5. The runout</h2>"
    body += (f"<p>The shop reports the runout at {ro['reported']['cpk']:.2f}; it is {f['percentile_ppk']:.2f} ({f['percentile_lower']:.2f} to {f['percentile_upper']:.2f}) by the percentile method on the fitted "
             f"{f['distribution']}. The module's figure comes from zero entered as the lower limit in the master: the lower side then governs at the mean over three sd. "
             f"The distribution is barely skewed ({f['skewness']:.2f}), so the normal calculation against the upper limit alone agrees at {f['module_upper_only']['cpk']:.2f}; Box-Cox gives {f['boxcox_ppk']:.2f}.</p>")
    body += tbl(["Calculation", "Index"],
                [["Shop's latest report (module, 25 subgroups)", f"{ro['reported']['cpk']:.2f}"],
                 [f"Module's calculation on all {YEAR} subgroups, limits as in the master (0 to {ro['capability']['usl']:.3f})", f"{f['module']['cpk']:.2f}"],
                 ["Normal calculation against the upper limit only", f"{f['module_upper_only']['cpk']:.2f}"],
                 [f"Percentile method on the fitted {f['distribution']} (95% interval)", f"{f['percentile_ppk']:.2f} ({f['percentile_lower']:.2f} to {f['percentile_upper']:.2f})"],
                 [f"Box-Cox, lambda {f['boxcox_lambda']:.2f}", f"{f['boxcox_ppk']:.2f}"]])
    body += cap(f"Table 5. Runout {ro['characteristic_id']}: the module's calculation and the alternatives, {f['readings']:,} readings.")

    L, c = ln["length"], ln["capability"]
    hrs = L["hours"].set_index("on_characteristic")
    on = hrs.loc[True] if True in hrs.index else pd.Series(dict(ncrs=0, rework=0.0, sorting=0.0, reinspection=0.0))
    tot = hrs.sum()
    body += "<h2 id='f6'>6. The milled length</h2>"
    body += (f"<p>The milled length is stable and not capable: Cpk {c['cpk']:.2f} ({c['cpk_lower']:.2f} to {c['cpk_upper']:.2f}), centred, with {ln['stability']['any_rule']} of {ln['stability']['points']} points signalling. "
             f"The process holds {L['width_133']:.2f} mm at 1.33 and {L['width_167']:.2f} mm at 1.67 against the drawing's {L['drawing_width']:.2f} mm. "
             f"{int(on['ncrs'])} of the {L['ncrs']} NCRs on the part cite the length; they carry {on['rework']:.0f} of the part's {tot['rework']:.0f} booked rework hours and "
             f"{on['sorting']:.0f} of its {tot['sorting']:.0f} sorting hours.</p>")

    s, c = sw["swiss"], sw["capability"]
    body += "<h2 id='f7'>7. The Swiss diameter</h2>"
    body += (f"<p>The Swiss diameter is {c['cpk']:.2f} within subgroups and {c['ppk']:.2f} overall. It drifts {100 * s['slope_per_piece']:.4f} mm per 100 pieces and resets every {s['reset_interval']} pieces, "
             f"{s['drift_range_sigma']:.1f} within sd over a tool life; {sw['stability']['any_rule']} of {sw['stability']['points']} points signal. "
             f"A tool change at {s['reset_interval'] // 2} pieces gives Ppk {s['ppk_at_half']:.2f}; {s['interval_for_133']} pieces is the longest interval that holds 1.33.</p>")
    body += figure_sawtooth(st_) + cap("Figure 3. Subgroup means against piece number in the lot over the first three tool lives, with the fitted drift and reset; dashed lines are the limits.")

    b = r["bores"]["table"]
    ordinary = res[res["restated_capable"] & ~res["characteristic_id"].isin(b["characteristic_id"])]
    body += "<h2 id='f8'>8. The F-21 bores and the measurement system</h2>"
    body += (f"<p>The six F-21 bores on the two-point bore gauge show {100 * b['signal_share_recorded'].min():.0f} to {100 * b['signal_share_recorded'].max():.0f}% of points signalling and Ppk "
             f"{(b['cpk_recorded'] - b['ppk_recorded']).min():.1f} to {(b['cpk_recorded'] - b['ppk_recorded']).max():.1f} below Cpk; the other capable characteristics have a median of "
             f"{100 * ordinary['rule_share'].median():.0f}% signalling. With the operator effects of [[S:first]] removed from the readings, signalling falls to "
             f"{100 * b['signal_share_net'].min():.0f} to {100 * b['signal_share_net'].max():.0f}% and Ppk rises from {b['ppk_recorded'].min():.2f} to {b['ppk_recorded'].max():.2f} as recorded to "
             f"{b['ppk_net'].min():.2f} to {b['ppk_net'].max():.2f}, against Cpk of {b['cpk_net'].min():.2f} to {b['cpk_net'].max():.2f}. "
             f"The operators account for most of the instability on these bores, not all of it.</p>")
    body += tbl(["Bore", "Subgroups", "Points signalling: as recorded", "net of operators", "Cpk: as recorded", "net", "Ppk (95%): as recorded", "net"],
                [[x.characteristic_id, x.subgroups, f"{100 * x.signal_share_recorded:.0f}%", f"{100 * x.signal_share_net:.0f}%", f"{x.cpk_recorded:.2f}", f"{x.cpk_net:.2f}",
                  f"{x.ppk_recorded:.2f} ({x.ppk_lower_recorded:.2f} to {x.ppk_upper_recorded:.2f})", f"{x.ppk_net:.2f} ({x.ppk_lower_net:.2f} to {x.ppk_upper_net:.2f})"] for x in b.itertuples()])
    body += cap(f"Table 6. The F-21 bores in {YEAR}, as recorded and with each machinist's effect from [[S:first]] (mixed model, {r['bores']['operators']} machinists) removed from the readings.")

    al = r["alarms"]
    at = al["by_text"]
    ok_ = int(at[(at["acknowledgement_text"] == "checked ok")]["alarms"].sum())
    blank = int(at[(at["acknowledgement_text"] == "") & at["acknowledged"]]["alarms"].sum())
    notack = int(at[~at["acknowledged"]]["alarms"].sum())
    body += "<h2 id='f9'>9. Stability as the module reports it</h2>"
    body += (f"<p>The module raised an alarm on {al['raised']:,} of {al['subgroups']:,} five-reading subgroups in {YEAR} ({100 * al['raised'] / al['subgroups']:.1f}%), on rules 1 and 2 against the limits in the master. "
             f"{ok_:,} were acknowledged \"checked ok\" ({100 * ok_ / al['raised']:.0f}%), {blank:,} with no text and {notack:,} not at all. "
             f"On the study characteristics the rules find what the module raises and more: rules 3 and 4 are not raised.</p>")
    body += tbl(["Characteristic", "Points", "Rule 1", "Rule 2", "Rule 3", "Rule 4", "Signalling any rule", "Module alarms raised", "Acknowledged"],
                [[f"{name[0].upper() + name[1:]}", d["stability"]["points"], d["stability"]["rule_1"], d["stability"]["rule_2"], d["stability"]["rule_3"], d["stability"]["rule_4"],
                  f"{d['stability']['any_rule']} ({100 * d['stability']['share_any']:.1f}%)", d["stability"]["module_raised"], d["stability"]["module_acknowledged"]] for name, d in st_.items()])
    body += cap(f"Table 7. Western Electric rules 1 to 4 on the {YEAR} record against the alarms the module raised.")
    body += figure_charts(st_) + cap("Figure 4. Subgroup means of the four named characteristics with centre and three-sigma limits from the data; points signalling a rule are marked.")

    bb = fl["by_band"].set_index("band")
    low = bb.loc["index below 1.0"]
    body += "<h2 id='f10'>10. The flinching pile-up</h2>"
    body += (f"<p>On the {int(low['characteristics'])} hand-gauge characteristics with an index below 1.0, {int(low['observed_inside'])} readings sit in the last resolution step inside a limit against "
             f"{low['expected_inside']:.0f} expected, and {int(low['observed_outside'])} in the two steps outside against {low['expected_outside']:.0f}. "
             f"Readings are used as recorded in every calculation of this study.</p>")
    body += tbl(["Index of the characteristic", "Characteristics", "Readings", "Last step inside: recorded", "expected", "Two steps outside: recorded", "expected"],
                [[x.band, x.characteristics, f"{x.readings:,}", x.observed_inside, f"{x.expected_inside:.0f}", x.observed_outside, f"{x.expected_outside:.0f}"] for x in fl["by_band"].itertuples()])
    body += cap("Table 8. Readings at the limit on hand gauges by the index of the characteristic, January 2024 to December 2025.")
    body += figure_pileup(fl["histogram"]) + cap("Figure 5. Recorded and expected readings by resolution step either side of the limit (dashed line), characteristics with an index below 1.0.")

    body += "<h2 id='rec'>Recommendation</h2><ul>"
    body += ("<li>Restate capability to customers from the full history with the pooled within-subgroup sd, a stability check printed with every report, and the percentile method for bounded characteristics.</li>"
             f"<li>Correct the lower limit of the runout {ro['characteristic_id']} in the master.</li>"
             "<li>Put the F-21 bores on the air gauge ([[S:first]]) before any restatement to the customer.</li>"
             f"<li>Set the tool change on the Swiss diameter at {s['reset_interval'] // 2} pieces; {s['interval_for_133']} pieces is the limit.</li>"
             f"<li>The milled length holds {L['width_133']:.2f} mm at 1.33 against the drawing's {L['drawing_width']:.2f} mm: take it to the customer as a tolerance request or to engineering as a process change, "
             "with the sorting and rework hours as the cost ([[R:supplier]]).</li></ul>")

    body += "<h2 id='method'>Method and data</h2>"
    body += (f"<p class='note'>Capability: AIAG SPC 2nd edition. Cp and Cpk from the pooled within-subgroup sd (mean moving range over 1.128 where every piece is measured); Pp and Ppk from the sd of all readings; "
             f"all {YEAR} subgroups. Cpk interval by Bissell's approximation with the degrees of freedom of the sigma estimate; Ppk and percentile-index intervals by bootstrap over subgroups (1,000 and 500 resamples). "
             "Bounded characteristics (runout, flatness, position, Ra): folded normal, lognormal and Weibull fitted to the readings, the best by Anderson-Darling, index from the 50th and 99.865th percentiles "
             "against the upper limit; Box-Cox beside. Restated category: the lower of Cpk and Ppk at or above 1.33 capable, from 1.0 marginal. "
             "Stability: Western Electric rules 1 to 4 on subgroup means with centre and sigma from the year's data. "
             "Sampling interval of a report: Bissell's interval at 125 readings and 100 degrees of freedom (25 readings and 24 for the medical bore). "
             "Medical bore subgroups: five consecutive pieces every 50 pieces of each lot, a construction from the every-piece record. "
             "F-21 bores net of operators: each reading less the machinist's effect from the mixed model of [[S:first]]. "
             "Flinching: expected counts from the distribution fitted to each characteristic (normal; folded normal for runout and flatness) in the last resolution step inside each limit and the two steps outside; "
             "digit preference is not modelled. Readings are used as recorded.</p>")

    body += "<h2 id='app'>Appendix</h2>"
    body += tbl(["Characteristic", "Type", "Reported Cpk", "Half-width", "Reported", "Within interval of 1.33", "Restated Cpk", "Restated Ppk", "Method", "Restated", "Subgroups", "Signalling"],
                [[x.characteristic_id, x.characteristic_type, f"{x.cpk_reported:.2f}", f"{x.halfwidth:.2f}", x.reported_category, "yes" if x.within_interval_of_133 else "", f"{x.cpk:.2f}", f"{x.ppk:.2f}",
                  x.method + (f" ({x.fitted_distribution})" if isinstance(x.fitted_distribution, str) else ""), x.restated_category, x.subgroups, f"{100 * x.rule_share:.0f}%"]
                 for x in m.sort_values(["cpk_reported", "characteristic_id"]).itertuples()])
    body += cap(f"Table A1. The {len(m)} critical characteristics with a {YEAR} report: reported against restated.")
    body += tbl(["Characteristic", "Lots", "Points", "Rule 1", "Rule 2", "Rule 3", "Rule 4", "Any rule", "Range chart out", "Module rule 1; rule 2", "Acknowledged", f"Any rule, {YEAR - 1}"],
                [[f"{name}, {d['characteristic_id']}", d["stability"]["lots"], d["stability"]["points"], d["stability"]["rule_1"], d["stability"]["rule_2"], d["stability"]["rule_3"], d["stability"]["rule_4"],
                  f"{d['stability']['any_rule']} ({100 * d['stability']['share_any']:.1f}%)", d["stability"]["range_chart_out"], f"{d['stability']['module_rule_1']}; {d['stability']['module_rule_2']}",
                  d["stability"]["module_acknowledged"], f"{d['stability_2024']['any_rule']} ({100 * d['stability_2024']['share_any']:.1f}%)"] for name, d in st_.items()])
    body += cap("Table A2. Stability of the five study characteristics.")
    body += tbl(["Cited", "Disposition", "NCRs", "Rework hours booked", "Sorting hours"],
                [[{"D02": "the length", "D03": "a bore", "D11": "cosmetic"}.get(x.defect_code, x.defect_code), x.disposition, x.ncrs, f"{x.rework:.1f}", f"{x.sorting:.1f}"] for x in L["by_code"].itertuples()])
    body += cap(f"Table A3. NCRs on part {L['part']} in the window; drawing tolerance {L['drawing_width']:.3f} mm, {L['width_133']:.3f} mm held at 1.33, {L['width_167']:.3f} mm at 1.67.")
    body += tbl(["", "Value"],
                [["Drift slope, mm per piece (95% interval)", f"{s['slope_per_piece']:.7f} ({s['slope_lower']:.7f} to {s['slope_upper']:.7f})"], ["Reset interval, pieces (R-sq of the fit)", f"{s['reset_interval']} ({s['r_squared']:.2f})"],
                 ["Tool change notes; median pieces between notes", f"{s['tool_change_notes']}; {s['median_gap_between_notes']:.0f}"], ["Drift over a tool life, mm", f"{s['drift_range']:.4f}"],
                 ["Offset at reset against nominal, mm", f"{s['start_offset']:+.4f}"], ["Ppk at the present interval, from the fit", f"{s['ppk_at_interval']:.2f}"],
                 [f"Ppk at {s['reset_interval'] // 2} pieces", f"{s['ppk_at_half']:.2f}"], ["Longest interval with Ppk at or above 1.33, pieces", s["interval_for_133"]]])
    body += cap(f"Table A4. Swiss diameter {sw['characteristic_id']}: drift and reset.")
    bg = fl["by_gauge"]
    body += tbl(["Gauge type", "Characteristics", "Readings", "Last step inside: recorded", "expected", "Two steps outside: recorded", "expected"],
                [[x.gauge_type, x.characteristics, f"{x.readings:,}", x.observed_inside, f"{x.expected_inside:.0f}", x.observed_outside, f"{x.expected_outside:.0f}"] for x in bg.itertuples()]
                + [["All hand gauges", bg["characteristics"].sum(), f"{bg['readings'].sum():,}", bg["observed_inside"].sum(), f"{bg['expected_inside'].sum():.0f}", bg["observed_outside"].sum(), f"{bg['expected_outside'].sum():.0f}"]])
    body += cap("Table A5. Readings at the limit by gauge type.")
    body += tbl(["Distribution", "Anderson-Darling", "0.135th percentile", "Median", "99.865th percentile"], [[x.distribution, f"{x.ad:.2f}", f"{x.p0135:.4f}", f"{x.median:.4f}", f"{x.p99865:.4f}"] for x in f["fits"].itertuples()])
    body += cap("Table A6. Distributions fitted to the runout readings.")

    toc = [("f1", "Restatement"), ("f2", "Sampling interval"), ("f3", "Medical bore"), ("f4", "Turned diameter"), ("f5", "Runout"), ("f6", "Milled length"), ("f7", "Swiss diameter"),
           ("f8", "F-21 bores"), ("f9", "Stability"), ("f10", "Pile-up"), ("rec", "Recommendation"), ("method", "Method"), ("app", "Appendix")]
    return {"body": body, "toc": toc[:-3], "meta": HEADER}
