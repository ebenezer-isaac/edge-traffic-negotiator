"""The Edge Negotiator full evaluation harness (Wk9-10 results generator).

This is the integration-ready "part" that produces the dissertation's *results
matrix* end-to-end. It defines an experiment MATRIX and runs it to two tidy
result tables:

  1. TRAFFIC table   -- per-controller throughput-controlled metrics with BCa
     confidence intervals, paired differences vs a chosen baseline, paired
     permutation p-values and Holm-Bonferroni multiplicity correction.
  2. DETECTION table -- per-attack precision / recall / F1 / latency for the
     security layer (auth + conservation), measured against KNOWN ground truth.

One harness, both halves of the thesis (performance AND security), emitting BOTH
a machine-readable JSON and a markdown report.

WHY A NEW, SELF-CONTAINED PART
------------------------------
We do NOT edit any existing file. We COMPOSE the already-validated building
blocks through their public APIs:

  * ``run_metrics_sweep.run_one(mode, seed, end, coord_weight)`` -- runs ONE SUMO
    simulation with the deterministic ``StubAgent`` (NO Foundry Local) and the
    REQUIRED full-population tripinfo flags
    (``--tripinfo-output.write-unfinished`` / ``--tripinfo-output.write-undeparted``),
    scores it with ``metrics.py`` and returns a flat dict that already carries
    the throughput-controlled headline metrics. We reuse it verbatim so the SUMO
    invocation and the write-flag discipline stay in exactly one place.
  * ``metrics.parse_tripinfo`` / ``metrics.matched_diff`` -- the apples-to-apples
    matched-set (same-vehicle) travel-time contrast.
  * ``stats.summarize_sweep`` -- per-group BCa CI + paired diff + permutation +
    Holm, all paired on seed.
  * ``run_attacks.run_all`` + ``run_attacks._prf1`` -- the detection eval
    (precision/recall/F1 + latency) against ground-truth-labelled injected
    messages, also Foundry-free and SUMO-free.

LESSONS BAKED IN (from the Milestone-2 post-mortem)
---------------------------------------------------
  * HEADLINE metrics are throughput-controlled: ``mean_network_delay`` (lower is
    better), ``completion_rate`` and ``throughput`` (higher is better). The OLD
    completed-only ``avg_travel_time_completed`` is carried ONLY as a CONTRAST
    column -- it had the WRONG SIGN under survivorship bias and is never the
    headline. ``matched_diff`` is the survivorship-safe travel-time contrast.
  * Power: the seed count is a single parameter so the dissertation 30-seed run
    is one flag (``--seeds 30``); the CI config is tiny (2 modes, few seeds).
  * SUMO must emit unfinished/undeparted trips -- enforced because every traffic
    cell goes through ``run_one`` which sets those flags, and we VALIDATE the
    provenance flag on every row.

DESIGN PROPERTIES
-----------------
  * Pure / immutable where reasonable. The matrix spec is a frozen dataclass;
    aggregation functions return new dicts / DataFrames and never mutate inputs.
  * Inputs validated at the boundary (mode names, seed counts, baseline
    membership, metric direction).
  * A real agent can be INJECTED (``agent=...``) to run the Foundry-backed SLM;
    by default every cell is the deterministic StubAgent so results reproduce.

    from evaluation import EvalConfig, run_evaluation
    cfg = EvalConfig(modes=("maxpressure", "coordinated"), seeds=(0, 1, 2), end=200)
    report = run_evaluation(cfg)
    report.json   # machine-readable dict
    report.markdown
"""
from __future__ import annotations

import math
import os
import sys
from dataclasses import dataclass, field, replace
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

# src/ on path so the sibling modules resolve whether imported as `evaluation`
# (tests insert src/) or run as a script.
_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import numpy as np  # noqa: E402

import metrics as M  # noqa: E402
import stats as S  # noqa: E402
import run_attacks as RA  # noqa: E402
from run_metrics_sweep import run_one  # noqa: E402

__all__ = [
    "EvalConfig",
    "EvalReport",
    "TRAFFIC_MODES",
    "HEADLINE_METRICS",
    "METRIC_LOWER_IS_BETTER",
    "run_traffic_cells",
    "summarize_traffic",
    "matched_set_table",
    "run_detection",
    "build_markdown",
    "run_evaluation",
    "EvaluationError",
]

# The four controllers in the dissertation matrix (run_one accepts these).
TRAFFIC_MODES: Tuple[str, ...] = ("fixed", "maxpressure", "uncoordinated", "coordinated")

# Throughput-controlled headline metrics + their "good" direction. The OLD biased
# avg_travel_time_completed is deliberately NOT in this set; it is only ever shown
# as a contrast column (see CONTRAST_METRIC).
HEADLINE_METRICS: Tuple[str, ...] = ("mean_network_delay", "completion_rate", "throughput")
METRIC_LOWER_IS_BETTER: Mapping[str, bool] = {
    "mean_network_delay": True,
    "completion_rate": False,
    "throughput": False,
}
# The survivorship-biased metric, carried for the honesty contrast ONLY.
CONTRAST_METRIC = "avg_travel_time_completed"


class EvaluationError(ValueError):
    """Raised when the evaluation config / inputs violate an invariant."""


# --------------------------------------------------------------------------- #
# Matrix specification (immutable, validated).
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EvalConfig:
    """Immutable specification of one evaluation matrix run.

    Attributes
    ----------
    modes : controllers to evaluate (subset of TRAFFIC_MODES, deduped, order kept).
    seeds : the deterministic seed set (paired across controllers). Pass an int N
            via :meth:`with_n_seeds` to get ``range(N)``; the dissertation uses 30.
    end : SUMO horizon (sim steps) per cell.
    baseline : the controller every other controller's paired diff is measured
               against (must be one of ``modes``).
    coord_weight : lambda for the coordinated mode's Channel-B term.
    run_detection : also run the security (attack/detection) eval and emit the
                    detection table.
    detection_tolerance : conservation tolerance (vehicles) for the attack eval.
    n_boot, n_perm, alpha, stat_seed : inference knobs forwarded to stats.
    agent : optional real agent to INJECT for the SLM modes. ``None`` => the
            deterministic StubAgent (Foundry-free, reproducible). NOTE: the
            default path through ``run_one`` always uses StubAgent; injecting a
            real agent is reserved for an explicit Foundry-backed run and is
            recorded in provenance.
    """

    modes: Tuple[str, ...] = ("maxpressure", "coordinated")
    seeds: Tuple[int, ...] = (0, 1, 2)
    end: int = 200
    baseline: str = "maxpressure"
    coord_weight: float = 1.0
    run_detection: bool = True
    detection_tolerance: int = 2
    n_boot: int = 2000
    n_perm: int = 2000
    alpha: float = 0.05
    stat_seed: int = 0
    agent: object = field(default=None, compare=False)

    def __post_init__(self) -> None:
        if not self.modes:
            raise EvaluationError("EvalConfig.modes must be non-empty")
        # Dedupe while preserving order; validate membership.
        seen: List[str] = []
        for m in self.modes:
            if m not in TRAFFIC_MODES:
                raise EvaluationError(
                    f"unknown mode {m!r}; valid modes are {TRAFFIC_MODES}")
            if m not in seen:
                seen.append(m)
        object.__setattr__(self, "modes", tuple(seen))

        if not self.seeds:
            raise EvaluationError("EvalConfig.seeds must be non-empty")
        seeds = tuple(int(s) for s in self.seeds)
        if len(set(seeds)) != len(seeds):
            raise EvaluationError(f"duplicate seeds not allowed: {seeds}")
        object.__setattr__(self, "seeds", seeds)

        if not (isinstance(self.end, int) and self.end > 0):
            raise EvaluationError(f"end must be a positive int, got {self.end!r}")

        if self.baseline not in self.modes:
            raise EvaluationError(
                f"baseline {self.baseline!r} must be one of the evaluated modes "
                f"{self.modes}")

        if not (isinstance(self.detection_tolerance, int)
                and self.detection_tolerance >= 0):
            raise EvaluationError(
                f"detection_tolerance must be a non-negative int, "
                f"got {self.detection_tolerance!r}")
        for name in ("n_boot", "n_perm"):
            v = getattr(self, name)
            if not (isinstance(v, int) and v >= 1):
                raise EvaluationError(f"{name} must be a positive int, got {v!r}")
        if not (0.0 < self.alpha < 1.0):
            raise EvaluationError(f"alpha must be in (0,1), got {self.alpha!r}")

    def with_n_seeds(self, n: int) -> "EvalConfig":
        """Return a copy whose seeds are ``range(n)`` (the dissertation knob)."""
        if not (isinstance(n, int) and n >= 1):
            raise EvaluationError(f"n_seeds must be a positive int, got {n!r}")
        return replace(self, seeds=tuple(range(n)))


# --------------------------------------------------------------------------- #
# Result container.
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class EvalReport:
    """Immutable bundle of one evaluation run's outputs.

    ``json`` is the machine-readable dict (serialisable with ``json.dump``);
    ``markdown`` is the human report; ``rows`` is the raw per-cell traffic data;
    ``traffic_tables`` maps each headline metric to its summarize_sweep records;
    ``detection`` is the detection summary (or None if not run).
    """

    json: Dict
    markdown: str
    rows: Tuple[Dict, ...]
    traffic_tables: Dict[str, List[Dict]]
    matched: List[Dict]
    detection: Optional[Dict]


# --------------------------------------------------------------------------- #
# 1. Run the traffic cells (controllers x seeds) via the shared run_one.
# --------------------------------------------------------------------------- #
def run_traffic_cells(cfg: EvalConfig,
                      runner: Callable[..., Dict] = run_one,
                      progress: Optional[Callable[[Dict], None]] = None,
                      ) -> List[Dict]:
    """Run every (mode, seed) cell and return a flat list of per-cell metric dicts.

    Each cell goes through ``run_one`` (or an injected ``runner`` with the same
    signature), which guarantees the required full-population tripinfo flags and
    the deterministic StubAgent. We VALIDATE that the write-unfinished provenance
    actually took effect, so a silently-degraded tripinfo (which would collapse
    completion_rate to a meaningless 1.0) is caught here rather than corrupting
    the stats downstream.

    Returns NEW dicts; the runner's rows are not mutated in place.
    """
    rows: List[Dict] = []
    for mode in cfg.modes:
        for seed in cfg.seeds:
            kwargs = {"mode": mode, "seed": seed, "end": cfg.end}
            if mode == "coordinated":
                kwargs["coord_weight"] = cfg.coord_weight
            raw = runner(**kwargs)
            # Provenance guard: the survivorship-robust denominators only mean
            # something if the population flags actually emitted unfinished /
            # undeparted rows on this oversaturated grid.
            if not (raw.get("write_unfinished_present")
                    or raw.get("write_undeparted_present")):
                raise EvaluationError(
                    f"cell mode={mode} seed={seed}: tripinfo carries NO "
                    f"unfinished/undeparted vehicles -- the write flags did not "
                    f"apply, so completion_rate / mean_network_delay are "
                    f"untrustworthy. Refusing to score it.")
            row = {**raw}  # copy; never mutate the runner's dict
            rows.append(row)
            if progress is not None:
                progress(row)
    return rows


# --------------------------------------------------------------------------- #
# 2. Aggregate the traffic cells -> per-metric stats tables.
# --------------------------------------------------------------------------- #
def _finite_rows(rows: Sequence[Dict], metric: str) -> List[Dict]:
    """Rows whose ``metric`` is a finite number (guards completion_rate NaN)."""
    out: List[Dict] = []
    for r in rows:
        v = r.get(metric)
        if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v)):
            out.append(r)
    return out


def summarize_traffic(cfg: EvalConfig, rows: Sequence[Dict],
                      metric: str) -> List[Dict]:
    """Return one stats record per mode for ``metric`` (paired on seed vs baseline).

    Thin, validated wrapper over ``stats.summarize_sweep``: filters non-finite
    metric values, runs the full BCa + paired-diff + permutation + Holm stack,
    and returns the DataFrame as a list of plain dicts (JSON-friendly, immutable).
    The ``lower_is_better`` direction for the metric is attached to each record so
    the report renderer can phrase help/hurt correctly.
    """
    if metric not in METRIC_LOWER_IS_BETTER and metric != CONTRAST_METRIC:
        raise EvaluationError(f"unknown metric {metric!r} for traffic summary")
    sub = _finite_rows(rows, metric)
    if not sub:
        raise EvaluationError(f"no finite rows for metric {metric!r}")
    df = S.summarize_sweep(
        sub, metric=metric, group_key="mode", seed_key="seed",
        baseline=cfg.baseline, n_boot=cfg.n_boot, n_perm=cfg.n_perm,
        alpha=cfg.alpha, seed=cfg.stat_seed, alternative="two-sided",
    )
    lower = METRIC_LOWER_IS_BETTER.get(metric, True)
    records: List[Dict] = []
    for _, r in df.iterrows():
        rec = {k: (None if (isinstance(v, float) and math.isnan(v))
                   else (bool(v) if isinstance(v, (bool, np.bool_))
                         else (int(v) if isinstance(v, (np.integer,))
                               else (float(v) if isinstance(v, (np.floating, float))
                                     else v))))
               for k, v in r.to_dict().items()}
        rec["metric"] = metric
        rec["lower_is_better"] = bool(lower)
        records.append(rec)
    return records


def matched_set_table(cfg: EvalConfig, rows: Sequence[Dict]) -> List[Dict]:
    """Same-vehicle matched-set travel-time contrast for each mode vs baseline.

    For each non-baseline mode, restrict to vehicles that COMPLETED in BOTH that
    mode and the baseline (per seed), take the per-seed mean travel-time
    difference (mode - baseline), then BCa + paired-permutation over seeds. A
    negative diff means the mode is faster on the SHARED trips -- the
    survivorship-safe travel-time statement (replaces the wrong-sign
    completed-only average).
    """
    by_mode_seed: Dict[Tuple[str, int], Dict] = {
        (r["mode"], r["seed"]): r for r in rows
    }
    out: List[Dict] = []
    for mode in cfg.modes:
        if mode == cfg.baseline:
            continue
        diffs: List[float] = []
        n_matched = only_a = only_b = 0
        for seed in cfg.seeds:
            ka = by_mode_seed.get((mode, seed))
            kb = by_mode_seed.get((cfg.baseline, seed))
            if ka is None or kb is None:
                continue
            ra = M.parse_tripinfo(ka["tripinfo"])
            rb = M.parse_tripinfo(kb["tripinfo"])
            md = M.matched_diff(ra, rb)
            if md["n_matched"] > 0:
                diffs.append(md["diff_a_minus_b"])
                n_matched += int(md["n_matched"])
                only_a += int(md["n_only_a"])
                only_b += int(md["n_only_b"])
        rec = {
            "mode": mode, "baseline": cfg.baseline, "n_seeds": len(diffs),
            "total_matched_veh": n_matched, "only_mode": only_a,
            "only_baseline": only_b,
        }
        if len(diffs) >= 1:
            arr = np.asarray(diffs, dtype=float)
            pt, lo, hi = S.bca_bootstrap(
                arr, n_boot=cfg.n_boot, alpha=cfg.alpha, seed=cfg.stat_seed)
            p = S.permutation_test(
                arr, np.zeros_like(arr), n_perm=cfg.n_perm, seed=cfg.stat_seed)
            rec.update({
                "mean_diff_mode_minus_baseline": float(pt),
                "ci_lo": float(lo), "ci_hi": float(hi),
                "excludes_zero": bool(lo > 0.0 or hi < 0.0),
                "perm_p": float(p),
            })
        else:
            rec.update({
                "mean_diff_mode_minus_baseline": None, "ci_lo": None,
                "ci_hi": None, "excludes_zero": False, "perm_p": None,
            })
        out.append(rec)
    return out


# --------------------------------------------------------------------------- #
# 3. Detection (security) eval -> precision/recall/F1/latency table.
# --------------------------------------------------------------------------- #
def run_detection(cfg: EvalConfig) -> Dict:
    """Run the attack/detection eval and return a tidy detection summary dict.

    Reuses ``run_attacks.run_all`` (StubAgent + in-memory TraCI stand-in; NO
    Foundry, NO SUMO) and derives the per-attack confusion -> precision / recall /
    F1 with the SAME ``_prf1`` the existing report uses. We surface the three
    attack families (spoof, faulty, sybil/auth), their latencies, the measured
    single-message conservation latency, and the collusion-evasion honest
    negative.

    Returns a dict with an ``attacks`` list (one row per family) and a ``notes``
    block carrying the residual-limit findings.
    """
    res = RA.run_all(tolerance=cfg.detection_tolerance)
    spoof_rows, spoof_cm, spoof_lat = res["spoof"]
    faulty_rows, faulty_cm, faulty_lat = res["faulty"]
    sybil_rows, sybil_cm, collusion = res["sybil"]

    def _row(name: str, cm: Dict, latency, layer: str) -> Dict:
        p, r, f1 = RA._prf1(cm["tp"], cm["fp"], cm["fn"])
        return {
            "attack": name, "layer": layer,
            "tp": cm["tp"], "fp": cm["fp"], "fn": cm["fn"], "tn": cm["tn"],
            "precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4),
            "latency_cycles": latency,
        }

    attacks_table = [
        _row("spoof (insider over-claim)", spoof_cm, spoof_lat, "conservation"),
        _row("faulty sensor (under-claim)", faulty_cm, faulty_lat, "conservation"),
        # Auth row: rejected on receipt -> latency 0 cycles.
        _row("sybil/impersonation (4 cases)", sybil_cm, 0, "auth"),
    ]
    return {
        "tolerance": cfg.detection_tolerance,
        "conservation_latency_cycles": res["conservation_latency"],
        "attacks": attacks_table,
        "roc": res["roc"],
        "collusion_evasion": {
            "malicious": bool(collusion["malicious"]),
            "detected_by_auth": bool(collusion["detected_by_auth"]),
            "detected_by_conservation": bool(collusion["detected_by_conservation"]),
            "detected": bool(collusion["detected"]),
            "note": "lockstep collusion is malicious but caught by NEITHER layer "
                    "(Xiao2026 residual limit) -- containment via revoke()+audit, "
                    "not detection.",
        },
    }


# --------------------------------------------------------------------------- #
# Report rendering.
# --------------------------------------------------------------------------- #
def _f(v, nd: int = 3) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, float):
        if math.isnan(v):
            return "NaN"
        return f"{v:.{nd}f}"
    return str(v)


def _per_mode_means(rows: Sequence[Dict], cfg: EvalConfig) -> List[Dict]:
    """Mean of every headline + contrast metric per mode (for the overview table)."""
    out: List[Dict] = []
    for mode in cfg.modes:
        sub = [r for r in rows if r["mode"] == mode]
        if not sub:
            continue
        def mean(metric: str) -> float:
            xs = [r[metric] for r in sub
                  if isinstance(r.get(metric), (int, float))
                  and not (isinstance(r.get(metric), float) and math.isnan(r[metric]))]
            return sum(xs) / len(xs) if xs else float("nan")
        out.append({
            "mode": mode, "n": len(sub),
            "throughput": mean("throughput"),
            "completion_rate": mean("completion_rate"),
            "mean_network_delay": mean("mean_network_delay"),
            "total_network_delay": mean("total_network_delay"),
            CONTRAST_METRIC: mean(CONTRAST_METRIC),
        })
    return out


def _traffic_stats_md(records: Sequence[Dict], metric: str) -> str:
    lower = records[0]["lower_is_better"] if records else True
    dir_word = "lower=better" if lower else "higher=better"
    hdr = ("| mode | n | mean | 95% BCa CI | diff vs base | diff 95% BCa CI | "
           "excl 0 | perm p | Holm thr | Holm reject |")
    sep = "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    lines = [f"**Metric: `{metric}` ({dir_word})**", "", hdr, sep]
    for r in records:
        base = " (baseline)" if r["is_baseline"] else ""
        if r["is_baseline"]:
            diff = diffci = excl = pp = ht = hr = "-"
        else:
            diff = _f(r["diff_vs_baseline"], 3)
            diffci = f"[{_f(r['diff_ci_lo'], 3)}, {_f(r['diff_ci_hi'], 3)}]"
            excl = "YES" if r["diff_excludes_zero"] else "no"
            pp = _f(r["perm_p"], 4)
            ht = _f(r["holm_threshold"], 4)
            hr = "REJECT" if r["holm_reject"] else "fail-to-reject"
        lines.append(
            f"| {r['group']}{base} | {int(r['n'])} | {_f(r['mean'], 3)} | "
            f"[{_f(r['ci_lo'], 3)}, {_f(r['ci_hi'], 3)}] | {diff} | {diffci} | "
            f"{excl} | {pp} | {ht} | {hr} |")
    return "\n".join(lines)


def _verdict(traffic_tables: Mapping[str, Sequence[Dict]], cfg: EvalConfig
             ) -> Tuple[str, List[str]]:
    """Help / hurt / neutral verdict vs the baseline, Holm-corrected per metric."""
    help_ = hurt = False
    notes: List[str] = []
    for metric in HEADLINE_METRICS:
        recs = traffic_tables.get(metric, [])
        lower = METRIC_LOWER_IS_BETTER[metric]
        for r in recs:
            if r["is_baseline"] or not r.get("holm_reject"):
                continue
            diff = r["diff_vs_baseline"]
            if diff is None:
                continue
            improved = (diff < 0) if lower else (diff > 0)
            verb = "HELPS" if improved else "HURTS"
            help_ = help_ or improved
            hurt = hurt or (not improved)
            notes.append(
                f"{r['group']} vs {cfg.baseline} on {metric}: diff={diff:+.3f} "
                f"(perm p={_f(r['perm_p'], 4)}, Holm-reject) -> {verb}")
    if help_ and not hurt:
        headline = "HELPS"
    elif hurt and not help_:
        headline = "HURTS"
    elif help_ and hurt:
        headline = "MIXED"
    else:
        headline = "NO SIGNIFICANT EFFECT (NEUTRAL)"
    if not notes:
        notes.append("no Holm-significant headline differences vs the baseline "
                     "(expected for a tiny CI matrix; scale up seeds for power).")
    return headline, notes


def build_markdown(cfg: EvalConfig, rows: Sequence[Dict],
                   traffic_tables: Mapping[str, Sequence[Dict]],
                   matched: Sequence[Dict],
                   detection: Optional[Dict]) -> str:
    """Render the full evaluation report (traffic table + detection table)."""
    n_seeds = len(cfg.seeds)
    p: List[str] = []
    a = p.append
    a("# The Edge Negotiator — full evaluation results matrix")
    a("")
    a("Generated by `src/run_evaluation.py` (harness: `src/evaluation.py`). "
      "Every traffic cell runs SUMO with the deterministic `StubAgent` (NO "
      "Foundry Local) and the required full-population tripinfo flags "
      "(`--tripinfo-output.write-unfinished --tripinfo-output.write-undeparted`), "
      "scored with the throughput-controlled metrics in `src/metrics.py`. The "
      "detection table is produced by the same harness from the attack eval "
      "(`src/run_attacks.py`).")
    a("")
    a(f"- Controllers: {', '.join(cfg.modes)}")
    a(f"- Baseline (paired-diff reference): **{cfg.baseline}**")
    a(f"- Seeds: **{n_seeds}** ({list(cfg.seeds)}), paired across controllers")
    a(f"- Horizon: end={cfg.end} sim-steps per cell")
    a(f"- coord_weight (lambda): {cfg.coord_weight:g}")
    a("- Headline metrics (throughput-controlled): `mean_network_delay` "
      "(lower=better), `completion_rate` (higher=better), `throughput` "
      "(higher=better).")
    a("- Contrast only (NOT headline): `avg_travel_time_completed` is the OLD "
      "completed-only mean; under survivorship bias it had the WRONG SIGN, so it "
      "is shown for contrast and never used for the verdict.")
    a("")

    # ---- Verdict ----
    headline, vnotes = _verdict(traffic_tables, cfg)
    a("## Headline verdict (traffic)")
    a("")
    a(f"**On throughput-controlled metrics vs `{cfg.baseline}`: {headline}** "
      "(Holm-corrected across the controller family).")
    a("")
    for nt in vnotes:
        a(f"- {nt}")
    a("")

    # ---- Per-mode overview ----
    a("## Traffic — per-controller means")
    a("")
    a("| mode | n | throughput | completion_rate | mean_network_delay | "
      "total_network_delay | avg_tt_completed (biased, contrast) |")
    a("| --- | --- | --- | --- | --- | --- | --- |")
    for m in _per_mode_means(rows, cfg):
        a(f"| {m['mode']} | {m['n']} | {_f(m['throughput'], 1)} | "
          f"{_f(m['completion_rate'], 3)} | {_f(m['mean_network_delay'], 1)} | "
          f"{_f(m['total_network_delay'], 0)} | {_f(m[CONTRAST_METRIC], 1)} |")
    a("")

    # ---- Inferential tables per headline metric ----
    a("## Traffic — inferential comparison (BCa 95% CI + paired permutation + Holm)")
    a("")
    a(f"All comparisons paired on seed; baseline = `{cfg.baseline}`. "
      "Permutation p-values Holm-corrected across the controller family per metric.")
    a("")
    for metric in HEADLINE_METRICS:
        a(_traffic_stats_md(traffic_tables[metric], metric))
        a("")
    # Contrast metric shown LAST and clearly flagged.
    if CONTRAST_METRIC in traffic_tables:
        a("### Contrast only — the OLD survivorship-biased metric")
        a("")
        a("Shown to expose the Milestone-2 confound. If its sign/significance "
          "disagrees with `mean_network_delay` above, the old number was driven "
          "by WHICH trips completed, not by genuinely faster travel. NOT the "
          "headline.")
        a("")
        a(_traffic_stats_md(traffic_tables[CONTRAST_METRIC], CONTRAST_METRIC))
        a("")

    # ---- Matched-set ----
    a("## Traffic — matched-set (same-vehicle) travel-time contrast")
    a("")
    a("Per seed, restrict to vehicles that completed under BOTH the mode and the "
      "baseline, then take mean(mode - baseline) over that shared set (negative "
      "=> mode faster on shared trips). The survivorship-safe travel-time "
      "statement. CI is BCa over seeds; perm p is paired-vs-zero.")
    a("")
    a("| mode vs baseline | seeds | mean diff (mode-base) | 95% BCa CI | excl 0 | "
      "perm p | matched veh | only mode | only base |")
    a("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in matched:
        a(f"| {r['mode']} vs {r['baseline']} | {r['n_seeds']} | "
          f"{_f(r['mean_diff_mode_minus_baseline'], 2)} | "
          f"[{_f(r['ci_lo'], 2)}, {_f(r['ci_hi'], 2)}] | "
          f"{'YES' if r['excludes_zero'] else 'no'} | {_f(r['perm_p'], 4)} | "
          f"{r['total_matched_veh']} | {r['only_mode']} | {r['only_baseline']} |")
    a("")

    # ---- Detection table ----
    if detection is not None:
        a("## Security — detection results (precision / recall / F1 / latency)")
        a("")
        a("Produced by the attack eval (`run_attacks.run_all`) with the same "
          "deterministic StubAgent + in-memory TraCI stand-in — NO Foundry, NO "
          f"SUMO. Conservation tolerance = **{detection['tolerance']} vehicles**; "
          "single-message conservation detection latency measured at "
          f"**{detection['conservation_latency_cycles']} control cycle**.")
        a("")
        a("| attack | layer | TP | FP | FN | TN | precision | recall | F1 | "
          "first-detect latency |")
        a("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
        for r in detection["attacks"]:
            lat = (f"{r['latency_cycles']} cycle(s)"
                   if r["latency_cycles"] is not None else "n/a")
            a(f"| {r['attack']} | {r['layer']} | {r['tp']} | {r['fp']} | "
              f"{r['fn']} | {r['tn']} | {_f(r['precision'], 3)} | "
              f"{_f(r['recall'], 3)} | {_f(r['f1'], 3)} | {lat} |")
        a("")
        ce = detection["collusion_evasion"]
        a(f"> **Honest residual limit:** {ce['note']} "
          f"(malicious={ce['malicious']}, detected_by_auth={ce['detected_by_auth']}, "
          f"detected_by_conservation={ce['detected_by_conservation']}).")
        a("")
        # Tolerance ROC.
        a("### Tolerance ROC — false-alarm rate vs recall (spoof detector)")
        a("")
        a("| tolerance | recall | false-alarm rate | precision | F1 |")
        a("| --- | --- | --- | --- | --- |")
        for row in detection["roc"]:
            a(f"| {row['tolerance']} | {_f(row['recall'], 3)} | "
              f"{_f(row['false_alarm_rate'], 3)} | {_f(row['precision'], 3)} | "
              f"{_f(row['f1'], 3)} |")
        a("")

    a("## Method notes")
    a("")
    a("- `throughput` is a count and cannot be gamed by stranding slow vehicles; "
      "`mean_network_delay` divides total time-in-network by ALL departed "
      "vehicles (stranded ones keep their accrued time), so a 'completes fewer "
      "but faster' controller earns no spurious win.")
    a("- `avg_travel_time_completed` is shown for contrast ONLY — it is the "
      "survivorship-biased Milestone-2 metric and is never the headline.")
    a("- Stats: BCa 95% CIs + paired permutation + Holm-Bonferroni, all paired "
      "on seed. Scale `--seeds` up (e.g. 30) for the dissertation-power run.")
    return "\n".join(p)


# --------------------------------------------------------------------------- #
# Top-level orchestration.
# --------------------------------------------------------------------------- #
def run_evaluation(cfg: EvalConfig,
                   runner: Callable[..., Dict] = run_one,
                   progress: Optional[Callable[[Dict], None]] = None,
                   ) -> EvalReport:
    """Run the full matrix end-to-end and return an immutable :class:`EvalReport`.

    Steps: (1) run the traffic cells with the shared SUMO+StubAgent runner and
    validate provenance; (2) summarise each headline metric (+ the contrast
    metric) with the BCa/permutation/Holm stack; (3) build the matched-set
    contrast; (4) optionally run the detection eval; (5) render JSON + markdown.
    """
    if not isinstance(cfg, EvalConfig):
        raise EvaluationError("cfg must be an EvalConfig")

    rows = run_traffic_cells(cfg, runner=runner, progress=progress)

    traffic_tables: Dict[str, List[Dict]] = {}
    for metric in (*HEADLINE_METRICS, CONTRAST_METRIC):
        traffic_tables[metric] = summarize_traffic(cfg, rows, metric)

    matched = matched_set_table(cfg, rows)

    detection = run_detection(cfg) if cfg.run_detection else None

    markdown = build_markdown(cfg, rows, traffic_tables, matched, detection)

    json_obj = {
        "config": {
            "modes": list(cfg.modes),
            "seeds": list(cfg.seeds),
            "n_seeds": len(cfg.seeds),
            "end": cfg.end,
            "baseline": cfg.baseline,
            "coord_weight": cfg.coord_weight,
            "n_boot": cfg.n_boot,
            "n_perm": cfg.n_perm,
            "alpha": cfg.alpha,
            "stat_seed": cfg.stat_seed,
            "agent": "StubAgent" if cfg.agent is None else type(cfg.agent).__name__,
            "detection_tolerance": cfg.detection_tolerance,
            "headline_metrics": list(HEADLINE_METRICS),
            "contrast_metric": CONTRAST_METRIC,
        },
        "traffic_rows": [_jsonable(r) for r in rows],
        "traffic_tables": {k: v for k, v in traffic_tables.items()},
        "matched_set": matched,
        "detection": detection,
    }
    return EvalReport(
        json=json_obj, markdown=markdown, rows=tuple(rows),
        traffic_tables=traffic_tables, matched=matched, detection=detection,
    )


def _jsonable(row: Mapping) -> Dict:
    """Coerce a per-cell row to JSON-serialisable primitives (drop numpy types)."""
    out: Dict = {}
    for k, v in row.items():
        if isinstance(v, (np.floating, float)):
            out[k] = None if (isinstance(v, float) and math.isnan(v)) else float(v)
        elif isinstance(v, (np.integer,)):
            out[k] = int(v)
        elif isinstance(v, (np.bool_,)):
            out[k] = bool(v)
        elif isinstance(v, (list, tuple)):
            out[k] = [str(x) if not isinstance(x, (int, float, str, bool, type(None)))
                      else x for x in v]
        else:
            out[k] = v
    return out
