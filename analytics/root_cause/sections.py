"""Root cause of scrap on family F-14.

Built by its report under analytics.reports.
"""
import warnings

import numpy as np
import pandas as pd

from analytics.root_cause.study import CHANGED, CONTROL, FAMILY, STANDARD, compute
from analytics.style import style as S

HEADER = ("Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant. January 2024 to December 2025; family F-14, 4140 bar, multi-axis turned.<br>"
          "Sources: ERP lots and scrap transactions, material certificates, NCRs and corrective actions.<br>"
          "Corrective action record; DMAIC project.")
CONTROLLED = "machine with hardness band, insert grade and their interaction, all lots"
TERM = {"mt04": "MT-04", "hard": "Bar above 32 HRC", "kgrade": "K20 insert", "hard:kgrade": "Above 32 HRC with the K20 insert"}


def tbl(head, rows):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f'<td class="{"num" if i else ""}">{v}</td>' for i, v in enumerate(r)) + "</tr>" for r in rows)
    return f'<table class="data"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>'


def cap(text):
    return f'<div class="caption">{text}</div>'


def day(t):
    t = pd.Timestamp(t)
    return f"{t.day} {t.strftime('%B %Y')}"


def figure_pareto(p, name, h=3.6):
    f, ax = S.fig(h=h, w=7.6)
    x = np.arange(len(p))
    ax.bar(x - 0.2, S.sig(100 * p["scrap_pieces_share"]), width=0.4, color=S.BRAND_BLUE, label="Share of the family's scrap pieces")
    ax.bar(x + 0.2, S.sig(100 * p["lots_share"]), width=0.4, color=S.LIGHT_BLUE, label="Share of the family's lots")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{m}\n(machine {n})" for m, n in zip(p["machine_id"], p["shop_machine_no"])])
    ax.set_ylabel("%")
    ax.set_title("F-14 scrap by machine before the change")
    ax.legend(frameon=False)
    f.tight_layout()
    return S.save_conformed(f, name, "Share of family scrap and share of family lots by machine before the insert change")


def figure_interaction(cells, name, h=3.8):
    f, ax = S.fig(h=h, w=6.8)
    bands = ["32 HRC and below", "above 32 HRC"]
    for insert, color in ((STANDARD, S.RED), (CHANGED, S.GREEN)):
        c = cells[cells["insert_grade"] == insert].set_index("hardness_band").reindex(bands)
        y = 100 * c["rate"].to_numpy()
        ax.errorbar([0, 1], S.sig(y), yerr=[S.sig(y - 100 * c["lower"].to_numpy()), S.sig(100 * c["upper"].to_numpy() - y)], marker="o", ms=7, lw=1.6, color=color, capsize=3,
                    label=f"{insert} insert" + (" (standard)" if insert == STANDARD else ""))
        for i, b in enumerate(bands):
            ax.annotate(f"{int(c.loc[b, 'lots'])} lots", (i, float(S.sig(y[i]))), textcoords="offset points", xytext=(12, 7 if insert == STANDARD else -15), fontsize=9, color=S.DARK_GREY)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Bar at or below 32 HRC", "Bar above 32 HRC"])
    ax.set_xlim(-0.4, 1.5)
    ax.set_ylabel("Scrap rate, %")
    ax.set_title("F-14 scrap rate by bar hardness and insert grade")
    ax.legend(frameon=False, loc="upper left")
    f.tight_layout()
    return S.save_conformed(f, name, "Scrap rate by bar hardness band for each insert grade with lots in each cell")


def figure_timeline(f14, ctl, rec):
    f, ax = S.fig(h=3.9, w=9.0)
    ax.plot(ctl["start_time"], S.sig(100 * ctl["rate"]), "o", ms=3.5, color=S.LIGHT_BLUE, label=f"{CONTROL} lots")
    ax.plot(f14["start_time"], S.sig(100 * f14["rate"]), "o", ms=4, color=S.BRAND_BLUE, label=f"{FAMILY} lots")
    top = float(100 * f14["rate"].max()) * 1.05
    for when, label in ((rec["opened"], "corrective action opened"), (rec["first_lot"], "first K20 lot"), (rec["closed"], "closed")):
        ax.axvline(when, color=S.AMBER, lw=1.1, ls="--")
        ax.annotate(label, (when, top), rotation=90, va="top", ha="right", fontsize=8.5, color=S.DARK_GREY)
    ax.set_ylabel("Lot scrap rate, %")
    ax.set_xlabel("Lot start")
    ax.set_title("Lot scrap rate by start date")
    ax.legend(frameon=False, loc="upper left")
    f.tight_layout()
    return S.save_conformed(f, "root_cause_fig4_scrap_by_date", "Lot scrap rate by start date for F-14 and F-12 with the corrective action dates")


def figure_hardness(f14):
    f, ax = S.fig(h=4.0, w=8.2)
    for insert, color in ((STANDARD, S.RED), (CHANGED, S.GREEN)):
        for on04, face in ((1, color), (0, "white")):
            d = f14[(f14["insert_grade"] == insert) & (f14["mt04"] == on04)]
            ax.plot(S.sig(d["hardness_hrc"]), S.sig(100 * d["rate"]), "o", ms=5, mec=color, mfc=face, mew=1.2, ls="none",
                    label=f"{insert} insert, {'MT-04' if on04 else 'other machines'}")
    ax.axvline(32, color=S.DARK_GREY, lw=1, ls="--")
    ax.set_xlabel("Bar-lot hardness on the certificate, HRC")
    ax.set_ylabel("Lot scrap rate, %")
    ax.set_title("Lot scrap rate against bar hardness")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    f.tight_layout()
    return S.save_conformed(f, "root_cause_fig3_scrap_against_hardness", "Lot scrap rate against certificate hardness by insert grade, MT-04 lots filled")


def build():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = compute()
    p, rec, f14 = r["pareto"], r["change"]["record"], r["frame"]
    k = rec["capa"]
    mt = p.set_index("machine_id").loc["MT-04"]
    codes = r["cause_codes"].set_index("cause_code")["ncrs"]
    two = r["mt04_against_others"].set_index("mt04")
    models = r["models"].set_index(["model", "term"])
    alone = models.loc[("machine alone, before the change", "mt04")]
    ctrl = models.loc[(CONTROLLED, "mt04")]
    cells = r["cells"]
    bad = cells[(cells["hardness_band"] == "above 32 HRC") & (cells["insert_grade"] == STANDARD)].iloc[0]
    rest = cells.drop(bad.name)
    v = r["variance_shares"]
    an = r["anova"]
    anb = an[an["scope"] == "before the change"].set_index("factor")
    hb = r["hard_by_machine"].set_index("mt04")
    ba = r["before_after"]
    conf = ba[ba["window"].str.startswith("confirmation")].set_index("family")
    alla = ba[ba["window"] == "all lots after"].set_index("family")
    cost = r["cost"].set_index("period")
    hc = r["hardness_check"]
    ctl_before = conf.loc[CONTROL, "rate_before"]

    body = "<h2 id='f1'>1. The shop's view</h2>"
    body += (f"<p>MT-04, machine {int(mt['shop_machine_no'])} on the scrap report, carried {100 * mt['scrap_pieces_share']:.0f}% of the family's scrap pieces and {int(mt['scrap_ncrs'])} of its "
             f"{r['scrap_ncrs_before']} scrap NCRs before the change, on {100 * mt['lots_share']:.0f}% of the lots. The NCRs name the machine on {codes.get('machine', 0)} of {r['scrap_ncrs_before']} and the operator on "
             f"{codes.get('operator', 0)}; material is named once.</p>")
    body += tbl(["Machine (shop no.)", "Lots", "Share of lots", "Scrap pieces", "Share", "Scrap cost", "Share", "Scrap NCRs", "Share"],
                [[f"{x.machine_id} ({x.shop_machine_no})", x.lots, f"{100 * x.lots_share:.1f}%", f"{x.scrap_pieces:,.0f}", f"{100 * x.scrap_pieces_share:.1f}%", f"${x.scrap_cost:,.0f}",
                  f"{100 * x.scrap_cost_share:.1f}%", x.scrap_ncrs, f"{100 * x.scrap_ncrs_share:.1f}%"] for x in p.itertuples()]
                + [["All", p["lots"].sum(), "", f"{p['scrap_pieces'].sum():,.0f}", "", f"${p['scrap_cost'].sum():,.0f}", "", p["scrap_ncrs"].sum(), ""]])
    body += cap(f"Table 1. Scrap on family {FAMILY} by machine on the {r['lots_before']} lots started before {day(rec['first_lot'])}.")
    body += figure_pareto(p, "root_cause_fig1_pareto_by_machine") + cap("Figure 1. Each machine's share of the family's scrap pieces and of its lots before the change.")
    body += tbl(["Cause code as entered", "Scrap NCRs", "Pieces"], [[x.cause_code, x.ncrs, x.pieces] for x in r["cause_codes"].itertuples()])
    body += cap("Table 2. Cause codes on the family's scrap NCRs before the change. Cause text most often entered: "
                + "; ".join(f"{a} ({b})" for a, b in zip(r["cause_text"].iloc[:, 0], r["cause_text"].iloc[:, 1])) + ".")

    body += "<h2 id='f2'>2. The comparison by machine</h2>"
    body += (f"<p>MT-04 scrapped {100 * two.loc[1, 'rate']:.2f}% against {100 * two.loc[0, 'rate']:.2f}% on the other five machines. Lot by lot the odds ratio is {alone['odds_ratio']:.2f} "
             f"({alone['or_lower']:.2f} to {alone['or_upper']:.2f}, p = {alone['p']:.2f}) with dispersion {alone['dispersion']:.0f}: the lots differ far more than pieces drawn at one rate would. "
             f"The piece-level intervals of the Pareto do not overlap ({100 * two.loc[1, 'lower']:.2f} to {100 * two.loc[1, 'upper']:.2f}% against {100 * two.loc[0, 'lower']:.2f} to {100 * two.loc[0, 'upper']:.2f}%) "
             f"because they treat {int(two.loc[1, 'pieces']):,} pieces as independent. The scrap report supports a difference between machines that the lots do not.</p>")
    body += tbl(["Machine", "Lots", "Pieces", "Scrap", "Rate (95% interval on pieces)"],
                [[x.machine_id, f"{x.lots:.0f}", f"{x.pieces:,.0f}", f"{x.scrap:,.0f}", f"{100 * x.rate:.2f}% ({100 * x.lower:.2f} to {100 * x.upper:.2f})"] for x in r["naive"].itertuples()]
                + [["MT-04" if x.mt04 else "The other five", f"{x.lots:.0f}", f"{x.pieces:,.0f}", f"{x.scrap:,.0f}", f"{100 * x.rate:.2f}% ({100 * x.lower:.2f} to {100 * x.upper:.2f})"]
                   for x in r["mt04_against_others"].sort_values("mt04", ascending=False).itertuples()])
    body += cap(f"Table 3. Scrap rate by machine before the change; Jeffreys intervals on pieces, dispersion {alone['dispersion']:.0f} at the lot level.")

    body += "<h2 id='f3'>3. Lot scrap rate across machines, bar suppliers and hardness</h2>"
    body += (f"<p>Before the change the machine explains {100 * anb.loc['machine_id', 'eta_squared']:.1f}% of the variance of lot scrap rate (p = {anb.loc['machine_id', 'p']:.2f}), the bar supplier none, "
             f"and the bar-lot hardness band {100 * anb.loc['hardness_band', 'eta_squared']:.1f}%. Every F-14 lot ran from its own bar lot.</p>")
    lab = {"machine_id": "Machine", "bar_supplier_id": "Bar supplier", "hardness_band": "Bar-lot hardness band (above 32 HRC or not)", "insert_grade": "Insert grade"}
    body += tbl(["Factor", "Levels", "Lots", "F", "p", "Share of variance"], [[lab[x.factor], x.levels, x.lots, f"{x.F:.2f}", f"{x.p:.4f}", f"{100 * x.eta_squared:.1f}%"] for x in an[an["scope"] == "before the change"].itertuples()])
    body += cap("Table 4. One-way analysis of variance of lot scrap rate, lots before the change.")

    body += "<h2 id='f4'>4. The regression</h2>"
    body += (f"<p>With bar-lot hardness, insert grade and their interaction in the model the MT-04 odds ratio is {ctrl['odds_ratio']:.2f} ({ctrl['or_lower']:.2f} to {ctrl['or_upper']:.2f}, p = {ctrl['p']:.2f}). "
             f"Bar above 32 HRC carries an odds ratio of {models.loc[(CONTROLLED, 'hard'), 'odds_ratio']:.1f} on the standard insert, and the K20 insert removes it "
             f"(interaction odds ratio {models.loc[(CONTROLLED, 'hard:kgrade'), 'odds_ratio']:.2f}). Dispersion falls from {models.loc[('machine alone, all lots', 'mt04'), 'dispersion']:.0f} to {ctrl['dispersion']:.1f}.</p>")
    rows = [["MT-04 alone, lots before the change", "MT-04", int(alone["lots"]), f"{alone['odds_ratio']:.2f} ({alone['or_lower']:.2f} to {alone['or_upper']:.2f})", f"{alone['p']:.3f}", f"{alone['dispersion']:.1f}"]]
    for term in ("mt04", "hard", "hard:kgrade"):
        x = models.loc[(CONTROLLED, term)]
        rows.append(["With hardness, insert and interaction, all lots", TERM[term], int(x["lots"]), f"{x['odds_ratio']:.2f} ({x['or_lower']:.2f} to {x['or_upper']:.2f})", "below 0.001" if x["p"] < 0.001 else f"{x['p']:.3f}", f"{x['dispersion']:.1f}"])
    body += tbl(["Model", "Term", "Lots", "Odds ratio (95% interval)", "p", "Dispersion"], rows) + cap("Table 5. Binomial logit on lot scrap with lot quantity as exposure; standard errors scaled by the dispersion.")

    body += "<h2 id='f5'>5. The mechanism</h2>"
    body += (f"<p>Lots on bar above 32 HRC run with the standard insert scrapped {100 * bad['rate']:.1f}% ({int(bad['lots'])} lots); the other three combinations scrapped {100 * rest['rate'].min():.1f} to {100 * rest['rate'].max():.1f}%. "
             f"That one combination explains {100 * v['interaction']:.1f}% of the between-lot scrap variance of the family; MT-04 explains {100 * v['machine']:.1f}%.</p>")
    body += tbl(["Bar hardness (certificate)", "Insert", "Lots", "of them on MT-04", "Pieces", "Scrap", "Rate (95% interval)"],
                [[x.hardness_band, x.insert_grade, f"{x.lots:.0f}", x.lots_on_mt04, f"{x.pieces:,.0f}", f"{x.scrap:,.0f}", f"{100 * x.rate:.2f}% ({100 * x.lower:.2f} to {100 * x.upper:.2f})"] for x in cells.itertuples()])
    body += cap(f"Table 6. Scrap rate by bar-lot hardness band and insert grade, all {r['lots']} lots.")
    body += figure_interaction(cells, "root_cause_fig2_hardness_by_insert") + cap("Figure 2. Scrap rate by bar hardness band for each insert grade, with the lots in each cell and 95% intervals.")
    body += figure_hardness(f14) + cap("Figure 3. Lot scrap rate against the certificate hardness of the bar lot; colour is the insert grade, filled points are MT-04 lots, the dashed line is 32 HRC.")

    parts = r["by_part"]
    top = parts[parts["on_mt04"] >= 3]
    body += "<h2 id='f6'>6. Why MT-04 carried the scrap</h2>"
    body += (f"<p>{100 * hb.loc[1, 'above_32'] / hb.loc[1, 'lots']:.0f}% of MT-04's lots before the change ran on bar above 32 HRC against {100 * hb.loc[0, 'above_32'] / hb.loc[0, 'lots']:.0f}% on the other five machines. "
             f"MT-04 ran {int(top['on_mt04'].sum())} of its {int(hb.loc[1, 'lots'])} lots on {len(top)} part numbers, whose bar averaged {top['mean_hardness'].min():.1f} to {top['mean_hardness'].max():.1f} HRC; "
             f"the other part numbers averaged {parts[parts['on_mt04'] < 3]['mean_hardness'].mean():.1f} HRC.</p>")
    body += tbl(["", "Lots", "Lots above 32 HRC", "Share", "Mean certificate hardness"],
                [["MT-04", hb.loc[1, "lots"], hb.loc[1, "above_32"], f"{100 * hb.loc[1, 'above_32'] / hb.loc[1, 'lots']:.0f}%", f"{hb.loc[1, 'mean_hardness']:.1f} HRC"],
                 ["The other five machines", hb.loc[0, "lots"], hb.loc[0, "above_32"], f"{100 * hb.loc[0, 'above_32'] / hb.loc[0, 'lots']:.0f}%", f"{hb.loc[0, 'mean_hardness']:.1f} HRC"]])
    body += cap("Table 7. Bar hardness of the lots each machine ran before the change.")

    body += "<h2 id='f7'>7. The change and its confirmation</h2>"
    c14, cal = conf.loc[FAMILY], alla.loc[FAMILY]
    body += (f"<p>The family's scrap rate fell from {100 * c14['rate_before']:.2f}% to {100 * c14['rate_after']:.2f}% on the {int(c14['lots_after'])} lots of the confirmation window "
             f"(difference {100 * c14['difference']:.2f} points, {100 * c14['lower']:.2f} to {100 * c14['upper']:.2f}, p &lt; 0.001) and stands at {100 * cal['rate_after']:.2f}% on all {int(cal['lots_after'])} lots since. "
             f"{CONTROL} did not move: {100 * conf.loc[CONTROL, 'rate_before']:.2f}% and {100 * conf.loc[CONTROL, 'rate_after']:.2f}% over the same dates (p = {conf.loc[CONTROL, 'p']:.2f}). "
             f"{k['capa_id']} was opened on {day(rec['opened'])}, the first lot ran the K20 insert on {day(rec['first_lot'])}, and the action was closed on {day(rec['closed'])}. "
             f"No lot above 32 HRC has run the standard insert since.</p>")
    body += tbl(["Window", "Family", "Before: lots; pieces; scrap; rate", "After: lots; pieces; scrap; rate", "Difference, points (95% interval)", "p"],
                [[x.window, x.family, f"{x.lots_before}; {x.pieces_before:,}; {x.scrap_before:,}; {100 * x.rate_before:.2f}%", f"{x.lots_after}; {x.pieces_after:,}; {x.scrap_after:,}; {100 * x.rate_after:.2f}%",
                  f"{100 * x.difference:.2f} ({100 * x.lower:.2f} to {100 * x.upper:.2f})", "below 0.001" if x.p < 0.001 else f"{x.p:.2f}"] for x in ba.itertuples()])
    body += cap(f"Table 8. Scrap rate before and after the first K20 lot ({day(rec['first_lot'])}); the confirmation window ends at the closure of {k['capa_id']} ({day(rec['closed'])}).")
    body += figure_timeline(f14, r["control"], rec) + cap(f"Figure 4. Scrap rate of every {FAMILY} and {CONTROL} lot by start date, with the dates of {k['capa_id']} and of the first K20 lot.")

    cb, ca = cost.loc["before the change"], cost.loc["after the change"]
    body += "<h2 id='f8'>8. The cost</h2>"
    body += (f"<p>Scrap on the family cost ${cb['scrap_cost']:,.0f} before the change, ${cb['cost_per_month']:,.0f} a month, of which ${cb['cost_on_hard_standard']:,.0f} fell on the {int(bad['lots'])} lots above 32 HRC "
             f"on the standard insert. Since the change it has cost ${ca['scrap_cost']:,.0f}, ${ca['cost_per_month']:,.0f} a month.</p>")
    body += tbl(["Period", "Lots", "Scrap pieces", "Scrap cost", "Per lot", "Per month", "On lots above 32 HRC with the standard insert"],
                [[x.Index, x.lots, f"{x.scrap_pieces:,}", f"${x.scrap_cost:,.0f}", f"${x.cost_per_lot:,.0f}", f"${x.cost_per_month:,.0f}", f"${x.cost_on_hard_standard:,.0f}"] for x in cost.itertuples()])
    body += cap("Table 9. Scrap cost of the family at standard cost, from the scrap transactions.")

    recs = ["Keep the K20 insert on bar above 32 HRC and the receiving hardness check on every F-14 lot, as the corrective action states.",
            "Record the insert grade on every job on the 4140 families.",
            "Add material hardness to the NCR cause-code list.",
            "Specify 4140 bar for the family at 32 HRC or below, or price the K20 insert into lots that arrive above it.",
            "Report F-14 scrap by bar hardness band on the monthly scrap report in place of the machine Pareto."]
    body += "<h2 id='rec'>Recommendation</h2><ul>" + "".join(f"<li>{x}</li>" for x in recs) + "</ul>"
    owner = k["owner"]
    text = k["actions_text"].replace("F-14 bar lots", "bar")
    cm = [[f"{text[0].upper() + text[1:]} ({k['capa_id']})", f"Quality engineer {owner}", f"opened {day(rec['opened'])}; first K20 lot {day(rec['first_lot'])}; closed {day(rec['closed'])}"]]
    cm += [["Insert grade recorded on every job on the other 4140 families", "Production manager", "March 2026"],
           ["4140 bar for the family specified at 32 HRC or below, or the K20 insert priced into lots above it", "Purchasing manager", "March 2026"],
           ["Material hardness added to the NCR cause-code list; F-14 scrap by hardness band on the monthly scrap report", "Quality manager", "March 2026"]]
    target = "Family scrap rate below 1.0% on every bar lot, held through 2026."
    follow = "Scrap rate by bar hardness band on the monthly report. The next bar lot above 32 HRC run on the standard insert, if any, flagged at release."
    body += f"<p>Target: {target}</p>" + tbl(["Action", "Owner", "When"], cm) + f"<p>Follow-up: {follow}</p>"
    body += "<h2 id='method'>Method and data</h2>"
    body += (f"<p class='note'>Lot scrap is the scrap transactions of the lot in pieces over the lot quantity. Regression: binomial logit on lot scrap with lot quantity as exposure; standard errors scaled by the Pearson "
             f"dispersion (quasi-likelihood). Share of between-lot variance: R squared of the lot scrap rate on one indicator, {r['lots']} lots. Before and after: score test of two proportions with the Newcombe interval. "
             f"The split is the start of the first lot run on the K20 insert; the corrective action record supplies the dates. Bar hardness is the certificate value; on the {hc['lots_with_both']} lots with a receiving check "
             f"the two differ by at most {hc['largest']:.1f} HRC and no lot changes band. Every F-14 lot ran from its own bar lot, so the bar lot enters by its supplier and its hardness band. "
             f"Scrap cost is at standard cost. {r['lots']} lots, {int(f14['quantity'].sum()):,} pieces.</p>")

    body += "<h2 id='app'>Appendix</h2>"
    body += tbl(["Model", "Term", "Lots", "Coefficient", "se", "p", "Odds ratio (95% interval)", "Dispersion"],
                [[x.model, TERM[x.term], x.lots, f"{x.coefficient:+.3f}", f"{x.se:.3f}", f"{x.p:.4f}", f"{x.odds_ratio:.2f} ({x.or_lower:.2f} to {x.or_upper:.2f})", f"{x.dispersion:.1f}"] for x in r["models"].itertuples()])
    six = r["six_machines"]
    body += cap(f"Table A1. The regressions in full. Six machines as a factor in the controlled model: F({six['df1']}, {six['df2']}) = {six['F']:.2f}, p = {six['p']:.2f}.")
    body += tbl(["Part", "Lots before the change", "on MT-04", "Mean certificate hardness, HRC", "Lots above 32 HRC"], [[x.part_id, x.lots, x.on_mt04, f"{x.mean_hardness:.1f}", x.above_32] for x in parts.itertuples()])
    body += cap("Table A2. The family's part numbers before the change.")
    body += tbl(["", "Value"], [["Lots with both values", f"{hc['lots_with_both']} of {hc['lots']}"], ["Certificate minus receiving check, mean; sd", f"{hc['mean_diff']:+.2f}; {hc['sd_diff']:.2f} HRC"],
                               ["Largest difference", f"{hc['largest']:.1f} HRC"], ["Lots whose band differs between the two", hc["band_changes"]]])
    body += cap("Table A3. Certificate hardness against the receiving hardness check.")
    body += tbl(["Corrective action", "Opened", "Closed", "Source", "Subject"], [[x.capa_id, str(x.opened)[:10], str(x.closed)[:10], f"{x.source_id}, lot {x.job_id}", x.actions_text] for x in rec["other"].itertuples()])
    body += cap("Table A4. The other corrective actions on the family's lots in the window.")
    body += tbl(["Factor", "Levels", "Lots", "F", "p", "Share of variance"], [[lab[x.factor], x.levels, x.lots, f"{x.F:.2f}", f"{x.p:.4f}", f"{100 * x.eta_squared:.1f}%"] for x in an[an["scope"] == "all lots"].itertuples()])
    body += cap("Table A5. One-way analysis of variance of lot scrap rate, all lots.")

    toc = [("f1", "Shop's view"), ("f2", "By machine"), ("f3", "ANOVA"), ("f4", "Regression"), ("f5", "Mechanism"), ("f6", "MT-04"), ("f7", "Change"), ("f8", "Cost"), ("rec", "Recommendation"),
           ("method", "Method"), ("app", "Appendix")]
    return {"body": body, "toc": toc[:-3], "meta": HEADER}
