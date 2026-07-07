"""Capability as restated: every critical characteristic on SPC, on the subgroups of the report year.

Normal characteristics: Cp and Cpk from the pooled within-subgroup standard deviation, Pp and Ppk from all readings (the mean moving
range where every piece is measured). Bounded characteristics: the percentile method on the best-fitting distribution.
"""
import numpy as np
import pandas as pd

from analytics import stats

BOUNDED = {"runout", "flatness", "true position", "surface finish Ra"}
R5 = ["r1", "r2", "r3", "r4", "r5"]


def model(dbt, session):
    dbt.config(materialized="table")
    year = int(dbt.config.get("report_year") or 2025)
    history = dbt.ref("int_process_history")
    batches = dbt.ref("stg_erp__export_batch")
    h = history.df()
    batch = batches.df()["export_batch_id"].min()
    h = h[h["critical_flag"] & (h["recorded_year"] == year)].sort_values(["characteristic_id", "recorded_at", "subgroup_id"])
    rows = []
    for cid, g in h.groupby("characteristic_id", sort=True):
        first = g.iloc[0]
        size, ctype, usl = int(first["subgroup_size"]), first["characteristic_type"], float(first["usl"])
        lsl = float(first["lsl"]) if pd.notna(first["lsl"]) and ctype not in BOUNDED else np.nan
        if len(g) < 5:
            continue
        row = dict(characteristic_id=cid, part_id=first["part_id"], characteristic_type=ctype, gauge_type=first["gauge_type"], report_year=year, subgroup_size=size,
                   subgroups=len(g), readings=len(g) * size, cp=np.nan, pp=np.nan, fitted_distribution=None)
        if size == 1:
            cap = stats.individuals_capability(g["r1"].to_numpy(), lsl, usl)
            row.update(method="individuals, normal", cp=cap["cp"], cpk=cap["cpk"], pp=cap["pp"], ppk=cap["ppk"], sigma_within=cap["sigma_within"], sigma_overall=cap["sigma_overall"])
        elif ctype in BOUNDED:
            x = g[R5].to_numpy()
            pc = stats.percentile_capability(x.ravel(), usl, floor=float(first["resolution"]) / 2)
            row.update(method="percentile", fitted_distribution=pc["distribution"], cpk=pc["ppk"], ppk=pc["ppk"], sigma_within=np.nan, sigma_overall=float(x.std(ddof=1)))
        else:
            cap = stats.capability(g[R5].to_numpy(), lsl, usl)
            row.update(method="pooled within, normal", cp=cap["cp"], cpk=cap["cpk"], pp=cap["pp"], ppk=cap["ppk"], sigma_within=cap["sigma_within"], sigma_overall=cap["sigma_overall"])
        row["restated_capable"] = bool(min(row["cpk"], row["ppk"]) >= 1.33)
        row["export_batch_id"] = batch
        rows.append(row)
    return pd.DataFrame(rows)
