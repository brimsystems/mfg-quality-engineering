"""Cost of quality: the four categories from the cost lines, each line reconciled to its source table, and the cost
attributable to the findings on capability, root cause and supplier quality."""
import warnings

import numpy as np
import pandas as pd

from analytics.data import query

YEARS = (2024, 2025)
LENGTH = "C-11909-01"              # the milled length of the capability study
FAMILY = "F-14"
SUPPLIER = "S-017"


def compute():
    lines = query("select * from marts.mart_cost_of_quality_lines order by line_id")
    rates = query("select role, \"year\", loaded_rate from marts.mart_labor_rates").set_index(["role", "year"])["loaded_rate"]
    ncr = query("select * from marts.mart_ncrs order by ncr_id")
    ncr["year"] = pd.to_datetime(ncr["mrb_date"]).dt.year
    comp = query("select * from marts.mart_complaints order by complaint_id")
    comp["year"] = pd.to_datetime(comp["received_date"]).dt.year
    lots = query("select * from marts.mart_lot_outcomes order by job_id")
    tx = query("select job_id, cost, quantity, reason_code, transaction_date from staging.stg_erp__scrap_transactions order by transaction_id")
    tx["year"] = pd.to_datetime(tx["transaction_date"]).dt.year
    out = {}
    # the four categories by month
    monthly = lines.groupby(["period", "cost_group"])["amount"].sum().unstack(fill_value=0.0).reset_index()
    out["monthly"] = monthly
    by_line = lines.groupby(["cost_group", "cost_line", "period_year"]).agg(lines=("line_id", "size"), amount=("amount", "sum"), hours=("line_hours", "sum")).reset_index()
    out["by_line"] = by_line
    # reconciliation of each line to its source table
    rec = []

    def add(line, year, source, n, amount, hours=np.nan):
        sel = lines[(lines["cost_line"] == line) & (lines["period_year"] == year)]
        rec.append(dict(cost_line=line, year=year, lines=len(sel), line_amount=float(sel["amount"].sum()), line_hours=float(sel["line_hours"].sum()), source=source, source_records=int(n),
                        source_amount=float(amount), source_hours=float(hours) if hours == hours else np.nan))
    cmm = query("select substr(period, 1, 4) as y, sum(reports) as reports from marts.mart_cmm_reports_monthly group by 1 order by 1").set_index("y")["reports"]
    cal = query("select * from marts.mart_calibration_events where performed_by = 'laboratory' and done_date is not null order by calibration_id")
    cal["year"] = pd.to_datetime(cal["done_date"]).dt.year
    for y in YEARS:
        n_y = ncr[ncr["year"] == y]
        c_y = comp[(comp["year"] == y) & comp["credit_issued"].notna()]
        add("scrap", y, "scrap transactions", (tx["year"] == y).sum(), tx.loc[tx["year"] == y, "cost"].sum())
        rw = n_y[n_y["rework_hours_booked"] > 0]
        add("rework labor", y, "NCR rework hours at the machinist rate", len(rw), rw["rework_hours_booked"].sum() * rates[("machinist", y)], rw["rework_hours_booked"].sum())
        ri = n_y[n_y["reinspection_hours"] > 0]
        add("re-inspection", y, "NCR re-inspection hours at the inspector rate", len(ri), ri["reinspection_hours"].sum() * rates[("inspector", y)], ri["reinspection_hours"].sum())
        so = n_y[n_y["sorting_hours"] > 0]
        add("sorting and containment", y, "NCR sorting hours; complaint containment and sorting hours", len(so) + len(c_y),
            (so["sorting_hours"].sum() + c_y["sorting_hours"].sum()) * rates[("inspector", y)] + c_y["containment_cost"].sum(), so["sorting_hours"].sum() + c_y["sorting_hours"].sum())
        add("customer credit", y, "complaint credits", len(c_y), c_y["credit_issued"].sum())
        add("return freight", y, "complaint return freight", len(c_y), c_y["return_freight_cost"].sum())
        sel = lines[(lines["cost_line"] == "CMM time") & (lines["period_year"] == y)]
        add("CMM time", y, "CMM reports (hours per report and rate per hour as booked)", cmm.get(str(y), 0), sel["amount"].sum(), sel["line_hours"].sum())
        cl = lines[(lines["cost_line"] == "calibration") & (lines["period_year"] == y)]
        lab, tech = cl[cl["source_type"] == "invoice"], cl[cl["source_type"] == "timesheet"]
        rec.append(dict(cost_line="calibration, laboratory", year=y, lines=len(lab), line_amount=float(lab["amount"].sum()), line_hours=np.nan, source="laboratory calibration events (count; the record carries no cost)",
                        source_records=int((cal["year"] == y).sum()), source_amount=float(lab["amount"].sum()), source_hours=np.nan))
        rec.append(dict(cost_line="calibration, technician time", year=y, lines=len(tech), line_amount=float(tech["amount"].sum()), line_hours=float(tech["line_hours"].sum()), source="timesheets", source_records=0,
                        source_amount=np.nan, source_hours=np.nan))
        for line in ("inspection labor", "training", "SPC software", "supplier audit travel"):
            add(line, y, "timesheets" if line == "inspection labor" else "invoices", 0, np.nan)
    rec = pd.DataFrame(rec)
    rec["difference"] = rec["line_amount"] - rec["source_amount"]
    rec["cost_group"] = rec["cost_line"].map(lambda k: "appraisal" if k.startswith(("CMM", "calibration", "inspection")) else "prevention" if k in ("training", "SPC software", "supplier audit travel") else "failure")
    out["reconciliation"] = rec
    out["cmm_rate"] = dict(hours_per_report=float(lines[lines["cost_line"] == "CMM time"]["line_hours"].sum() / cmm.sum()),
                           rate=float(lines[lines["cost_line"] == "CMM time"]["amount"].sum() / lines[lines["cost_line"] == "CMM time"]["line_hours"].sum()))
    unfound = lines[lines["source_found"] == False]  # noqa: E712
    out["sources_not_found"] = len(unfound)
    # rework left on the production job: hours over standard on lots with a rework NCR that has no booked hours
    lot = lots.set_index("job_id")
    rw_all = ncr[(ncr["disposition"] == "rework") & ncr["job_id"].notna() & ncr["year"].isin(YEARS)]
    unb_ncrs = rw_all[rw_all["rework_hours_booked"].isna()]
    unb = unb_ncrs.drop_duplicates("job_id").copy()
    unb["hours_over_standard"] = (unb["job_id"].map(lot["actual_hours"]) - unb["job_id"].map(lot["standard_hours"])).clip(lower=0)
    unb["amount"] = [h * rates[("machinist", int(y))] for h, y in zip(unb["hours_over_standard"], unb["year"])]
    out["rework"] = pd.DataFrame([dict(year=y, rework_ncrs=int((rw_all["year"] == y).sum()), booked_ncrs=int(((rw_all["year"] == y) & rw_all["rework_hours_booked"].notna()).sum()),
                                       booked_hours=float(rw_all[rw_all["year"] == y]["rework_hours_booked"].sum()), booked_amount=float(rw_all[rw_all["year"] == y]["rework_hours_booked"].sum() * rates[("machinist", y)]),
                                       unbooked_ncrs=int((unb_ncrs["year"] == y).sum()), unbooked_lots=int((unb["year"] == y).sum()), estimated_hours=float(unb[unb["year"] == y]["hours_over_standard"].sum()),
                                       estimated_amount=float(unb[unb["year"] == y]["amount"].sum())) for y in YEARS])
    # totals, shares, revenue
    lots["ship_year"] = pd.to_datetime(lots["ship_date"]).dt.year
    lots["revenue"] = lots["quantity_good"] * lots["unit_price"]
    rows = []
    for label, ys in (("2024", (2024,)), ("2025", (2025,)), ("24 months", YEARS)):
        sel = lines[lines["period_year"].isin(ys)]
        g = sel.groupby("cost_group")["amount"].sum()
        est = float(out["rework"][out["rework"]["year"].isin(ys)]["estimated_amount"].sum())
        scrap_report = float(tx[tx["year"].isin(ys)]["cost"].sum())
        revenue = float(lots[lots["ship_year"].isin(ys)]["revenue"].sum())
        failure_booked = float(g.get("failure", 0))
        total_booked = float(g.sum())
        rows.append(dict(period=label, revenue=revenue, scrap_report=scrap_report, failure_booked=failure_booked, rework_estimate=est, failure=failure_booked + est, appraisal=float(g.get("appraisal", 0)),
                         prevention=float(g.get("prevention", 0)), total_booked=total_booked, total=total_booked + est))
    t = pd.DataFrame(rows)
    for c in ("failure", "appraisal", "prevention"):
        t[f"{c}_share"] = t[c] / t["total"]
    t["failure_booked_share"], t["appraisal_booked_share"], t["prevention_booked_share"] = t["failure_booked"] / t["total_booked"], t["appraisal"] / t["total_booked"], t["prevention"] / t["total_booked"]
    traced = rec[rec["source_amount"].notna()].groupby(["year", "cost_group"])["line_amount"].sum()
    out["traced"] = {y: {g: float(traced.get((y, g), 0.0)) for g in ("failure", "appraisal", "prevention")} for y in YEARS}
    t["over_revenue"], t["booked_over_revenue"] = t["total"] / t["revenue"], t["total_booked"] / t["revenue"]
    t["failure_over_scrap"], t["failure_booked_over_scrap"] = t["failure"] / t["scrap_report"], t["failure_booked"] / t["scrap_report"]
    out["totals"] = t
    # attributable to the capability study: the milled length
    src = lines[lines["source_type"] == "NCR"].merge(ncr[["ncr_id", "characteristic_id", "part_id", "family_code", "job_id"]], left_on="source_record", right_on="ncr_id", how="left")
    part = ncr.loc[ncr["characteristic_id"] == LENGTH, "part_id"].iloc[0]
    length_lines = src[src["part_id"] == part].assign(cited=lambda d: np.where(d["characteristic_id"] == LENGTH, "the length", "other on the part"))
    out["length"] = length_lines.groupby(["cited", "cost_line", "period_year"]).agg(lines=("line_id", "size"), amount=("amount", "sum"), hours=("line_hours", "sum")).reset_index()
    out["length_part"] = part
    assert not (lots[lots["part_id"] == part]["family_code"] == FAMILY).any()
    ln = ncr[(ncr["characteristic_id"] == LENGTH) & (ncr["disposition"] == "rework") & ncr["year"].isin(YEARS)]
    out["length_rework"] = {y: dict(ncrs=int((ln["year"] == y).sum()), without_hours=int(((ln["year"] == y) & ln["rework_hours_booked"].isna()).sum())) for y in YEARS}
    out["length_other"] = sorted(x for x in length_lines.loc[length_lines["cited"] != "the length", "characteristic_id"].dropna().unique())
    # attributable to the root cause study: F-14 scrap before and after the first K20 lot
    f = lots[lots["family_code"] == FAMILY].copy()
    f["start_time"] = pd.to_datetime(f["start_time"])
    change = f[f["insert_grade"] == "K20"]["start_time"].min()
    f["period"] = np.where(f["start_time"] < change, "before", "after")
    mb, ma = (change - pd.Timestamp("2024-01-01")).days / 30.4375, (pd.Timestamp("2026-01-01") - change).days / 30.4375
    out["scrap14"] = pd.DataFrame([dict(period=k, lots=int((f["period"] == k).sum()), scrap_cost=float(f[f["period"] == k]["scrap_cost"].sum()), months=m,
                                   per_month=float(f[f["period"] == k]["scrap_cost"].sum() / m)) for k, m in (("before", mb), ("after", ma))])
    ftx = tx[tx["job_id"].isin(f["job_id"])]
    out["scrap14_by_year"] = ftx.groupby("year")["cost"].sum().to_dict()
    out["scrap14_change"] = change
    # attributable to the sampling study: receiving hours under the plan as tabled and under the switching rules; the escapes
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from analytics.sampling.study import compute as receiving
        plan = receiving()
    hrs, si = plan["hours"], plan["switching_by_interval"]
    out["receiving"] = dict(minutes_per_piece=hrs["minutes_per_piece"], cost_per_hour=hrs["cost_per_hour"], booked_hours=hrs["booked_hours"], booked_amount=hrs["booked_amount"], pieces_taken=hrs["pieces"],
                     table_pieces=float(si["table_pieces"].sum()), switched_pieces=float(si["switched_pieces"].sum()), table_hours=float(si["table_pieces"].sum() * hrs["hours_per_piece"]),
                     switched_hours=float(si["switched_pieces"].sum() * hrs["hours_per_piece"]))
    esc = plan["escapes"]
    esc["year"] = pd.to_datetime(esc["received_date"]).dt.year
    # failure cost by line and year with the part that falls under the three findings
    fl = lines[lines["cost_group"] == "failure"].groupby(["cost_line", "period_year"])["amount"].sum()
    e_y = esc.groupby("year")[["credit_issued", "containment_cost", "return_freight_cost"]].sum()
    length_by_line = out["length"][out["length"]["cited"] == "the length"].set_index(["cost_line", "period_year"])["amount"]
    rows = []
    for y in YEARS:
        found = {"scrap": ("F-14 scrap; the length", out["scrap14_by_year"].get(y, 0.0) + length_by_line.get(("scrap", y), 0.0)), "customer credit": ("S-017 escapes", e_y["credit_issued"].get(y, 0.0)),
                 "sorting and containment": ("S-017 escapes; the length", e_y["containment_cost"].get(y, 0.0) + length_by_line.get(("sorting and containment", y), 0.0)),
                 "rework labor": ("the length", length_by_line.get(("rework labor", y), 0.0)), "return freight": ("S-017 escapes", e_y["return_freight_cost"].get(y, 0.0)), "re-inspection": ("the length", length_by_line.get(("re-inspection", y), 0.0))}
        for k, (what, v) in found.items():
            rows.append(dict(year=y, cost_line=k, amount=float(fl[(k, y)]), finding=what, attributed=float(v), remaining=float(fl[(k, y)] - v)))
    out["failure_lines"] = pd.DataFrame(rows)
    # failure by line and month, with the F-14 scrap of the month
    out["failure_monthly"] = lines[lines["cost_group"] == "failure"].groupby(["period", "cost_line"])["amount"].sum().unstack(fill_value=0.0).reset_index()
    ftx = ftx.assign(period=pd.to_datetime(ftx["transaction_date"]).dt.strftime("%Y-%m"))
    out["f14_scrap_monthly"] = ftx.groupby("period")["cost"].sum().to_dict()
    out["escapes"] = esc.groupby("year").agg(complaints=("complaint_id", "size"), credit=("credit_issued", "sum"), containment=("containment_cost", "sum"), freight=("return_freight_cost", "sum")).reset_index()
    return out
