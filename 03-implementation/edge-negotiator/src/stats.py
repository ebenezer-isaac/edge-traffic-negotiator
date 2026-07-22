"""Statistical inference harness for the Edge Negotiator experimental sweep.

Source of truth: MASTER-SPEC.md section 7 ("Stats: BCa bootstrap,
Holm-Bonferroni"). The powered sweep is 30 seeds x 4 scenarios comparing four
controllers (fixed-time, MaxPressure, uncoordinated-SLM, coordinated-SLM) on
traffic metrics (average travel time, average queue, throughput).

Design constraints (deliberate):
  * stdlib + numpy ONLY. We do NOT depend on scipy. The bias-corrected and
    accelerated (BCa) bootstrap, the inverse-normal CDF, the Holm step-down
    correction and the paired permutation test are all implemented from first
    principles so that every number in the dissertation is auditable.
  * Same RNG seeds are reused across controllers in the sweep, so controller
    comparisons are PAIRED (per seed x scenario). We exploit that pairing.

References
----------
Efron, B. & Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*.
    Chapman & Hall. BCa interval: Chapter 14, eqs. (14.9)-(14.10) for z0 and
    the acceleration `a`; final endpoints eq. (14.10).
Efron, B. (1987). "Better Bootstrap Confidence Intervals." JASA 82(397).
Holm, S. (1979). "A Simple Sequentially Rejective Multiple Test Procedure."
    Scand. J. Statist. 6(2), 65-70.
Good, P. (2005). *Permutation, Parametric and Bootstrap Tests of Hypotheses*.
"""

from __future__ import annotations

import math
from typing import Callable, Dict, List

import numpy as np
import pandas as pd

__all__ = [
    "norm_cdf",
    "norm_ppf",
    "bca_bootstrap",
    "paired_diff_ci",
    "permutation_test",
    "holm_bonferroni",
    "summarize_sweep",
]


# ---------------------------------------------------------------------------
# Normal distribution helpers (no scipy).
# ---------------------------------------------------------------------------
def norm_cdf(z: float) -> float:
    """Standard normal CDF via the error function (math.erf, exact)."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p: float) -> float:
    """Standard normal inverse CDF (quantile / probit function).

    Peter Acklam's rational approximation, |error| < ~1.15e-9 over (0, 1).
    Edge cases p<=0 / p>=1 return -inf / +inf so callers can detect them.
    """
    if not (0.0 < p < 1.0):
        if p <= 0.0:
            return -math.inf
        return math.inf

    # Coefficients in rational approximations.
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]

    plow = 0.02425
    phigh = 1.0 - plow

    if p < plow:  # lower region
        q = math.sqrt(-2.0 * math.log(p))
        x = (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
    elif p <= phigh:  # central region
        q = p - 0.5
        r = q * q
        x = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
            (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    else:  # upper region
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
            ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)

    # One Halley refinement step (tightens to near machine precision).
    e = norm_cdf(x) - p
    u = e * math.sqrt(2.0 * math.pi) * math.exp(x * x / 2.0)
    x = x - u / (1.0 + x * u / 2.0)
    return x


# ---------------------------------------------------------------------------
# 1. BCa bootstrap confidence interval.
# ---------------------------------------------------------------------------
def bca_bootstrap(
    data,
    statistic: Callable[[np.ndarray], float] = np.mean,
    n_boot: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
):
    """Bias-corrected and accelerated (BCa) bootstrap CI for `statistic`.

    Implements Efron & Tibshirani (1993, Ch. 14):

      z0 (bias correction):
          z0 = Phi^-1( #{ theta*_b < theta_hat } / B )
      a  (acceleration), from the jackknife of the statistic:
          a = sum (theta_bar - theta_(i))^3
              / ( 6 * [ sum (theta_bar - theta_(i))^2 ]^(3/2) )
      adjusted percentiles:
          alpha1 = Phi( z0 + (z0 + z_a)   / (1 - a*(z0 + z_a)) )
          alpha2 = Phi( z0 + (z0 + z_1-a) / (1 - a*(z0 + z_1-a)) )
      and the CI is the (alpha1, alpha2) empirical percentiles of the
      bootstrap replicates.

    Parameters
    ----------
    data : 1-D array-like of observations.
    statistic : callable mapping a 1-D array to a scalar (default np.mean).
    n_boot : number of bootstrap resamples B.
    alpha : two-sided miscoverage; CI is 100*(1-alpha)%.
    seed : seed for np.random.default_rng (reproducibility).

    Returns
    -------
    (point, lo, hi) : observed statistic and the BCa interval endpoints.

    Edge cases (handled explicitly, not papered over)
    -------------------------------------------------
    * n < 2 observations: no resampling is meaningful -> return (point, point, point).
    * All bootstrap replicates equal the observed value (degenerate / constant
      data): proportion-below is 0 -> z0 = -inf. We detect a degenerate spread
      and return the point as a tight interval rather than emitting NaNs.
    * z0 not finite (proportion 0 or 1): clamp the proportion into
      (1/(2B), 1-1/(2B)) so z0 is finite but extreme (standard continuity fix).
    * Jackknife with all-equal leave-one-out values (denominator 0):
      a = 0, reducing BCa to the bias-corrected percentile interval.
    """
    x = np.asarray(data, dtype=float).ravel()
    n = x.size
    point = float(statistic(x))

    if n < 2:
        return point, point, point

    rng = np.random.default_rng(seed)

    # Bootstrap replicates.
    idx = rng.integers(0, n, size=(n_boot, n))
    boot = np.empty(n_boot, dtype=float)
    for b in range(n_boot):
        boot[b] = statistic(x[idx[b]])

    # Degenerate data (e.g. all observations identical): no variability.
    if np.ptp(boot) == 0.0 and np.ptp(x) == 0.0:
        return point, point, point

    # z0: bias correction from proportion of replicates strictly below point.
    prop = float(np.mean(boot < point))
    # Clamp to avoid z0 = +-inf when prop is exactly 0 or 1 (continuity fix).
    lo_clamp = 1.0 / (2.0 * n_boot)
    prop = min(max(prop, lo_clamp), 1.0 - lo_clamp)
    z0 = norm_ppf(prop)

    # a: acceleration via jackknife (leave-one-out).
    jack = np.empty(n, dtype=float)
    all_idx = np.arange(n)
    for i in range(n):
        jack[i] = statistic(x[all_idx != i])
    jack_mean = jack.mean()
    diffs = jack_mean - jack  # (theta_bar - theta_(i))
    num = np.sum(diffs ** 3)
    den = 6.0 * (np.sum(diffs ** 2) ** 1.5)
    a = 0.0 if den == 0.0 else float(num / den)

    # Adjusted percentiles.
    z_alpha_lo = norm_ppf(alpha / 2.0)
    z_alpha_hi = norm_ppf(1.0 - alpha / 2.0)

    def _adjust(z_a: float) -> float:
        denom = 1.0 - a * (z0 + z_a)
        if denom == 0.0:
            denom = 1e-12  # avoid divide-by-zero; degenerate acceleration
        return norm_cdf(z0 + (z0 + z_a) / denom)

    a1 = _adjust(z_alpha_lo)
    a2 = _adjust(z_alpha_hi)

    # Guard percentiles into [0,1] (extreme z0/a can push slightly outside).
    a1 = min(max(a1, 0.0), 1.0)
    a2 = min(max(a2, 0.0), 1.0)

    lo = float(np.quantile(boot, a1, method="linear"))
    hi = float(np.quantile(boot, a2, method="linear"))
    if lo > hi:  # numerical inversion safety
        lo, hi = hi, lo
    return point, lo, hi


# ---------------------------------------------------------------------------
# 2. Paired-difference BCa CI.
# ---------------------------------------------------------------------------
def paired_diff_ci(
    a,
    b,
    n_boot: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
) -> Dict:
    """BCa CI on the paired mean difference d_i = a_i - b_i.

    Because the sweep reuses the same RNG seeds across controllers, the i-th
    element of `a` and the i-th element of `b` are the SAME seed x scenario
    cell; the comparison is paired. We bootstrap the vector of paired
    differences (resampling pairs jointly is equivalent to resampling the
    difference vector), then form a BCa interval on its mean.

    Returns a dict:
        {
          "point": mean difference (a - b),
          "ci": (lo, hi),
          "alpha": alpha,
          "excludes_zero": bool,   # is 0 outside the CI? (significant)
          "n": number of pairs,
        }
    """
    av = np.asarray(a, dtype=float).ravel()
    bv = np.asarray(b, dtype=float).ravel()
    if av.shape != bv.shape:
        raise ValueError(
            f"paired_diff_ci requires equal-length paired inputs; "
            f"got {av.shape} vs {bv.shape}"
        )
    diff = av - bv
    point, lo, hi = bca_bootstrap(
        diff, statistic=np.mean, n_boot=n_boot, alpha=alpha, seed=seed
    )
    excludes_zero = (lo > 0.0) or (hi < 0.0)
    return {
        "point": point,
        "ci": (lo, hi),
        "alpha": alpha,
        "excludes_zero": bool(excludes_zero),
        "n": int(diff.size),
    }


# ---------------------------------------------------------------------------
# 4. Paired permutation (sign-flip) test.  [defined before #5 which uses it]
# ---------------------------------------------------------------------------
def permutation_test(
    a,
    b,
    n_perm: int = 10000,
    seed: int = 0,
    alternative: str = "two-sided",
) -> float:
    """Paired permutation p-value for the mean difference of a - b.

    Under the paired null H0: the distribution of d_i = a_i - b_i is symmetric
    about 0, so flipping the sign of any subset of the d_i is equiprobable.
    We draw `n_perm` random sign vectors s in {-1,+1}^n and compare the
    permuted mean(s*d) to the observed mean(d).

    p-value uses the standard +1 small-sample correction (Good 2005,
    Davison & Hinkley): p = (1 + #{T* as-or-more-extreme}) / (n_perm + 1),
    which keeps the test valid (never reports p = 0) and is the recommended
    estimator for a Monte-Carlo permutation distribution.

    alternative:
        "two-sided" : |T*| >= |T_obs|
        "greater"   : T* >= T_obs   (a tends to exceed b)
        "less"      : T* <= T_obs   (a tends to be below b)
    """
    if alternative not in ("two-sided", "greater", "less"):
        raise ValueError(f"unknown alternative {alternative!r}")

    av = np.asarray(a, dtype=float).ravel()
    bv = np.asarray(b, dtype=float).ravel()
    if av.shape != bv.shape:
        raise ValueError(
            f"permutation_test requires equal-length paired inputs; "
            f"got {av.shape} vs {bv.shape}"
        )
    d = av - bv
    n = d.size
    if n == 0:
        return 1.0

    t_obs = float(d.mean())

    # Degenerate: all paired differences exactly zero -> no evidence at all.
    if np.all(d == 0.0):
        return 1.0

    rng = np.random.default_rng(seed)
    signs = rng.integers(0, 2, size=(n_perm, n)) * 2 - 1  # {-1, +1}
    t_perm = (signs * d).mean(axis=1)

    tol = 1e-12  # treat ties as "as extreme" (conservative)
    if alternative == "two-sided":
        count = int(np.sum(np.abs(t_perm) >= abs(t_obs) - tol))
    elif alternative == "greater":
        count = int(np.sum(t_perm >= t_obs - tol))
    else:  # "less"
        count = int(np.sum(t_perm <= t_obs + tol))

    return (1.0 + count) / (n_perm + 1.0)


# ---------------------------------------------------------------------------
# 3. Holm-Bonferroni step-down correction.
# ---------------------------------------------------------------------------
def holm_bonferroni(
    pvalues: Dict[str, float],
    alpha: float = 0.05,
) -> Dict[str, Dict]:
    """Holm (1979) step-down multiple-comparison correction.

    Sort the m hypotheses by ascending p-value. The k-th smallest (k = 1..m)
    is compared against threshold alpha / (m - k + 1). Reject while p_(k) is
    below its threshold; on the FIRST failure, stop and accept that hypothesis
    and all larger ones (the step-down "stopping" rule -- this is what makes
    Holm uniformly more powerful than plain Bonferroni while controlling the
    family-wise error rate).

    Returns, per hypothesis name:
        {
          "p": raw p,
          "rank": 1-based rank by ascending p (ties broken by insertion order),
          "adjusted_threshold": alpha / (m - rank + 1),
          "reject": bool,
        }
    """
    if not pvalues:
        return {}

    m = len(pvalues)
    # Stable sort preserves insertion order for ties (deterministic).
    items = sorted(pvalues.items(), key=lambda kv: kv[1])

    result: Dict[str, Dict] = {}
    still_rejecting = True
    for rank, (name, p) in enumerate(items, start=1):
        threshold = alpha / (m - rank + 1)
        if still_rejecting and p <= threshold:
            reject = True
        else:
            reject = False
            still_rejecting = False  # step-down: once we fail, stop rejecting
        result[name] = {
            "p": float(p),
            "rank": rank,
            "adjusted_threshold": float(threshold),
            "reject": bool(reject),
        }
    return result


# ---------------------------------------------------------------------------
# 5. Sweep summariser.
# ---------------------------------------------------------------------------
def summarize_sweep(
    rows: List[Dict],
    metric: str,
    group_key: str = "mode",
    seed_key: str = "seed",
    baseline: str | None = None,
    n_boot: int = 10000,
    n_perm: int = 10000,
    alpha: float = 0.05,
    seed: int = 0,
    alternative: str = "two-sided",
) -> pd.DataFrame:
    """Summarise a controller sweep: per-group BCa CIs + paired diffs vs baseline.

    `rows` is a list of dicts (one per run), each with at least:
        group_key (e.g. "mode"), seed_key (e.g. "seed"), and `metric`.
    Comparisons are PAIRED on `seed_key`: for each non-baseline group we align
    on the seeds present in BOTH that group and the baseline, compute the BCa
    CI on the paired mean difference (group - baseline) and a paired permutation
    p-value, then Holm-correct the family of permutation p-values across groups.

    The baseline defaults to the alphabetically-first group if not given; in the
    Edge Negotiator sweep you would pass baseline="fixed-time" (or "maxpressure").

    Returns one DataFrame row per group with columns:
        group, n, mean, ci_lo, ci_hi,                  (per-group BCa on the metric)
        is_baseline,
        diff_vs_baseline, diff_ci_lo, diff_ci_hi,      (paired BCa diff, group-baseline)
        diff_excludes_zero, n_pairs,
        perm_p, holm_threshold, holm_reject            (multiplicity-corrected)
    """
    df = pd.DataFrame(rows)
    for col in (group_key, seed_key, metric):
        if col not in df.columns:
            raise ValueError(f"rows missing required column {col!r}")

    groups = list(dict.fromkeys(df[group_key].tolist()))  # stable unique order
    if baseline is None:
        baseline = sorted(groups)[0]
    if baseline not in groups:
        raise ValueError(f"baseline {baseline!r} not present in groups {groups}")

    # Per-seed metric per group (mean within a seed if duplicated, e.g. scenarios).
    by_group_seed = (
        df.groupby([group_key, seed_key])[metric].mean().reset_index()
    )

    def _series(g: str) -> pd.Series:
        sub = by_group_seed[by_group_seed[group_key] == g]
        return pd.Series(sub[metric].values, index=sub[seed_key].values)

    base_s = _series(baseline)

    records: List[Dict] = []
    perm_pvalues: Dict[str, float] = {}

    for g in groups:
        gs = _series(g)
        vals = gs.values.astype(float)
        m_pt, m_lo, m_hi = bca_bootstrap(
            vals, statistic=np.mean, n_boot=n_boot, alpha=alpha, seed=seed
        )

        rec: Dict = {
            "group": g,
            "n": int(vals.size),
            "mean": m_pt,
            "ci_lo": m_lo,
            "ci_hi": m_hi,
            "is_baseline": g == baseline,
            "diff_vs_baseline": np.nan,
            "diff_ci_lo": np.nan,
            "diff_ci_hi": np.nan,
            "diff_excludes_zero": False,
            "n_pairs": 0,
            "perm_p": np.nan,
            "holm_threshold": np.nan,
            "holm_reject": False,
        }

        if g != baseline:
            # Align on shared seeds for a genuine paired comparison.
            common = gs.index.intersection(base_s.index)
            common = sorted(common)
            ga = gs.loc[common].values.astype(float)
            ba = base_s.loc[common].values.astype(float)
            if ga.size >= 1:
                pd_ci = paired_diff_ci(
                    ga, ba, n_boot=n_boot, alpha=alpha, seed=seed
                )
                rec["diff_vs_baseline"] = pd_ci["point"]
                rec["diff_ci_lo"] = pd_ci["ci"][0]
                rec["diff_ci_hi"] = pd_ci["ci"][1]
                rec["diff_excludes_zero"] = pd_ci["excludes_zero"]
                rec["n_pairs"] = pd_ci["n"]
                p = permutation_test(
                    ga, ba, n_perm=n_perm, seed=seed, alternative=alternative
                )
                rec["perm_p"] = p
                perm_pvalues[g] = p

        records.append(rec)

    # Holm correction across the family of non-baseline comparisons.
    holm = holm_bonferroni(perm_pvalues, alpha=alpha)
    for rec in records:
        h = holm.get(rec["group"])
        if h is not None:
            rec["holm_threshold"] = h["adjusted_threshold"]
            rec["holm_reject"] = h["reject"]

    return pd.DataFrame.from_records(records)


# ===========================================================================
# Self-test: synthetic data with KNOWN effects. Asserts can genuinely FAIL.
# ===========================================================================
def _selftest() -> bool:
    ok = True

    def check(label: str, cond: bool, detail: str = "") -> None:
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"[{status}] {label}" + (f"  --  {detail}" if detail else ""))

    rng = np.random.default_rng(12345)

    # --- T1: BCa CI brackets the true mean of a known distribution. -------
    # Population mean = 50. Draw n=200. A correct 95% CI should contain 50.
    true_mu = 50.0
    sample = rng.normal(true_mu, 8.0, size=200)
    pt, lo, hi = bca_bootstrap(sample, n_boot=4000, seed=1)
    check(
        "T1 BCa CI brackets true mean (50) for a normal sample",
        lo < true_mu < hi,
        f"point={pt:.3f} ci=({lo:.3f},{hi:.3f})",
    )
    # And the CI must be a proper, finite, ordered interval (anti-tautology).
    check(
        "T1b BCa CI is finite and ordered (lo<point<hi)",
        math.isfinite(lo) and math.isfinite(hi) and lo < pt < hi,
        f"point={pt:.3f} ci=({lo:.3f},{hi:.3f})",
    )

    # --- T2: paired_diff_ci flags a REAL effect (B = A - 10 + noise). -----
    # Paired: same underlying "seed" draws. Mean(A-B) = +10, CI must exclude 0.
    base = rng.normal(120.0, 15.0, size=30)        # e.g. travel time, fixed-time
    A = base + rng.normal(0.0, 3.0, size=30)       # controller A
    B = A - 10.0 + rng.normal(0.0, 2.0, size=30)   # controller B is 10 better
    res_real = paired_diff_ci(A, B, n_boot=5000, seed=2)
    check(
        "T2 paired_diff_ci detects the +10 difference (CI excludes 0)",
        res_real["excludes_zero"] and res_real["ci"][0] > 0.0,
        f"point={res_real['point']:.3f} ci={tuple(round(v,3) for v in res_real['ci'])}",
    )
    check(
        "T2b paired_diff_ci point estimate near the true +10",
        8.0 < res_real["point"] < 12.0,
        f"point={res_real['point']:.3f}",
    )

    # --- T3/T4: CALIBRATION of the null.  --------------------------------
    # A single realised "null" draw can, by chance, have a non-zero sample
    # mean and be (correctly) flagged -- that is not a bug, it is sampling.
    # The honest, non-tautological check is CALIBRATION: across many genuine
    # nulls (two controllers with identical mean, independent noise), a valid
    # 95% method must (a) cover 0 ~95% of the time and (b) have permutation
    # false-positive rate ~alpha. A broken z0/acceleration would mis-cover and
    # FAIL these bounds. We use a generous tolerance for Monte-Carlo error.
    n_trials = 300
    cal_rng = np.random.default_rng(20240604)
    covered = 0
    perm_reject = 0
    for _ in range(n_trials):
        mu = cal_rng.normal(100.0, 20.0)            # arbitrary shared mean
        per_seed = cal_rng.normal(0.0, 6.0, size=30)  # paired structure
        x1 = mu + per_seed + cal_rng.normal(0.0, 3.0, size=30)
        x2 = mu + per_seed + cal_rng.normal(0.0, 3.0, size=30)  # TRUE null
        # Cheaper bootstrap inside the calibration loop (still BCa).
        r = paired_diff_ci(x1, x2, n_boot=800, seed=int(cal_rng.integers(1e9)))
        if not r["excludes_zero"]:
            covered += 1
        p = permutation_test(x1, x2, n_perm=800,
                             seed=int(cal_rng.integers(1e9)))
        if p < 0.05:
            perm_reject += 1
    coverage = covered / n_trials
    fpr = perm_reject / n_trials
    check(
        "T3 BCa coverage of a true null ~95% (0.90..0.99)",
        0.90 <= coverage <= 0.99,
        f"coverage={coverage:.3f} over {n_trials} nulls",
    )
    check(
        "T4 permutation false-positive rate ~alpha (<= 0.10)",
        fpr <= 0.10,
        f"fpr={fpr:.3f} (target ~0.05)",
    )
    # And the REAL effect must still be detected decisively (anti-tautology:
    # a method that never rejects would pass T3/T4 but fail here).
    p_real = permutation_test(A, B, n_perm=5000, seed=4)
    check(
        "T4b permutation p small for the real +10 effect",
        p_real < 0.01,
        f"p_real={p_real:.4g}",
    )

    # --- T5: Holm rejects the strongest, controls the weak. ---------------
    # Family: one tiny p (clear), two moderate, one large null.
    fam = {"strong": 0.0001, "mid1": 0.02, "mid2": 0.04, "null": 0.80}
    holm = holm_bonferroni(fam, alpha=0.05)
    check(
        "T5 Holm rejects the strongest hypothesis",
        holm["strong"]["reject"] is True,
        f"strong p={fam['strong']} thr={holm['strong']['adjusted_threshold']:.4g}",
    )
    check(
        "T5b Holm does NOT reject the obvious null",
        holm["null"]["reject"] is False,
        f"null p={fam['null']}",
    )
    # Step-down property: thresholds are alpha/(m-rank+1); strongest gets alpha/m.
    check(
        "T5c Holm strongest threshold == alpha/m",
        abs(holm["strong"]["adjusted_threshold"] - 0.05 / 4) < 1e-12,
        f"thr={holm['strong']['adjusted_threshold']:.6g} expected={0.05/4:.6g}",
    )
    # Anti-tautology: a hypothesis with p just ABOVE its step-down threshold
    # must NOT be rejected, AND it must block all weaker ones (step-down stop).
    fam2 = {"a": 0.01, "b": 0.02, "c": 0.001}  # m=3
    # sorted: c(0.001 vs .0167)->rej, a(0.01 vs .025)->rej, b(0.02 vs .05)->rej
    holm2 = holm_bonferroni(fam2, alpha=0.05)
    check(
        "T5d Holm step-down accepts when a middle p exceeds its threshold",
        # Make b fail: raise b above 0.05 so it and nothing after it rejects.
        holm_bonferroni({"c": 0.001, "a": 0.04, "b": 0.30}, 0.05)["a"]["reject"]
        is False,
        "a should be blocked: c rejects (thr .0167) but a=0.04>.025 fails, "
        "stopping rejection",
    )

    # --- T6: end-to-end summarize_sweep on the four-controller sweep. ------
    # Build 30 seeds x 4 modes. Travel time: fixed-time worst, coordinated best.
    sweep_rng = np.random.default_rng(999)
    base_seed_effect = sweep_rng.normal(0.0, 6.0, size=30)  # shared per-seed
    means = {
        "fixed-time": 130.0,
        "maxpressure": 115.0,
        "uncoordinated-slm": 112.0,
        "coordinated-slm": 100.0,
    }
    rows: List[Dict] = []
    for mode, mu in means.items():
        noise = sweep_rng.normal(0.0, 3.0, size=30)
        vals = mu + base_seed_effect + noise  # paired through base_seed_effect
        for s in range(30):
            rows.append({"mode": mode, "seed": s, "avg_travel_time": float(vals[s])})

    summary = summarize_sweep(
        rows,
        metric="avg_travel_time",
        group_key="mode",
        seed_key="seed",
        baseline="fixed-time",
        n_boot=3000,
        n_perm=3000,
        seed=7,
    )
    summary_idx = summary.set_index("group")
    check(
        "T6 summarize_sweep returns one row per mode",
        len(summary) == 4,
        f"rows={len(summary)}",
    )
    check(
        "T6b coordinated-slm vs fixed-time diff is negative and excludes 0",
        summary_idx.loc["coordinated-slm", "diff_vs_baseline"] < 0
        and bool(summary_idx.loc["coordinated-slm", "diff_excludes_zero"]),
        f"diff={summary_idx.loc['coordinated-slm','diff_vs_baseline']:.3f}",
    )
    check(
        "T6c coordinated-slm survives Holm correction (real ~30-unit gain)",
        bool(summary_idx.loc["coordinated-slm", "holm_reject"]),
        f"perm_p={summary_idx.loc['coordinated-slm','perm_p']:.4g} "
        f"thr={summary_idx.loc['coordinated-slm','holm_threshold']:.4g}",
    )
    check(
        "T6d baseline row carries no diff/perm test",
        bool(summary_idx.loc["fixed-time", "is_baseline"])
        and math.isnan(summary_idx.loc["fixed-time", "perm_p"]),
        "baseline must not be compared to itself",
    )

    # --- T7: norm_ppf / norm_cdf round-trip (the BCa engine's core). ------
    for q in (0.025, 0.5, 0.975, 0.001, 0.999):
        z = norm_ppf(q)
        back = norm_cdf(z)
        if abs(back - q) > 1e-6:
            check(f"T7 norm_ppf/cdf round-trip at q={q}", False,
                  f"got {back:.8f}")
            break
    else:
        check("T7 norm_ppf/cdf round-trip within 1e-6", True)
    # Known quantile: Phi^-1(0.975) ~ 1.959964.
    check(
        "T7b norm_ppf(0.975) == 1.959964 (known value)",
        abs(norm_ppf(0.975) - 1.959963985) < 1e-6,
        f"got {norm_ppf(0.975):.9f}",
    )

    print("-" * 60)
    print("ALL TESTS PASSED" if ok else "SOME TESTS FAILED")
    return ok


if __name__ == "__main__":
    import sys

    sys.exit(0 if _selftest() else 1)
