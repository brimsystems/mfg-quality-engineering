"""S2. Process capability: stability and capability of the five study characteristics, the restatement of the critical
characteristics against the capability reports, the sampling interval of a 25-subgroup report and the flinching pile-up."""
import zlib

import numpy as np
import pandas as pd
from scipy import stats as st

from analytics import stats
from analytics.data import query

YEAR = 2025
SEED = 20250102
R5 = ["r1", "r2", "r3", "r4", "r5"]
BOUNDED = {"runout", "flatness", "true position", "surface finish Ra"}
STUDY = {"turned diameter": "C-14103-05", "runout": "C-14108-14", "milled length": "C-11909-01", "Swiss diameter": "C-11163-06", "medical bore": "C-17004-05"}
RESAMPLES = 1000


def rng(*keys):
    return np.random.default_rng([SEED] + [zlib.crc32(str(k).encode()) for k in keys])


def history(cid, year=YEAR):
    where = f"and recorded_year = {year}" if year else ""
    return query(f"select * from marts.mart_spc_history where characteristic_id = '{cid}' {where} order by recorded_at, subgroup_id")


def limits(g):
    first = g.iloc[0]
    ctype = first["characteristic_type"]
    lsl = float(first["lsl"]) if pd.notna(first["lsl"]) and ctype not in BOUNDED else np.nan
    return lsl, float(first["usl"]), int(first["subgroup_size"]), ctype


def stability(g):
    """Western Electric rules 1 to 4 on the subgroup means (the readings where every piece is measured), limits from the data."""
    lsl, usl, size, _ = limits(g)
    if size == 5:
        x = g[R5].to_numpy()
        pts, sigma = x.mean(axis=1), np.sqrt(x.var(axis=1, ddof=1).mean()) / np.sqrt(5)
        rng_ = x.max(axis=1) - x.min(axis=1)
        r_out = int((rng_ > 2.114 * rng_.mean()).sum())
    else:
        pts = g["r1"].to_numpy()
        sigma = np.abs(np.diff(pts)).mean() / 1.128
        mr = np.abs(np.diff(pts))
        r_out = int((mr > 3.267 * mr.mean()).sum())
    r1, r2, r3, r4 = stats.western_electric(pts, pts.mean(), sigma)
    any_ = r1 | r2 | r3 | r4
    raised = (g["alarm_rule_1"] | g["alarm_rule_2"]).to_numpy()
    return dict(points=len(pts), lots=g["job_id"].nunique(), rule_1=int(r1.sum()), rule_2=int(r2.sum()), rule_3=int(r3.sum()), rule_4=int(r4.sum()), any_rule=int(any_.sum()),
                share_any=float(any_.mean()), range_chart_out=r_out, module_rule_1=int(g["alarm_rule_1"].sum()), module_rule_2=int(g["alarm_rule_2"].sum()),
                module_raised=int(raised.sum()), module_acknowledged=int((raised & g["acknowledged"].to_numpy()).sum()), both=int((raised & any_).sum()))


def capability_row(g, key):
    """Capability with intervals: Bissell on Cpk with the degrees of freedom of the sigma estimate, bootstrap over subgroups on Ppk."""
    lsl, usl, size, _ = limits(g)
    x = g[R5].to_numpy() if size == 5 else g[["r1"]].to_numpy()
    cap = stats.capability(x, lsl, usl) if size == 5 else stats.individuals_capability(x.ravel(), lsl, usl)
    hw = stats.cpk_halfwidth(cap["cpk"], cap["readings"], cap["df_within"])
    r = rng("ppk", key)
    n = len(x)
    boot = []
    for _ in range(RESAMPLES):
        xb = x[r.integers(0, n, n)]
        m, s = xb.mean(), xb.std(ddof=1)
        boot.append(np.nanmin([(usl - m) / (3 * s) if np.isfinite(usl) else np.nan, (m - lsl) / (3 * s) if np.isfinite(lsl) else np.nan]))
    ppm = lambda s: 1e6 * ((st.norm.sf((usl - cap["mean"]) / s) if np.isfinite(usl) else 0) + (st.norm.cdf((lsl - cap["mean"]) / s) if np.isfinite(lsl) else 0))
    out_obs = int(((x > usl + 1e-9) | (x < (lsl if np.isfinite(lsl) else -np.inf) - 1e-9)).sum())
    cap.update(cpk_lower=cap["cpk"] - hw, cpk_upper=cap["cpk"] + hw, ppk_lower=float(np.quantile(boot, 0.025)), ppk_upper=float(np.quantile(boot, 0.975)),
               ppm_within=float(ppm(cap["sigma_within"])), ppm_overall=float(ppm(cap["sigma_overall"])), readings_out=out_obs, lsl=lsl, usl=usl)
    return cap


def runout_fit(g, master_lsl):
    lsl, usl, _, _ = limits(g)
    x = g[R5].to_numpy()
    res = float(g["resolution"].iloc[0])
    pc = stats.percentile_capability(x.ravel(), usl, floor=res / 2)
    module = stats.module_capability(x, master_lsl, usl)
    module_upper = stats.module_capability(x, np.nan, usl)
    r = rng("percentile", "runout")
    n = len(x)
    boot = []
    for _ in range(RESAMPLES // 2):
        xb = x[r.integers(0, n, n)].ravel()
        c, _, s = st.foldnorm.fit(xb, xb.mean() / xb.std(), floc=0, scale=xb.std())
        d = st.foldnorm(c, loc=0, scale=s)
        boot.append((usl - d.ppf(0.5)) / (d.ppf(0.99865) - d.ppf(0.5)))
    xp = np.maximum(x.ravel(), res / 2)
    bc, lam = st.boxcox(xp)
    t_usl = (usl ** lam - 1) / lam if abs(lam) > 1e-9 else np.log(usl)
    boxcox = (t_usl - bc.mean()) / (3 * bc.std(ddof=1))
    return dict(fits=pc["fits"], distribution=pc["distribution"], percentile_ppk=pc["ppk"], percentile_lower=float(np.quantile(boot, 0.025)), percentile_upper=float(np.quantile(boot, 0.975)),
                median=pc["median"], p99865=pc["p99865"], module=module, module_upper_only=module_upper, boxcox_lambda=float(lam), boxcox_ppk=float(boxcox), readings=x.size,
                skewness=float(st.skew(x.ravel())), master_lsl=master_lsl)


def length_detail(g, cap):
    lsl, usl, _, _ = limits(g)
    part = g["part_id"].iloc[0]
    cid = g["characteristic_id"].iloc[0]
    n = query(f"select * from marts.mart_ncrs where part_id = '{part}' order by ncr_id")
    n["on_characteristic"] = n["characteristic_id"] == cid
    hours = n.groupby("on_characteristic").agg(ncrs=("ncr_id", "size"), rework=("rework_hours_booked", "sum"), sorting=("sorting_hours", "sum"), reinspection=("reinspection_hours", "sum")).reset_index()
    by_code = n.groupby(["defect_code", "disposition"]).agg(ncrs=("ncr_id", "size"), rework=("rework_hours_booked", "sum"), sorting=("sorting_hours", "sum")).reset_index()
    return dict(drawing_width=usl - lsl, width_133=6 * 1.33 * cap["sigma_overall"], width_167=6 * 1.67 * cap["sigma_overall"], hours=hours, by_code=by_code, part=part, ncrs=len(n))


def swiss_detail(g, cap):
    lsl, usl, _, _ = limits(g)
    notes = g[g["acknowledgement_text"] == "tool change"]
    gaps = notes.groupby("job_id")["piece_no"].diff().dropna()
    f = int(g.groupby("job_id")["piece_no"].diff().dropna().mode().iloc[0])
    cands = [c for c in range(100, 400, 10) if abs(gaps.median() - c) <= f]
    # reset interval: the candidate that gives the tightest sawtooth
    best = None
    for c in range(150, 320, 10):
        phase = (g["piece_no"] - 3) % c
        lr = st.linregress(phase, g["subgroup_mean"])
        if best is None or lr.rvalue ** 2 > best[1]:
            best = (c, lr.rvalue ** 2, lr)
    interval, _, lr = best
    phase = (g["piece_no"] - 3) % interval
    resid = g["subgroup_mean"] - (lr.intercept + lr.slope * phase)
    between = max(resid.var(ddof=2) - cap["sigma_within"] ** 2 / 5, 0.0)
    ppk_at = lambda length: (usl - lsl) / (6 * np.sqrt(cap["sigma_within"] ** 2 + between + (lr.slope * length) ** 2 / 12))
    grid = np.arange(interval, 20, -5)
    restore = int(max([int(v) for v in grid if ppk_at(v) >= 1.33], default=0))
    return dict(slope_per_piece=lr.slope, slope_lower=lr.slope - 1.96 * lr.stderr, slope_upper=lr.slope + 1.96 * lr.stderr, reset_interval=interval, r_squared=lr.rvalue ** 2,
                tool_change_notes=len(notes), median_gap_between_notes=float(gaps.median()), drift_range=lr.slope * interval, drift_range_sigma=lr.slope * interval / cap["sigma_within"],
                ppk_at_interval=float(ppk_at(interval)), ppk_at_half=float(ppk_at(interval / 2)), interval_for_133=restore, start_offset=lr.intercept - (usl + lsl) / 2)


def medical_three_ways(g, reported):
    lsl, usl, _, _ = limits(g)
    x = g["r1"].to_numpy()
    every = stats.individuals_capability(x, lsl, usl)
    # subgroups of five consecutive pieces every 50 pieces of each lot, as a sampled characteristic is recorded
    sub = []
    for _, lot in g.groupby("job_id", sort=False):
        v = lot.sort_values("piece_no")
        pn = v["piece_no"].to_numpy()
        for end in range(50, int(pn.max()) + 1, 50):
            rows_ = v[(v["piece_no"] > end - 5) & (v["piece_no"] <= end)]["r1"].to_numpy()
            if len(rows_) == 5:
                sub.append(rows_)
    sub = np.array(sub)
    year = stats.capability(sub, lsl, usl)
    hw_y = stats.cpk_halfwidth(year["cpk"], year["readings"], year["df_within"])
    hw_e = stats.cpk_halfwidth(every["cpk"], every["readings"], every["df_within"])
    hw_r = stats.cpk_halfwidth(reported["cpk"], 25, 24)
    rows = [dict(basis="Shop's report, last 25 readings selected", readings=25, cpk=reported["cpk"], lower=reported["cpk"] - hw_r, upper=reported["cpk"] + hw_r, ppk=reported["ppk"], run=str(reported["run_date"])[:10]),
            dict(basis="Subgroups of five every 50 pieces, the year", readings=int(year["readings"]), cpk=year["cpk"], lower=year["cpk"] - hw_y, upper=year["cpk"] + hw_y, ppk=year["ppk"], run=""),
            dict(basis="Every piece, the year", readings=int(every["readings"]), cpk=every["cpk"], lower=every["cpk"] - hw_e, upper=every["cpk"] + hw_e, ppk=every["ppk"], run="")]
    made = query(f"select sum(quantity) q, count(*) lots from marts.mart_lot_outcomes where part_id = '{g['part_id'].iloc[0]}' and extract(year from start_time) = {YEAR}")
    return dict(table=pd.DataFrame(rows), pieces_made=int(made["q"].iloc[0]), lots=int(made["lots"].iloc[0]), readings=len(x))


def restatement():
    res = query("select * from marts.mart_capability_restated order by characteristic_id")
    rep = query(f"select * from marts.mart_capability_reported where critical_flag and run_year = {YEAR} and latest_in_year order by characteristic_id")
    h = query(f"select * from marts.mart_spc_history where critical_flag and recorded_year = {YEAR} order by characteristic_id, recorded_at, subgroup_id")
    stab = {cid: stability(g) for cid, g in h.groupby("characteristic_id", sort=True)}
    res["rules_1_to_4"] = res["characteristic_id"].map(lambda c: stab[c]["any_rule"])
    res["rule_share"] = res["characteristic_id"].map(lambda c: stab[c]["share_any"])
    res["module_raised"] = res["characteristic_id"].map(lambda c: stab[c]["module_raised"])
    res["restated_category"] = np.where(res["restated_capable"], "capable", np.where(np.minimum(res["cpk"], res["ppk"]) >= 1.0, "marginal", "not capable"))
    m = rep.merge(res, on="characteristic_id", suffixes=("_reported", ""))
    df = np.where(m["subgroup_size"] == 5, 100, 24)
    n = np.where(m["subgroup_size"] == 5, 125, 25)
    m["halfwidth"] = [stats.cpk_halfwidth(c, int(nn), int(d)) for c, nn, d in zip(m["cpk_reported"], n, df)]
    m["within_interval_of_133"] = (m["reported_category"] == "capable") & (m["cpk_reported"] - m["halfwidth"] < 1.33)
    # a selection with gaps leaves out subgroups between its first and last
    full = query("select characteristic_id, subgroup_id from marts.mart_spc_history where critical_flag order by characteristic_id, recorded_at, subgroup_id")
    pos = {cid: {sid: i for i, sid in enumerate(g["subgroup_id"])} for cid, g in full.groupby("characteristic_id", sort=True)}
    gaps = []
    for x in m.itertuples():
        idx = [pos[x.characteristic_id][sid] for sid in x.subgroup_ids.split(";")]
        gaps.append(idx[-1] - idx[0] + 1 != len(idx))
    m["selection_leaves_out_subgroups"] = gaps
    notes = query(f"select characteristic_id, count(*) as n from marts.mart_spc_history where acknowledgement_text = 'tool change' and recorded_year = {YEAR} group by 1 order by 1")
    drifting = m["characteristic_id"].isin(notes["characteristic_id"])
    m["cause"] = np.where(m["method"] == "percentile", "bounded", np.where(drifting, "drift", np.where(m["selection_leaves_out_subgroups"], "selection",
                          np.where(m["cpk"] - m["ppk"] > 0.3, "shifts", "sampling"))))
    m.loc[(m["reported_category"] != "capable") | m["restated_capable"], "cause"] = ""
    return dict(restated=res, compared=m)


def flinching():
    """Readings in the last resolution step inside each limit and in the two steps outside, against the fitted distribution."""
    h = query("select characteristic_id, characteristic_type, gauge_type, resolution, usl, lsl, r1, r2, r3, r4, r5 from marts.mart_spc_history where hand_gauge and subgroup_size = 5 "
              "order by characteristic_id, recorded_at, subgroup_id")
    rows, hist = [], []
    for cid, g in h.groupby("characteristic_id", sort=True):
        first = g.iloc[0]
        res, usl, ctype = float(first["resolution"]), float(first["usl"]), first["characteristic_type"]
        x = g[R5].to_numpy().ravel()
        k = np.rint(x / res).astype(np.int64)
        if ctype in BOUNDED:
            c, _, s = st.foldnorm.fit(x, x.mean() / max(x.std(), 1e-12), floc=0, scale=x.std())
            d = st.foldnorm(c, loc=0, scale=s)
            sides = [(1, usl)]
            index = (usl - d.ppf(0.5)) / (d.ppf(0.99865) - d.ppf(0.5))
        else:
            d = st.norm(x.mean(), x.std(ddof=1))
            sides = [(1, usl), (-1, float(first["lsl"]))]
            index = min(usl - x.mean(), x.mean() - float(first["lsl"])) / (3 * x.std(ddof=1))
        for side, lim in sides:
            k_in = int(np.floor(lim / res + 1e-6)) if side == 1 else int(np.ceil(lim / res - 1e-6))
            cdf = lambda kk: d.cdf((kk + 0.5) * res)
            if side == 1:
                e_in, e_out = cdf(k_in) - cdf(k_in - 1), cdf(k_in + 2) - cdf(k_in)
                o_out = int(((k == k_in + 1) | (k == k_in + 2)).sum())
            else:
                e_in, e_out = cdf(k_in) - cdf(k_in - 1), cdf(k_in - 1) - cdf(k_in - 3)
                o_out = int(((k == k_in - 1) | (k == k_in - 2)).sum())
            rows.append(dict(characteristic_id=cid, gauge_type=first["gauge_type"], index=index, readings=len(x), observed_inside=int((k == k_in).sum()), expected_inside=len(x) * e_in,
                             observed_outside=o_out, expected_outside=len(x) * e_out))
            if index < 1.0:
                for step in range(-6, 4):                      # steps from the last one inside the limit; positive is outside
                    kk = k_in + side * step
                    e = (cdf(kk) - cdf(kk - 1))
                    hist.append(dict(step=step, observed=int((k == kk).sum()), expected=len(x) * e))
    t = pd.DataFrame(rows)
    c = t.groupby(["characteristic_id", "gauge_type"]).agg(index=("index", "first"), readings=("readings", "first"), observed_inside=("observed_inside", "sum"),
                                                          expected_inside=("expected_inside", "sum"), observed_outside=("observed_outside", "sum"), expected_outside=("expected_outside", "sum")).reset_index()
    by = c.groupby("gauge_type").agg(characteristics=("characteristic_id", "size"), readings=("readings", "sum"), observed_inside=("observed_inside", "sum"), expected_inside=("expected_inside", "sum"),
                                     observed_outside=("observed_outside", "sum"), expected_outside=("expected_outside", "sum")).reset_index()
    c["band"] = pd.cut(c["index"], [-np.inf, 1.0, 1.33, np.inf], labels=["index below 1.0", "1.0 to 1.33", "1.33 and above"])
    band = c.groupby("band", observed=True).agg(characteristics=("characteristic_id", "size"), readings=("readings", "sum"), observed_inside=("observed_inside", "sum"),
                                                expected_inside=("expected_inside", "sum"), observed_outside=("observed_outside", "sum"), expected_outside=("expected_outside", "sum")).reset_index()
    return dict(by_gauge=by, by_band=band, by_characteristic=c, histogram=pd.DataFrame(hist).groupby("step")[["observed", "expected"]].sum().reset_index())


def f21_bores():
    """The F-21 bores on the bore gauge: stability and capability as recorded and with the operator effects of S1 removed."""
    from analytics.s1_msa.s1_msa import gauge_studies, production
    effects = production(gauge_studies()["bore"])["by_operator"].set_index("operator_id")["random_effect"]
    h = query(f"select * from marts.mart_s1_bore_history where recorded_year = {YEAR} order by characteristic_id, recorded_at, subgroup_id")
    rows = []
    for cid, g in h.groupby("characteristic_id", sort=True):
        net = g.copy()
        net[R5] = net[R5].sub(net["operator_id"].map(effects), axis=0)
        row = dict(characteristic_id=cid, part_id=g["part_id"].iloc[0], subgroups=len(g))
        for label, d in (("recorded", g), ("net", net)):
            sb, cap = stability(d), capability_row(d, f"{cid} {label}")
            row.update({f"signal_share_{label}": sb["share_any"], f"cpk_{label}": cap["cpk"], f"ppk_{label}": cap["ppk"], f"ppk_lower_{label}": cap["ppk_lower"],
                        f"ppk_upper_{label}": cap["ppk_upper"], f"sd_overall_{label}": cap["sigma_overall"]})
        rows.append(row)
    t = pd.DataFrame(rows)
    return dict(table=t, effects=effects.reset_index(), operators=len(effects))


def module_alarms():
    """Alarms the module raised on five-reading subgroups and how they were acknowledged."""
    a = query(f"""select coalesce(acknowledgement_text, '') as acknowledgement_text, acknowledged, count(*) as alarms
                  from marts.mart_spc_history where (alarm_rule_1 or alarm_rule_2) and recorded_year = {YEAR} and subgroup_size = 5 group by 1, 2 order by 3 desc, 1""")
    n = query(f"select count(*) as subgroups, sum(case when alarm_rule_1 or alarm_rule_2 then 1 else 0 end) as raised from marts.mart_spc_history where recorded_year = {YEAR} and subgroup_size = 5")
    return dict(by_text=a, subgroups=int(n["subgroups"].iloc[0]), raised=int(n["raised"].iloc[0]))


def compute():
    out = {"study": {}}
    rep = query(f"select * from marts.mart_capability_reported where run_year = {YEAR} and latest_in_year order by characteristic_id").set_index("characteristic_id")
    master = query("select characteristic_id, lsl, usl, nominal, part_id, characteristic_name, gauge_id from staging.stg_qms__characteristics").set_index("characteristic_id")
    for name, cid in STUDY.items():
        g = history(cid)
        cap = capability_row(g, name)
        d = dict(characteristic_id=cid, part_id=g["part_id"].iloc[0], name=g["characteristic_name"].iloc[0], gauge_type=g["gauge_type"].iloc[0], stability=stability(g), capability=cap,
                 reported=rep.loc[cid].to_dict() if cid in rep.index else None, stability_2024=stability(history(cid, YEAR - 1)))
        if name == "runout":
            d["fit"] = runout_fit(g, float(master.loc[cid, "lsl"]))
        if name == "milled length":
            d["length"] = length_detail(g, cap)
        if name == "Swiss diameter":
            d["swiss"] = swiss_detail(g, cap)
        if name == "medical bore":
            d["three_ways"] = medical_three_ways(g, d["reported"])
        out["study"][name] = d
    out.update(restatement())
    out["flinching"] = flinching()
    out["bores"] = f21_bores()
    out["alarms"] = module_alarms()
    return out
