"""Trust-coefficient demonstration (MASTER-SPEC §4 H2 extension; both supervisors).

Scripts a sequence of neighbour EV-approach claims, each VERIFIED against the
recipient's local sensing (the ground truth), and shows the trust dynamics the
supervisors asked for:

  1. an agent that CONSISTENTLY tells the truth earns rising trust (toward 1);
  2. a LIE collapses trust extremely (asymmetric): one lie undoes many truths;
  3. local sensing is the ULTIMATE TRUTH -- it is the arbiter, never itself doubted;
  4. once a source's trust collapses it can no longer CORROBORATE a preemption, so a
     caught insider-liar is bounded.

Deterministic mechanism demonstration (pinned parameters, not fitted). No SUMO/Foundry.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from trust import (  # noqa: E402
    CORROBORATION_FLOOR, LIE_FACTOR, PRIOR, REWARD, TrustLedger, truths_to_reach,
)

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))


def _run_sequence(ledger: TrustLedger, source: str, outcomes: list) -> tuple:
    """Feed a source a sequence of local-sensing verification outcomes (True=truth,
    False=lie); return (ledger, trajectory of trust after each step)."""
    traj = [round(ledger.trust_of(source), 4)]
    for confirmed in outcomes:
        ledger = ledger.record_claim(source).verify(source, confirmed)
        traj.append(round(ledger.trust_of(source), 4))
    return ledger, traj


def run() -> dict:
    L = TrustLedger()

    # Agent HONEST: 12 consecutive verified-true EV-approach claims -> earns trust.
    L, honest_traj = _run_sequence(L, "junction-honest", [True] * 12)

    # Agent RECOVERING: builds trust with 8 truths, tells ONE lie (local sensing shows
    # the claimed EV never arrived), then earns back slowly -- shows the extreme single
    # -lie collapse AND that recovery takes many truths (asymmetry).
    L, recov_traj = _run_sequence(L, "junction-recovering",
                                  [True] * 8 + [False] + [True] * 3)

    # Agent PERSISTENT-LIAR: a few truths then keeps lying -> stays locked out.
    L, liar_traj = _run_sequence(L, "junction-liar", [True] * 3 + [False] * 3)

    # Agent FLAKY: alternates truth/lie -- trust cannot recover under repeated lies.
    L, flaky_traj = _run_sequence(L, "junction-flaky", [True, False] * 5)

    honest = L.trust_of("junction-honest")

    # Asymmetry: truths to climb prior->0.90 vs the drop from the recovering agent's
    # single lie (after 8 truths).
    n_up = truths_to_reach(0.90)
    trust_before_lie = recov_traj[8]         # after 8 truths, before the lie
    trust_after_lie = recov_traj[9]          # immediately after the single lie
    one_lie_drop = trust_before_lie - trust_after_lie
    # How many truths the recovering agent needed to climb back above the floor.
    # Count the RECOVERY truths (indices 10+; index 9 is the lie itself) needed to
    # climb back above the floor.
    recovery_steps = 0
    for i in range(10, len(recov_traj)):
        recovery_steps += 1
        if recov_traj[i] >= CORROBORATION_FLOOR:
            break
    # Runtime proof that local sensing is the SOLE arbiter: a bare claim (no
    # local-sensing verification) must not move trust.
    arbiter_ok = (TrustLedger().record_claim("probe").trust_of("probe") == PRIOR)

    checks = {
        "honest_trust_rises": honest > 0.9,
        "one_lie_collapses_below_floor": trust_after_lie < CORROBORATION_FLOOR,
        "one_lie_undoes_many_truths": (one_lie_drop > 0.5 and trust_after_lie < PRIOR),
        "persistent_liar_cannot_corroborate": not L.can_corroborate("junction-liar"),
        "flaky_cannot_corroborate": not L.can_corroborate("junction-flaky"),
        "honest_source_can_corroborate": L.can_corroborate("junction-honest"),
        "recovery_is_slow": recovery_steps >= 3,   # many truths to undo one lie
        "asymmetry_truths_up_gt_one_lie_down": n_up >= 5,
        "local_sensing_is_arbiter": arbiter_ok,   # a bare claim moves nothing (runtime)
    }
    passed = all(checks.values())

    result = {
        "experiment": "H2_trust_coefficient",
        "mechanism": ("per-source trust; verified against the recipient's LOCAL SENSING "
                      "(ground truth); truth nudges up (diminishing), a lie collapses "
                      "trust x%.2f (extreme, asymmetric)" % LIE_FACTOR),
        "params": {"prior": PRIOR, "reward": REWARD, "lie_factor": LIE_FACTOR,
                   "corroboration_floor": CORROBORATION_FLOOR},
        "trajectories": {"honest": honest_traj, "recovering": recov_traj,
                         "liar": liar_traj, "flaky": flaky_traj},
        "recovery_steps_after_one_lie": recovery_steps,
        "final": L.summary(),
        "asymmetry": {
            "truths_to_reach_0.90": n_up,
            "trust_before_one_lie": round(trust_before_lie, 4),
            "trust_after_one_lie": round(trust_after_lie, 4),
            "single_lie_drop": round(one_lie_drop, 4),
            "reading": (f"{n_up} consecutive verified truths to climb from the {PRIOR} "
                        f"prior to 0.90 trust; but a SINGLE lie from a high-trust source "
                        f"(here {trust_before_lie:.2f}, after 8 truths) collapses it by "
                        f"{one_lie_drop:.2f} to {trust_after_lie:.2f}, below the "
                        f"{CORROBORATION_FLOOR} corroboration floor. Honesty is earned "
                        "slowly, betrayed instantly."),
        },
        "checks": checks,
        "passed": passed,
        "note": ("Deterministic mechanism demonstration; parameters are pinned design "
                 "choices, not fitted. Local sensing is the arbiter and is never doubted "
                 "-- it is the ground truth an agent can always rely on."),
    }
    os.makedirs(RESULTS, exist_ok=True)
    jp = os.path.join(RESULTS, "experiment_trust.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    mp = os.path.join(RESULTS, "experiment_trust.md")
    with open(mp, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print(result, jp, mp)
    return result


def render_md(r: dict) -> str:
    f = r["final"]
    a = r["asymmetry"]
    lines = ["# H2: trust coefficient (local sensing as the ultimate truth)", ""]
    lines.append(f"**{'PASS' if r['passed'] else 'FAIL'}** &mdash; {r['mechanism']}.")
    lines.append("")
    lines.append(f"- Params: prior {r['params']['prior']}, truth-reward "
                 f"{r['params']['reward']}, lie-factor {r['params']['lie_factor']} "
                 f"(x, multiplicative collapse), corroboration floor "
                 f"{r['params']['corroboration_floor']}.")
    lines.append("")
    lines.append("## Trust trajectories (trust after each verified claim)")
    lines.append("")
    lines.append(f"- honest (12 truths): {r['trajectories']['honest']}")
    lines.append(f"- recovering (8 truths, 1 lie, 3 truths): {r['trajectories']['recovering']}")
    lines.append(f"- persistent liar (3 truths, 3 lies): {r['trajectories']['liar']}")
    lines.append(f"- flaky (truth/lie x5): {r['trajectories']['flaky']}")
    lines.append("")
    lines.append("## Final trust")
    lines.append("")
    lines.append("| Source | Trust | Truths | Lies | Can corroborate? |")
    lines.append("|---|---|---|---|---|")
    for src, s in f.items():
        lines.append(f"| {src} | {s['trust']} | {s['truths']} | {s['lies']} | "
                     f"{'yes' if s['can_corroborate'] else 'NO'} |")
    lines.append("")
    lines.append("## The asymmetry (extreme lie penalty)")
    lines.append("")
    lines.append(f"- {a['reading']}")
    lines.append("")
    lines.append("## Checks")
    lines.append("")
    for k, v in r["checks"].items():
        lines.append(f"- [{'x' if v else ' '}] {k}")
    lines.append("")
    lines.append(f"> {r['note']}")
    lines.append("")
    return "\n".join(lines)


def _print(r, jp, mp):
    print("=" * 66)
    print(f"TRUST COEFFICIENT DEMO: {'PASS' if r['passed'] else 'FAIL'}")
    f = r["final"]
    print(f"  honest -> {f['junction-honest']['trust']} (can corroborate: {f['junction-honest']['can_corroborate']})")
    print(f"  liar   -> {f['junction-liar']['trust']} (can corroborate: {f['junction-liar']['can_corroborate']})")
    print(f"  asymmetry: {r['asymmetry']['reading']}")
    print(f"  checks: {sum(1 for v in r['checks'].values() if v)}/{len(r['checks'])}")
    print("=" * 66)
    print(f"  wrote: {jp}\n  wrote: {mp}")


if __name__ == "__main__":
    res = run()
    raise SystemExit(0 if res["passed"] else 1)
