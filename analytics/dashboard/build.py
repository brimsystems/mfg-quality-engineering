"""Quality dashboard: one static page from the marts, monthly grain with a 12-month view and the 24-month trend, weekly grain for the SPC alarms.

Usage: python -m analytics.dashboard.build
"""
import warnings

import numpy as np
import pandas as pd

from analytics import stats
from analytics.data import query
from analytics.s2_capability.s2_capability import restatement
from analytics.s4_sampling.s4_sampling import scorecard
from analytics.style import style as S

VIEW_MONTHS, VIEW_WEEKS = 12, 13
SUPPLIER, FAMILY, CHANGED = "S-017", "F-14", "K20"
PROGRAMS = [("automotive", S.BRAND_BLUE), ("aerospace", S.AMBER), ("medical", S.GREEN), ("industrial", S.ACCENT)]
CAUSES = ["operator", "machine", "material", "tooling", "supplier", "program", "gauge", "other", "no cause code"]
PALETTE = [S.BRAND_BLUE, S.AMBER, S.GREEN, S.ACCENT, S.RED, S.LIGHT_BLUE, "#7A5C99", "#B8A04A", S.GREY]
DETECTION = ["in-process", "final", "CMM", "receiving", "customer"]

# ── data ────────────────────────────────────────────────────────────────────
M = query("select * from marts.mart_dashboard_monthly order by period").set_index("period")
CM = M.index.max()                                             # the current month: the last complete month in the export
V = list(M.index[-VIEW_MONTHS:])
W = query("select * from marts.mart_dashboard_alarms_weekly order by week_start")
W["week_start"] = pd.to_datetime(W["week_start"])
W = W.set_index("week_start")
CW = W.index[W["working_days"] == 5].max()                     # the current week: the last week with five working days
PARTIAL = [t for t in W.index if t > CW]
VW = list(W.index[W.index <= CW][-VIEW_WEEKS:])
batch = M["export_batch_id"].iloc[0]
DEFINITIONS = []


def mname(p, year=True):
    return pd.Timestamp(p + "-01").strftime("%B %Y" if year else "%B")


def mshort(p):
    return pd.Timestamp(p + "-01").strftime("%b %Y")


def wk(ts):
    return f"{ts:%B} {ts.day}, {ts.year}"


def usd(x):
    return f"${x:,.0f}"


def tiles(items):
    return "<div class='kpis'>" + "".join(f"<div class='kpi'><div class='v'>{v_}</div><div class='l'>{l}</div></div>" for v_, l in items) + "</div>"


def tbl(head, rows, scroll=False):
    h = "".join(f"<th>{c}</th>" for c in head)
    b = "".join("<tr>" + "".join(f'<td class="{"num" if i else ""}">{v}</td>' for i, v in enumerate(r)) + "</tr>" for r in rows)
    style = "overflow:auto;max-height:420px" if scroll else "overflow-x:auto"
    return f'<div style="{style}"><table class="data"><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table></div>'


def cap(text):
    return f"<div class='caption'>{text}</div>"


def definition(text):
    DEFINITIONS.append(text)
    return f"<div class='glossary' style='margin-top:6px'>{text}</div>"


def month_axis(ax, periods, step=1):
    ax.set_xticks(range(0, len(periods), step))
    ax.set_xticklabels([mshort(p) for p in periods[::step]], fontsize=8, rotation=45, ha="right")


# ── headline ────────────────────────────────────────────────────────────────
def lots_f14():
    f = query(f"select job_id, start_time, quantity, scrap_quantity, insert_grade from marts.mart_lot_outcomes where family_code = '{FAMILY}' order by start_time, job_id")
    f["start_time"] = pd.to_datetime(f["start_time"])
    change = f[f["insert_grade"] == CHANGED]["start_time"].min()
    f["period"] = np.where(f["start_time"] < change, "before", "after")
    return f, change


def headline(cmp_):
    y = M.loc[V]
    booked = y[["failure_booked", "appraisal", "prevention"]].sum(axis=1)
    c = M.loc[CM]
    open_ = query("select count(*) as n, sum(case when mrb_date is null then 1 else 0 end) as no_mrb, max(case when mrb_date is null then opened end) as opened from marts.mart_ncrs where closed is null").iloc[0]
    capable = cmp_[cmp_["reported_category"] == "capable"]
    lo, hi = stats.jeffreys(int(y["s017_lots_accepted"].sum()), int(y["s017_lots"].sum()))
    f, change = lots_f14()
    after = f[f["period"] == "after"]
    last = M[M["f14_lots"] > 0].index.max()
    items = [(S.pct(booked.sum() / y["revenue"].sum()), f"Cost of quality as booked over revenue<br>{mname(CM, False)}: {S.pct((c.failure_booked + c.appraisal + c.prevention) / c.revenue)}"),
             (f"{y['failure_booked'].sum() / y['scrap_report'].sum():.2f}", f"Failure cost as booked over the scrap report<br>{mname(CM, False)}: {c.failure_booked / c.scrap_report:.2f}"),
             (f"{int(open_.n)}", "Open NCRs"),
             (f"{len(capable)}; {int(capable['restated_capable'].sum())}", "Critical characteristics reported capable; capable as restated"),
             (f"{int(c.s017_lots_accepted)} of {int(c.s017_lots)}", f"{SUPPLIER} lots accepted in {mname(CM, False)}<br>{VIEW_MONTHS} months: {int(y['s017_lots_accepted'].sum())} of {int(y['s017_lots'].sum())} ({S.pct(lo)} to {S.pct(hi)})"),
             (S.pct(after["scrap_quantity"].sum() / after["quantity"].sum(), 2), f"{FAMILY} scrap rate since {change.day} {change:%B %Y}, {len(after)} lots<br>{mname(last, False)}: "
              f"{S.pct(M.loc[last, 'f14_scrap_quantity'] / M.loc[last, 'f14_quantity'], 2)} on {int(M.loc[last, 'f14_lots'])} lots")]
    d = definition(f"Cost of quality as booked: the failure, appraisal and prevention cost lines over quantity shipped at unit price; 12 months to {mname(CM)}; the month beneath. "
                   f"Failure cost over the scrap report: failure cost as booked over the sum of scrap transactions; 12 months to {mname(CM)}; the month beneath. "
                   f"Open NCRs: NCRs not closed at the end of the export; the customer NCR of {pd.Timestamp(open_.opened).day} {pd.Timestamp(open_.opened):%B} has no MRB date and is counted open. "
                   f"Reported capable: Cpk at or above 1.33 on the latest {V[0][:4]} capability report; as restated: the pooled within-subgroup standard deviation, the fitted distribution for bounded characteristics, "
                   f"all {V[0][:4]} subgroups; {len(capable) - int(capable['restated_capable'].sum())} of the {len(capable)} are not capable as restated. "
                   f"{SUPPLIER} lot acceptance: receiving lots accepted over lots received, with the 95% Jeffreys interval on the year. "
                   f"{FAMILY} scrap rate: scrap quantity over lot quantity on the lots started since the {CHANGED} insert; no {FAMILY} lot ended in {mname(CM, False)}.")
    return tiles(items) + d


# ── 1 capability ────────────────────────────────────────────────────────────
def panel_capability(res, cmp_):
    year = V[0][:4]
    cat = res["restated_category"].value_counts()
    capable, marginal = cmp_[cmp_["reported_category"] == "capable"], cmp_[cmp_["reported_category"] == "marginal"]
    t = res.merge(cmp_[["characteristic_id", "cpk_reported", "reported_category"]], on="characteristic_id", how="left")
    t["index"] = np.minimum(t["cpk"], t["ppk"])
    t = t.sort_values(["index", "characteristic_id"])
    f, ax = S.fig(h=4.2, w=6.2)
    for k, color in (("capable", S.GREEN), ("marginal", S.AMBER), ("not capable", S.RED)):
        d = cmp_[cmp_["restated_category"] == k]
        ax.plot(S.sig(d["cpk_reported"]), S.sig(np.minimum(d["cpk"], d["ppk"])), "o", ms=5, color=color, label=f"{k[0].upper() + k[1:]} as restated")
    lim = [0.6, float(max(cmp_["cpk_reported"].max(), np.minimum(cmp_["cpk"], cmp_["ppk"]).max())) + 0.1]
    ax.plot(lim, lim, color="#CCCCCC", lw=1)
    ax.axhline(1.33, color=S.DARK_GREY, lw=0.9, ls="--")
    ax.axvline(1.33, color=S.DARK_GREY, lw=0.9, ls="--")
    ax.set_xlim(lim)
    ax.set_ylim(lim)
    ax.set_xlabel("Cpk as reported")
    ax.set_ylabel("Lower of Cpk and Ppk as restated")
    ax.set_title("Capability as reported and as restated")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    f.tight_layout()
    a = S.save(f, "dashboard_capability", "Reported Cpk against the restated index for the critical characteristics with a capability report")
    rows = [[x.part_id, x.characteristic_id, x.characteristic_type, "" if x.cpk_reported != x.cpk_reported else f"{x.cpk_reported:.2f}", f"{x.cpk:.2f}", f"{x.ppk:.2f}", x.method, x.restated_category] for x in t.itertuples()]
    return ("<h2 id='p1'>1. Capability, critical characteristics</h2>" +
            tiles([(f"{len(capable)}", "Reported capable"), (f"{int(capable['restated_capable'].sum())}", "Of those, capable as restated"),
                   (f"{int(marginal['restated_capable'].sum())} of {len(marginal)}", "Reported marginal that are capable as restated"),
                   (f"{cat.get('capable', 0)}; {cat.get('marginal', 0)}; {cat.get('not capable', 0)}", f"Characteristics on SPC: capable; marginal; not capable as restated")]) +
            a + cap(f"Cpk on the latest {year} capability report against the lower of Cpk and Ppk as restated, {len(cmp_)} critical characteristics with a report; the dashed lines are 1.33.") +
            tbl(["Part", "Characteristic", "Type", "Cpk as reported", "Cpk as restated", "Ppk as restated", "Method", "Category as restated"], rows, scroll=True) +
            cap(f"The {len(t)} critical characteristics on SPC in {year}, lowest restated index first; the reported Cpk is blank where no report was issued in {year}.") +
            definition(f"Capability as reported is the Cpk of the SPC module on the latest {year} report. Capability as restated uses the pooled within-subgroup standard deviation for Cpk, all readings for Ppk and the "
                       f"percentile method on the fitted distribution for bounded characteristics, on all {year} subgroups. Categories as restated: capable where the lower of Cpk and Ppk is at or above 1.33, "
                       f"marginal from 1.0 to 1.33, not capable below 1.0."))


# ── 2 PPM ───────────────────────────────────────────────────────────────────
def panel_ppm():
    p = query("select * from marts.mart_dashboard_ppm_monthly order by period, customer_id")
    g = p.groupby(["period", "program"])[["complaint_quantity", "pieces_shipped"]].sum()
    ppm = (g["complaint_quantity"] * 1e6 / g["pieces_shipped"]).unstack()
    y = p[p["period"].isin(V)]
    yp = y.groupby("program")[["complaint_quantity", "pieces_shipped", "complaints"]].sum()
    f, ax = S.fig(h=3.4, w=9.6, ncols=2)
    for prog, color in PROGRAMS:
        ax[0].plot(range(len(V)), S.sig(ppm.loc[V, prog]), marker="o", ms=3.5, lw=1.5, color=color, label=prog[0].upper() + prog[1:])
        ax[1].plot(range(len(ppm)), S.sig(ppm[prog].rolling(3).mean()), lw=1.4, color=color)
    month_axis(ax[0], V)
    month_axis(ax[1], list(ppm.index), 3)
    ax[0].set_ylabel("PPM")
    ax[0].set_title(f"PPM by program, {VIEW_MONTHS} months")
    ax[1].set_title("Three-month mean, 24 months")
    ax[0].legend(frameon=False, fontsize=8.5)
    f.tight_layout()
    a = S.save(f, "dashboard_ppm", "PPM by program and month, and the three-month mean over 24 months")
    c = y.groupby(["customer_id", "customer_name", "program"])[["complaint_quantity", "pieces_shipped", "complaints"]].sum().reset_index()
    c = c[c["pieces_shipped"] > 0]
    c["ppm"] = c["complaint_quantity"] * 1e6 / c["pieces_shipped"]
    c["median"] = c.groupby("program")["ppm"].transform("median")
    top = c[(c["ppm"] > c["median"]) & (c["complaints"] > 0)].sort_values(["program", "ppm", "customer_id"], ascending=[True, False, True])
    cur = p[p["period"] == CM].groupby("program")[["complaint_quantity", "pieces_shipped"]].sum()
    items = [(f"{yp.loc[prog, 'complaint_quantity'] * 1e6 / yp.loc[prog, 'pieces_shipped']:,.0f}",
              f"PPM, {prog}, {VIEW_MONTHS} months<br>{mname(CM, False)}: {cur.loc[prog, 'complaint_quantity'] * 1e6 / cur.loc[prog, 'pieces_shipped']:,.0f}") for prog, _ in PROGRAMS]
    return ("<h2 id='p2'>2. PPM by customer and month</h2>" + tiles(items) +
            a + cap(f"Complaint quantity per million pieces shipped by program and month, {mname(V[0])} to {mname(CM)}, and the three-month mean from {mname(M.index[2])}.") +
            tbl(["Customer", "Program", "Complaints", "Complaint quantity", "Pieces shipped", "PPM", "Program median"],
                [[x.customer_id, x.program, int(x.complaints), f"{x.complaint_quantity:,.0f}", f"{x.pieces_shipped:,.0f}", f"{x.ppm:,.0f}", f"{x.median:,.0f}"] for x in top.itertuples()]) +
            cap(f"Customers above the median PPM of their program, {VIEW_MONTHS} months to {mname(CM)}.") +
            definition("PPM is the complaint quantity received in the month per million pieces shipped in the month, by the customer on the complaint; a complaint entered twice for the same lot is counted once."))


# ── 3 NCRs ──────────────────────────────────────────────────────────────────
def panel_ncrs():
    n = query("select ncr_id, opened, closed, coalesce(cause_code, 'no cause code') as cause, detected_at from marts.mart_ncrs order by ncr_id")
    n["period"] = pd.to_datetime(n["opened"]).dt.strftime("%Y-%m")
    y = n[n["period"].isin(V)]
    by = y.groupby(["period", "cause"]).size().unstack(fill_value=0).reindex(index=V, columns=CAUSES, fill_value=0)
    det = y["detected_at"].value_counts().reindex(DETECTION, fill_value=0)
    f, ax = S.fig(h=3.6, w=9.6, ncols=2, gridspec_kw=dict(width_ratios=[1.7, 1]))
    base = np.zeros(len(V))
    for k, color in zip(CAUSES, PALETTE):
        ax[0].bar(range(len(V)), by[k].to_numpy(), bottom=base, color=color, width=0.78, label=k[0].upper() + k[1:])
        base = base + by[k].to_numpy()
    month_axis(ax[0], V)
    ax[0].set_ylabel("NCRs opened")
    ax[0].set_title("By cause code as entered")
    ax[0].legend(frameon=False, fontsize=7.5, ncols=3, loc="upper left")
    ax[0].set_ylim(0, float(base.max()) * 1.45)
    ax[1].barh(range(len(det))[::-1], det.to_numpy(), color=S.ACCENT, height=0.6)
    ax[1].set_yticks(range(len(det))[::-1])
    ax[1].set_yticklabels([k[0].upper() + k[1:] for k in det.index])
    ax[1].set_title(f"By detection point, {VIEW_MONTHS} months")
    f.tight_layout()
    a = S.save(f, "dashboard_ncrs", "NCRs opened by month and cause code as entered, and by detection point")
    f, ax = S.fig(h=2.6, w=9.6)
    ax.plot(range(len(M)), M["ncrs_opened"].to_numpy(), color=S.BRAND_BLUE, lw=1.5, marker="o", ms=3, label="Opened in the month")
    ax.plot(range(len(M)), M["ncrs_open_at_month_end"].to_numpy(), color=S.AMBER, lw=1.5, marker="o", ms=3, label="Open at month end")
    month_axis(ax, list(M.index), 3)
    ax.legend(frameon=False, fontsize=9)
    f.tight_layout()
    b = S.save(f, "dashboard_ncrs_trend", "NCRs opened in the month and open at month end, 24 months")
    return ("<h2 id='p3'>3. NCRs by cause and detection point</h2>" +
            tiles([(f"{int(M.loc[CM, 'ncrs_opened'])}", f"NCRs opened in {mname(CM, False)}"), (f"{int(M.loc[CM, 'ncrs_open_at_month_end'])}", "Open at the end of the export"),
                   (S.pct((y["cause"] == "no cause code").mean()), f"With no cause code, of {len(y)} opened in {VIEW_MONTHS} months"),
                   (S.pct(y["cause"].isin(["operator", "machine"]).mean()), "Coded operator or machine")]) +
            a + cap(f"NCRs opened by month and cause code as entered, and by detection point, {mname(V[0])} to {mname(CM)}.") +
            b + cap(f"NCRs opened in the month and open at month end, from {mname(M.index[0])}.") +
            definition("An NCR is counted in the month it was opened, with the cause code as the opener entered it and the detection point on the record. Open at month end: opened on or before the last day of the month "
                       "and not closed by it."))


# ── 4 suppliers ─────────────────────────────────────────────────────────────
def panel_suppliers():
    s = scorecard()
    d = s.sort_values(["defect_rate", "supplier_id"]).reset_index(drop=True)
    f, ax = S.fig(h=3.8, w=9.6, ncols=2, gridspec_kw=dict(width_ratios=[1.9, 1]))
    x = np.arange(len(d))
    color = np.where(d["interval_above_1pct"], S.RED, np.where(d["small_history"], S.GREY, S.BRAND_BLUE))
    for xi, lo, hi, r, c in zip(x, d["defect_lower"], d["defect_upper"], d["defect_rate"], color):
        ax[0].plot([xi, xi], S.sig(np.array([lo, hi]) * 100), color=c, lw=1.3)
        ax[0].plot(xi, float(S.sig(r * 100)), "o", ms=3, color=c)
    ax[0].axhline(1.0, color=S.DARK_GREY, lw=0.9, ls="--")
    ax[0].set_ylim(0, float(np.ceil(d["defect_upper"].max() * 100)))
    ax[0].set_xticks([])
    ax[0].set_xlabel(f"{len(d)} suppliers, lowest defect rate first")
    ax[0].set_ylabel("Defect rate in the samples, %")
    ax[0].set_title("Defect rate with 95% intervals")
    y = M.loc[V]
    ax[1].bar(range(len(V)), y["s017_lots"].to_numpy(), color=S.LIGHT_BLUE, width=0.78, label="Lots received")
    ax[1].bar(range(len(V)), y["s017_lots_accepted"].to_numpy(), color=S.BRAND_BLUE, width=0.5, label="Accepted")
    month_axis(ax[1], V, 2)
    ax[1].set_title(f"{SUPPLIER} lots by month")
    ax[1].legend(frameon=False, fontsize=8.5)
    f.tight_layout()
    a = S.save(f, "dashboard_suppliers", "Supplier defect rates with Jeffreys intervals against 1%, and S-017 lots received and accepted by month")
    sel = s[s["interval_above_1pct"] | (s["scorecard_rank_as_published"] > s["scorecard_rank_as_published"].max() - 5)].sort_values("scorecard_rank_as_published")
    rows = [[x_.supplier_id, x_.commodity, int(x_.lots), f"{x_.pieces_sampled:,.0f}", f"{100 * x_.defect_rate:.2f}% ({100 * x_.defect_lower:.2f} to {100 * x_.defect_upper:.2f})",
             f"{100 * x_.acceptance_rate:.1f}% ({100 * x_.acceptance_lower:.1f} to {100 * x_.acceptance_upper:.1f})", int(x_.scorecard_rank_as_published),
             "" if x_.restated_rank != x_.restated_rank else int(x_.restated_rank)] for x_ in sel.itertuples()]
    lo, hi = stats.jeffreys(int(y["s017_lots_accepted"].sum()), int(y["s017_lots"].sum()))
    return ("<h2 id='p4'>4. Supplier scorecard</h2>" +
            tiles([(f"{int(s['interval_above_1pct'].sum())} of {len(s)}", "Suppliers with the defect-rate interval above 1%"),
                   (f"{int(y['s017_lots_accepted'].sum())} of {int(y['s017_lots'].sum())}", f"{SUPPLIER} lots accepted, {VIEW_MONTHS} months ({S.pct(lo)} to {S.pct(hi)})"),
                   (f"{int(s['small_history'].sum())}", "Suppliers ranked on fewer than five lots")]) +
            a + cap(f"Defect rate found in the receiving samples by supplier with the 95% interval, {mname(M.index[0])} to {mname(CM)} (red: interval above 1%; grey: fewer than five lots), "
                    f"and {SUPPLIER} lots received and accepted by month.") +
            tbl(["Supplier", "Commodity", "Lots", "Pieces sampled", "Defect rate (95% interval)", "Lot acceptance (95% interval)", "Published rank", "Rank by defect rate"], rows) +
            cap("The suppliers with the defect-rate interval above 1% and the five lowest on the published scorecard; the rank by defect rate is blank under five lots.") +
            definition("Defect rate is defects found over pieces sampled at receiving; lot acceptance is lots accepted over lots received; intervals are 95% Jeffreys intervals over the 24 months. The published rank is "
                       "the rank on the scorecard purchasing publishes; the rank by defect rate leaves out suppliers with fewer than five lots."))


# ── 5 cost of quality ───────────────────────────────────────────────────────
def panel_cost():
    y, c = M.loc[V], M.loc[CM]
    booked = y[["failure_booked", "appraisal", "prevention"]].sum(axis=1)

    def bars(ax, d):
        base = np.zeros(len(d))
        for col, color, label in (("failure_booked", S.BRAND_BLUE, "Failure"), ("appraisal", S.ACCENT, "Appraisal"), ("prevention", S.AMBER, "Prevention")):
            v = S.sig(d[col].to_numpy() / 1000)
            ax.bar(range(len(d)), v, bottom=base, color=color, width=0.78, label=label)
            base = base + v
        ax.plot(range(len(d)), S.sig(d["scrap_report"].to_numpy() / 1000), color=S.RED, lw=1.5, marker="o", ms=3, label="Scrap report")
        return base
    f, ax = S.fig(h=3.5, w=9.6, ncols=2)
    top = bars(ax[0], y)
    month_axis(ax[0], V)
    ax[0].set_ylim(0, float(top.max()) * 1.3)
    ax[0].set_ylabel("$ thousand")
    ax[0].set_title(f"As booked, {VIEW_MONTHS} months")
    ax[0].legend(frameon=False, fontsize=8, ncols=4, loc="upper left")
    bars(ax[1], M)
    month_axis(ax[1], list(M.index), 3)
    ax[1].set_title("24 months")
    f.tight_layout()
    a = S.save(f, "dashboard_cost", "Cost of quality as booked by category and month with the scrap report, 12 and 24 months")
    return ("<h2 id='p5'>5. Cost of quality</h2>" +
            tiles([(S.pct(booked.sum() / y["revenue"].sum()), f"Booked total over revenue, {VIEW_MONTHS} months<br>{mname(CM, False)}: {S.pct((c.failure_booked + c.appraisal + c.prevention) / c.revenue)}"),
                   (f"{y['failure_booked'].sum() / y['scrap_report'].sum():.2f}", f"Failure cost over the scrap report, {VIEW_MONTHS} months<br>{mname(CM, False)}: {c.failure_booked / c.scrap_report:.2f}"),
                   (S.pct(y["prevention"].sum() / booked.sum()), f"Prevention share of the booked total, {VIEW_MONTHS} months"),
                   (f"{int(y['rework_ncrs_without_booked_hours'].sum())} of {int(y['rework_ncrs'].sum())}", f"Rework NCRs without hours on the rework code, {VIEW_MONTHS} months")]) +
            a + cap(f"Failure, appraisal and prevention cost as booked by month with the scrap report as the line, {mname(V[0])} to {mname(CM)} and from {mname(M.index[0])}.") +
            definition("Cost of quality is the failure, appraisal and prevention cost lines as accounting books them; re-inspection booked against NCRs is counted as failure. The scrap report is the sum of scrap "
                       "transactions and is a component of failure cost. Revenue is quantity shipped at unit price by ship date. Rework NCRs are counted in the month of the MRB date."))


# ── 6 calibration ───────────────────────────────────────────────────────────
def panel_calibration():
    k = query("select * from marts.mart_dashboard_calibration_month_end order by period, gauge_type")
    c = k[k["period"] == CM]
    t = k.groupby("period")[["gauges_active", "gauges_overdue", "gauges_due_in_month", "gauges_due_in_month_done", "gauges_due_next_month", "gauges_out_of_service", "gauges_lost"]].sum()
    nxt = (pd.Timestamp(CM + "-01") + pd.offsets.MonthBegin(1)).strftime("%B %Y")
    assigned = int(query("select count(distinct c.gauge_id) as n from staging.stg_qms__characteristics c join staging.stg_calibration__gauges g on g.gauge_id = c.gauge_id where g.status = 'lost'")["n"].iloc[0])
    d = c[(c["gauges_overdue"] + c["gauges_out_of_service"] + c["gauges_lost"]) > 0].sort_values(["gauges_active", "gauge_type"], ascending=[False, True])
    f, ax = S.fig(h=3.3, w=9.6, ncols=2)
    yy = np.arange(len(d))[::-1]
    left = np.zeros(len(d))
    for col, color, label in (("gauges_overdue", S.RED, "Overdue"), ("gauges_out_of_service", S.GREY, "Out of service"), ("gauges_lost", S.AMBER, "Lost")):
        ax[0].barh(yy, d[col].to_numpy(), left=left, color=color, height=0.6, label=label)
        left = left + d[col].to_numpy()
    ax[0].set_yticks(yy)
    ax[0].set_yticklabels([g[0].upper() + g[1:] for g in d["gauge_type"]], fontsize=8.5)
    ax[0].set_xlabel("Gauges")
    ax[0].set_title(f"By gauge type at the end of {mname(CM)}")
    ax[0].legend(frameon=False, fontsize=8.5)
    ax[0].xaxis.grid(True, color="#EEEEEE")
    ax[1].plot(range(len(t)), S.sig(100 * t["gauges_overdue"] / t["gauges_active"]), color=S.RED, lw=1.5, marker="o", ms=3)
    month_axis(ax[1], list(t.index), 3)
    ax[1].set_ylim(0, 8)
    ax[1].set_ylabel("% of active gauges")
    ax[1].set_title("Overdue at month end, 24 months")
    f.tight_layout()
    a = S.save(f, "dashboard_calibration", "Gauges overdue, out of service and lost by gauge type, and the overdue share at each month end")
    tc = t.loc[CM]
    return ("<h2 id='p6'>6. Gauge calibration status</h2>" +
            tiles([(f"{int(tc.gauges_due_next_month)}", f"Gauges due in {nxt}<br>{mname(CM, False)}: {int(tc.gauges_due_in_month_done)} of {int(tc.gauges_due_in_month)} due and done by month end"),
                   (f"{int(tc.gauges_overdue)}", f"Gauges overdue at the end of {mname(CM, False)}, of {int(tc.gauges_active)} active"),
                   (f"{int(tc.gauges_out_of_service)}", "Out of service"), (f"{int(tc.gauges_lost)}; {assigned}", "Lost; still assigned in the characteristics master")]) +
            a + cap(f"Gauges overdue, out of service and lost by gauge type at the end of {mname(CM)}, and the share of active gauges overdue at each month end from {mname(M.index[0])}.") +
            definition("A gauge is overdue at a month end when a calibration due before it was not done by it; gauges out of service or lost at the month end are left out of the active count. Due in a month: a calibration "
                       "with its due date in the month, not done by the end of the month before."))


# ── 7 SPC alarms ────────────────────────────────────────────────────────────
def panel_alarms():
    c = W.loc[CW]
    series = (("alarms_raised", S.BRAND_BLUE, "Raised by the module"), ("alarms_acknowledged", S.GREEN, "Acknowledged"), ("rules_1_to_4", S.AMBER, "Rules 1 to 4 on the same subgroups"))
    f, ax = S.fig(h=3.5, w=9.6, ncols=2)
    vp = VW + PARTIAL
    for col, color, label in series:
        ax[0].plot(range(len(VW)), W.loc[VW, col].to_numpy(), color=color, marker="o", ms=3.5, lw=1.6, label=label)
        if PARTIAL:
            ax[0].plot([len(VW) - 1 + k for k in range(len(PARTIAL) + 1)], W.loc[[VW[-1]] + PARTIAL, col].to_numpy(), color=color, marker="o", ms=3.5, lw=1.2, ls=":", alpha=0.45, markerfacecolor="white")
        ax[1].plot(W.index[W.index <= CW], W.loc[W.index <= CW, col].rolling(4).mean().to_numpy(), color=color, lw=1.3)
    ax[0].set_xticks(range(len(vp)))
    ax[0].set_xticklabels([f"{t:%b} {t.day}" for t in vp], fontsize=7.5, rotation=45, ha="right")
    ax[0].axvline(len(VW) - 1, color=S.GREY, lw=0.8, ls=":")
    ax[0].set_ylabel("Subgroups")
    ax[0].set_title(f"By week, {VIEW_WEEKS} weeks")
    ax[0].legend(frameon=False, fontsize=8.5)
    ax[1].set_title("Four-week mean, 24 months")
    ax[1].tick_params(axis="x", labelsize=8)
    f.tight_layout()
    a = S.save(f, "dashboard_alarms", "SPC alarms raised, acknowledged and flagged by rules 1 to 4 by week")
    note = "" if not PARTIAL else f" The week of {wk(PARTIAL[0])} has {int(W.loc[PARTIAL[0], 'working_days'])} working days and is drawn lighter."
    rows = [[f"{t:%b} {t.day}, {t.year}", f"{int(W.loc[t, 'subgroups']):,}", int(W.loc[t, "alarms_raised"]), int(W.loc[t, "alarms_acknowledged"]), int(W.loc[t, "rules_1_to_4"])] for t in VW]
    return ("<h2 id='p7'>7. SPC alarms</h2>" +
            tiles([(f"{int(c.alarms_raised)}", f"Alarms raised, week of {wk(CW)}, on {int(c.subgroups):,} subgroups"), (f"{int(c.alarms_acknowledged)}", "Of those, acknowledged"),
                   (f"{int(c.rules_1_to_4)}", "Subgroups flagged by rules 1 to 4"),
                   (f"{int(W.loc[VW, 'alarms_raised'].sum()):,}; {int(W.loc[VW, 'rules_1_to_4'].sum()):,}", f"Raised; flagged by rules 1 to 4, {VIEW_WEEKS} weeks, on {int(W.loc[VW, 'subgroups'].sum()):,} subgroups")]) +
            a + cap(f"Alarms the module raised, those acknowledged and the subgroups flagged by rules 1 to 4, by week from the week of {wk(VW[0])}, and the four-week mean from the week of {wk(W.index[3])}.{note}") +
            tbl(["Week of", "Subgroups recorded", "Alarms raised", "Acknowledged", "Flagged by rules 1 to 4"], rows) + cap(f"Subgroups recorded and alarms by week, {VIEW_WEEKS} weeks.") +
            definition("Alarms raised are the subgroups the SPC module flagged on Western Electric rules 1 and 2; acknowledged are those the machinist acknowledged. Rules 1 to 4 are applied to the same subgroups with the "
                       "centre and limits from the subgroups of each characteristic in the year. Weeks start on Monday; the current week is the last week with five working days."))


# ── 8 F-14 scrap ────────────────────────────────────────────────────────────
def panel_f14():
    f_, change = lots_f14()
    b, a_ = f_[f_["period"] == "before"], f_[f_["period"] == "after"]
    f, ax = S.fig(h=3.2, w=9.6)
    for d, color, label in ((b, S.RED, "Before"), (a_, S.GREEN, f"Since the {CHANGED} insert")):
        ax.plot(d["start_time"], S.sig(100 * d["scrap_quantity"] / d["quantity"]), "o", ms=4, color=color, label=label)
    ax.axvline(change, color=S.AMBER, lw=1.1, ls="--")
    ax.annotate(f"{change.day} {change:%B %Y}", (change, 0.97), xycoords=("data", "axes fraction"), rotation=90, va="top", ha="right", fontsize=8.5, color=S.DARK_GREY)
    ax.set_ylabel("Lot scrap rate, %")
    ax.set_xlabel("Lot start")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    f.tight_layout()
    a = S.save(f, "dashboard_f14", "Scrap rate of each F-14 lot by start date with the insert change marked")
    return (f"<h2 id='p8'>8. {FAMILY} scrap</h2>" +
            tiles([(S.pct(a_["scrap_quantity"].sum() / a_["quantity"].sum(), 2), f"Scrap rate since {change.day} {change:%B %Y}, {len(a_)} lots"),
                   (S.pct(b["scrap_quantity"].sum() / b["quantity"].sum(), 2), f"Before, {len(b)} lots")]) +
            a + cap(f"Scrap rate of each {FAMILY} lot by start date; the dashed line is the first lot on the {CHANGED} insert, {change.day} {change:%B %Y}.") +
            definition(f"Lot scrap rate is scrap quantity over lot quantity. The periods divide at the start of the first lot run on the {CHANGED} insert."))


# ── page ────────────────────────────────────────────────────────────────────
def main():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        r = restatement()
    res, cmp_ = r["restated"], r["compared"]
    partial = f"; the week of {PARTIAL[0]:%B} {PARTIAL[0].day} is partial" if PARTIAL else ""
    meta = (f"Precision machining shop, about 150 employees, IATF 16949 and AS9100, one plant. {mname(CM)} (current month); {VIEW_MONTHS}-month view from {mname(V[0])}; trend from {mname(M.index[0])}; "
            f"week of {wk(CW)} (current week{partial}).<br>Sources: ERP, QMS with its SPC module, CMM software, calibration system and accounting exports (batch {batch}). US dollars.")
    body = "\n".join([headline(cmp_), panel_capability(res, cmp_), panel_ppm(), panel_ncrs(), panel_suppliers(), panel_cost(), panel_calibration(), panel_alarms(), panel_f14()])
    toc = [("p1", "Capability"), ("p2", "PPM"), ("p3", "NCRs"), ("p4", "Suppliers"), ("p5", "Cost of quality"), ("p6", "Calibration"), ("p7", "SPC alarms"), ("p8", "F-14 scrap")]
    out = S.DOCS / "dashboard"
    out.mkdir(parents=True, exist_ok=True)
    (out / "index.html").write_text(S.shell("Quality dashboard", "Dashboard", meta, body, toc), encoding="utf8", newline="\n")
    return out / "index.html"


if __name__ == "__main__":
    print(main())
