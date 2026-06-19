"""S4. Acceptance sampling and supplier quality: the Z1.4 plan and the zero-acceptance plan on supplier S-017's plated lots,
and the supplier scorecard restated with intervals."""
import numpy as np
import pandas as pd
from scipy import optimize, special
from scipy import stats as st

from analytics import stats
from analytics.data import query

SUPPLIER = "S-017"
POINTS = [0.005, 0.01, 0.025, 0.04, 0.065]
BAD = 0.025
TIGHTENED = {"J": 1, "K": 2, "H": 0, "L": 3, "M": 5}       # acceptance numbers, AQL 1.0 tightened, same sample sizes
GRID = np.linspace(1e-5, 0.25, 4000)


def pa(p, lot, n, ac):
    """Probability of acceptance: binomial for lots above ten times the sample, hypergeometric otherwise."""
    p = np.asarray(p, dtype=float)
    if lot > 10 * n:
        return st.binom.cdf(ac, n, p)
    return st.hypergeom.cdf(ac, lot, np.rint(p * lot).astype(int), n)


def plan_row(name, lot, n, ac):
    grid = np.linspace(0.0005, 0.15, 3000)
    curve = st.binom.cdf(ac, n, grid)
    aoq = grid * pa(grid, lot, n, ac) * (lot - n) / lot
    row = dict(plan=name, lot_size=lot, sample_size=n, acceptance_number=ac, curve="binomial" if lot > 10 * n else "hypergeometric", aoql=float(aoq.max()), aoql_at=float(grid[aoq.argmax()]),
               ltpd=float(grid[np.argmin(np.abs(curve - 0.10))]), p_at_95=float(grid[np.argmin(np.abs(curve - 0.95))]))
    for p in POINTS:
        row[f"pa_{p}"] = float(pa(p, lot, n, ac))
    return row


def fit_beta_binomial(x, n):
    """Lot defect rate as a beta distribution, fitted to defects found in the samples by maximum likelihood."""
    def nll(theta):
        a, b = np.exp(theta)
        return -np.sum(special.betaln(x + a, n - x + b) - special.betaln(a, b))
    res = optimize.minimize(nll, np.log([1.5, 100.0]), method="Nelder-Mead", options=dict(xatol=1e-6, fatol=1e-9, maxiter=4000))
    a, b = np.exp(res.x)
    return float(a), float(b)


def switching(lots):
    """Z1.4 switching between normal and tightened inspection applied to the lot sequence as recorded."""
    state, run_ok, recent, rows, on_tight_rejects = "normal", 0, [], [], 0
    for x in lots.itertuples():
        ac = x.acceptance_number if state == "normal" else TIGHTENED[x.table_code_letter]
        ok = x.defects_found <= ac
        rows.append(dict(receiving_id=x.receiving_id, state=state, accepted=ok))
        if state == "normal":
            recent = (recent + [ok])[-5:]
            if recent.count(False) >= 2:
                state, run_ok, recent, on_tight_rejects = "tightened", 0, [], 0
        else:
            run_ok = run_ok + 1 if ok else 0
            on_tight_rejects += 0 if ok else 1
            if run_ok >= 5:
                state, recent = "normal", []
    return pd.DataFrame(rows)


REDUCED = {13: (5, 0, 1), 50: (20, 0, 2), 80: (32, 1, 3), 125: (50, 1, 4), 200: (80, 2, 5), 315: (125, 3, 6)}      # normal sample size: reduced sample size, Ac, Re at AQL 1.0
TIGHT_AC = {13: 0, 50: 0, 80: 1, 125: 2, 200: 3, 315: 5}                                                            # tightened acceptance numbers on the same samples
REPLICATIONS = 400
SEED = 20250104


def switching_with_reduced(lots, supplier, allow_reduced=True):
    """Z1.4 switching between normal, tightened and reduced inspection on one supplier's lot sequence.

    The switching score is as the standard states it: plus 3 for a lot that would pass one AQL step tighter where the acceptance number is 2 or more,
    plus 2 for an accepted lot otherwise, reset on any other result; reduced inspection from a score of 30. The reduced sample is drawn from the
    sample taken, so the result is averaged over seeded replications.
    """
    n_tab, x, taken = lots["table_sample_size"].to_numpy(), lots["defects_found"].to_numpy(), lots["sample_size"].to_numpy()
    ac = lots["acceptance_number"].to_numpy()
    full = np.array([min(REDUCED, key=lambda k: abs(k - v)) for v in n_tab])
    rng = np.random.default_rng([SEED, int(supplier.split("-")[1])])
    tot = dict(reduced=0, tightened=0, pieces=0, rejected=0, rejected_tightened=0)
    for _ in range(REPLICATIONS):
        state, score, recent, run_ok = "normal", 0, [], 0
        for i in range(len(x)):
            if state == "normal":
                ok = x[i] <= ac[i]
                tot["pieces"] += n_tab[i]
                step_ok = x[i] <= TIGHT_AC[full[i]] if ac[i] >= 2 else ok
                score = score + (3 if ac[i] >= 2 else 2) if step_ok else 0
                recent = (recent + [ok])[-5:]
                if recent.count(False) >= 2:
                    state, recent, run_ok, score = "tightened", [], 0, 0
                elif allow_reduced and score >= 30:
                    state, score, recent = "reduced", 0, []
            elif state == "tightened":
                ok = x[i] <= TIGHT_AC[full[i]]
                tot["tightened"] += 1
                tot["pieces"] += n_tab[i]
                tot["rejected_tightened"] += 0 if ok else 1
                run_ok = run_ok + 1 if ok else 0
                if run_ok >= 5:
                    state, recent = "normal", []
            else:
                n_red, ac_red, re_red = REDUCED[full[i]]
                n_red = min(n_red, n_tab[i])
                d = rng.hypergeometric(x[i], max(taken[i] - x[i], 0), min(n_red, taken[i])) if x[i] > 0 else 0
                tot["reduced"] += 1
                tot["pieces"] += n_red
                ok = d < re_red
                if d > ac_red:
                    state, recent = "normal", []
            tot["rejected"] += 0 if ok else 1
    return {k: v / REPLICATIONS for k, v in tot.items()}


def c0_pass_chance(n, x, n0, a, b):
    """Chance that the zero-acceptance sample holds no defect: drawn from the sample taken, or from the fitted lot quality where the sample taken is smaller."""
    return np.where(n >= n0, st.hypergeom.pmf(0, n, x, np.minimum(n0, n)), np.exp(special.betaln(a + x, b + n - x + n0) - special.betaln(a + x, b + n - x)))


def compute():
    r = query(f"select * from marts.mart_receiving_lots where supplier_id = '{SUPPLIER}' order by received_at, receiving_id")
    out = dict(lots=len(r), first=r["received_at"].min(), last=r["received_at"].max())
    # the two plans at the lot sizes of the supplier
    plans, volume = [], []
    for letter, g in r.groupby("table_code_letter", sort=True):
        lot = int(g["lot_quantity"].median())
        n, ac, n0 = int(g["table_sample_size"].iloc[0]), int(g["acceptance_number"].iloc[0]), int(g["c0_sample_size"].iloc[0])
        for name, nn, cc in ((f"Z1.4 code {letter}", n, ac), (f"c=0, lots of code {letter}", n0, 0)):
            row = plan_row(name, lot, nn, cc)
            row.update(code_letter=letter, lots=len(g), lot_range=f"{int(g['lot_quantity'].min())} to {int(g['lot_quantity'].max())}")
            plans.append(row)
        volume.append(dict(code_letter=letter, lots=len(g), z14_pieces=int(g["table_sample_size"].sum()), taken_pieces=int(g["sample_size"].sum()), c0_pieces=int(g["c0_sample_size"].sum())))
    out["plans"], out["volume"] = pd.DataFrame(plans), pd.DataFrame(volume)
    # the lot-quality distribution from the receiving history
    a, b = fit_beta_binomial(r["defects_found"].to_numpy(), r["sample_size"].to_numpy())
    dist = st.beta(a, b)
    out["distribution"] = dict(a=a, b=b, mean=float(dist.mean()), p05=float(dist.ppf(0.05)), median=float(dist.ppf(0.5)), p95=float(dist.ppf(0.95)), above_bad=float(dist.sf(BAD)),
                               pooled_rate=float(r["defects_found"].sum() / r["sample_size"].sum()), pieces=int(r["sample_size"].sum()), defects=int(r["defects_found"].sum()))
    w = dist.pdf(GRID)
    w = w / w.sum()
    bad = GRID > BAD
    exp_rows = {}
    for name, n_col, ac_of in (("Z1.4", "table_sample_size", lambda x: x.acceptance_number), ("c=0", "c0_sample_size", lambda x: 0)):
        acc_bad = acc_all = defect_pieces = 0.0
        for x in r.itertuples():
            curve = pa(GRID, x.lot_quantity, int(getattr(x, n_col)), int(ac_of(x)))
            acc_bad += float((curve * w)[bad].sum())
            acc_all += float((curve * w).sum())
            defect_pieces += float((curve * w * GRID).sum()) * x.lot_quantity
        exp_rows[name] = dict(plan=name, lots=len(r), expected_lots_above=len(r) * float(w[bad].sum()), expected_accepted=acc_all, expected_accepted_above=acc_bad,
                              share_of_bad_accepted=acc_bad / (len(r) * float(w[bad].sum())), expected_defective_pieces_accepted=defect_pieces)
    # the record: lots that passed the plan, and the chance each is above 2.5% given its sample
    post = st.beta.sf(BAD, a + r["defects_found"], b + r["sample_size"] - r["defects_found"])
    passed = (r["defects_found"] <= r["acceptance_number"]).to_numpy()
    accepted = (r["disposition"] == "accept").to_numpy()
    mean_post = (a + r["defects_found"]) / (a + b + r["sample_size"])
    exp_rows["Z1.4"].update(recorded_passed=int(passed.sum()), recorded_accepted=int(accepted.sum()), recorded_above_passed=float(post[passed].sum()), recorded_above_accepted=float(post[accepted].sum()),
                            recorded_defective_pieces_accepted=float((mean_post * r["lot_quantity"])[accepted].sum()))
    # the zero-acceptance plan on the same lots: the chance that its smaller sample, drawn from the sample taken, holds no defect
    n, x_, n0 = r["sample_size"].to_numpy(), r["defects_found"].to_numpy(), r["c0_sample_size"].to_numpy()
    p0 = c0_pass_chance(n, x_, n0, a, b)
    exp_rows["c=0"].update(recorded_passed=float(p0.sum()), recorded_accepted=np.nan, recorded_above_passed=float((p0 * post).sum()), recorded_above_accepted=np.nan,
                           recorded_defective_pieces_accepted=float((p0 * mean_post * r["lot_quantity"]).sum()))
    out["on_history"] = pd.DataFrame(exp_rows.values())
    out["above_ac_accepted"] = int((accepted & ~passed).sum())
    # escapes recorded in complaints
    c = query("select * from marts.mart_complaints where not repeated_entry order by received_date, complaint_id")
    esc = c[c["job_id"].isin(r["job_id"]) & (c["defect_code"] == "D12")].merge(r[["job_id", "receiving_id", "lot_quantity", "sample_size", "defects_found", "acceptance_number", "disposition"]], on="job_id")
    esc["chance_above"] = st.beta.sf(BAD, a + esc["defects_found"], b + esc["sample_size"] - esc["defects_found"])
    out["escapes"] = esc
    acc_lots = r[accepted]
    out["escape_summary"] = dict(complaints=len(esc), pieces=int(esc["quantity"].sum()), accepted_lots=int(accepted.sum()),
                                 mean_defects_complaint_lots=float(esc["defects_found"].mean()), mean_defects_other_accepted=float(acc_lots[~acc_lots["job_id"].isin(esc["job_id"])]["defects_found"].mean()),
                                 credit=float(esc["credit_issued"].sum()), containment=float(esc["containment_cost"].sum()), freight=float(esc["return_freight_cost"].sum()))
    # switching rules on the history
    sw = switching(r)
    out["switching_frame"] = sw.assign(received_at=r["received_at"].to_numpy())
    out["switching"] = dict(lots_on_tightened=int((sw["state"] == "tightened").sum()), switches_to_tightened=int(((sw["state"] == "tightened") & (sw["state"].shift(fill_value="normal") == "normal")).sum()),
                            not_accepted_normal=int(((sw["state"] == "normal") & ~sw["accepted"]).sum()), not_accepted_tightened=int(((sw["state"] == "tightened") & ~sw["accepted"]).sum()),
                            first_switch=str(r.loc[sw[sw["state"] == "tightened"].index.min(), "received_at"])[:10] if (sw["state"] == "tightened").any() else "",
                            plans_recorded=sorted(r["code_letter"].unique()), c0_expected_rejections=float(len(r) - p0.sum()))
    # the scorecard restated
    s = query("select * from marts.mart_supplier_history order by supplier_id")
    for col, x, n_ in (("acceptance", "lots_accepted", "lots"), ("defect", "defects_found", "pieces_sampled"), ("on_time", "lots_on_time", "lots")):
        ci = [stats.jeffreys(int(a_), int(b_)) for a_, b_ in zip(s[x], s[n_])]
        s[f"{col}_rate"], s[f"{col}_lower"], s[f"{col}_upper"] = s[x] / s[n_], [v[0] for v in ci], [v[1] for v in ci]
    s["interval_above_1pct"] = s["defect_lower"] > 0.01
    s["interval_below_1pct"] = s["defect_upper"] < 0.01
    s["small_history"] = s["lots"] < 5
    ranked = s[~s["small_history"]].sort_values(["defect_rate", "supplier_id"])
    s["restated_rank"] = s["supplier_id"].map(dict(zip(ranked["supplier_id"], range(1, len(ranked) + 1))))
    out["scorecard"] = s.sort_values("scorecard_rank_as_published").reset_index(drop=True)
    # shortcuts and dispositions by inspector, all receiving lots
    out["inspectors"] = query("""select inspector, count(*) as lots, sum(case when sample_below_table then 1 else 0 end) as sample_below_table,
                                        sum(case when above_acceptance_number then 1 else 0 end) as above_acceptance_number,
                                        sum(case when accepted_above_acceptance_number then 1 else 0 end) as accepted_above
                                 from marts.mart_receiving_lots group by 1 order by 1""")
    out["all_lots"] = query("select count(*) as lots, sum(sample_size) as pieces, sum(table_sample_size) as table_pieces, sum(c0_sample_size) as c0_pieces from marts.mart_receiving_lots").iloc[0].to_dict()
    # hours per sampled piece from the receiving inspectors' booked hours
    hrs = query("select sum(line_hours) as hours, sum(amount) as amount from marts.mart_cost_of_quality_lines where category = 'inspection labor' and source_type = 'timesheet' and source_record like 'receiving %'").iloc[0]
    rate = float(hrs["hours"]) / float(out["all_lots"]["pieces"])
    out["hours"] = dict(booked_hours=float(hrs["hours"]), booked_amount=float(hrs["amount"]), pieces=float(out["all_lots"]["pieces"]), hours_per_piece=rate, minutes_per_piece=60 * rate,
                        cost_per_hour=float(hrs["amount"]) / float(hrs["hours"]))
    # every supplier's lots under the zero-acceptance plan, by where the defect-rate interval lies
    allr = query("select * from marts.mart_receiving_lots order by received_at, receiving_id")
    a0, b0 = fit_beta_binomial(allr["defects_found"].to_numpy(), allr["sample_size"].to_numpy())
    allr["c0_pass"] = c0_pass_chance(allr["sample_size"].to_numpy(), allr["defects_found"].to_numpy(), allr["c0_sample_size"].to_numpy(), a0, b0)
    allr["passed"] = allr["defects_found"] <= allr["acceptance_number"]
    grp = allr["supplier_id"].map(s.set_index("supplier_id").apply(lambda v: "interval above 1%" if v["interval_above_1pct"] else "interval below 1%" if v["interval_below_1pct"] else "interval includes 1%", axis=1))
    out["by_interval"] = allr.groupby(grp).agg(suppliers=("supplier_id", "nunique"), lots=("receiving_id", "size"), table_pieces=("table_sample_size", "sum"), c0_pieces=("c0_sample_size", "sum"),
                                              not_passed=("passed", lambda v: int((~v).sum())), c0_expected_rejections=("c0_pass", lambda v: float((1 - v).sum()))).reset_index(names="group")
    rows = []
    for sid, g in allr.groupby("supplier_id", sort=True):
        res = switching_with_reduced(g, sid, allow_reduced=grp.loc[g.index[0]] == "interval below 1%")
        rows.append(dict(supplier_id=sid, group=grp.loc[g.index[0]], lots=len(g), table_pieces=int(g["table_sample_size"].sum()), not_passed=int((~g["passed"]).sum()), **res))
    sw_all = pd.DataFrame(rows)
    out["switching_by_supplier"] = sw_all
    out["switching_by_interval"] = sw_all.groupby("group").agg(suppliers=("supplier_id", "size"), lots=("lots", "sum"), table_pieces=("table_pieces", "sum"), switched_pieces=("pieces", "sum"),
                                                              lots_on_reduced=("reduced", "sum"), suppliers_reaching_reduced=("reduced", lambda v: int((v >= 1).sum())), lots_on_tightened=("tightened", "sum"),
                                                              not_passed_normal=("not_passed", "sum"), rejected_with_switching=("rejected", "sum"), rejected_on_tightened=("rejected_tightened", "sum")).reset_index()
    out["shortcuts"] = dict(lots=len(allr), below=int(allr["sample_below_table"].sum()), above_ac=int(allr["above_acceptance_number"].sum()), accepted_above=int(allr["accepted_above_acceptance_number"].sum()))
    out["history"] = r
    return out
