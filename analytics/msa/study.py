"""Measurement system analysis: gauge R&R on the bore gauge and the air gauge, bias and linearity, attribute agreement,
and the cross-checks against the production record."""
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats as st

from analytics import stats
from analytics.data import query, worksheet

YEAR = 2025
NOMINAL = 19.05
R5 = ["r1", "r2", "r3", "r4", "r5"]
SEED = 20250101


def gauge_studies():
    out = {}
    for key, name in (("bore", "gauge_rr_bore_gauge.csv"), ("air", "gauge_rr_air_gauge.csv")):
        head, t = worksheet(name)
        tol = float(head["tolerance_mm"])
        g = stats.gauge_rr(t, tol)
        g["average_range"] = stats.gauge_rr_average_range(t, tol)
        g["header"], g["tolerance"], g["readings"], g["worksheet"] = head, tol, len(t), t
        g["pct_tolerance_515"] = 100 * 5.15 * g["grr_sd"] / tol
        by_op = t.groupby("operator")["reading"].agg(["mean", "count"])
        ranges = t.groupby(["operator", "part"])["reading"].agg(lambda s: s.max() - s.min()).groupby(level=0).mean()
        g["by_operator"] = by_op.assign(mean_range=ranges).reset_index()
        out[key] = g
    return out


def bias_linearity():
    c = query("select * from marts.mart_gauge_checkpoints order by gauge_id, done_date, point_no")
    bore = c[c["gauge_type"] == "bore gauge"]
    rows = []
    for cid, g in bore.groupby("calibration_id", sort=False):
        lr = st.linregress(g["reference_value"], g["as_found_error"])
        mid = g.iloc[len(g) // 2]
        rows.append(dict(calibration_id=cid, due_date=g["due_date"].iloc[0], done_date=g["done_date"].iloc[0], result=g["result"].iloc[0], past_due=bool(g["done_past_due"].iloc[0]),
                         points=len(g), bias_mid_range=mid["as_found_error"], mean_bias=g["as_found_error"].mean(), largest_error=g["as_found_error"].abs().max(),
                         tolerance=g["tolerance"].iloc[0], slope=lr.slope, slope_p=lr.pvalue, r_squared=lr.rvalue ** 2, intercept=lr.intercept,
                         slope_lower=lr.slope - st.t.ppf(0.975, len(g) - 2) * lr.stderr, slope_upper=lr.slope + st.t.ppf(0.975, len(g) - 2) * lr.stderr))
    records = pd.DataFrame(rows)
    out_tol = records[records["largest_error"] > records["tolerance"]]
    air = c[c["gauge_type"] == "air gauge"].groupby(["calibration_id", "done_date", "result"], sort=False)["as_found_error"].agg(lambda s: s.abs().max()).reset_index(name="largest_error")
    return dict(records=records, points=bore[bore["calibration_id"].isin(out_tol["calibration_id"])], all_points=bore, air=air)


def attribute_agreement():
    head, t = worksheet("attribute_agreement_cosmetic.csv")
    parts = sorted(t["part"].unique())
    wide = t.pivot_table(index="part", columns=["inspector", "trial"], values="call", aggfunc="first")
    ref = t.drop_duplicates("part").set_index("part")["reference"].reindex(parts)
    insp = sorted(t["inspector"].unique())
    n = len(parts)
    rows = []
    for i in insp:
        a, b = wide[(i, 1)], wide[(i, 2)]
        same = int((a == b).sum())
        both = int(((a == ref) & (b == ref)).sum())
        calls = t[t["inspector"] == i]
        rows.append(dict(inspector=i, parts=n, within_matched=same, within=same / n, within_ci=stats.jeffreys(same, n), reference_matched=both, reference=both / n,
                         reference_ci=stats.jeffreys(both, n), reject_share=float((calls["call"] == "reject").mean()),
                         false_rejects=int(((calls["call"] == "reject") & (calls["reference"] == "accept")).sum()),
                         false_accepts=int(((calls["call"] == "accept") & (calls["reference"] == "reject")).sum())))
    by_insp = pd.DataFrame(rows)
    calls = wide.to_numpy()
    all_same = (calls == calls[:, [0]]).all(axis=1)
    all_ref = all_same & (calls[:, 0] == ref.to_numpy())
    counts = np.c_[(calls == "accept").sum(axis=1), (calls == "reject").sum(axis=1)]
    kappa = stats.fleiss_kappa(counts)
    r = np.random.default_rng([SEED, 1])
    boot = [stats.fleiss_kappa(counts[r.integers(0, n, n)]) for _ in range(2000)]
    return dict(header=head, by_inspector=by_insp, parts=n, between_matched=int(all_same.sum()), between=float(all_same.mean()), between_ci=stats.jeffreys(int(all_same.sum()), n),
                all_reference_matched=int(all_ref.sum()), all_reference=float(all_ref.mean()), all_reference_ci=stats.jeffreys(int(all_ref.sum()), n),
                within_mean=float(by_insp["within"].mean()), reference_mean=float(by_insp["reference"].mean()), kappa=kappa,
                kappa_ci=(float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))), reference_reject_share=float((ref == "reject").mean()))


def production(study):
    """The bore's production record against the study: operator component, measurement share, bias against the CMM."""
    h = query("select * from marts.mart_bore_history order by recorded_at, subgroup_id")
    out = {}
    rows = []
    for year, g in h.groupby("recorded_year"):
        dev = g[R5].to_numpy() - NOMINAL
        d = g.assign(y=g["subgroup_mean"] - NOMINAL)
        mm = smf.mixedlm("y ~ C(job_id)", d, groups=d["operator_id"]).fit(reml=True)
        var_op = float(mm.cov_re.iloc[0, 0])
        k = d["operator_id"].nunique()
        lo, hi = np.sqrt((k - 1) * var_op / st.chi2.ppf(0.975, k - 1)), np.sqrt((k - 1) * var_op / st.chi2.ppf(0.025, k - 1))
        total = float(dev.var(ddof=1))
        grr2 = study["grr_sd"] ** 2
        prod_meas = study["repeatability_sd"] ** 2 + var_op + (study["reproducibility_sd"] ** 2 - study["operator_sd"] ** 2)
        rows.append(dict(year=int(year), subgroups=len(g), readings=dev.size, lots=g["job_id"].nunique(), operators=k, total_sd=np.sqrt(total), total_variance=total,
                         operator_sd=np.sqrt(var_op), operator_sd_lower=lo, operator_sd_upper=hi, ratio_to_study=np.sqrt(var_op) / study["operator_sd"],
                         share_study=grr2 / total, share_production=prod_meas / total, process_sd_study=np.sqrt(max(total - grr2, 0)), process_sd_production=np.sqrt(max(total - prod_meas, 0)),
                         past_due_subgroups=int(g["gauge_past_due"].sum()), cpk_apparent=stats.capability(g[R5].to_numpy(), NOMINAL - 0.025, NOMINAL + 0.025)["ppk"]))
        if year == YEAR:
            eff = d.assign(resid=d["y"] - d.groupby("job_id")["y"].transform("mean")).groupby("operator_id")["resid"].agg(["count", "mean"]).reset_index()
            eff["random_effect"] = eff["operator_id"].map({kk: float(v.iloc[0]) for kk, v in mm.random_effects.items()})
            out["by_operator"] = eff
    out["by_year"] = pd.DataFrame(rows)
    # bias against the CMM on the pieces measured by both
    m = query("select * from marts.mart_bore_cmm_match order by recorded_at, subgroup_id")
    cal = query("select distinct done_date from marts.mart_gauge_checkpoints where gauge_type = 'bore gauge' order by 1")["done_date"]
    late = query("select distinct due_date, done_date from marts.mart_gauge_checkpoints where gauge_type = 'bore gauge' and done_past_due and done_date >= date '2024-01-01'")
    edges = sorted([pd.Timestamp("2000-01-01")] + [pd.Timestamp(x) for x in cal] + [pd.Timestamp(x) + pd.Timedelta(days=1) for x in late["due_date"]] + [pd.Timestamp("2100-01-01")])
    out["past_due_windows"] = late
    m["recorded_at"] = pd.to_datetime(m["recorded_at"])
    m["interval"] = pd.cut(m["recorded_at"], edges, right=False)

    def summary(g):
        d_ = g["gauge_minus_cmm"]
        half = st.t.ppf(0.975, len(d_) - 1) * d_.std(ddof=1) / np.sqrt(len(d_)) if len(d_) > 1 else np.nan
        return pd.Series(dict(pieces=len(d_), mean=d_.mean(), sd=d_.std(ddof=1), lower=d_.mean() - half, upper=d_.mean() + half))
    out["match_all"] = summary(m)
    out["match_by_year"] = m.groupby("recorded_year").apply(summary, include_groups=False).reset_index()
    by_int = m.groupby("interval", observed=True).apply(summary, include_groups=False).reset_index()
    by_int["from"] = [max(i.left, m["recorded_at"].min()).date() for i in by_int["interval"]]
    by_int["to"] = [min(i.right, m["recorded_at"].max()).date() for i in by_int["interval"]]
    out["match_by_interval"] = by_int.drop(columns="interval")
    out["match_by_operator"] = m[m["recorded_year"] == YEAR].groupby("operator_id").apply(summary, include_groups=False).reset_index()
    y = m[m["recorded_year"] == YEAR]
    out["match_variance"] = dict(pieces=len(y), variance=float(y["gauge_minus_cmm"].var(ddof=1)),
                                 share=float(y["gauge_minus_cmm"].var(ddof=1) / out["by_year"].set_index("year").loc[YEAR, "total_variance"]))
    out["mapping"] = query("select * from marts.mart_cmm_mapping_summary order by map_method")
    return out


def compute():
    g = gauge_studies()
    return dict(gauge=g, bias=bias_linearity(), attribute=attribute_agreement(), production=production(g["bore"]))
