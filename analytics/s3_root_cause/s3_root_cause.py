"""S3. Root cause of scrap on family F-14: the shop's view by machine, the lot regression on machine, bar-lot hardness and insert
grade, and the change of insert grade on bar lots above 32 HRC."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats as st

from analytics import stats
from analytics.data import query

FAMILY, CONTROL = "F-14", "F-12"
HARD = 32.0
STANDARD, CHANGED = "P25", "K20"


def change_record():
    """The dates the records give for the insert change: the corrective action on the family and the first lot on the changed insert."""
    capa = query(f"select * from marts.mart_capa where family_code = '{FAMILY}' order by opened, capa_id")
    k = capa[capa["actions_text"].str.contains(CHANGED)].iloc[0]
    first = query(f"select min(start_time) as t from marts.mart_lot_outcomes where family_code = '{FAMILY}' and insert_grade = '{CHANGED}'")["t"].iloc[0]
    return dict(capa=k, other=capa[capa["capa_id"] != k["capa_id"]], opened=pd.Timestamp(k["opened"]), first_lot=pd.Timestamp(first), closed=pd.Timestamp(k["closed"]))


def lots(family, change):
    t = query(f"select * from marts.mart_lot_outcomes where family_code = '{family}' order by start_time, job_id")
    t["start_time"] = pd.to_datetime(t["start_time"])
    t["period"] = np.where(t["start_time"] < change, "before", "after")
    t["hard"] = (t["hardness_hrc"] > HARD).astype(int)
    t["kgrade"] = (t["insert_grade"] == CHANGED).astype(int)
    t["hard_standard"] = t["hard"] * (1 - t["kgrade"])
    t["mt04"] = (t["machine_id"] == "MT-04").astype(int)
    t["rate"] = t["scrap_quantity"] / t["quantity"]
    return t


def rate_row(g):
    x, n = int(g["scrap_quantity"].sum()), int(g["quantity"].sum())
    lo, hi = stats.jeffreys(x, n)
    return pd.Series(dict(lots=len(g), pieces=n, scrap=x, rate=x / n, lower=lo, upper=hi))


def compute():
    rec = change_record()
    CHANGE = rec["first_lot"]
    f = lots(FAMILY, CHANGE)
    before, after = f[f["period"] == "before"], f[f["period"] == "after"]
    out = dict(lots=len(f), lots_before=len(before), lots_after=len(after))
    # the shop's view: the Pareto by machine and the cause codes as entered
    n = query(f"select * from marts.mart_ncrs where family_code = '{FAMILY}' order by ncr_id")
    n["opened"] = pd.to_datetime(n["opened"])
    nb = n[n["job_id"].isin(before["job_id"])]
    sc = nb[nb["disposition"] == "scrap"]
    pareto = before.groupby(["machine_id", "shop_machine_no"]).agg(lots=("job_id", "size"), pieces=("quantity", "sum"), scrap_pieces=("scrap_quantity", "sum"), scrap_cost=("scrap_cost", "sum")).reset_index()
    pareto["scrap_ncrs"] = pareto["machine_id"].map(sc.groupby("machine_id").size()).fillna(0).astype(int)
    pareto["ncr_scrap_pieces"] = pareto["machine_id"].map(sc.groupby("machine_id")["quantity_affected"].sum()).fillna(0).astype(int)
    for c in ("lots", "scrap_pieces", "scrap_cost", "scrap_ncrs", "ncr_scrap_pieces"):
        pareto[f"{c}_share"] = pareto[c] / pareto[c].sum()
    out["pareto"] = pareto.sort_values("scrap_pieces", ascending=False).reset_index(drop=True)
    codes = sc.assign(cause_code=sc["cause_code"].fillna("(none)")).groupby("cause_code").agg(ncrs=("ncr_id", "size"), pieces=("quantity_affected", "sum")).reset_index().sort_values("ncrs", ascending=False)
    out["cause_codes"], out["scrap_ncrs_before"], out["ncrs_before"] = codes, len(sc), len(nb)
    out["cause_text"] = sc["cause_text"].value_counts().head(6).reset_index()
    # naive comparison by machine before the change
    naive = before.groupby("machine_id").apply(rate_row, include_groups=False).reset_index()
    out["naive"] = naive
    out["mt04_against_others"] = before.groupby("mt04").apply(rate_row, include_groups=False).reset_index()
    # one-way analyses of variance of the lot scrap rate
    rows = []
    f["hardness_band"] = np.where(f["hard"] == 1, "above 32 HRC", "32 HRC and below")
    for scope, d in (("before the change", before.assign(hardness_band=np.where(before["hard"] == 1, "above 32 HRC", "32 HRC and below"))), ("all lots", f)):
        for factor in ("machine_id", "bar_supplier_id", "hardness_band", "insert_grade"):
            groups = [g["rate"].to_numpy() for _, g in d.groupby(factor)]
            if len(groups) < 2:
                continue
            fs, p = st.f_oneway(*groups)
            grand = d["rate"].mean()
            ssb = sum(len(g) * (g.mean() - grand) ** 2 for g in groups)
            rows.append(dict(scope=scope, factor=factor, levels=len(groups), lots=len(d), F=fs, p=p, eta_squared=ssb / ((d["rate"] - grand) ** 2).sum()))
    out["anova"] = pd.DataFrame(rows)
    # binomial logit on lot scrap, lot quantity as exposure, quasi-likelihood dispersion
    models = []
    for label, formula, d in (("machine alone, before the change", "mt04", before), ("machine alone, all lots", "mt04", f),
                              ("machine with hardness band, insert grade and their interaction, all lots", "mt04 + hard + kgrade + hard:kgrade", f)):
        fit, phi = stats.quasi_binomial(formula, d, "scrap_quantity", "quantity")
        for term in fit.params.index:
            if term == "Intercept":
                continue
            models.append(dict(model=label, term=term, lots=len(d), dispersion=phi, **stats.quasi_term(fit, phi, term)))
    out["models"] = pd.DataFrame(models)
    fit6, phi6 = stats.quasi_binomial("C(machine_id) + hard + kgrade + hard:kgrade", f, "scrap_quantity", "quantity")
    fit0, _ = stats.quasi_binomial("hard + kgrade + hard:kgrade", f, "scrap_quantity", "quantity")
    fstat = ((fit0.deviance - fit6.deviance) / (fit0.df_resid - fit6.df_resid)) / phi6
    out["six_machines"] = dict(F=float(fstat), df1=int(fit0.df_resid - fit6.df_resid), df2=int(fit6.df_resid), p=float(st.f.sf(fstat, fit0.df_resid - fit6.df_resid, fit6.df_resid)))
    # the interaction: scrap rate by hardness band and insert grade
    cells = f.groupby(["hardness_band", "insert_grade"]).apply(rate_row, include_groups=False).reset_index()
    cells["lots_on_mt04"] = [int(f[(f["hardness_band"] == a) & (f["insert_grade"] == b)]["mt04"].sum()) for a, b in zip(cells["hardness_band"], cells["insert_grade"])]
    out["cells"] = cells
    out["hard_by_machine"] = before.groupby("mt04").agg(lots=("job_id", "size"), above_32=("hard", "sum"), mean_hardness=("hardness_hrc", "mean")).reset_index()
    parts = before.groupby("part_id").agg(lots=("job_id", "size"), on_mt04=("mt04", "sum"), mean_hardness=("hardness_hrc", "mean"), above_32=("hard", "sum"), bar=("bar_lot", "first")).reset_index()
    out["by_part"] = parts.sort_values("on_mt04", ascending=False)
    r2 = lambda col: float(sm.OLS(f["rate"], sm.add_constant(f[[col]].astype(float))).fit().rsquared)
    out["variance_shares"] = dict(interaction=r2("hard_standard"), hardness=r2("hard"), machine=r2("mt04"), lots=len(f), hard_standard_lots=int(f["hard_standard"].sum()))
    # certificate hardness against the receiving check
    both = f[f["receiving_hardness_hrc"].notna()].copy()
    both["diff"] = both["hardness_hrc"] - both["receiving_hardness_hrc"]
    both["band_changes"] = (both["hardness_hrc"] > HARD) != (both["receiving_hardness_hrc"] > HARD)
    out["hardness_check"] = dict(lots_with_both=len(both), lots=len(f), mean_diff=float(both["diff"].mean()), sd_diff=float(both["diff"].std(ddof=1)), largest=float(both["diff"].abs().max()),
                                 band_changes=int(both["band_changes"].sum()), changed=both[both["band_changes"]][["job_id", "start_time", "machine_id", "hardness_hrc", "receiving_hardness_hrc", "insert_grade", "rate"]])
    # the change and the before and after: the confirmation window of the corrective action, and every lot after
    out["change"] = dict(record=rec, changed_lots=int(f["kgrade"].sum()), changed_on_soft=int(((f["kgrade"] == 1) & (f["hard"] == 0)).sum()),
                         hard_after_standard=int(((after["hard"] == 1) & (after["kgrade"] == 0)).sum()))
    ctl = lots(CONTROL, CHANGE)
    rows = []
    for window, end in (("confirmation window, to the closure of the corrective action", rec["closed"] + pd.Timedelta(days=1)), ("all lots after", pd.Timestamp("2100-01-01"))):
        for fam, d in ((FAMILY, f), (CONTROL, ctl)):
            b_ = d[d["period"] == "before"]
            a_ = d[(d["period"] == "after") & (d["start_time"] < end)]
            tp = stats.two_proportions(int(b_["scrap_quantity"].sum()), int(b_["quantity"].sum()), int(a_["scrap_quantity"].sum()), int(a_["quantity"].sum()))
            rows.append(dict(window=window, family=fam, lots_before=len(b_), pieces_before=int(b_["quantity"].sum()), scrap_before=int(b_["scrap_quantity"].sum()), rate_before=tp["p1"],
                             lots_after=len(a_), pieces_after=int(a_["quantity"].sum()), scrap_after=int(a_["scrap_quantity"].sum()), rate_after=tp["p2"],
                             difference=tp["difference"], lower=tp["lower"], upper=tp["upper"], p=tp["p_value"]))
    out["before_after"] = pd.DataFrame(rows)
    # scrap cost of the family at standard cost
    months_b = (CHANGE - pd.Timestamp("2024-01-01")).days / 30.4375
    months_a = (pd.Timestamp("2026-01-01") - CHANGE).days / 30.4375
    cost = []
    for label, d, months in (("before the change", before, months_b), ("after the change", after, months_a)):
        cost.append(dict(period=label, lots=len(d), scrap_pieces=int(d["scrap_quantity"].sum()), scrap_cost=float(d["scrap_cost"].sum()), cost_per_lot=float(d["scrap_cost"].sum() / len(d)),
                         cost_per_month=float(d["scrap_cost"].sum() / months), cost_on_hard_standard=float(d[d["hard_standard"] == 1]["scrap_cost"].sum())))
    out["cost"] = pd.DataFrame(cost)
    out["control"] = ctl
    out["frame"] = f
    return out
