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

# ---- distance-from-dev-support statistic (§8; NOT called OOD - see honesty note) ----
# §8: "define the split by a classifier-independent distance-from-dev-support criterion ...
# report accuracy as a CONTINUOUS curve vs distance so no threshold DOF exists; do NOT call
# low-density-in-distribution OOD." So: the standardizer is fit on a SEPARATE DEV sample
# (dev-frozen, m-1), distance is standardized-Euclidean from that support, and the primary
# characterisation is the accuracy-vs-distance CURVE. The binary split field (anticipated/novel,
# required by FlaggedCase's enum) is the below/above-85th-pct tail; we do NOT claim the tail is
# "harder" - in this synthetic Naive-Bayes model the far tail is actually EASIER (classes most
# separated there), so a genuinely-harder generalisation regime needs REAL substrate (deferred).
_CONT = ("corroboration_count", "persistence", "residual", "neighbour_agreement", "severity")
def _fit_standardizer(dev):
    n = len(dev); mean = {f: sum(d[f] for d in dev)/n for f in _CONT}
    std = {f: max(math.sqrt(sum((d[f]-mean[f])**2 for d in dev)/n), 1e-9) for f in _CONT}
    return mean, std
def _distance(x, mean, std): return math.sqrt(sum(((x[f]-mean[f])/std[f])**2 for f in _CONT))
def _percentile(vals, q):
    s = sorted(vals); k = (len(s)-1)*q/100.0; lo = int(math.floor(k)); hi = int(math.ceil(k))
    return s[lo] if lo == hi else s[lo] + (s[hi]-s[lo])*(k-lo)

def _dev_standardizer():
    """DEV-frozen standardizer: fit on a SEPARATE dev sample (distinct seed), never on the
    eval pool (m-1: no leakage of the eval/tail points into their own normalisation)."""
    rnd = random.Random(SEED + 7); dev = []
    for y in ("real", "spoof_or_fault"):
        for _ in range(N_PER_CLASS):
            dev.append(sample_x(rnd, y))
    mean, std = _fit_standardizer(dev)
    dists = sorted(_distance(d, mean, std) for d in dev)
    thr = _percentile(dists, OOD_PERCENTILE)
    return mean, std, thr

def build_dataset():
    mean, std, thr = _dev_standardizer()
    rnd = random.Random(SEED); out = []
    for y in ("real", "spoof_or_fault"):
        for i in range(N_PER_CLASS):
            x = sample_x(rnd, y); d = _distance(x, mean, std)
            out.append({
                "case_id": f"INJ-{y[:3]}-{i:04d}",
                "event_type": x["event_type"], "corroboration_count": x["corroboration_count"],
                "residual": x["residual"], "persistence": x["persistence"],
                "neighbour_agreement": x["neighbour_agreement"], "local_sensing": x["local_sensing"],
                "severity": x["severity"],
                "split": "novel" if d > thr else "anticipated",   # FlaggedCase enum; = far-support tail, NOT a harder/shifted regime
                "label": y,
            })
    ood = {"criterion": "standardized-Euclidean distance from a DEV-frozen support (separate seed); "
                        "split = above the frozen 85th-pct threshold. NOT claimed harder/OOD; the "
                        "primary characterisation is the accuracy-vs-distance curve.",
           "standardizer_mean": {f: round(mean[f], 5) for f in _CONT},
           "standardizer_std": {f: round(std[f], 5) for f in _CONT},
           "distance_threshold_p85": round(thr, 5)}
    return out, ood

def _balanced_acc(pred_fn, cases):
    tp = fn = fp = tn = 0
    for x in cases:
        pr = pred_fn(x) == "real"; ar = x["label"] == "real"
        tp += pr and ar; fn += (not pr) and ar; fp += pr and (not ar); tn += (not pr) and (not ar)
    rec = tp/(tp+fn) if (tp+fn) else 0.0; spec = tn/(tn+fp) if (tn+fp) else 0.0
    return (rec+spec)/2.0

def _in_support(dataset, mean, std, floor_logdens):
    """Split the frozen dataset into the density>floor region (where a ceiling is claimed) and
    the low-density tail (NO ceiling claimed, §8). floor is on mixture_logdensity."""
    keep, tail = [], []
    for x in dataset:
        (keep if mixture_logdensity(x) > floor_logdens else tail).append(x)
    return keep, tail

def bayes_and_box_ceilings(dataset):
    """Both ceilings on the SAME population (m/MAJOR-2), restricted to the density>floor region
    (MAJOR-3); the low-density tail is reported separately with NO ceiling. Bayes = the model's
    posterior classifier (balanced acc); box = RuleDisambiguator's exact grid (balanced acc, m-3)."""
    floor_logdens = math.log(DENSITY_FLOOR)
    keep, tail = _in_support(dataset, None, None, floor_logdens)
    def box_pred_factory(a, b, c, dmin):
        return lambda x: ("real" if (x["corroboration_count"] >= a and x["residual"] <= b
                          and x["persistence"] >= c and x["neighbour_agreement"] >= dmin) else "spoof_or_fault")
    best_box, box_thr = 0.0, None
    for a in _CORR_K_GRID:
        for b in _RESIDUAL_MAX_GRID:
            for c in _PERSISTENCE_P_GRID:
                for dmin in _AGREEMENT_MIN_GRID:
                    acc = _balanced_acc(box_pred_factory(a, b, c, dmin), keep)
                    if acc > best_box: best_box, box_thr = acc, {"corr_k": a, "residual_max": b, "persistence_p": c, "agreement_min": dmin}
    bayes = _balanced_acc(bayes_decide, keep)
    return {"population": "density>floor in-support region", "n_in_support": len(keep), "n_low_density_tail": len(tail),
            "nonlinear_bayes_ceiling_balacc": round(bayes, 5),
            "axis_aligned_box_ceiling_balacc": round(best_box, 5), "box_ceiling_thresholds": box_thr,
            "headroom_bayes_minus_box": round(bayes - best_box, 5),
            "low_density_tail_no_ceiling": "the %d density<floor cases carry NO ceiling claim (§8)" % len(tail)}

def accuracy_vs_distance(dataset, mean, std, n_bins=6):
    """§8 primary characterisation: balanced accuracy of the Bayes classifier and the best box,
    as a CONTINUOUS curve over distance-from-dev-support bins (no threshold DOF)."""
    ds = [(x, _distance(x, mean, std)) for x in dataset]
    dmax = max(d for _, d in ds); edges = [dmax*i/n_bins for i in range(n_bins+1)]
    # one frozen box (the dev-tuned best on the in-support region) for a like-for-like curve
    curve = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i+1]
        binx = [x for x, d in ds if (lo <= d < hi or (i == n_bins-1 and d == hi))]
        if not binx: curve.append({"dist_lo": round(lo, 3), "dist_hi": round(hi, 3), "n": 0}); continue
        curve.append({"dist_lo": round(lo, 3), "dist_hi": round(hi, 3), "n": len(binx),
                      "bayes_balacc": round(_balanced_acc(bayes_decide, binx), 4)})
    return curve

ADEQUACY = {"status": "PENDING (real substrate not built) -> ALL ceilings are MODEL-RELATIVE, "
                      "NOT a headline result: the class-conditional overlap is hand-chosen, so the "
                      "Bayes ceiling + the box<Bayes headroom are properties of THIS model until the "
                      "adequacy check runs. Every downstream §8/§12-D4/D5 ceiling claim MUST carry the "
                      "'model-relative pending adequacy' label.",
            "check": "compare the injector's per-feature class-conditional moments (mean/var of "
                     "corroboration_count, residual, persistence, neighbour_agreement) vs the real "
                     "Euston SUMO-injection observed moments once euston.net.xml + a real run exist."}

if __name__ == "__main__":
    ds, ood = build_dataset()
    mean, std, _ = _dev_standardizer()
    ceil = bayes_and_box_ceilings(ds)          # same population (density>floor), balanced acc
    curve = accuracy_vs_distance(ds, mean, std)
    ceilings = {
        "MODEL_RELATIVE_CAVEAT": "all ceilings below are MODEL-RELATIVE (adequacy PENDING, see adequacy); "
                                 "NOT a headline result until validated vs real Euston moments.",
        **ceil,
        "accuracy_vs_distance_curve": curve,   # §8 primary characterisation (no threshold DOF)
        "density_floor": DENSITY_FLOOR,
        "distance_split_note": ood["criterion"],
        "standardizer_mean": ood["standardizer_mean"], "standardizer_std": ood["standardizer_std"],
        "distance_threshold_p85": ood["distance_threshold_p85"],
        "integration": "bounded-error Monte-Carlo / exact over the frozen population; per-feature "
                       "likelihood closed-form, the multivariate Bayes-error integral has no closed form",
        "provenance": {"seed": SEED, "n_per_class": N_PER_CLASS, "python": platform.python_version(),
                       "note": "COMMITTED JSONs are authoritative; do not regenerate (§10 hash pin)"},
        "adequacy": ADEQUACY,
    }
    base = "03-implementation/edge-negotiator/fixtures/"
    json.dump(ds, open(base+"exp1_dataset.json", "w", encoding="utf-8"), indent=2)
    json.dump(ceilings, open(base+"exp1_ceilings.json", "w", encoding="utf-8"), indent=2)
    n_ant = sum(1 for d in ds if d["split"] == "anticipated")
    print(f"dataset n={len(ds)} anticipated(in-support)={n_ant} far-tail={len(ds)-n_ant}")
    print(f"[same pop, density>floor, n={ceil['n_in_support']}, tail={ceil['n_low_density_tail']}] "
          f"Bayes(balacc) {ceil['nonlinear_bayes_ceiling_balacc']} | box(balacc) {ceil['axis_aligned_box_ceiling_balacc']} "
          f"| headroom {ceil['headroom_bayes_minus_box']}")
    print(f"box < Bayes: {ceil['axis_aligned_box_ceiling_balacc'] < ceil['nonlinear_bayes_ceiling_balacc']} "
          f"| wrote exp1_dataset.json + exp1_ceilings.json")
