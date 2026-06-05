"""CLI for the full Edge Negotiator evaluation matrix (Wk9-10 results generator).

Runs the controllers x seeds matrix end-to-end with the deterministic StubAgent
(NO Foundry Local) + the required full-population tripinfo flags, scores every
cell with the throughput-controlled metrics, aggregates with BCa + paired
permutation + Holm, ALSO runs the attack/detection eval, and writes BOTH a
machine-readable JSON and a markdown report.

The seed COUNT is a single flag, so the small CI matrix and the 30-seed
dissertation sweep differ by one number:

    # tiny, CI-able default (2 modes, 3 seeds, end=200):
    .venv/Scripts/python src/run_evaluation.py

    # the FULL dissertation sweep (one line):
    .venv/Scripts/python src/run_evaluation.py --seeds 30 --end 1000 \
        --modes fixed maxpressure uncoordinated coordinated \
        --baseline maxpressure --out results/evaluation_matrix

``--out`` is a PATH STEM: ``<stem>.md`` and ``<stem>.json`` are written.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from evaluation import (  # noqa: E402
    EvalConfig, TRAFFIC_MODES, run_evaluation,
)
from run_baseline import HERE  # noqa: E402

DEFAULT_OUT_STEM = os.path.join(HERE, "..", "results", "evaluation_matrix")


def _build_config(args) -> EvalConfig:
    """Translate CLI args into a validated EvalConfig (seeds = range(N))."""
    return EvalConfig(
        modes=tuple(args.modes),
        seeds=tuple(range(args.seeds)),
        end=args.end,
        baseline=args.baseline,
        coord_weight=args.coord_weight,
        run_detection=not args.no_detection,
        detection_tolerance=args.tolerance,
        n_boot=args.n_boot,
        n_perm=args.n_perm,
        alpha=args.alpha,
        stat_seed=args.stat_seed,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=int, default=3,
                    help="number of deterministic seeds (0..N-1). 30 for the "
                         "dissertation; 2-3 for CI. Default 3.")
    ap.add_argument("--end", type=int, default=200,
                    help="SUMO horizon (sim steps) per cell. 1000 for the "
                         "dissertation; 200 for CI. Default 200.")
    ap.add_argument("--modes", nargs="+", default=["maxpressure", "coordinated"],
                    choices=list(TRAFFIC_MODES),
                    help="controllers to evaluate. Default: maxpressure coordinated.")
    ap.add_argument("--baseline", default="maxpressure",
                    help="paired-diff reference controller (must be in --modes).")
    ap.add_argument("--coord-weight", type=float, default=1.0,
                    dest="coord_weight", help="lambda for the coordinated mode.")
    ap.add_argument("--no-detection", action="store_true",
                    help="skip the security/detection table (traffic only).")
    ap.add_argument("--tolerance", type=int, default=2,
                    help="conservation tolerance (vehicles) for the attack eval.")
    ap.add_argument("--n-boot", type=int, default=10000, dest="n_boot",
                    help="bootstrap resamples for BCa CIs.")
    ap.add_argument("--n-perm", type=int, default=10000, dest="n_perm",
                    help="permutations for the paired permutation test.")
    ap.add_argument("--alpha", type=float, default=0.05)
    ap.add_argument("--stat-seed", type=int, default=0, dest="stat_seed")
    ap.add_argument("--out", default=DEFAULT_OUT_STEM,
                    help="output path STEM; writes <stem>.md and <stem>.json.")
    args = ap.parse_args(argv)

    cfg = _build_config(args)

    print(f"=== evaluation matrix: modes={list(cfg.modes)} "
          f"seeds={len(cfg.seeds)} end={cfg.end} baseline={cfg.baseline} "
          f"detection={cfg.run_detection} ===")

    def _progress(row: dict) -> None:
        print(f"[cell] mode={row['mode']:13s} seed={row['seed']:2d} "
              f"thru={row.get('throughput', float('nan')):.0f} "
              f"comp_rate={row.get('completion_rate', float('nan')):.3f} "
              f"mnd={row.get('mean_network_delay', float('nan')):.1f}")

    report = run_evaluation(cfg, progress=_progress)

    stem = args.out
    md_path = stem + ".md"
    json_path = stem + ".json"
    os.makedirs(os.path.dirname(os.path.abspath(md_path)), exist_ok=True)

    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(report.markdown + "\n")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(report.json, fh, indent=2)

    print()
    print(f"[wrote] {os.path.abspath(md_path)}")
    print(f"[wrote] {os.path.abspath(json_path)}")
    if report.detection is not None:
        for r in report.detection["attacks"]:
            print(f"[detect] {r['attack']:34s} P={r['precision']:.3f} "
                  f"R={r['recall']:.3f} F1={r['f1']:.3f} "
                  f"lat={r['latency_cycles']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
