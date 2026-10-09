"""S5 report and A3: designed experiment on surface finish.

Usage: python -m analytics.s5_doe.report
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats as st

from analytics.s5_doe.s5_doe import ALIAS, LABEL, compute
from analytics.style import style as S

HEADER = ("Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant. January 2024 to December 2025; Ra in micrometres.<br>"
          "Sources: designed experiment worksheet, SPC module, characteristics master, ERP lots.<br>"
          "PPAP element 11 supporting data; DMAIC project with A3.")


def tbl(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f'<td class="{"num" if i else ""}">{v}</td>' for i, v in enumerate(r)) + "</tr>" for r in rows)
    return f'<table class="data"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def cap(text):
    return f'<div class="caption">{text}</div>'


def day(t):
    t = pd.Timestamp(t)
    return f"{t.day} {t.strftime('%B %Y')}"


def effects_rows(t):
    return [[LABEL.get(x.term, x.term), "" if x.effect != x.effect else f"{x.effect:+.4f}", f"{x.coef:+.4f}", f"{x.se:.4f}", f"{x.t:.2f}", "0.000" if x.p < 0.0005 else f"{x.p:.3f}", ALIAS.get(x.term, "")] for x in t.itertuples()]


def figure_half_normal(hn, keep):
    f, ax = S.fig(h=3.8, w=6.6)
    sig_ = hn["term"].isin(keep)
    ax.plot(S.sig(hn.loc[~sig_, "abs_effect"]), S.sig(hn.loc[~sig_, "quantile"]), "o", ms=6, color=S.ACCENT, label="Not significant at 0.05")
    ax.plot(S.sig(hn.loc[sig_, "abs_effect"]), S.sig(hn.loc[sig_, "quantile"]), "s", ms=7, color=S.RED, label="Significant at 0.05")
    small = hn[~sig_]
    slope = float((small["quantile"] * small["abs_effect"]).sum() / (small["abs_effect"] ** 2).sum())
    ax.plot([0, float(hn["abs_effect"].max())], [0, float(S.sig(slope * hn["abs_effect"].max()))], color="#CCCCCC", lw=1)
    for x in hn[sig_].itertuples():
        ax.annotate(LABEL[x.term], (x.abs_effect, x.quantile), textcoords="offset points", xytext=(-8, 6), ha="right", fontsize=9, color=S.DARK_GREY)
    ax.set_ylim(0, 2.2)
    ax.set_xlabel("Absolute effect on Ra, µm")
    ax.set_ylabel("Half-normal quantile")
    ax.set_title("Half-normal plot of the effects")
    ax.legend(frameon=False, loc="lower right")
    f.tight_layout()
    return S.save(f, "s5_fig1_half_normal", "Half-normal plot of the seven effects of the half fraction")


def figure_effects(runs, lv, name, h=3.6):
    f, ax = S.fig(h=h, w=9.6, ncols=2, gridspec_kw=dict(width_ratios=[1.5, 1]))
    xs = 0
    ticks, labels = [], []
    for code, lab in (("A", "Feed"), ("B", "Speed"), ("C", "Nose radius"), ("D", "Coolant")):
        m = runs.groupby(code)["ra_um"].mean()
        ax[0].plot([xs, xs + 1], S.sig([m[-1], m[1]]), marker="o", color=S.BRAND_BLUE, lw=1.6)
        ticks += [xs, xs + 1]
        labels += [f"{lv[code][0]:g}", f"{lv[code][1]:g}"]
        ax[0].annotate(lab, (xs + 0.5, 0.02), xycoords=("data", "axes fraction"), ha="center", fontsize=9, color=S.DARK_GREY)
        xs += 2
    ax[0].axhline(float(runs["ra_um"].mean()), color="#DDDDDD", lw=1)
    ax[0].set_xticks(ticks)
    ax[0].set_xticklabels(labels, fontsize=9)
    ax[0].set_ylabel("Mean Ra, µm")
    ax[0].set_title("Main effects")
    for c_, color in ((-1, S.RED), (1, S.GREEN)):
        m = runs[runs["C"] == c_].groupby("A")["ra_um"].mean()
        ax[1].plot([0, 1], S.sig([m[-1], m[1]]), marker="o", color=color, lw=1.6, label=f"Nose radius {lv['C'][0] if c_ == -1 else lv['C'][1]:g} mm")
    ax[1].set_xticks([0, 1])
    ax[1].set_xticklabels([f"Feed {lv['A'][0]:g}", f"Feed {lv['A'][1]:g}"])
    ax[1].set_title("Feed by nose radius")
    ax[1].legend(frameon=False, fontsize=9)
    lo = min(a.get_ylim()[0] for a in ax) - 0.08
    hi = max(a.get_ylim()[1] for a in ax)
    for a in ax:
        a.set_ylim(lo, hi)
    f.tight_layout()
    return S.save(f, name, "Main effects of the four factors and the feed by nose radius interaction on Ra")


def figure_residuals(fit):
    f, ax = S.fig(h=6.2, w=9.2, ncols=2, nrows=2)
    r = np.asarray(fit["resid"])
    q = st.norm.ppf((np.arange(1, len(r) + 1) - 0.5) / len(r))
    ax[0, 0].plot(S.sig(np.sort(r)), S.sig(q), "o", ms=5, color=S.BRAND_BLUE)
    ax[0, 0].plot([float(r.min()), float(r.max())], [float(S.sig(r.min() / r.std(ddof=1))), float(S.sig(r.max() / r.std(ddof=1)))], color="#CCCCCC", lw=1)
    ax[0, 0].set_title("Normal probability plot")
    ax[0, 0].set_xlabel("Residual")
    ax[0, 0].set_ylabel("Normal quantile")
    ax[0, 1].plot(S.sig(fit["fits"]), S.sig(r), "o", ms=5, color=S.BRAND_BLUE)
    ax[0, 1].axhline(0, color="#CCCCCC", lw=1)
    ax[0, 1].set_title("Versus fits")
    ax[0, 1].set_xlabel("Fitted value")
    ax[0, 1].set_ylabel("Residual")
    ax[1, 0].hist(S.sig(r), bins=7, color=S.LIGHT_BLUE, edgecolor="white")
    ax[1, 0].set_title("Histogram")
    ax[1, 0].set_xlabel("Residual")
    ax[1, 0].set_ylabel("Runs")
    o = np.argsort(fit["order"])
    ax[1, 1].plot(np.asarray(fit["order"])[o], S.sig(r[o]), marker="o", ms=5, color=S.BRAND_BLUE, lw=1)
    ax[1, 1].axhline(0, color="#CCCCCC", lw=1)
    ax[1, 1].axvline(8.5, color=S.AMBER, lw=1, ls="--")
    ax[1, 1].set_title("Versus run order (dashed line: second day)")
    ax[1, 1].set_xlabel("Run order")
    ax[1, 1].set_ylabel("Residual")
    f.tight_layout()
    return S.save(f, "s5_fig3_residuals", "Residual plots of the reduced model: normal probability, versus fits, histogram, versus run order")


def figure_lots(r, name, h=3.8):
    lots, c, b, ch = r["lots"], r["chosen"], r["before"], r["change"]
    f, ax = S.fig(h=h, w=9.4)
    ax.axhspan(c["prediction"] - c["pi_half"], c["prediction"] + c["pi_half"], color="#E3EFE6", lw=0, label="95% prediction interval at the chosen settings")
    ax.axhline(c["prediction"], color=S.GREEN, lw=1)
    ax.axhline(r["usl"], color=S.RED, lw=1, ls="--", label=f"Upper limit {r['usl']:g}")
    ax.plot(lots["start"], S.sig(lots["mean_ra"]), "o", ms=4.5, color=S.BRAND_BLUE, label="Lot mean Ra")
    top = r["usl"] + 0.22
    for when, label in ((ch["confirmation_date"], "confirmation runs"), (ch["first_lot"], "first lot at the new level")):
        ax.axvline(when, color=S.AMBER, lw=1.1, ls="--")
        ax.annotate(label, (when, top), rotation=90, va="top", ha="right", fontsize=8.5, color=S.DARK_GREY)
    ax.set_ylim(0.4, top)
    ax.set_ylabel("Ra, µm")
    ax.set_xlabel("Lot start")
    ax.set_title("Lot mean Ra in production")
    ax.legend(frameon=False, fontsize=9, loc="center left")
    f.tight_layout()
    return S.save(f, name, "Lot mean Ra by start date against the prediction interval at the chosen settings and the upper limit")


def build():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = compute()
    hd, lv, keep = r["header"], r["levels"], r["keep"]
    full, red, fs, rs_ = r["full"].set_index("term"), r["reduced"], r["full_summary"], r["reduced_summary"]
    ar, res, c, b, cs, al, ch = r["anova_reduced"], r["residuals"], r["chosen"], r["before"], r["confirmation_summary"], r["alias"], r["change"]
    prod = r["production"].set_index("period")
    capb = r["capability"].set_index("period")
    after = r["lots"][r["lots"]["period"] == "after"]
    lof = ar[ar["source"].str.strip() == "Lack of fit"].iloc[0]
    fe = r["feed_effect"]
    ac = full.loc["AC"]
    days = res["by_day"]
    day_gap = abs(float(days["mean"].iloc[0] - days["mean"].iloc[1]))
    part = hd["part"]
    cid = r["characteristic_id"]

    body = "<h2 id='f1'>1. The design</h2>"
    body += (f"<p>Sixteen runs on {r['runs']['machine'].iloc[0]} on {day(r['runs']['date'].min())} and the day after: a half fraction of four factors at two levels (D = ABC), two replicates, run order randomized. "
             f"The design is resolution IV: feed by nose radius is aliased with speed by coolant.</p>")
    body += tbl(["Factor", "Low", "High"], [["A Feed, mm/rev", f"{lv['A'][0]:g}", f"{lv['A'][1]:g}"], ["B Surface speed, m/min", f"{lv['B'][0]:g}", f"{lv['B'][1]:g}"],
                                           ["C Insert nose radius, mm", f"{lv['C'][0]:g}", f"{lv['C'][1]:g}"], ["D Coolant concentration, %", f"{lv['D'][0]:g}", f"{lv['D'][1]:g}"]])
    body += cap(f"Table 1. Factors and levels, worksheet {hd['study_id']}, part {part}, {hd['material']}. Alias structure (I = ABCD): " + "; ".join(f"{k} = {v}" for k, v in ALIAS.items()) + ".")

    body += "<h2 id='f2'>2. Effects</h2>"
    body += (f"<p>Feed and nose radius interact: effect {ac['effect']:+.3f} µm (p &lt; 0.001), {abs(ac['effect']) / abs(full.loc['C', 'effect']):.1f} times the largest main effect, nose radius at {full.loc['C', 'effect']:+.3f}. "
             f"Feed is {full.loc['A', 'effect']:+.3f}. Speed ({full.loc['B', 'effect']:+.3f}, p = {full.loc['B', 'p']:.2f}), coolant ({full.loc['D', 'effect']:+.3f}, p = {full.loc['D', 'p']:.2f}) "
             f"and the other two interaction pairs are not significant.</p>")
    body += tbl(["Term", "Effect", "Coef", "SE Coef", "T-Value", "P-Value", "Aliased with"], effects_rows(r["full"]))
    body += cap(f"Table 2. Estimated effects and coefficients for Ra, full model. S = {fs['s']:.4f}; R-sq = {100 * fs['r2']:.2f}%; R-sq(adj) = {100 * fs['r2_adj']:.2f}%; R-sq(pred) = {100 * fs['r2_pred']:.2f}%.")
    body += figure_half_normal(r["half_normal"], keep) + cap("Figure 1. Half-normal plot of the seven effects; the line passes through the effects not significant at 0.05.")

    body += "<h2 id='f3'>3. The reduced model</h2>"
    body += (f"<p>Feed, nose radius and their interaction explain {100 * rs_['r2_adj']:.1f}% of the variation in Ra (R-sq adjusted), with S = {rs_['s']:.3f} µm and no lack of fit (p = {lof['p']:.2f}). "
             f"The feed effect is {fe['at_low_radius']:+.2f} µm at the {lv['C'][0]:g} mm radius and {fe['at_high_radius']:+.2f} µm at {lv['C'][1]:g} mm: it reverses.</p>")
    body += tbl(["Source", "DF", "SS", "MS", "F", "P"],
                [[x.source.replace("  ", "&nbsp;&nbsp;"), x.df, f"{x.ss:.5f}", "" if x.ms != x.ms else f"{x.ms:.5f}", "" if x.F != x.F else f"{x.F:.2f}", "" if x.p != x.p else ("0.000" if x.p < 0.0005 else f"{x.p:.3f}")] for x in ar.itertuples()])
    body += cap(f"Table 3. Analysis of variance, reduced model. S = {rs_['s']:.4f}; R-sq = {100 * rs_['r2']:.2f}%; R-sq(adj) = {100 * rs_['r2_adj']:.2f}%; R-sq(pred) = {100 * rs_['r2_pred']:.2f}%.")
    body += figure_effects(r["runs"], lv, "s5_fig2_effects") + cap("Figure 2. Mean Ra at each level of the four factors (left) and by feed at each nose radius (right).")

    body += "<h2 id='f4'>4. Residuals</h2>"
    body += (f"<p>Normality (p = {res['ad_p']:.2f}) and run order (p = {res['order_p']:.2f}) are clean; the spread of the residuals rises with the fitted value (p = {res['abs_resid_on_fit_p']:.3f}); "
             f"the two days differ by {day_gap:.3f} µm in mean residual and the design did not block on day. The prediction interval below is the constant-variance interval of the model.</p>")
    body += figure_residuals(r["fit"]) + cap("Figure 3. Residuals of the reduced model.")

    body += "<h2 id='f5'>5. The prediction and the confirmation</h2>"
    body += (f"<p>At feed {lv['A'][1]:g} mm/rev with the {lv['C'][1]:g} mm nose radius the model predicts Ra {c['prediction']:.2f} µm ({c['prediction'] - c['pi_half']:.2f} to {c['prediction'] + c['pi_half']:.2f}) "
             f"against {b['prediction']:.2f} µm at the settings before. The four confirmation runs of {day(cs['date'])} gave " + ", ".join(f"{v:.2f}" for v in r["confirmation"]["ra_um"])
             + f": {cs['inside']} of {cs['runs']} inside the interval, mean {cs['mean']:.2f}.</p>")
    body += tbl(["Settings", "Predicted Ra", "95% prediction interval", "95% confidence interval of the mean"],
                [[f"Before: {hd['settings_before']}", f"{b['prediction']:.3f}", f"{b['prediction'] - b['pi_half']:.3f} to {b['prediction'] + b['pi_half']:.3f}", f"{b['prediction'] - b['ci_half']:.3f} to {b['prediction'] + b['ci_half']:.3f}"],
                 [f"Chosen: feed {lv['A'][1]:g} mm/rev; speed {lv['B'][0]:g} m/min; nose radius {lv['C'][1]:g} mm; coolant {lv['D'][0]:g}%", f"{c['prediction']:.3f}",
                  f"{c['prediction'] - c['pi_half']:.3f} to {c['prediction'] + c['pi_half']:.3f}", f"{c['prediction'] - c['ci_half']:.3f} to {c['prediction'] + c['ci_half']:.3f}"]])
    body += cap("Table 4. Predicted Ra from the reduced model at the settings before and at the chosen settings.")

    body += "<h2 id='f6'>6. The alias check</h2>"
    body += (f"<p>The interaction is feed by nose radius, not speed by coolant. The confirmation runs lie in the half fraction, where the two take the same sign and cannot be told apart. "
             f"The settings before the change lie outside it: the model gives {al['before_if_feed_radius']:.3f} µm there if the interaction is feed by nose radius and {al['before_if_speed_coolant']:.3f} if it is speed by coolant. "
             f"{int(prod.loc['before', 'lots'])} production lots at those settings ran at {prod.loc['before', 'mean']:.3f}.</p>")
    body += tbl(["", "Value"], [["Speed main effect", f"{al['speed']:+.4f}, p = {al['speed_p']:.2f}"], ["Coolant main effect", f"{al['coolant']:+.4f}, p = {al['coolant_p']:.2f}"],
                               ["Chosen settings: in the half fraction", "yes; the two interactions take the same sign"],
                               ["Settings before: in the half fraction", "no; the two interactions take opposite signs"],
                               ["Ra at the settings before if the interaction is feed by nose radius", f"{al['before_if_feed_radius']:.3f}"],
                               ["Ra at the settings before if the interaction is speed by coolant", f"{al['before_if_speed_coolant']:.3f}"],
                               [f"Production Ra at the settings before, {int(prod.loc['before', 'lots'])} lots", f"{prod.loc['before', 'mean']:.3f}"]])
    body += cap("Table 5. The aliased pair against the production record.")

    cb, ca = capb.loc["before"], capb.loc["after"]
    body += "<h2 id='f7'>7. Production after the change</h2>"
    body += (f"<p>The {len(after)} lots run since {day(ch['first_lot'])} average {after['mean_ra'].mean():.3f} µm against the predicted {c['prediction']:.3f}: every lot below it, all {int(after['inside_pi'].sum())} inside the prediction interval "
             f"and {int(after['within_0_1'].sum())} of {len(after)} within 0.1 µm; the confirmation runs averaged {cs['mean']:.3f}. Against the upper limit of {r['usl']:g} µm the index was {cb['index']:.2f} on the "
             f"{int(cb['lots'])} lots before ({cb['ppm']:,.0f} ppm expected above the limit, {int(cb['readings_above'])} readings recorded above it) and is {ca['index']:.2f} on the {int(ca['lots'])} lots since.</p>")
    body += tbl(["Period", "Lots", "Readings", "Mean Ra", "sd", "Fitted distribution", "Median", "99.865th percentile", "Index", "Expected ppm above the limit", "Readings above the limit"],
                [[f"{x.period[0].upper() + x.period[1:]} the change", x.lots, f"{x.readings:,}", f"{x.mean:.3f}", f"{x.sd:.3f}", x.distribution, f"{x.median:.3f}", f"{x.p99865:.3f}", f"{x.index:.2f}", f"{x.ppm:,.0f}", x.readings_above]
                 for x in r["capability"].itertuples()])
    body += cap(f"Table 6. Ra on {cid} in production against the upper limit of {r['usl']:g} µm, percentile method.")
    body += figure_lots(r, "s5_fig4_lot_means") + cap("Figure 4. Mean Ra of each production lot by start date, with the prediction interval at the chosen settings, the upper limit, the confirmation runs and the first lot at the new level.")

    body += "<h2 id='rec'>Recommendation</h2><ul>"
    body += (f"<li>Run {cid} at feed {lv['A'][1]:.2f} mm/rev with the {lv['C'][1]:g} mm nose radius, speed and coolant at the current settings.</li>"
             "<li>Write the settings into the routing and the setup sheet so that the lot record carries them.</li>"
             "<li>Hold the roughness tester's calibration and the sampling plan on the part as they are.</li>"
             "<li>Use the Ra mean of each lot against the prediction interval on the SPC chart as the control.</li></ul>")
    body += "<h2 id='method'>Method and data</h2>"
    body += (f"<p class='note'>Design: two-level half fraction of four factors, D = ABC, two replicates, 16 runs, resolution IV; main effects are aliased with three-factor interactions and each two-factor interaction with one other. "
             f"Model: least squares on coded levels; the reduced model keeps the terms significant at 0.05 with the main effects of a kept interaction; S = {rs_['s']:.3f} on {rs_['df_resid']} degrees of freedom. "
             "Prediction interval: 95%, for a single run at the settings, constant variance. Confirmation: four further runs at the chosen settings. "
             f"Production: lot means of the five-reading subgroups on {cid}. The lot record carries no cutting settings; the change is dated at the first lot at the new level, {day(ch['first_lot'])}, "
             f"and {ch['lots_between']} lot started after the confirmation runs at the old level ({day(r['lots'][r['lots']['start'] > ch['confirmation_date']]['start'].min())}, "
             f"{r['lots'][r['lots']['start'] > ch['confirmation_date']]['mean_ra'].iloc[0]:.2f} µm). "
             "Capability: percentile method on the distribution fitted to the readings, index from the median and the 99.865th percentile against the upper limit, as in S2.</p>")

    body += "<h2 id='app'>Appendix</h2>"
    body += tbl(["Std order", "Run order", "Date", "Feed", "Speed", "Nose radius", "Coolant", "Ra", "Fit", "Residual"],
                [[int(x.std_order), x.run_order, x.date, f"{x.feed_mm_per_rev:g}", x.surface_speed_m_per_min, f"{x.nose_radius_mm:g}", x.coolant_pct, f"{x.ra_um:.2f}", f"{fit:.4f}", f"{rr:+.4f}"]
                 for x, fit, rr in zip(r["runs"].itertuples(), r["fit"]["fits"], r["fit"]["resid"])])
    body += cap("Table A1. The sixteen runs in standard order, with fitted values and residuals of the reduced model.")
    body += tbl(["Term", "Effect", "Coef", "SE Coef", "T-Value", "P-Value", "Aliased with"], effects_rows(red)) + cap("Table A2. Estimated effects and coefficients, reduced model.")
    body += tbl(["Lot", "Start", "Subgroups", "Mean Ra", "Difference from the prediction", "Within 0.1"],
                [[x.job_id, str(x.start)[:10], x.subgroups, f"{x.mean_ra:.3f}", f"{x.mean_ra - c['prediction']:+.3f}", "yes" if x.within_0_1 else "no"] for x in after.itertuples()])
    body += cap(f"Table A3. Production lots since {day(ch['first_lot'])}.")
    body += tbl(["Check", "Result"], [["Normality, Anderson-Darling", f"A-sq {res['ad']:.3f}, p = {res['ad_p']:.3f}"],
                                     ["Residual on run order, slope", f"{res['order_slope']:+.4f} per run, p = {res['order_p']:.3f}; Durbin-Watson {res['durbin_watson']:.2f}"],
                                     ["Mean residual by day", "; ".join(f"{x.date}: {x.mean:+.4f}" for x in days.itertuples())],
                                     ["Absolute residual on fitted value, slope", f"{res['abs_resid_on_fit_slope']:+.4f}, p = {res['abs_resid_on_fit_p']:.3f}"],
                                     ["Largest standardized residual", f"{res['largest_standardized']:.2f}"]])
    body += cap("Table A4. Residual checks.")

    toc = [("f1", "Design"), ("f2", "Effects"), ("f3", "Reduced model"), ("f4", "Residuals"), ("f5", "Prediction"), ("f6", "Alias check"), ("f7", "Production"), ("rec", "Recommendation"), ("method", "Method"), ("app", "Appendix")]
    (S.DOCS / "reports").mkdir(parents=True, exist_ok=True)
    (S.DOCS / "reports" / "s5_doe.html").write_text(S.report_shell("S5. Designed experiment on surface finish", "Study report", HEADER, body, toc), encoding="utf8", newline="\n")

    left = [f"<section><h2>Background and problem</h2><p>Ra on {cid} (part {part}, {hd['material']}) ran at {prod.loc['before', 'mean']:.2f} µm on {int(prod.loc['before', 'lots'])} lots against an upper limit of {r['usl']:g} µm: "
            f"index {cb['index']:.2f}, {cb['ppm']:,.0f} ppm expected above the limit.</p></section>",
            f"<section><h2>Current condition</h2>{figure_lots(r, 's5_a3_lot_means', 2.7)}<div class='caption'>Lot mean Ra by start date with the upper limit and the prediction interval at the chosen settings.</div></section>",
            f"<section><h2>Target</h2><p>Ra at or below {c['prediction']:.2f} µm with the index against the {r['usl']:g} µm limit at or above 1.33, held through 2026.</p></section>",
            f"<section><h2>Analysis</h2>{figure_effects(r['runs'], lv, 's5_a3_effects', 2.5)}<div class='caption'>Main effects and the feed by nose radius interaction, 16 runs.</div><ul>"
            f"<li>Feed by nose radius: effect {ac['effect']:+.3f} µm, p &lt; 0.001.</li>"
            f"<li>Feed effect {fe['at_low_radius']:+.2f} µm at the {lv['C'][0]:g} mm radius and {fe['at_high_radius']:+.2f} µm at {lv['C'][1]:g} mm.</li>"
            f"<li>Prediction at the chosen settings {c['prediction']:.2f} µm, interval {c['prediction'] - c['pi_half']:.2f} to {c['prediction'] + c['pi_half']:.2f}.</li>"
            f"<li>The alias with speed by coolant is resolved by production at the old settings: {prod.loc['before', 'mean']:.2f} µm against {al['before_if_feed_radius']:.2f} and {al['before_if_speed_coolant']:.2f}.</li></ul></section>"]
    cm = [[f"Feed {lv['A'][1]:.2f} mm/rev and {lv['C'][1]:g} mm nose radius written into the routing and the setup sheet", "Manufacturing engineer", f"in production from {day(ch['first_lot'])}; documents March 2026"],
          ["Lot mean Ra against the prediction interval as the control limit on the SPC chart", "Quality engineer", "March 2026"]]
    right = [f"<section><h2>Countermeasures</h2>{tbl(['Action', 'Owner', 'When'], cm)}</section>",
             f"<section><h2>Results</h2><p>Ra {after['mean_ra'].mean():.3f} µm on {len(after)} lots since {day(ch['first_lot'])}, every lot inside the prediction interval; {cs['inside']} of {cs['runs']} confirmation runs inside it; "
             f"index {ca['index']:.2f} against the limit, from {cb['index']:.2f}.</p>"
             + tbl(["", "Lots", "Mean Ra", "Index", "Expected ppm above the limit"], [[f"{x.period[0].upper() + x.period[1:]} the change", x.lots, f"{x.mean:.3f}", f"{x.index:.2f}", f"{x.ppm:,.0f}"] for x in r["capability"].itertuples()])
             + "</section>",
             "<section><h2>Follow-up</h2><p>Lot mean Ra against the interval on every lot. A further experiment on the two aliased pairs if a customer asks for the speed and coolant effects.</p></section>"]
    (S.DOCS / "a3").mkdir(parents=True, exist_ok=True)
    (S.DOCS / "a3" / "s5_doe.html").write_text(S.a3_shell("Surface finish: designed experiment", "S5 A3", HEADER.split("<br>")[0] + "<br>PPAP element 11 supporting data; DMAIC project.", "\n".join(left), "\n".join(right)),
                                              encoding="utf8", newline="\n")
    return S.DOCS / "reports" / "s5_doe.html"


if __name__ == "__main__":
    print(build())
