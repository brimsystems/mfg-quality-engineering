"""Designed experiment on surface finish: the half fraction, its effects and reduced model, the confirmation runs and the
production record of Ra before and after the change of settings."""
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats as st
from statsmodels.stats.diagnostic import normal_ad
from statsmodels.stats.stattools import durbin_watson

from analytics import stats
from analytics.data import query, worksheet

FACTORS = {"A": "feed_mm_per_rev", "B": "surface_speed_m_per_min", "C": "nose_radius_mm", "D": "coolant_pct"}
LABEL = {"A": "Feed", "B": "Speed", "C": "Nose radius", "D": "Coolant", "AB": "Feed*Speed", "AC": "Feed*Nose radius", "AD": "Feed*Coolant"}
ALIAS = {"A": "BCD", "B": "ACD", "C": "ABD", "D": "ABC", "AB": "CD", "AC": "BD", "AD": "BC"}
TERMS = ["A", "B", "C", "D", "AB", "AC", "AD"]


def coded(t):
    out = t.copy()
    levels = {}
    for code, col in FACTORS.items():
        lo, hi = sorted(t[col].unique())[0], sorted(t[col].unique())[-1]
        levels[code] = (lo, hi)
        out[code] = np.where(t[col] == hi, 1, -1)
    for term in ("AB", "AC", "AD"):
        out[term] = out[term[0]] * out[term[1]]
    return out, levels


def effects_table(fit):
    rows = [dict(term="Constant", effect=np.nan, coef=fit.params["const"], se=fit.bse["const"], t=fit.tvalues["const"], p=fit.pvalues["const"])]
    for k in fit.params.index:
        if k != "const":
            rows.append(dict(term=k, effect=2 * fit.params[k], coef=fit.params[k], se=fit.bse[k], t=fit.tvalues[k], p=fit.pvalues[k]))
    return pd.DataFrame(rows)


def summary(fit, y):
    h = fit.get_influence().hat_matrix_diag
    press = float(((fit.resid / (1 - h)) ** 2).sum())
    return dict(s=float(np.sqrt(fit.mse_resid)), r2=float(fit.rsquared), r2_adj=float(fit.rsquared_adj), r2_pred=1 - press / float(((y - y.mean()) ** 2).sum()), df_resid=int(fit.df_resid))


def predict(fit, keep, point):
    x0 = np.array([1.0] + [np.prod([point[c] for c in k]) for k in keep])
    pred = float(x0 @ fit.params.to_numpy())
    xtx = np.linalg.inv(fit.model.exog.T @ fit.model.exog)
    t = st.t.ppf(0.975, fit.df_resid)
    return dict(prediction=pred, pi_half=float(t * np.sqrt(fit.mse_resid * (1 + x0 @ xtx @ x0))), ci_half=float(t * np.sqrt(fit.mse_resid * (x0 @ xtx @ x0))))


def compute():
    head, t = worksheet("doe_surface_finish.csv")
    t, levels = coded(t)
    runs, conf = t[t["confirmation"] == 0].sort_values("std_order").reset_index(drop=True), t[t["confirmation"] == 1].reset_index(drop=True)
    y = runs["ra_um"]
    full = sm.OLS(y, sm.add_constant(runs[TERMS].astype(float))).fit()
    keep = [k for k in TERMS if full.pvalues[k] < 0.05]
    for k in list(keep):
        if len(k) == 2:
            keep += [m for m in k if m not in keep]
    keep = [k for k in TERMS if k in keep]
    red = sm.OLS(y, sm.add_constant(runs[keep].astype(float))).fit()
    out = dict(header=head, levels=levels, runs=runs, confirmation=conf, keep=keep, full=effects_table(full), reduced=effects_table(red), full_summary=summary(full, y), reduced_summary=summary(red, y))
    # half-normal plot of the effects
    eff = (2 * full.params.drop("const")).abs().sort_values()
    out["half_normal"] = pd.DataFrame(dict(term=eff.index, abs_effect=eff.to_numpy(), quantile=st.halfnorm.ppf((np.arange(1, len(eff) + 1) - 0.5) / len(eff))))
    # analysis of variance
    grand = y.mean()
    ss = {k: float(len(runs) * full.params[k] ** 2) for k in TERMS}
    ss_total, ss_err = float(((y - grand) ** 2).sum()), float(full.ssr)
    rows = [dict(source="Main effects", df=4, ss=sum(ss[k] for k in "ABCD")), dict(source="2-way interactions (aliased pairs)", df=3, ss=sum(ss[k] for k in ("AB", "AC", "AD")))]
    for r_ in rows:
        r_["ms"] = r_["ss"] / r_["df"]
        r_["F"] = r_["ms"] / full.mse_resid
        r_["p"] = float(st.f.sf(r_["F"], r_["df"], full.df_resid))
    rows += [dict(source="Residual error (pure error)", df=int(full.df_resid), ss=ss_err, ms=float(full.mse_resid), F=np.nan, p=np.nan), dict(source="Total", df=len(runs) - 1, ss=ss_total, ms=np.nan, F=np.nan, p=np.nan)]
    out["anova_full"] = pd.DataFrame(rows)
    lof_ss, lof_df = float(red.ssr) - ss_err, int(red.df_resid - full.df_resid)
    out["anova_reduced"] = pd.DataFrame([
        dict(source="Regression (" + ", ".join(LABEL[k] for k in keep) + ")", df=len(keep), ss=float(red.ess), ms=float(red.ess / len(keep)), F=float(red.fvalue), p=float(red.f_pvalue)),
        dict(source="Residual error", df=int(red.df_resid), ss=float(red.ssr), ms=float(red.mse_resid), F=np.nan, p=np.nan),
        dict(source="  Lack of fit", df=lof_df, ss=lof_ss, ms=lof_ss / lof_df, F=(lof_ss / lof_df) / float(full.mse_resid), p=float(st.f.sf((lof_ss / lof_df) / full.mse_resid, lof_df, full.df_resid))),
        dict(source="  Pure error", df=int(full.df_resid), ss=ss_err, ms=float(full.mse_resid), F=np.nan, p=np.nan),
        dict(source="Total", df=len(runs) - 1, ss=ss_total, ms=np.nan, F=np.nan, p=np.nan)])
    # residual checks on the reduced model
    resid, fits = red.resid.to_numpy(), red.fittedvalues.to_numpy()
    ad, ad_p = normal_ad(resid)
    order = runs["run_order"].to_numpy()
    lr_order = st.linregress(order, resid)
    lr_fit = st.linregress(fits, np.abs(resid))
    by_day = runs.assign(resid=resid).groupby("date")["resid"].agg(["mean", "count"]).reset_index()
    out["residuals"] = dict(table=runs.assign(fit=fits, resid=resid)[["std_order", "run_order", "date", "ra_um", "fit", "resid"]], ad=float(ad), ad_p=float(ad_p), order_slope=float(lr_order.slope),
                            order_p=float(lr_order.pvalue), abs_resid_on_fit_slope=float(lr_fit.slope), abs_resid_on_fit_p=float(lr_fit.pvalue), durbin_watson=float(durbin_watson(resid[np.argsort(order)])),
                            largest_standardized=float(np.abs(red.get_influence().resid_studentized_internal).max()), by_day=by_day)
    # the settings before and the chosen settings: the confirmation runs fix the chosen point
    chosen = {c: int(conf[c].iloc[0]) for c in "ABCD"}
    before = dict(chosen, C=-1)
    out["chosen"], out["before"] = dict(point=chosen, **predict(red, keep, chosen)), dict(point=before, **predict(red, keep, before))
    c_ = out["chosen"]
    conf = conf.assign(inside=(conf["ra_um"] - c_["prediction"]).abs() <= c_["pi_half"])
    out["confirmation"] = conf
    out["confirmation_summary"] = dict(runs=len(conf), inside=int(conf["inside"].sum()), mean=float(conf["ra_um"].mean()), sd=float(conf["ra_um"].std(ddof=1)), date=str(conf["date"].iloc[0]))
    # the production record of Ra on the part
    cid = head["characteristic"].split(" ")[0]
    h = query(f"select job_id, job_start, subgroup_mean, usl, resolution, r1, r2, r3, r4, r5 from marts.mart_spc_history where characteristic_id = '{cid}' order by recorded_at, subgroup_id")
    lots = h.groupby("job_id").agg(start=("job_start", "first"), subgroups=("subgroup_mean", "size"), mean_ra=("subgroup_mean", "mean")).reset_index().sort_values("start").reset_index(drop=True)
    lots["start"] = pd.to_datetime(lots["start"])
    # the lot record carries no settings; the change is the first lot whose mean Ra is nearer the prediction at the chosen settings than at the old
    midpoint = (c_["prediction"] + out["before"]["prediction"]) / 2
    change = lots.loc[lots["mean_ra"] < midpoint, "start"].min()
    lots["period"] = np.where(lots["start"] >= change, "after", "before")
    out["change"] = dict(first_lot=change, confirmation_date=pd.Timestamp(conf["date"].iloc[0]), lots_between=int(((lots["start"] > pd.Timestamp(conf["date"].iloc[0])) & (lots["start"] < change)).sum()))
    lots["within_0_1"] = (lots["mean_ra"] - c_["prediction"]).abs() <= 0.1
    lots["inside_pi"] = (lots["mean_ra"] - c_["prediction"]).abs() <= c_["pi_half"]
    out["lots"] = lots
    out["production"] = lots.groupby("period").agg(lots=("job_id", "size"), subgroups=("subgroups", "sum"), mean=("mean_ra", "mean"), sd=("mean_ra", "std"), low=("mean_ra", "min"), high=("mean_ra", "max"),
                                                    first=("start", "min"), last=("start", "max")).reset_index()
    # alias check: feed by nose radius is aliased with speed by coolant; the settings before the change lie outside the half fraction
    b0, pa_, pc_, pac = red.params["const"], red.params.get("A", 0.0), red.params.get("C", 0.0), red.params.get("AC", 0.0)
    pt = out["before"]["point"]
    out["alias"] = dict(speed=full.params["B"] * 2, speed_p=float(full.pvalues["B"]), coolant=full.params["D"] * 2, coolant_p=float(full.pvalues["D"]),
                        in_fraction_chosen=bool(chosen["A"] * chosen["B"] * chosen["C"] == chosen["D"]), in_fraction_before=bool(pt["A"] * pt["B"] * pt["C"] == pt["D"]),
                        before_if_feed_radius=float(b0 + pa_ * pt["A"] + pc_ * pt["C"] + pac * pt["A"] * pt["C"]), before_if_speed_coolant=float(b0 + pa_ * pt["A"] + pc_ * pt["C"] + pac * pt["B"] * pt["D"]),
                        production_before=float(lots[lots["period"] == "before"]["mean_ra"].mean()), lots_before=int((lots["period"] == "before").sum()))
    # capability against the Ra limit before and after, percentile method on the fitted distribution
    usl, res = float(h["usl"].iloc[0]), float(h["resolution"].iloc[0])
    period_of = lots.set_index("job_id")["period"]
    rows = []
    for period in ("before", "after"):
        x = h[h["job_id"].map(period_of) == period][["r1", "r2", "r3", "r4", "r5"]].to_numpy()
        pc = stats.percentile_capability(x.ravel(), usl, floor=res / 2)
        rows.append(dict(period=period, lots=int((period_of == period).sum()), subgroups=len(x), readings=x.size, mean=float(x.mean()), sd=float(x.std(ddof=1)), distribution=pc["distribution"], median=pc["median"],
                         p99865=pc["p99865"], index=pc["ppk"], ppm=pc["ppm_above"], readings_above=int((x > usl + 1e-9).sum())))
    out["capability"], out["usl"] = pd.DataFrame(rows), usl
    out["feed_effect"] = dict(at_low_radius=float(2 * (pa_ - pac)), at_high_radius=float(2 * (pa_ + pac)))
    out["fit"] = dict(resid=resid, fits=fits, order=order, standardized=red.get_influence().resid_studentized_internal)
    out["characteristic_id"] = cid
    return out
