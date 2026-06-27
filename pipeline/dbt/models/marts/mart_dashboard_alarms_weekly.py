"""SPC alarms by week: subgroups recorded, alarms the module raised and those acknowledged, and the subgroups Western Electric
rules 1 to 4 flag on the same record (limits from the subgroups of each characteristic in the year, as in the capability study)."""
import numpy as np
import pandas as pd

from analytics import stats

R5 = ["r1", "r2", "r3", "r4", "r5"]


def model(dbt, session):
    dbt.config(materialized="table")
    history = dbt.ref("int_process_history")
    batches = dbt.ref("stg_erp__export_batch")
    h = history.df()
    batch = batches.df()["export_batch_id"].min()
    h = h.sort_values(["characteristic_id", "recorded_at", "subgroup_id"]).reset_index(drop=True)
    flagged = np.zeros(len(h), bool)
    for _, g in h.groupby(["characteristic_id", "recorded_year"], sort=True):
        if len(g) < 5:
            continue
        if int(g["subgroup_size"].iloc[0]) == 5:
            x = g[R5].to_numpy()
            pts, sigma = x.mean(axis=1), np.sqrt(x.var(axis=1, ddof=1).mean()) / np.sqrt(5)
        else:
            pts = g["r1"].to_numpy()
            sigma = np.abs(np.diff(pts)).mean() / 1.128
        if not sigma > 0:
            continue
        r1, r2, r3, r4 = stats.western_electric(pts, pts.mean(), sigma)
        flagged[g.index.to_numpy()] = r1 | r2 | r3 | r4
    h["rules_1_to_4"] = flagged
    h["raised"] = (h["alarm_rule_1"] | h["alarm_rule_2"]).astype(bool)
    h["raised_acknowledged"] = h["raised"] & h["acknowledged"].fillna(False).astype(bool)
    day = pd.to_datetime(h["recorded_at"]).dt.normalize()
    h["week_start"] = day - pd.to_timedelta(day.dt.weekday, unit="D")
    w = h.groupby("week_start").agg(subgroups=("subgroup_id", "size"), alarms_raised=("raised", "sum"), alarms_acknowledged=("raised_acknowledged", "sum"),
                                    rules_1_to_4=("rules_1_to_4", "sum")).reset_index()
    days = pd.date_range(pd.Timestamp(day.min().year, 1, 1), pd.Timestamp(day.max().year, 12, 31), freq="D")
    days = days[days.weekday < 5]
    per_week = pd.Series(1, index=days - pd.to_timedelta(days.weekday, unit="D")).groupby(level=0).sum()
    w["weekdays_in_export"] = w["week_start"].map(per_week).fillna(0).astype(int)
    w["working_days"] = w["week_start"].map(h.assign(day=day)[day.dt.weekday < 5].groupby("week_start")["day"].nunique()).fillna(0).astype(int)      # weekdays with subgroups recorded
    for c in ("subgroups", "alarms_raised", "alarms_acknowledged", "rules_1_to_4", "working_days"):
        w[c] = w[c].astype(int)
    w["week_start"] = w["week_start"].dt.date
    w["export_batch_id"] = batch
    return w
