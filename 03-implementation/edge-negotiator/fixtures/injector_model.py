"""Exp-1 injector: an EXPLICIT parametric generative model p(x|y) for the
disambiguation dataset (MASTER-SPEC v7 §8 Experiment 1, §9 prerequisite artifact).

FROZEN prerequisite artifact. Hash-pinned by the §10 gate. Pure stdlib (math,
random) to match the project (no numpy). It exists so that:
  1. the labelled Exp-1 dataset is NON-CIRCULAR: each label y is sampled from a
     documented generative story and the observable x is drawn from p(x|y);
     the label is NOT "whatever the rule would decide".
  2. the NONLINEAR Bayes-optimal ceiling is computable ANALYTICALLY/by bounded-
     error MC from the KNOWN p(x|y) (the Naive-Bayes posterior), and
  3. the reference rule's function class (RuleDisambiguator = an axis-aligned
     CONJUNCTION on {corr>=a, residual<=b, persistence>=c, agreement>=d}, OR'd
     with local_sensing) PROVABLY cannot reach the Bayes ceiling: the Bayes
     boundary is the log-likelihood-ratio surface, which is NOT axis-aligned,
     so a box classifier leaves a measurable gap. §8 reports BOTH ceilings and
     judges the SLM against the nonlinear one.

Scope: models the AMBIGUOUS/flagged middle (the cases that escalate per
FORMAL-SPECIFICATION §8) -> local_sensing is False for every injected case
(fully-sensed cases resolve deterministically and never reach the module), so
the discrimination lives entirely in the noisy continuous/count features, with
GENUINE class overlap (Bayes error > 0).

Feature model (conditional independence given y = Naive Bayes; closed-form
per-feature likelihood so the joint is closed-form):
  corroboration_count | y ~ Poisson(lambda_y)
  residual (band units)| y ~ LogNormal(mu_y, sigma_y)
  persistence          | y ~ Poisson(kappa_y)
  neighbour_agreement  | y ~ Beta(a_y, b_y)                 (clamped to (eps,1-eps))
  severity             | y ~ Beta(c_y, d_y)
  local_sensing        = False (ambiguous middle)
Priors P(real)=P(spoof_or_fault)=0.5 (balanced; the pinned class prior).

Every class-conditional pair OVERLAPS by construction (means differ by ~1 sd),
so no single feature and no axis-aligned box separates the classes at the Bayes
rate. Params are frozen constants below (PARAMS); changing them changes the
pinned hash.
"""
from __future__ import annotations
import math, random

# ---- frozen generative parameters (per class) --------------------------------
PARAMS = {
    "real": {
        "corr_lambda": 2.2, "persist_kappa": 2.8,
        "res_mu": -0.90, "res_sigma": 0.55,          # median residual ~0.41 (in-band)
        "agree_a": 6.0, "agree_b": 2.5,               # mean ~0.71
        "sev_a": 4.0, "sev_b": 2.0,                   # mean ~0.67
    },
    "spoof_or_fault": {
        "corr_lambda": 0.8, "persist_kappa": 1.1,
        "res_mu": 0.05, "res_sigma": 0.62,            # median residual ~1.05 (near/out of band)
        "agree_a": 2.2, "agree_b": 3.2,               # mean ~0.41
        "sev_a": 2.0, "sev_b": 3.0,                   # mean ~0.40
    },
}
PRIOR = {"real": 0.5, "spoof_or_fault": 0.5}
EPS = 1e-6

# Numeric density floor (§8/§9): the analytic ceiling is reported only where the
# mixture density p(x) exceeds this floor (in-distribution). On the low-density
# tail (novel/OOD split, distance-from-dev-support > threshold) NO optimal
# reference is claimed (§8): the SLM's tail performance is reported without a
# ceiling. p(x) = sum_y PRIOR[y]*exp(log_likelihood(x,y)).
DENSITY_FLOOR = 1e-4

# Analytic vs MC (§8/§9): the per-feature LIKELIHOODS are CLOSED-FORM (analytic).
# The Bayes-ERROR integral of this multivariate Naive-Bayes model has no closed
# form (the boundary is the log-likelihood-ratio = 0 surface), so it is computed
# by BOUNDED-ERROR Monte-Carlo with a propagated 95% half-width (§9 permits a
# "closed-form OR bounded-error-integrable likelihood"; the likelihood is
# closed-form, the error integral is bounded-error). n>=200k gives half-width
# ~1e-3.
def mixture_logdensity(x: dict) -> float:
    lr = math.log(PRIOR["real"]) + log_likelihood(x, "real")
    ls = math.log(PRIOR["spoof_or_fault"]) + log_likelihood(x, "spoof_or_fault")
    m = max(lr, ls)
    return m + math.log(math.exp(lr - m) + math.exp(ls - m))

# ---- closed-form log-likelihoods ---------------------------------------------
def _log_poisson(k: int, lam: float) -> float:
    if k < 0: return -math.inf
    return k * math.log(lam) - lam - math.lgamma(k + 1)

def _log_lognormal(x: float, mu: float, sigma: float) -> float:
    if x <= 0: return -math.inf
    return (-math.log(x * sigma * math.sqrt(2 * math.pi))
            - (math.log(x) - mu) ** 2 / (2 * sigma ** 2))

def _log_beta_pdf(x: float, a: float, b: float) -> float:
    x = min(max(x, EPS), 1 - EPS)
    logB = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    return (a - 1) * math.log(x) + (b - 1) * math.log(1 - x) - logB

def log_likelihood(x: dict, y: str) -> float:
    """log p(x | y) under the frozen Naive-Bayes model (closed-form)."""
    p = PARAMS[y]
    return (_log_poisson(x["corroboration_count"], p["corr_lambda"])
            + _log_poisson(x["persistence"], p["persist_kappa"])
            + _log_lognormal(x["residual"], p["res_mu"], p["res_sigma"])
            + _log_beta_pdf(x["neighbour_agreement"], p["agree_a"], p["agree_b"])
            + _log_beta_pdf(x["severity"], p["sev_a"], p["sev_b"]))

def posterior_real(x: dict) -> float:
    lr = math.log(PRIOR["real"]) + log_likelihood(x, "real")
    ls = math.log(PRIOR["spoof_or_fault"]) + log_likelihood(x, "spoof_or_fault")
    m = max(lr, ls)
    return math.exp(lr - m) / (math.exp(lr - m) + math.exp(ls - m))

def bayes_decide(x: dict) -> str:
    return "real" if posterior_real(x) >= 0.5 else "spoof_or_fault"

# ---- sampling ----------------------------------------------------------------
def _rbeta(rnd, a, b): return rnd.betavariate(a, b)
def _rpois(rnd, lam):
    # Knuth
    L, k, p = math.exp(-lam), 0, 1.0
    while True:
        k += 1; p *= rnd.random()
        if p <= L: return k - 1

def sample_x(rnd: random.Random, y: str) -> dict:
    p = PARAMS[y]
    return {
        "corroboration_count": _rpois(rnd, p["corr_lambda"]),
        "persistence": _rpois(rnd, p["persist_kappa"]),
        "residual": round(math.exp(rnd.normalvariate(p["res_mu"], p["res_sigma"])), 3),
        "neighbour_agreement": round(_rbeta(rnd, p["agree_a"], p["agree_b"]), 3),
        "severity": round(_rbeta(rnd, p["sev_a"], p["sev_b"]), 3),
        "local_sensing": False,
    }

def sample_dataset(seed: int, n_per_class: int):
    """Deterministic labelled dataset: n_per_class of each label. Label sampled
    first (the generative story), then x ~ p(x|y). Non-circular by construction."""
    rnd = random.Random(seed)
    out = []
    for y in ("real", "spoof_or_fault"):
        for i in range(n_per_class):
            x = sample_x(rnd, y)
            out.append({**x, "label": y, "case_id": f"{y[:3]}-{i:04d}"})
    return out

# ---- ceilings ----------------------------------------------------------------
def bayes_error_mc(seed: int, n: int):
    """Bounded-error MC estimate of the Bayes error (integration method =
    Monte-Carlo over the balanced mixture, with a binomial 95% half-width)."""
    rnd = random.Random(seed)
    wrong = 0
    for _ in range(n):
        y = "real" if rnd.random() < PRIOR["real"] else "spoof_or_fault"
        x = sample_x(rnd, y)
        if bayes_decide(x) != y: wrong += 1
    err = wrong / n
    half = 1.96 * math.sqrt(max(err * (1 - err), 1e-12) / n)
    return err, half

def axis_aligned_ceiling(seed: int, n: int):
    """Best accuracy achievable by the RuleDisambiguator's function class
    (corr>=a AND residual<=b AND persistence>=c AND agreement>=d; local_sensing
    is False here so the OR-local branch is inert), grid-searched on a large
    sampled set. This is the reference rule's ceiling; it is < the Bayes ceiling
    because the box cannot match the log-likelihood-ratio boundary."""
    rnd = random.Random(seed)
    data = [(sample_x(rnd, y), y) for _ in range(n)
            for y in ("real",) ] + [(sample_x(rnd, "spoof_or_fault"), "spoof_or_fault") for _ in range(n)]
    A = (0, 1, 2, 3); B = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
    C = (1, 2, 3, 4); D = (0.3, 0.4, 0.5, 0.6, 0.7, 0.8)
    best = 0.0; best_thr = None
    for a in A:
        for b in B:
            for c in C:
                for d in D:
                    ok = 0
                    for x, y in data:
                        pred = ("real" if (x["corroboration_count"] >= a and x["residual"] <= b
                                and x["persistence"] >= c and x["neighbour_agreement"] >= d)
                                else "spoof_or_fault")
                        if pred == y: ok += 1
                    acc = ok / len(data)
                    if acc > best: best, best_thr = acc, (a, b, c, d)
    return best, best_thr

# ---- model-adequacy check (spec §8/§9) ---------------------------------------
ADEQUACY = {
    "required_before_inferential_use": True,
    "check": "compare the injector's per-feature class-conditional MOMENTS "
             "(mean/variance of corroboration_count, residual, persistence, "
             "neighbour_agreement) against the real Euston SUMO-injection "
             "observed moments once euston.net.xml + a real injection run exist; "
             "the ceiling is labelled 'model-relative, not a real-world optimum' "
             "until this check passes.",
    "status": "PENDING (real substrate not built yet) -> ceilings are MODEL-RELATIVE",
}

if __name__ == "__main__":
    be, hw = bayes_error_mc(seed=12345, n=200000)
    acc_ceil, thr = axis_aligned_ceiling(seed=999, n=20000)
    print(f"Bayes error (MC n=200k): {be:.4f} +/- {hw:.4f}  -> Bayes ceiling acc = {1-be:.4f}")
    print(f"axis-aligned box ceiling: acc = {acc_ceil:.4f} at (corr>=,res<=,persist>=,agree>=) = {thr}")
    print(f"headroom (Bayes - box): {(1-be) - acc_ceil:.4f}  (the gap the SLM could capture)")
    print(f"genuine overlap (Bayes error > 0): {be > 0.0}; better than chance (< 0.5): {be < 0.5}")
    print(f"box strictly below Bayes ceiling: {acc_ceil < (1-be) - hw}")
