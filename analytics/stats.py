"""Statistics shared by the studies: gauge R&R, capability, control chart rules, attribute agreement, rate intervals and tests."""
import numpy as np
import pandas as pd
from scipy import stats as st

D2 = {2: 1.128, 3: 1.693, 4: 2.059, 5: 2.326}


def gauge_rr(df, tolerance, operator="operator", part="part", value="reading", pool_at=0.25):
    """Crossed gauge R&R by the ANOVA method (AIAG MSA, 4th edition); the interaction is pooled when its p-value exceeds pool_at."""
    k, n = df[operator].nunique(), df[part].nunique()
    r = len(df) // (k * n)
    grand = df[value].mean()
    ss_o = n * r * ((df.groupby(operator)[value].mean() - grand) ** 2).sum()
    ss_p = k * r * ((df.groupby(part)[value].mean() - grand) ** 2).sum()
    cell = df.groupby([operator, part])[value].mean()
    ss_e = ((df[value] - df.set_index([operator, part]).index.map(cell).to_numpy()) ** 2).sum()
    ss_t = ((df[value] - grand) ** 2).sum()
    ss_op = ss_t - ss_o - ss_p - ss_e
    df_o, df_p, df_op, df_e = k - 1, n - 1, (k - 1) * (n - 1), k * n * (r - 1)
    ms_o, ms_p, ms_op, ms_e = ss_o / df_o, ss_p / df_p, ss_op / df_op, ss_e / df_e
    f_op = ms_op / ms_e
    p_op = float(st.f.sf(f_op, df_op, df_e))
    anova = [("Part", df_p, ss_p, ms_p, ms_p / ms_op, float(st.f.sf(ms_p / ms_op, df_p, df_op))),
             ("Operator", df_o, ss_o, ms_o, ms_o / ms_op, float(st.f.sf(ms_o / ms_op, df_o, df_op))),
             ("Part * Operator", df_op, ss_op, ms_op, f_op, p_op), ("Repeatability", df_e, ss_e, ms_e, np.nan, np.nan), ("Total", k * n * r - 1, ss_t, np.nan, np.nan, np.nan)]
    pooled = p_op > pool_at
    if pooled:
        ms_r = (ss_op + ss_e) / (df_op + df_e)
        ev, inter = ms_r, 0.0
        av, pv = max((ms_o - ms_r) / (n * r), 0.0), max((ms_p - ms_r) / (k * r), 0.0)
    else:
        ev, inter = ms_e, max((ms_op - ms_e) / r, 0.0)
        av, pv = max((ms_o - ms_op) / (n * r), 0.0), max((ms_p - ms_op) / (k * r), 0.0)
    grr = ev + av + inter
    tv = grr + pv
    # approximate 95% intervals on the standard deviations (Satterthwaite on the mean squares each component is built from)
    if pooled:
        df_r = df_op + df_e
        terms = {"Repeatability": [(1.0, ms_r, df_r)], "Operator": [(1 / (n * r), ms_o, df_o), (-1 / (n * r), ms_r, df_r)],
                 "Part-To-Part": [(1 / (k * r), ms_p, df_p), (-1 / (k * r), ms_r, df_r)], "Total Gage R&R": [(1 / (n * r), ms_o, df_o), (1 - 1 / (n * r), ms_r, df_r)]}
    else:
        terms = {"Repeatability": [(1.0, ms_e, df_e)], "Operator": [(1 / (n * r), ms_o, df_o), (-1 / (n * r), ms_op, df_op)],
                 "Operator*Part": [(1 / r, ms_op, df_op), (-1 / r, ms_e, df_e)], "Part-To-Part": [(1 / (k * r), ms_p, df_p), (-1 / (k * r), ms_op, df_op)],
                 "Total Gage R&R": [(1 / (n * r), ms_o, df_o), (1 / r - 1 / (n * r), ms_op, df_op), (1 - 1 / r, ms_e, df_e)]}
    intervals = {name: satterthwaite_interval(t) for name, t in terms.items()}
    comp = {"Total Gage R&R": grr, "Repeatability": ev, "Reproducibility": av + inter, "Operator": av, "Operator*Part": inter, "Part-To-Part": pv, "Total Variation": tv}
    table = pd.DataFrame([dict(Source=s, VarComp=v, pct_contribution=100 * v / tv, StdDev=np.sqrt(v), study_var=6 * np.sqrt(v),
                               pct_study_var=100 * np.sqrt(v / tv), pct_tolerance=100 * 6 * np.sqrt(v) / tolerance) for s, v in comp.items()])
    table["sd_lower"] = [intervals.get(s_, (np.nan, np.nan, np.nan))[0] for s_ in table["Source"]]
    table["sd_upper"] = [intervals.get(s_, (np.nan, np.nan, np.nan))[1] for s_ in table["Source"]]
    return dict(anova=pd.DataFrame(anova, columns=["Source", "DF", "SS", "MS", "F", "P"]), components=table, interaction_pooled=pooled, interaction_p=p_op, intervals=intervals,
                grr_sd=float(np.sqrt(grr)), repeatability_sd=float(np.sqrt(ev)), reproducibility_sd=float(np.sqrt(av + inter)), operator_sd=float(np.sqrt(av)),
                part_sd=float(np.sqrt(pv)), pct_tolerance=float(100 * 6 * np.sqrt(grr) / tolerance), pct_study_var=float(100 * np.sqrt(grr / tv)),
                ndc=int(np.floor(1.41 * np.sqrt(pv / grr))) if grr > 0 else np.inf, operators=k, parts=n, trials=r)


def satterthwaite_interval(terms, level=0.95):
    """Interval on the standard deviation of a variance component written as a sum of coefficient times mean square (coefficient, mean square, df)."""
    est = sum(c * ms for c, ms, _ in terms)
    if est <= 0:
        return 0.0, np.nan, np.nan
    df = est ** 2 / sum((c * ms) ** 2 / d for c, ms, d in terms)
    lo, hi = df * est / st.chi2.ppf(0.5 + level / 2, df), df * est / st.chi2.ppf(0.5 - level / 2, df)
    return float(np.sqrt(lo)), float(np.sqrt(hi)), float(df)


def gauge_rr_average_range(df, tolerance, operator="operator", part="part", value="reading"):
    """Gauge R&R by the average and range method (AIAG MSA, 4th edition constants)."""
    k1 = {2: 0.8862, 3: 0.5908}
    k2 = {2: 0.7071, 3: 0.5231}
    k3 = {2: 0.7071, 3: 0.5231, 4: 0.4467, 5: 0.4030, 6: 0.3742, 7: 0.3534, 8: 0.3375, 9: 0.3249, 10: 0.3146}
    k, n = df[operator].nunique(), df[part].nunique()
    r = len(df) // (k * n)
    cell = df.groupby([operator, part])[value]
    rbar = float((cell.max() - cell.min()).mean())
    xdiff = float(df.groupby(operator)[value].mean().max() - df.groupby(operator)[value].mean().min())
    rp = float(df.groupby(part)[value].mean().max() - df.groupby(part)[value].mean().min())
    ev = rbar * k1[r]
    av = float(np.sqrt(max((xdiff * k2[k]) ** 2 - ev ** 2 / (n * r), 0.0)))
    grr, pv = float(np.sqrt(ev ** 2 + av ** 2)), rp * k3[n]
    return dict(ev=ev, av=av, grr=grr, pv=pv, pct_tolerance=100 * 6 * grr / tolerance, ndc=int(np.floor(1.41 * pv / grr)), mean_range=rbar)


def _indices(mean, s_within, s_overall, lsl, usl):
    two = np.isfinite(lsl) and np.isfinite(usl)
    cpu = (usl - mean) / (3 * s_within) if np.isfinite(usl) else np.nan
    cpl = (mean - lsl) / (3 * s_within) if np.isfinite(lsl) else np.nan
    ppu = (usl - mean) / (3 * s_overall) if np.isfinite(usl) else np.nan
    ppl = (mean - lsl) / (3 * s_overall) if np.isfinite(lsl) else np.nan
    return dict(cp=(usl - lsl) / (6 * s_within) if two else np.nan, cpk=float(np.nanmin([cpu, cpl])), pp=(usl - lsl) / (6 * s_overall) if two else np.nan,
                ppk=float(np.nanmin([ppu, ppl])), mean=float(mean), sigma_within=float(s_within), sigma_overall=float(s_overall))


def capability(x, lsl, usl):
    """Cp and Cpk from the pooled within-subgroup standard deviation, Pp and Ppk from all readings. x is subgroups by readings."""
    x = np.asarray(x, dtype=float)
    k, m = x.shape
    out = _indices(x.mean(), np.sqrt(x.var(axis=1, ddof=1).mean()), x.std(ddof=1), lsl, usl)
    out.update(subgroups=k, readings=k * m, df_within=k * (m - 1))
    return out


def module_capability(x, lsl, usl):
    """The SPC module's summary: normal assumption, within sigma from the mean range (moving range for single readings)."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1 or x.shape[1] == 1:
        return individuals_capability(x.ravel(), lsl, usl)
    k, m = x.shape
    s_w = (x.max(axis=1) - x.min(axis=1)).mean() / D2[m]
    out = _indices(x.mean(), s_w, x.std(ddof=1), lsl, usl)
    out.update(subgroups=k, readings=k * m, df_within=k * (m - 1))
    return out


def individuals_capability(x, lsl, usl):
    """Capability for single readings: within sigma from the mean moving range, overall sigma from all readings."""
    x = np.asarray(x, dtype=float)
    out = _indices(x.mean(), np.abs(np.diff(x)).mean() / D2[2], x.std(ddof=1), lsl, usl)
    out.update(subgroups=len(x), readings=len(x), df_within=len(x) - 1)
    return out


def cpk_halfwidth(cpk, readings, df, level=0.95):
    """Half-width of the interval on Cpk (Bissell's approximation, with the degrees of freedom of the sigma estimate)."""
    z = st.norm.ppf(0.5 + level / 2)
    return float(z * np.sqrt(1 / (9 * readings) + cpk ** 2 / (2 * df)))


def anderson_darling(x, cdf):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    f = np.clip(cdf(x), 1e-12, 1 - 1e-12)
    i = np.arange(1, n + 1)
    return float(-n - np.sum((2 * i - 1) * (np.log(f) + np.log(1 - f[::-1]))) / n)


def fit_bounded(x, floor=None):
    """Folded normal, lognormal and Weibull fitted to readings bounded at zero; returns the fits with their Anderson-Darling statistics."""
    x = np.asarray(x, dtype=float)
    xp = np.maximum(x, floor if floor else max(x[x > 0].min() / 2, 1e-9))
    fits = {}
    c, _, s = st.foldnorm.fit(x, x.mean() / max(x.std(), 1e-12), floc=0, scale=x.std())
    fits["folded normal"] = st.foldnorm(c, loc=0, scale=s)
    sh, _, sc = st.lognorm.fit(xp, floc=0)
    fits["lognormal"] = st.lognorm(sh, loc=0, scale=sc)
    sh, _, sc = st.weibull_min.fit(xp, floc=0)
    fits["Weibull"] = st.weibull_min(sh, loc=0, scale=sc)
    rows = []
    for name, d in fits.items():
        rows.append(dict(distribution=name, ad=anderson_darling(xp if name != "folded normal" else x, d.cdf), p0135=float(d.ppf(0.00135)), median=float(d.ppf(0.5)),
                         p99865=float(d.ppf(0.99865))))
    return pd.DataFrame(rows).sort_values("ad").reset_index(drop=True)


def percentile_capability(x, usl, lsl=np.nan, floor=None):
    """Percentile method on the best-fitting distribution: Ppk from the 0.135, 50 and 99.865 percentiles."""
    fits = fit_bounded(x, floor)
    b = fits.iloc[0]
    ppu = (usl - b["median"]) / (b["p99865"] - b["median"]) if np.isfinite(usl) else np.nan
    ppl = (b["median"] - lsl) / (b["median"] - b["p0135"]) if np.isfinite(lsl) else np.nan
    return dict(distribution=b["distribution"], ppk=float(np.nanmin([ppu, ppl])), median=float(b["median"]), p99865=float(b["p99865"]), fits=fits)


def western_electric(means, centre, sigma):
    """Western Electric rules 1 to 4 on a sequence of points; returns one boolean array per rule."""
    z = (np.asarray(means, dtype=float) - centre) / sigma
    n = len(z)
    r1 = np.abs(z) > 3
    r2, r3, r4 = np.zeros(n, bool), np.zeros(n, bool), np.zeros(n, bool)
    for sign in (1, -1):
        a = sign * z
        b2, b1, b0 = (a > 2).astype(int), (a > 1).astype(int), (a > 0).astype(int)
        c2, c1, c0 = np.cumsum(np.r_[0, b2]), np.cumsum(np.r_[0, b1]), np.cumsum(np.r_[0, b0])
        i = np.arange(n)
        r2 |= (b2 == 1) & ((c2[i + 1] - c2[np.maximum(i - 2, 0)]) >= 2)
        r3 |= (b1 == 1) & ((c1[i + 1] - c1[np.maximum(i - 4, 0)]) >= 4)
        r4 |= (i >= 7) & ((c0[i + 1] - c0[np.maximum(i - 7, 0)]) == 8)
    return r1, r2, r3, r4


def jeffreys(x, n, level=0.95):
    """Jeffreys interval for a proportion."""
    a = (1 - level) / 2
    lo = 0.0 if x == 0 else float(st.beta.ppf(a, x + 0.5, n - x + 0.5))
    hi = 1.0 if x == n else float(st.beta.ppf(1 - a, x + 0.5, n - x + 0.5))
    return lo, hi


def fleiss_kappa(counts):
    """Fleiss' kappa from a subjects by categories table of rating counts (the same number of ratings per subject)."""
    counts = np.asarray(counts, dtype=float)
    n, m = counts.shape[0], counts[0].sum()
    p_cat = counts.sum(axis=0) / (n * m)
    p_obs = ((counts ** 2).sum(axis=1) - m) / (m * (m - 1))
    pe = (p_cat ** 2).sum()
    return float((p_obs.mean() - pe) / (1 - pe))


def two_proportions(x1, n1, x2, n2, level=0.95):
    """Score test of two proportions with the Newcombe interval on the difference p1 - p2."""
    p1, p2, p = x1 / n1, x2 / n2, (x1 + x2) / (n1 + n2)
    z = (p1 - p2) / np.sqrt(p * (1 - p) * (1 / n1 + 1 / n2))
    zc = st.norm.ppf(0.5 + level / 2)

    def wilson(x, n):
        ph = x / n
        mid, half = (ph + zc ** 2 / (2 * n)) / (1 + zc ** 2 / n), zc * np.sqrt(ph * (1 - ph) / n + zc ** 2 / (4 * n ** 2)) / (1 + zc ** 2 / n)
        return mid - half, mid + half
    l1, u1 = wilson(x1, n1)
    l2, u2 = wilson(x2, n2)
    d = p1 - p2
    return dict(p1=p1, p2=p2, difference=d, z=float(z), p_value=float(2 * st.norm.sf(abs(z))),
                lower=float(d - np.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)), upper=float(d + np.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)))


def oc_binomial(p, n, ac):
    """Probability of acceptance of a single sampling plan at lot fraction nonconforming p."""
    return st.binom.cdf(ac, n, p)
