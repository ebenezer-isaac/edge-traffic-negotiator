"""Experiment D: the self-referential coupling boundary (MASTER-SPEC §4.5; gate D6).

The measured BLIND SPOT of the H2 audit, stated honestly as a boundary, not defended.
The self-referential twist: the preemption attack CONTROLS the signal phase, and the
phase GATES honest-witness coverage of a deviation footprint, so an insider can open a
COVERAGE DESERT that conceals a bounded, conservation-consistent deviation.

What this module demonstrates (all self-contained; no SUMO/Foundry):
  1. An INDEPENDENTLY-CALIBRATED conservation-residual detection threshold tau, fixed at
     a pinned false-positive budget over BENIGN residuals WITHOUT reference to any attack
     set (§4.5). NOTE: this is a STATIC quantile operating point (a simplified stand-in
     for the sequential-CUSUM detector the full §4.5 protocol specifies), NOT a sequential
     CUSUM; the benign-residual distribution vs tau is reported.
  2. A CONSERVATION-CONSISTENT deviation class: deviations whose residual stays below
     tau, so they leave no conservation trace and can only be caught by LIVE witness
     coverage.
  3. The phase-coupled COVERAGE-vs-ESCAPE SURFACE: per cell (average coverage x
     phase-lock degree), a Monte-Carlo escape proportion with a DESCRIPTIVE bootstrap
     CI. Escape = conservation-consistent AND in a coverage desert (unwitnessed) AND no
     quorum/cross-audit trace (honest-quorum hypothesis).
  4. The conditional LEMMA: under the four SUFFICIENT hypotheses [dense phase-coupled
     coverage > threshold] and [honest keys] and [cross-audited non-equivocating quorum]
     and [no operator creation-time omission], escape -> 0 (every deviation caught live
     or leaves a detectable trace). Verified numerically in the dense-coverage regime.
  5. The severe DIRECTIONAL finding at the phase-locked pocket (escape exceeds the
     well-mixed closed-form comparator at MATCHED average coverage), computed
     DESCRIPTIVELY.

HONEST GATE (this is the whole point of §4.5 / D6). The witness coverage here is
MODELLED, not grounded in documented A501 SCOOT/MOVA loop placement, and the demand is
not time-resolved. The spec REQUIRES that modelled cells be EXCLUDED from the headline
inferential contrast, and that the pre-registered contrast (estimator + external-harm
Delta + named CI + fixed-N seal) is a pre-registration PROTOCOL, NOT a passed control,
until those §9 artifacts exist and are hashed. So this run reports the surface + lemma
+ descriptive contrast as a MODELLED PILOT, and records the inferential decision as
PROTOCOL_NOT_A_PASSED_CONTROL. Geometry is n=1 (this corridor); no "corridors in
general" claim is made.
"""
from __future__ import annotations

import json
import math
import os
import random
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))

# --- Pinned protocol parameters (would live under the §8 seal for a real run). ---
FP_BUDGET = 0.05          # false-positive budget the CUSUM threshold is calibrated to
BENIGN_SCALE = 1.0        # scale of the benign conservation-residual distribution
COVERAGE_GRID = [0.1, 0.3, 0.5, 0.7, 0.9]   # average coverage levels (x-axis cells)
PHASELOCK_GRID = [0.0, 0.5, 1.0]            # 0 = well-mixed, 1 = fully phase-locked
MC_TRIALS = 4000          # Monte-Carlo draws per cell
BOOTSTRAP = 1000          # descriptive bootstrap resamples for per-cell CI
SEED = 42                 # fixed (no seed-manufactured significance)
# External-harm Delta placeholder: the decision-changing contrast magnitude. A REAL
# value must come from an external operational-harm threshold (§4.5); until then the
# decision is not run, so this is only illustrative of the protocol shape.
DELTA_EXTERNAL_HARM = 0.10


def _rng(seed):
    return random.Random(seed)


def calibrate_cusum_threshold(fp_budget=FP_BUDGET, scale=BENIGN_SCALE,
                              n=20000, seed=SEED) -> dict:
    """Calibrate the conservation-residual detection threshold tau (a STATIC quantile
    operating point, a simplified stand-in for the sequential-CUSUM detector) at a pinned
    FP budget over BENIGN residuals, WITHOUT reference to any attack (§4.5). Benign residuals are
    modelled as half-normal(scale) (nonneg magnitudes). tau = the (1-fp_budget) quantile
    so a benign residual exceeds tau with probability fp_budget."""
    r = _rng(seed)
    benign = sorted(abs(r.gauss(0.0, scale)) for _ in range(n))
    idx = min(n - 1, max(0, math.ceil((1.0 - fp_budget) * n) - 1))
    tau = benign[idx]
    realised_fp = sum(1 for x in benign if x > tau) / n
    return {"tau": tau, "fp_budget": fp_budget, "realised_fp_rate": realised_fp,
            "benign_model": f"half-normal(scale={scale})", "n_calib": n,
            "benign_residual_p50": benign[n // 2],
            "benign_residual_p95": benign[min(n - 1, math.ceil(0.95 * n) - 1)]}


def _effective_coverage(avg_coverage: float, phaselock: float) -> float:
    """Effective coverage of the FOOTPRINT given average coverage and phase-lock.

    Well-mixed (phaselock=0): the footprint sees the average coverage. Fully phase-locked
    (phaselock=1): the attacker, controlling the phase, suppresses the footprint's
    covering phase, so the footprint's effective coverage collapses toward 0 even though
    the AVERAGE coverage (across approaches) is unchanged -- the coverage desert. Linear
    interpolation is the simplest monotone model of the coupling; it is MODELLED, not
    measured, and is the quantity the real A501 loop geometry would replace."""
    return avg_coverage * (1.0 - phaselock)


def escape_proportion(avg_coverage: float, phaselock: float, tau: float,
                      trials=MC_TRIALS, seed=SEED) -> list:
    """Monte-Carlo: per trial, a conservation-consistent deviation (residual drawn below
    tau, so no conservation trace) escapes iff it is ALSO unwitnessed (coverage desert).
    Returns the 0/1 escape outcomes (for descriptive bootstrap CI). The honest-quorum +
    no-omission hypotheses hold here, so there is no separate equivocation trace: the
    only live channel is witness coverage."""
    r = _rng(seed + int(1000 * avg_coverage) + int(37 * phaselock))
    c_eff = _effective_coverage(avg_coverage, phaselock)
    out = []
    for _ in range(trials):
        # conservation-consistent by construction: residual uniformly in [0, tau)
        _residual = r.random() * tau            # < tau -> no conservation trace
        witnessed = r.random() < c_eff          # caught live iff covered
        out.append(0 if witnessed else 1)       # escape iff unwitnessed
    return out


def _mean_ci(outcomes: list, boot=BOOTSTRAP, seed=SEED) -> dict:
    """Descriptive bootstrap mean + 95% CI (NON-inferential; no per-cell claim)."""
    n = len(outcomes)
    mean = sum(outcomes) / n if n else 0.0
    r = _rng(seed)
    means = []
    for _ in range(boot):
        s = sum(outcomes[r.randrange(n)] for _ in range(n)) / n
        means.append(s)
    means.sort()
    lo = means[max(0, math.ceil(0.025 * boot) - 1)]
    hi = means[min(boot - 1, math.ceil(0.975 * boot) - 1)]
    return {"escape_mean": mean, "ci95_low": lo, "ci95_high": hi, "n": n}


def wellmixed_comparator(avg_coverage: float) -> float:
    """Closed-form well-mixed escape prediction at a given average coverage: if coverage
    were uniform (no phase-coupling), a conservation-consistent deviation escapes iff
    unwitnessed, probability (1 - avg_coverage). Parameters: uniform coverage, single
    footprint, honest quorum. Variance: Monte-Carlo/Binomial (stated, not modelled as 0)."""
    return 1.0 - avg_coverage


def build_surface(tau: float) -> dict:
    """The coverage-vs-escape surface over (avg_coverage x phaselock) cells, MODELLED."""
    cells = []
    for c in COVERAGE_GRID:
        for d in PHASELOCK_GRID:
            outcomes = escape_proportion(c, d, tau)
            stat = _mean_ci(outcomes)
            cells.append({
                "avg_coverage": c, "phaselock": d,
                "effective_coverage": _effective_coverage(c, d),
                "escape_mean": stat["escape_mean"],
                "escape_ci95": [stat["ci95_low"], stat["ci95_high"]],
                "wellmixed_escape": wellmixed_comparator(c),
                "excess_over_wellmixed": stat["escape_mean"] - wellmixed_comparator(c),
                "cell_provenance": "MODELLED",  # not documented A501 loop placement
            })
    return {"cells": cells, "coverage_grid": COVERAGE_GRID,
            "phaselock_grid": PHASELOCK_GRID, "mc_trials": MC_TRIALS}


def lemma_check(tau: float, dense_threshold: float = 0.9) -> dict:
    """Verify the conditional lemma numerically: under DENSE phase-coupled coverage
    (avg_coverage >= dense_threshold) in the WELL-MIXED regime (phaselock=0, so the
    footprint actually sees that dense coverage) + honest keys + cross-audited quorum +
    no omission, escape -> 0 (caught live or leaves a trace). We report escape at the
    densest well-mixed cell; the lemma holds iff it is near 0."""
    outcomes = escape_proportion(max(COVERAGE_GRID), 0.0, tau)
    stat = _mean_ci(outcomes)
    return {
        "hypotheses": [
            "phase-coupled coverage of the footprint within its live phase window > threshold",
            "honest independent corroboration keys only",
            "cross-audited non-equivocating quorum",
            "no operator creation-time omission",
        ],
        "dense_wellmixed_escape_mean": stat["escape_mean"],
        "lemma_holds_numerically": stat["escape_mean"] <= (1.0 - dense_threshold) + 0.02,
        "note": ("escape -> 0 as coverage -> 1 in the well-mixed regime; the residual is "
                 "the 1-coverage witness-miss floor, not an audit failure. The lemma is "
                 "near-definitional; its content is the empirical coverage threshold."),
    }


def severe_contrast(surface: dict) -> dict:
    """The ONE severe directional finding, computed DESCRIPTIVELY (not as a passed
    inferential control). Estimator = escape at the phase-locked pocket MINUS escape
    elsewhere at MATCHED average coverage (same avg_coverage, phaselock 1 vs 0)."""
    by = {(c["avg_coverage"], c["phaselock"]): c for c in surface["cells"]}
    rows = []
    for c in COVERAGE_GRID:
        locked = by.get((c, 1.0))
        mixed = by.get((c, 0.0))
        if locked and mixed:
            rows.append({
                "avg_coverage": c,
                "phaselocked_escape": locked["escape_mean"],
                "wellmixed_escape": mixed["escape_mean"],
                "contrast": locked["escape_mean"] - mixed["escape_mean"],
            })
    # The headline estimator: mean contrast at mid-coverage cells (where a pocket can
    # exist). Descriptive only.
    mid = [r["contrast"] for r in rows if 0.3 <= r["avg_coverage"] <= 0.7]
    est = sum(mid) / len(mid) if mid else 0.0
    return {
        "estimator": "escape(phase-locked pocket) - escape(well-mixed) at matched avg coverage",
        "per_coverage": rows,
        "descriptive_estimate_mid_coverage": est,
        "delta_external_harm_placeholder": DELTA_EXTERNAL_HARM,
        "direction_as_predicted": est > 0,  # phase-lock raises escape above well-mixed
        "decision_rule": "lower one-sided CI bound on the contrast EXCEEDS Delta (NOT excludes zero)",
        "ci_method": "curve-bootstrap, N fixed under the seal",
        "inferential_decision": "NOT_RUN",
        "status": "PROTOCOL_NOT_A_PASSED_CONTROL",
        "why_gated": [
            "witness coverage is MODELLED, not grounded in documented A501 SCOOT/MOVA "
            "loop placement -> per §4.5 modelled cells are EXCLUDED from the headline "
            "inferential contrast",
            "demand is not time-resolved (§8 hard startup gate) -> no inferential claim",
            "Delta must be pinned to a real external operational-harm threshold, not the "
            "placeholder here",
            "the pre-registration seal (estimator + comparator + Delta + CI + fixed N + "
            "hashed §9 artifacts) is not yet in force",
        ],
    }


def run() -> dict:
    calib = calibrate_cusum_threshold()
    calib["detector_note"] = ("static quantile operating point at the pinned FP budget; "
                              "a simplified stand-in for the sequential-CUSUM detector, "
                              "NOT a sequential CUSUM")
    tau = calib["tau"]
    surface = build_surface(tau)
    lemma = lemma_check(tau)
    contrast = severe_contrast(surface)
    result = {
        "experiment": "H2_experiment_D_coupling_boundary",
        "gate": "D6 (§4.5) -- SUPPORTING H2 boundary result",
        "label": "MODELLED PILOT (descriptive); inferential contrast PROTOCOL-gated",
        "geometry": "n=1 case study (this corridor); NO 'corridors in general' claim",
        "cusum_calibration": calib,
        "conservation_consistent_deviation": {
            "definition": "residual < tau (below the independently-calibrated threshold)",
            "tau": tau,
            "leaves_conservation_trace": False,
        },
        "coverage_escape_surface": surface,
        "lemma": lemma,
        "severe_contrast": contrast,
        "self_referential_twist": (
            "the preemption attack controls the signal phase; the phase gates honest-"
            "witness coverage of the footprint; so an insider can open a coverage desert "
            "that conceals a conservation-consistent deviation -- the audit's measured "
            "blind spot, reported not defended."),
        "provenance_indistinguishability_limitation": (
            "verified-provenance features carry PARTIAL physical signal (position/time/"
            "route) but not enough to adjudicate physical veracity; the veracity triad is "
            "unrecoverable, so those cells -> unknown (the system never adjudicates it)."),
        "caveats": [
            "Witness coverage is MODELLED (linear phase-lock model), NOT documented A501 "
            "loop placement; modelled cells are excluded from any headline inferential "
            "contrast per §4.5.",
            "Per-cell CIs are DESCRIPTIVE (bootstrap), non-inferential; no per-cell claim "
            "without a multiplicity correction.",
            "The severe directional finding is computed descriptively; the pre-registered "
            "inferential decision is NOT run (PROTOCOL_NOT_A_PASSED_CONTROL, §4.5/§12).",
            "Geometry n=1; the only generalisation axis is sensitivity to demand/phase-"
            "offset draws.",
        ],
    }
    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_coupling.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    mp = os.path.join(RESULTS, "experiment_coupling.md")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print_summary(result, jp, mp)
    return result


def _fmt(v, nd=3):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def render_md(r: dict) -> str:
    cal = r["cusum_calibration"]
    lines = ["# Experiment D: the self-referential coupling boundary (D6, §4.5)", ""]
    lines.append(f"**{r['label']}**. {r['geometry']}.")
    lines.append("")
    lines.append(f"> {r['self_referential_twist']}")
    lines.append("")
    lines.append("## Independently-calibrated detection threshold")
    lines.append("")
    lines.append(f"- CUSUM/conservation tau = {_fmt(cal['tau'])} at FP budget "
                 f"{_fmt(cal['fp_budget'])} (realised FP {_fmt(cal['realised_fp_rate'])}), "
                 f"benign model {cal['benign_model']}, calibrated WITHOUT the attack set.")
    lines.append(f"- Conservation-consistent deviation := residual < tau -> no conservation "
                 f"trace; only LIVE witness coverage can catch it.")
    lines.append("")
    lines.append("## Coverage-vs-escape surface (MODELLED, descriptive)")
    lines.append("")
    lines.append("| avg coverage | phase-lock | eff. coverage | escape (95% CI) | well-mixed | excess |")
    lines.append("|---|---|---|---|---|---|")
    for c in r["coverage_escape_surface"]["cells"]:
        ci = c["escape_ci95"]
        lines.append(f"| {_fmt(c['avg_coverage'],1)} | {_fmt(c['phaselock'],1)} | "
                     f"{_fmt(c['effective_coverage'],2)} | {_fmt(c['escape_mean'])} "
                     f"[{_fmt(ci[0])},{_fmt(ci[1])}] | {_fmt(c['wellmixed_escape'])} | "
                     f"{_fmt(c['excess_over_wellmixed'])} |")
    lines.append("")
    lem = r["lemma"]
    lines.append("## Conditional lemma (four sufficient hypotheses)")
    lines.append("")
    for h in lem["hypotheses"]:
        lines.append(f"- {h}")
    lines.append("")
    lines.append(f"- Dense well-mixed escape mean = {_fmt(lem['dense_wellmixed_escape_mean'])}; "
                 f"lemma holds numerically: **{lem['lemma_holds_numerically']}** "
                 f"(escape -> 0 as coverage -> 1). {lem['note']}")
    lines.append("")
    sc = r["severe_contrast"]
    lines.append("## The severe directional finding (DESCRIPTIVE; inferential decision gated)")
    lines.append("")
    lines.append(f"- Estimator: {sc['estimator']}")
    lines.append(f"- Descriptive estimate (mid-coverage) = {_fmt(sc['descriptive_estimate_mid_coverage'])}, "
                 f"direction as predicted (phase-lock raises escape): **{sc['direction_as_predicted']}**")
    lines.append(f"- Decision rule: {sc['decision_rule']}; CI: {sc['ci_method']}")
    lines.append(f"- **Inferential decision: {sc['inferential_decision']} -- {sc['status']}**")
    for w in sc["why_gated"]:
        lines.append(f"  - gated: {w}")
    lines.append("")
    lines.append("## Limitations")
    lines.append("")
    lines.append(f"- {r['provenance_indistinguishability_limitation']}")
    for c in r["caveats"]:
        lines.append(f"- {c}")
    lines.append("")
    return "\n".join(lines)


def _print_summary(r: dict, jp: str, mp: str) -> None:
    print("=" * 72)
    print("EXPERIMENT D (D6): self-referential coupling boundary")
    cal = r["cusum_calibration"]
    print(f"  tau={_fmt(cal['tau'])} @ FP budget {cal['fp_budget']} (realised {_fmt(cal['realised_fp_rate'])})")
    sc = r["severe_contrast"]
    print(f"  severe contrast (descriptive, mid-coverage) = "
          f"{_fmt(sc['descriptive_estimate_mid_coverage'])} "
          f"(direction as predicted: {sc['direction_as_predicted']})")
    print(f"  inferential decision: {sc['inferential_decision']} [{sc['status']}]")
    print(f"  lemma holds numerically: {r['lemma']['lemma_holds_numerically']}")
    print("=" * 72)
    print(f"  wrote: {jp}")
    print(f"  wrote: {mp}")


if __name__ == "__main__":
    run()
    sys.exit(0)
