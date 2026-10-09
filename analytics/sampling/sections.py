"""Acceptance sampling and supplier quality.

Built by its report under analytics.reports.
"""
import warnings

import numpy as np
import pandas as pd
from scipy import stats as st

from analytics.sampling.study import BAD, SUPPLIER, compute
from analytics.style import style as S

HEADER = ("Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant. January 2024 to December 2025.<br>"
          "Sources: receiving inspection, supplier master and published scorecard, complaints, inspection labor lines.<br>"
          "PPAP element 15 supporting data for purchased product; supplier control.")


def tbl(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f'<td class="{"num" if i else ""}">{v}</td>' for i, v in enumerate(r)) + "</tr>" for r in rows)
    return f'<table class="data"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def cap(text):
    return f'<div class="caption">{text}</div>'


def figure_oc(plans, d):
    f, ax = S.fig(h=5.4, w=9.4, ncols=2, nrows=2, gridspec_kw=dict(height_ratios=[3, 1.3]), sharex=True)
    p = np.linspace(0.0005, 0.08, 400)
    for j, letter in enumerate(sorted(plans["code_letter"].unique())):
        g = plans[plans["code_letter"] == letter]
        for x, color in zip(g.itertuples(), (S.BRAND_BLUE, S.AMBER)):
            ax[0, j].plot(100 * p, S.sig(100 * st.binom.cdf(x.acceptance_number, x.sample_size, p)), color=color, lw=1.6, label=f"{'Z1.4' if x.acceptance_number else 'c=0'}: n = {x.sample_size}, Ac = {x.acceptance_number}")
        ax[0, j].axhline(10, color="#DDDDDD", lw=1)
        ax[0, j].set_title(f"Lots of {'501 to 1,200' if letter == 'J' else '1,201 to 3,200'} pieces (code {letter})")
        ax[0, j].legend(frameon=False, fontsize=9)
        ax[1, j].fill_between(100 * p, S.sig(st.beta.pdf(p, d["a"], d["b"])), color=S.LIGHT_BLUE)
        ax[1, j].axvline(100 * BAD, color=S.RED, lw=1, ls="--")
        ax[1, j].set_yticks([])
        ax[1, j].set_xlabel("Lot defect rate, %")
    ax[0, 0].set_ylabel("Lots accepted, %")
    ax[1, 0].set_ylabel(f"{SUPPLIER} lots")
    f.tight_layout()
    return S.save_conformed(f, "sampling_fig2_oc_curves", "OC curves of the Z1.4 plan and the zero-acceptance plan with the lot quality of supplier S-017 beneath")


def figure_scorecard(sc):
    f, ax = S.fig(h=4.2, w=9.6)
    x = np.arange(1, len(sc) + 1)
    color = np.where(sc["interval_above_1pct"], S.RED, np.where(sc["small_history"], S.AMBER, S.ACCENT))
    y = 100 * sc["defect_rate"].to_numpy()
    ax.vlines(x, S.sig(100 * sc["defect_lower"]), S.sig(100 * sc["defect_upper"]), color=color, lw=1.6)
    ax.scatter(x, S.sig(y), s=14, color=color, zorder=3)
    ax.axhline(1.0, color=S.DARK_GREY, lw=1, ls="--")
    for c_, label in ((S.RED, "Interval above 1%"), (S.AMBER, "Fewer than five lots"), (S.ACCENT, "Other suppliers")):
        ax.plot([], [], "o", color=c_, label=label)
    ax.set_xlabel("Published scorecard rank (1 is best)")
    ax.set_ylabel("Defect rate in samples, %")
    ax.set_title("Supplier defect rates with 95% intervals, in published rank order")
    ax.legend(frameon=False, loc="upper left")
    f.tight_layout()
    return S.save_conformed(f, "sampling_fig3_scorecard_intervals", "Defect rate with 95% interval for each of 60 suppliers in published rank order")


def figure_history(r, sw):
    f, ax = S.fig(h=3.9, w=9.6)
    t = pd.to_datetime(r["received_at"])
    tight = (sw["state"] == "tightened").to_numpy()
    start = None
    for i in range(len(tight)):
        if tight[i] and start is None:
            start = t.iloc[i]
        if start is not None and (not tight[i] or i == len(tight) - 1):
            ax.axvspan(start, t.iloc[i], color="#F3E3C8", lw=0)
            start = None
    passed = r["defects_found"] <= r["acceptance_number"]
    acc = r["disposition"] == "accept"
    for mask, color, label in ((passed, S.ACCENT, "Passed the plan, accepted"), (~passed & acc, S.AMBER, "Above the acceptance number, accepted"), (~passed & ~acc, S.RED, "Above the acceptance number, rejected")):
        ax.plot(t[mask], r.loc[mask, "defects_found"], "o", ms=4, color=color, label=label)
    ax.plot([], [], color="#F3E3C8", lw=8, label="Tightened inspection under the Z1.4 switching rule")
    ax.set_ylabel("Defects found in the sample")
    ax.set_xlabel("Received")
    ax.set_title(f"{SUPPLIER} receiving lots")
    ax.legend(frameon=False, fontsize=9, loc="upper left", ncol=2)
    ax.set_ylim(-0.4, float(r["defects_found"].max()) + 3.5)
    f.tight_layout()
    return S.save_conformed(f, "sampling_fig1_s017_history", "Defects found in each S-017 receiving lot over time with dispositions and the periods of tightened inspection")


def build():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = compute()
    sw, sh, insp, plans, d, vol, hrs = r["switching"], r["shortcuts"], r["inspectors"], r["plans"], r["distribution"], r["volume"], r["hours"]
    h = r["on_history"].set_index("plan")
    z, c0 = h.loc["Z1.4"], h.loc["c=0"]
    sc, e, es = r["scorecard"], r["escapes"], r["escape_summary"]
    pl = plans.set_index("plan")
    zj, cj, zk, ck = pl.loc["Z1.4 code J"], pl.loc["c=0, lots of code J"], pl.loc["Z1.4 code K"], pl.loc["c=0, lots of code K"]
    ratio = vol["c0_pieces"].sum() / vol["z14_pieces"].sum()
    rate = hrs["hours_per_piece"]
    by = r["by_interval"].set_index("group")
    low = by.loc["interval below 1%"]
    above = sc[sc["interval_above_1pct"]]
    worst = sc.tail(5)
    ranked = sc[~sc["small_history"]].copy()
    ranked["published_among_ranked"] = ranked["scorecard_rank_as_published"].rank().astype(int)
    ranked["move"] = ranked["restated_rank"] - ranked["published_among_ranked"]
    moves = ranked.reindex(ranked["move"].abs().sort_values(ascending=False, kind="stable").index).head(5)

    body = "<h2 id='f1'>1. The plan as operated</h2>"
    body += (f"<p>Normal inspection is recorded on every one of {SUPPLIER}'s {r['lots']} lots; the Z1.4 switching rule would have put {sw['lots_on_tightened']} of them on tightened inspection, "
             f"from {pd.Timestamp(sw['first_switch']).day} {pd.Timestamp(sw['first_switch']).strftime('%B %Y')}. Across all {sh['lots']:,} receiving lots the sample was below the table value on "
             f"{100 * sh['below'] / sh['lots']:.1f}%, and {sh['accepted_above']} of the {sh['above_ac']} lots with defects above the acceptance number were dispositioned accept "
             f"({100 * sh['accepted_above'] / sh['lots']:.1f}% of all lots), with no deviation recorded.</p>")
    body += tbl(["Inspector", "Lots", "Sample below the table value", "Share", "Defects above the acceptance number", "of them accepted", "Share of all lots"],
                [[x.inspector, f"{x.lots:,}", f"{x.sample_below_table:.0f}", f"{100 * x.sample_below_table / x.lots:.1f}%", f"{x.above_acceptance_number:.0f}", f"{x.accepted_above:.0f}",
                  f"{100 * x.accepted_above / x.lots:.2f}%"] for x in insp.itertuples()]
                + [["Both", f"{insp['lots'].sum():,}", f"{insp['sample_below_table'].sum():.0f}", f"{100 * insp['sample_below_table'].sum() / insp['lots'].sum():.1f}%", f"{insp['above_acceptance_number'].sum():.0f}",
                    f"{insp['accepted_above'].sum():.0f}", f"{100 * insp['accepted_above'].sum() / insp['lots'].sum():.2f}%"]])
    body += cap("Table 1. Receiving inspection as recorded, all suppliers, by inspector.")
    body += figure_history(r["history"], r["switching_frame"])
    body += cap(f"Figure 1. Defects found in the sample of each {SUPPLIER} lot, by disposition; shaded periods are those the Z1.4 switching rule would have put on tightened inspection.")

    body += "<h2 id='f2'>2. The two plans at the shop's lot sizes</h2>"
    body += (f"<p>The c=0 plan gives the same LTPD as the Z1.4 plan ({100 * cj['ltpd']:.1f}% against {100 * zj['ltpd']:.1f}% on lots of 501 to 1,200, {100 * ck['ltpd']:.1f}% against {100 * zk['ltpd']:.1f}% on 1,201 to 3,200) "
             f"at {100 * ratio:.0f}% of the sample pieces. It accepts 95% of lots only at {100 * cj['p_at_95']:.2f}% defective or better, where the Z1.4 plan does so at {100 * zj['p_at_95']:.2f}%. "
             f"On {SUPPLIER} the Z1.4 table takes {vol['z14_pieces'].sum() / 2:,.0f} sample pieces a year, {rate * vol['z14_pieces'].sum() / 2:,.0f} hours; the c=0 plan {vol['c0_pieces'].sum() / 2:,.0f} pieces, "
             f"{rate * vol['c0_pieces'].sum() / 2:,.0f} hours.</p>")
    body += tbl(["Plan", "Lots; lot sizes", "n", "Ac", "Accepted at 0.5%", "1%", "2.5%", "4%", "6.5%", "AOQL", "LTPD", "Quality accepted 95% of the time"],
                [[x["plan"], f"{x['lots']}; {x['lot_range']}", x["sample_size"], x["acceptance_number"]] + [f"{100 * x[f'pa_{k}']:.1f}%" for k in (0.005, 0.01, 0.025, 0.04, 0.065)]
                 + [f"{100 * x['aoql']:.2f}%", f"{100 * x['ltpd']:.1f}%", f"{100 * x['p_at_95']:.2f}%"] for _, x in plans.iterrows()])
    body += cap(f"Table 2. Z1.4 single sampling (normal, level II, AQL 1.0) and the zero-acceptance plan at the same AQL, at the median lot size of each code letter on {SUPPLIER}.")
    body += figure_oc(plans, d) + cap(f"Figure 2. OC curves of the two plans, with the lot-quality distribution of {SUPPLIER} beneath; the dashed line is 2.5% defective.")

    body += f"<h2 id='f3'>3. {SUPPLIER}'s lot quality</h2>"
    body += (f"<p>{SUPPLIER}'s lots average {100 * d['mean']:.2f}% defective, above the AQL of 1.0%, and {100 * d['above_bad']:.1f}% of its lots are above 2.5%. The samples hold {d['defects']:,} defects in {d['pieces']:,} pieces; "
             f"the lot defect rate runs from {100 * d['p05']:.2f}% at the 5th percentile to {100 * d['p95']:.2f}% at the 95th.</p>")

    body += f"<h2 id='f4'>4. The two plans on {SUPPLIER}'s history</h2>"
    body += (f"<p>On {SUPPLIER}'s lot history the current plan passes {100 * z.share_of_bad_accepted:.0f}% of lots above 2.5% defective and the c=0 plan {100 * c0.share_of_bad_accepted:.0f}%. "
             f"The current plan rejects {z.lots - z.expected_accepted:.0f} of {int(z.lots)} lots and the c=0 plan {c0.lots - c0.expected_accepted:.0f}, because {SUPPLIER} runs above the AQL.</p>")
    body += tbl(["", "Z1.4 as used", "c=0 plan"],
                [[f"Lots above 2.5% defective, expected of {int(z.lots)}", f"{z.expected_lots_above:.1f}", f"{c0.expected_lots_above:.1f}"],
                 ["Lots passing the plan: expected; from the record", f"{z.expected_accepted:.1f}; {int(z.recorded_passed)}", f"{c0.expected_accepted:.1f}; {c0.recorded_passed:.1f}"],
                 ["Lots above 2.5% that pass: expected; from the record", f"{z.expected_accepted_above:.1f}; {z.recorded_above_passed:.1f}", f"{c0.expected_accepted_above:.1f}; {c0.recorded_above_passed:.1f}"],
                 ["Share of lots above 2.5% that pass", f"{100 * z.share_of_bad_accepted:.0f}%", f"{100 * c0.share_of_bad_accepted:.0f}%"],
                 ["Lots rejected, expected", f"{z.lots - z.expected_accepted:.1f}", f"{c0.lots - c0.expected_accepted:.1f}"],
                 ["Defective pieces in lots that pass, expected", f"{z.expected_defective_pieces_accepted:,.0f}", f"{c0.expected_defective_pieces_accepted:,.0f}"],
                 ["Lots dispositioned accept; above 2.5% among them, from the record", f"{int(z.recorded_accepted)} ({r['above_ac_accepted']} above the acceptance number); {z.recorded_above_accepted:.1f}", ""]])
    body += cap(f"Table 3. The two plans on the {int(z.lots)} lots of {SUPPLIER}: expected from the fitted lot quality, and from the record of each lot's sample.")

    body += "<h2 id='f5'>5. The escapes</h2>"
    body += (f"<p>{es['complaints']} complaints for plating defects trace to accepted {SUPPLIER} lots, {es['pieces']} pieces reported. By their own samples {e['chance_above'].sum():.1f} of those lots were above 2.5% defective; "
             f"their samples held {es['mean_defects_complaint_lots']:.1f} defects on average against {es['mean_defects_other_accepted']:.1f} on the other accepted lots. "
             f"They cost ${es['credit']:,.0f} in credits, ${es['containment']:,.0f} in containment and ${es['freight']:,.0f} in return freight.</p>")

    body += "<h2 id='f6'>6. The scorecard restated</h2>"
    body += (f"<p>{len(above)} of {len(sc)} suppliers have a defect rate whose 95% interval lies above 1%: " + ", ".join(f"{x.supplier_id} ({x.commodity}, {100 * x.defect_rate:.2f}%)" for x in above.itertuples())
             + f". {int(sc['interval_below_1pct'].sum())} lie entirely below 1%. Two of the five worst on the published scorecard, "
             + " and ".join(f"{x.supplier_id} ({x.lots} lots)" for x in worst[worst["small_history"]].itertuples())
             + f", are ranked on fewer than five lots. Ranked by defect rate, {moves.iloc[0]['supplier_id']} moves from {int(moves.iloc[0]['published_among_ranked'])} to {int(moves.iloc[0]['restated_rank'])} "
             f"and {moves.iloc[1]['supplier_id']} from {int(moves.iloc[1]['published_among_ranked'])} to {int(moves.iloc[1]['restated_rank'])}.</p>")
    ext = pd.concat([above, worst[worst["small_history"]], moves]).drop_duplicates("supplier_id")
    rank_of = ranked.set_index("supplier_id")

    def row(x):
        return [x.supplier_id, x.commodity, x.lots, x.scorecard_rank_as_published, f"{100 * x.acceptance_rate:.1f}% ({100 * x.acceptance_lower:.1f} to {100 * x.acceptance_upper:.1f})",
                f"{100 * x.defect_rate:.2f}% ({100 * x.defect_lower:.2f} to {100 * x.defect_upper:.2f})", f"{100 * x.on_time_rate:.0f}% ({100 * x.on_time_lower:.0f} to {100 * x.on_time_upper:.0f})",
                "fewer than five lots" if x.small_history else int(x.restated_rank)]
    head = ["Supplier", "Commodity", "Lots", "Published rank", "Lot acceptance (95%)", "Defect rate (95%)", "On time (95%)", "Restated rank"]
    body += tbl(head, [row(x) for x in ext.itertuples()])
    body += cap("Table 4. The suppliers above 1%, the two ranked on fewer than five lots, and the five largest moves in rank; restated rank is by defect rate among the 58 suppliers with five lots or more.")
    body += figure_scorecard(sc) + cap("Figure 3. Defect rate in the receiving samples with its 95% interval for every supplier, in published rank order; the dashed line is 1%.")

    body += "<h2 id='rec'>Recommendation</h2><ul>"
    si = r["switching_by_interval"].set_index("group")
    red, tight = si.loc["interval below 1%"], si.loc["interval above 1%"]
    saved = red["table_pieces"] - red["switched_pieces"]
    body += (f"<li>Apply the Z1.4 switching rules as written: reduced inspection for suppliers that qualify and tightened for those that do not. On the record, {red['lots_on_reduced']:,.0f} of the {int(red['lots']):,} lots of the "
             f"{int(red['suppliers'])} suppliers below 1% would have been on reduced inspection ({int(red['suppliers_reaching_reduced'])} suppliers qualify), saving {saved:,.0f} sample pieces and {rate * saved:,.0f} hours in 24 months; "
             f"{int(tight['lots_on_tightened'])} of the {int(tight['lots'])} lots of the four suppliers above 1% would have been on tightened, with {int(tight['rejected_with_switching'])} lots not accepted where {int(tight["not_passed_normal"])} failed the plan on normal inspection.</li>"
             f"<li>The c=0 plan at AQL 1.0 is the option where a customer requires it; on this record it rejects {c0.lots - c0.expected_accepted:.0f} of {int(z.lots)} {SUPPLIER} lots and about {low['c0_expected_rejections']:.0f} of the "
             f"{int(low['lots']):,} lots of the suppliers below 1%.</li>"
             f"<li>For {SUPPLIER} and the three other suppliers above 1% the plan is not the lever: a supplier corrective action with the lot history as the evidence, and source inspection or 100% sort at the supplier's cost "
             "until the interval falls below 1%.</li>"
             "<li>Record the inspection level on every receiving lot.</li>"
             "<li>Publish the scorecard with intervals and a minimum of five lots for a rank.</li>"
             "<li>Stop accepting lots above the acceptance number without a recorded deviation.</li></ul>")

    body += "<h2 id='method'>Method and data</h2>"
    body += (f"<p class='note'>Plans: ANSI/ASQ Z1.4 single sampling, normal inspection, general level II, AQL 1.0; the zero-acceptance plan from the published table at the same AQL, which carries no switching rule. "
             "OC curves are binomial where the lot is above ten times the sample and hypergeometric otherwise, lot by lot. "
             f"Lot quality: a beta distribution fitted by maximum likelihood to the defects found in each sample (a {d['a']:.2f}, b {d['b']:.1f}). "
             "Lots above 2.5% from the record: each lot that passed, weighted by the chance that it is above 2.5% given its own sample and the fitted distribution; a construction, since no lot's rate is observed. "
             "The c=0 plan on the record: the chance that its sample, drawn from the sample taken, holds no defect. "
             "Switching: tightened after 2 of 5 consecutive lots not accepted, normal again after 5 consecutive accepted, tightened acceptance numbers on the same samples; reduced from a switching score of 30 "
             "(plus 3 for a lot that passes one AQL step tighter where the acceptance number is 2 or more, plus 2 for an accepted lot otherwise, reset on any other result), production taken as steady, "
             "back to normal on a lot above the reduced acceptance number; the reduced sample is drawn from the sample taken and the result averaged over 400 seeded replications. "
             f"Hours: the receiving inspectors' booked hours ({hrs['booked_hours']:,.0f} in 24 months) over the pieces they sampled on all {sh['lots']:,} lots ({hrs['pieces']:,.0f}) give {hrs['minutes_per_piece']:.2f} minutes per sampled piece. "
             "Rate intervals are Jeffreys intervals. Restated rank: by defect rate among suppliers with five lots or more.</p>")

    body += "<h2 id='app'>Appendix</h2>"
    body += tbl(["Code letter", "Lots in 24 months", "Z1.4 table: pieces; hours", "As taken: pieces", "c=0 plan: pieces; hours", "c=0 against Z1.4"],
                [[x.code_letter, x.lots, f"{x.z14_pieces:,}; {rate * x.z14_pieces:,.0f}", f"{x.taken_pieces:,}", f"{x.c0_pieces:,}; {rate * x.c0_pieces:,.0f}", f"{100 * x.c0_pieces / x.z14_pieces:.0f}%"] for x in vol.itertuples()]
                + [["Both", vol["lots"].sum(), f"{vol['z14_pieces'].sum():,}; {rate * vol['z14_pieces'].sum():,.0f}", f"{vol['taken_pieces'].sum():,}", f"{vol['c0_pieces'].sum():,}; {rate * vol['c0_pieces'].sum():,.0f}", f"{100 * ratio:.0f}%"]])
    body += cap(f"Table A1. Sample pieces and inspection hours on {SUPPLIER} over 24 months under each plan, at {hrs['minutes_per_piece']:.2f} minutes per sampled piece.")
    body += tbl(["Suppliers by defect-rate interval", "Suppliers", "Lots", "Z1.4 table pieces", "c=0 pieces", "c=0 against Z1.4", "Lots not passing the current plan", "Lots the c=0 plan rejects, expected"],
                [[x.group, x.suppliers, f"{x.lots:,}", f"{x.table_pieces:,}", f"{x.c0_pieces:,}", f"{100 * x.c0_pieces / x.table_pieces:.0f}%", x.not_passed, f"{x.c0_expected_rejections:.0f}"] for x in r["by_interval"].itertuples()])
    body += cap("Table A2. The two plans on every supplier's lots, by where the supplier's defect-rate interval lies.")
    body += tbl(["Suppliers by defect-rate interval", "Suppliers", "Lots", "Lots on reduced", "Suppliers reaching reduced", "Lots on tightened", "Sample pieces: table; with switching", "Hours: table; with switching",
                 "Lots not accepted: as used; with switching"],
                [[x.group, x.suppliers, f"{x.lots:,}", f"{x.lots_on_reduced:,.0f}", x.suppliers_reaching_reduced, f"{x.lots_on_tightened:,.0f}", f"{x.table_pieces:,}; {x.switched_pieces:,.0f}",
                  f"{rate * x.table_pieces:,.0f}; {rate * x.switched_pieces:,.0f}", f"{x.not_passed_normal}; {x.rejected_with_switching:,.0f}"] for x in r["switching_by_interval"].itertuples()])
    body += cap("Table A3. The Z1.4 switching rules applied to every supplier's lot sequence over 24 months: reduced inspection for the suppliers below 1%, tightened for all.")
    body += tbl(["", "Value"], [["Defects found over pieces sampled", f"{d['defects']:,} of {d['pieces']:,} ({100 * d['pooled_rate']:.2f}%)"],
                               ["Lot defect rate: mean; 5th percentile; median; 95th percentile", f"{100 * d['mean']:.2f}%; {100 * d['p05']:.2f}%; {100 * d['median']:.2f}%; {100 * d['p95']:.2f}%"],
                               ["Share of lots above 2.5% defective", f"{100 * d['above_bad']:.1f}%"]])
    body += cap(f"Table A4. {SUPPLIER}'s lot quality from the receiving samples.")
    body += tbl(["Complaint", "Received", "Lot", "Pieces reported", "Sample; defects; acceptance number", "Disposition", "Chance the lot was above 2.5%"],
                [[x.complaint_id, str(x.received_date)[:10], x.job_id, x.quantity, f"{x.sample_size}; {x.defects_found}; {x.acceptance_number}", x.disposition, f"{100 * x.chance_above:.0f}%"] for x in e.itertuples()])
    body += cap(f"Table A5. Complaints for plating defects on accepted {SUPPLIER} lots.")
    body += tbl(["", "Value"], [["Inspection recorded", f"normal on every lot (code letters {', '.join(sw['plans_recorded'])})"],
                               ["Switches to tightened under the Z1.4 rule", f"{sw['switches_to_tightened']}, the first on {sw['first_switch']}"],
                               ["Lots that would have been on tightened", f"{sw['lots_on_tightened']} of {r['lots']}"],
                               ["Lots not accepted: on normal; on tightened", f"{sw['not_accepted_normal']}; {sw['not_accepted_tightened']}"]])
    body += cap(f"Table A6. The Z1.4 switching rule on {SUPPLIER}'s lot sequence.")
    body += tbl(head, [row(x) for x in sc.itertuples()]) + cap("Table A7. The scorecard restated, all 60 suppliers in published rank order.")

    toc = [("f1", "As operated"), ("f2", "Two plans"), ("f3", "Lot quality"), ("f4", "On the history"), ("f5", "Escapes"), ("f6", "Scorecard"), ("rec", "Recommendation"), ("method", "Method"), ("app", "Appendix")]
    return {"body": body, "toc": toc[:-3], "meta": HEADER}
