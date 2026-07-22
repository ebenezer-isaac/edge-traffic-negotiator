"""Exp-1 injector: an EXPLICIT parametric generative model p(x|y) for the
disambiguation dataset (MASTER-SPEC v7 §8 Experiment 1, §9 prerequisite artifact).

This module is the GENERATOR + documentation. The AUTHORITATIVE, hash-pinned
artifacts are the frozen files it writes:
  - exp1_dataset.json  : the labelled Exp-1 dataset (FlaggedCase-ready records,
                         each with event_type + anticipated/novel split), the
                         SOLE §8 Exp-1 data source (SUPERSEDES the hand-curated
                         ambiguous_decision.generate_dataset, which is retained
                         only as a stdlib unit-test fixture, NOT the §8 source).
  - exp1_ceilings.json : the frozen nonlinear Bayes ceiling (value + MC 95%
                         half-width + seed/n/python) and the axis-aligned box
                         ceiling (the RuleDisambiguator's exact function class,
                         over its real tuning grid).
Because CPython's betavariate/normalvariate are NOT in the cross-version
reproducibility contract, the COMMITTED JSONs are authoritative; the §10 hash
pin enforces they are never silently regenerated. Re-running this file on a
different interpreter may differ and MUST NOT overwrite the pinned JSONs.

NON-CIRCULAR: each label y is drawn first (balanced prior), then x ~ p(x|y);
the label is never "what the rule would decide". GENUINE overlap: class-
conditional pairs overlap by ~1 sd so no axis-aligned box reaches the Bayes
rate -> the box ceiling < the nonlinear Bayes ceiling (§8 judges the SLM vs the
nonlinear ceiling). Models the AMBIGUOUS middle: local_sensing=False for every
case. Pure stdlib.
"""
from __future__ import annotations
import json, math, random, sys, platform

EVENT_TYPES = ("emergency_claim", "incident_claim", "conservation_anomaly",
               "multi_emergency", "emergency_plus_incident")

PARAMS = {
    "real": {"corr_lambda": 2.2, "persist_kappa": 2.8, "res_mu": -0.90, "res_sigma": 0.55,
             "agree_a": 6.0, "agree_b": 2.5, "sev_a": 4.0, "sev_b": 2.0},
    "spoof_or_fault": {"corr_lambda": 0.8, "persist_kappa": 1.1, "res_mu": 0.05, "res_sigma": 0.62,
                       "agree_a": 2.2, "agree_b": 3.2, "sev_a": 2.0, "sev_b": 3.0},
}
PRIOR = {"real": 0.5, "spoof_or_fault": 0.5}
EPS = 1e-6
RESIDUAL_FLOOR = 1e-3                 # clamp so log_likelihood(residual) is finite (m9)
DENSITY_FLOOR = 1e-4                  # analytic ceiling only where mixture p(x) > floor; tail = no ceiling (§8)
OOD_PERCENTILE = 85                   # distance-from-support percentile: > threshold => novel (classifier-independent §8)
SEED = 20260721
N_PER_CLASS = 300                     # dataset size per class
CEIL_MC_N = 200000                    # MC draws for the Bayes-error integral
# RuleDisambiguator's EXACT tuning grid (mirror of ambiguous_decision.py _*_GRID; update if that changes).
_CORR_K_GRID = (0, 1, 2); _RESIDUAL_MAX_GRID = (0.75, 1.0, 1.25, 1.5)
_PERSISTENCE_P_GRID = (1, 2, 3); _AGREEMENT_MIN_GRID = (0.3, 0.5, 0.6, 0.75)

# ---- closed-form log-likelihoods ---------------------------------------------
def _log_poisson(k, lam): return -math.inf if k < 0 else k*math.log(lam) - lam - math.lgamma(k+1)
def _log_lognormal(x, mu, sigma):
    if x <= 0: return -math.inf
    return -math.log(x*sigma*math.sqrt(2*math.pi)) - (math.log(x)-mu)**2/(2*sigma**2)
def _log_beta_pdf(x, a, b):
    x = min(max(x, EPS), 1-EPS)
    return (a-1)*math.log(x) + (b-1)*math.log(1-x) - (math.lgamma(a)+math.lgamma(b)-math.lgamma(a+b))
def log_likelihood(x, y):
    p = PARAMS[y]
    return (_log_poisson(x["corroboration_count"], p["corr_lambda"])
            + _log_poisson(x["persistence"], p["persist_kappa"])
            + _log_lognormal(x["residual"], p["res_mu"], p["res_sigma"])
            + _log_beta_pdf(x["neighbour_agreement"], p["agree_a"], p["agree_b"])
            + _log_beta_pdf(x["severity"], p["sev_a"], p["sev_b"]))
def posterior_real(x):
    lr = math.log(PRIOR["real"]) + log_likelihood(x, "real")
    ls = math.log(PRIOR["spoof_or_fault"]) + log_likelihood(x, "spoof_or_fault")
    m = max(lr, ls)
    return math.exp(lr-m)/(math.exp(lr-m)+math.exp(ls-m))
def bayes_decide(x): return "real" if posterior_real(x) >= 0.5 else "spoof_or_fault"
def mixture_logdensity(x):
    lr = math.log(PRIOR["real"]) + log_likelihood(x, "real")
    ls = math.log(PRIOR["spoof_or_fault"]) + log_likelihood(x, "spoof_or_fault")
    m = max(lr, ls); return m + math.log(math.exp(lr-m)+math.exp(ls-m))

# ---- sampling ----------------------------------------------------------------
def _rpois(rnd, lam):
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1; p *= rnd.random()
        if p <= L: return k-1
def sample_x(rnd, y):
    p = PARAMS[y]
    return {
        "event_type": rnd.choice(EVENT_TYPES),        # nuisance feature (no label signal); required by FlaggedCase
        "corroboration_count": _rpois(rnd, p["corr_lambda"]),
        "persistence": _rpois(rnd, p["persist_kappa"]),
        "residual": round(max(math.exp(rnd.normalvariate(p["res_mu"], p["res_sigma"])), RESIDUAL_FLOOR), 3),
        "neighbour_agreement": round(rnd.betavariate(p["agree_a"], p["agree_b"]), 3),
        "severity": round(rnd.betavariate(p["sev_a"], p["sev_b"]), 3),
        "local_sensing": False,
    }

# ---- classifier-independent OOD split (distance from dev support) ------------
_CONT = ("corroboration_count", "persistence", "residual", "neighbour_agreement", "severity")
def _fit_standardizer(dev):
    n = len(dev); mean = {f: sum(d[f] for d in dev)/n for f in _CONT}
    std = {f: max(math.sqrt(sum((d[f]-mean[f])**2 for d in dev)/n), 1e-9) for f in _CONT}
    return mean, std
def _distance(x, mean, std): return math.sqrt(sum(((x[f]-mean[f])/std[f])**2 for f in _CONT))
def _percentile(vals, q):
    s = sorted(vals); k = (len(s)-1)*q/100.0; lo = int(math.floor(k)); hi = int(math.ceil(k))
    return s[lo] if lo == hi else s[lo] + (s[hi]-s[lo])*(k-lo)

# ---- build the frozen dataset + ceilings -------------------------------------
def build_dataset():
    rnd = random.Random(SEED)
    raw = []
    for y in ("real", "spoof_or_fault"):
        for i in range(N_PER_CLASS):
            raw.append({**sample_x(rnd, y), "label": y, "_y": y, "idx": i})
    # dev support = the sampled distribution; standardize + threshold at the pinned percentile
    mean, std = _fit_standardizer(raw)
    dists = [_distance(r, mean, std) for r in raw]
    thr = _percentile(dists, OOD_PERCENTILE)
    out = []
    for r, d in zip(raw, dists):
        split = "novel" if d > thr else "anticipated"
        out.append({
            "case_id": f"INJ-{r['_y'][:3]}-{r['idx']:04d}",
            "event_type": r["event_type"], "corroboration_count": r["corroboration_count"],
            "residual": r["residual"], "persistence": r["persistence"],
            "neighbour_agreement": r["neighbour_agreement"], "local_sensing": r["local_sensing"],
            "severity": r["severity"], "split": split, "label": r["label"],
        })
    return out, {"standardizer_mean": {f: round(mean[f], 5) for f in _CONT},
                 "standardizer_std": {f: round(std[f], 5) for f in _CONT},
                 "ood_distance_threshold": round(thr, 5), "ood_percentile": OOD_PERCENTILE}

def bayes_error_mc():
    rnd = random.Random(SEED + 1); wrong = 0
    for _ in range(CEIL_MC_N):
        y = "real" if rnd.random() < PRIOR["real"] else "spoof_or_fault"
        x = sample_x(rnd, y)
        if bayes_decide(x) != y: wrong += 1
    err = wrong/CEIL_MC_N
    return err, 1.96*math.sqrt(max(err*(1-err), 1e-12)/CEIL_MC_N)

def box_ceiling(dataset):
    """Best accuracy of RuleDisambiguator's exact function class (its real grid),
    over the anticipated (dev) split; local_sensing=False so the OR-local branch is inert."""
    dev = [d for d in dataset if d["split"] == "anticipated"]
    best, thr = 0.0, None
    for a in _CORR_K_GRID:
        for b in _RESIDUAL_MAX_GRID:
            for c in _PERSISTENCE_P_GRID:
                for dmin in _AGREEMENT_MIN_GRID:
                    ok = 0
                    for x in dev:
                        pred = ("real" if (x["corroboration_count"] >= a and x["residual"] <= b
                                and x["persistence"] >= c and x["neighbour_agreement"] >= dmin)
                                else "spoof_or_fault")
                        if pred == x["label"]: ok += 1
                    acc = ok/len(dev)
                    if acc > best: best, thr = acc, {"corr_k": a, "residual_max": b, "persistence_p": c, "agreement_min": dmin}
    return best, thr

ADEQUACY = {"status": "PENDING (real substrate not built) -> ceilings MODEL-RELATIVE",
            "check": "compare the injector's per-feature class-conditional moments vs the real "
                     "Euston SUMO-injection observed moments once euston.net.xml + a real run exist; "
                     "until then the ceilings are labelled model-relative, not real-world optima."}

if __name__ == "__main__":
    ds, ood = build_dataset()
    be, hw = bayes_error_mc()
    box_acc, box_thr = box_ceiling(ds)
    ceilings = {
        "nonlinear_bayes_ceiling_accuracy": round(1-be, 5),
        "bayes_error": round(be, 5), "bayes_error_mc_half_width_95": round(hw, 5),
        "axis_aligned_box_ceiling_accuracy": round(box_acc, 5), "box_ceiling_thresholds": box_thr,
        "headroom_bayes_minus_box": round((1-be)-box_acc, 5),
        "density_floor": DENSITY_FLOOR, **ood,
        "integration": "bounded-error Monte-Carlo over the balanced mixture; likelihood closed-form, error integral MC",
        "provenance": {"seed": SEED, "mc_n": CEIL_MC_N, "n_per_class": N_PER_CLASS,
                       "python": platform.python_version(), "note": "COMMITTED JSONs are authoritative; do not regenerate (§10 hash pin)"},
        "adequacy": ADEQUACY,
    }
    base = "03-implementation/edge-negotiator/fixtures/"
    json.dump(ds, open(base+"exp1_dataset.json", "w", encoding="utf-8"), indent=2)
    json.dump(ceilings, open(base+"exp1_ceilings.json", "w", encoding="utf-8"), indent=2)
    n_ant = sum(1 for d in ds if d["split"] == "anticipated"); n_nov = len(ds)-n_ant
    print(f"dataset n={len(ds)} anticipated={n_ant} novel={n_nov}")
    print(f"Bayes ceiling {1-be:.4f} (err {be:.4f}+/-{hw:.4f}) | box ceiling {box_acc:.4f} | headroom {(1-be)-box_acc:.4f}")
    print(f"box < Bayes: {box_acc < (1-be)-hw} | overlap(>0): {be>0} | wrote exp1_dataset.json + exp1_ceilings.json")
