"""Run + sweep harness for authenticated cross-junction coordination.

Reuses CFG / HERE / parse_metrics from run_baseline. Four modes:

  * ``fixed``         -- SUMO default fixed-time program (no controller logic).
  * ``maxpressure``   -- classical MaxPressure baseline / shield.
  * ``uncoordinated`` -- event-gated hybrid (SLM proposes, MaxPressure disposes),
                         NO neighbour messaging. Uses SLMAgent unless an agent is
                         injected.
  * ``coordinated``   -- hybrid + signed neighbour coordination: per-junction
                         Ed25519 identities, a permissioned Registry, a signed
                         MessageBus over the grid adjacency, and a
                         ConservationChecker reconciling claims vs observation.

The deterministic modes (fixed, maxpressure) and the StubAgent
coordinated/uncoordinated modes run with NO Foundry Local dependency, so they are
CI-able. Only the real-SLMAgent modes need Foundry.

    python src/run_coordinated.py --mode coordinated
    python src/run_coordinated.py --mode maxpressure --seeds 1 2 3
"""
from __future__ import annotations

import argparse
import os

import traci
from sumolib import checkBinary

from conservation import ConservationChecker
from controllers import FixedTimeController, MaxPressureController
from coordinated_controller import CoordinatedController, StubAgent
from hybrid_controller import HybridController
from identity import JunctionIdentity
from message_bus import MessageBus
from registry import Registry
from run_baseline import CFG, HERE, parse_metrics

# Grid neighbour adjacency (bidirectional edges A0<->A1, A0<->B0, A1<->B1, B0<->B1).
ADJACENCY = {"A0": ["A1", "B0"], "A1": ["A0", "B1"],
             "B0": ["A0", "B1"], "B1": ["A1", "B0"]}

MODES = ("fixed", "maxpressure", "uncoordinated", "coordinated")


def _build_coordination(tls):
    """Build identities + a fully-registered Registry + signed bus + checker.

    One Ed25519 identity per signalised junction, every junction registered in
    the permissioned allowlist, a MessageBus over the static grid adjacency, and
    a ConservationChecker. Returns ``(identities, registry, bus, checker)``.
    """
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    checker = ConservationChecker()
    return identities, registry, bus, checker


def run(mode: str, slm_junctions=None, seed: int = 42, end: int = 1000,
        agent=None, coord_weight: float = 1.0, flow_window: float = 30.0) -> dict:
    """Run one simulation in ``mode`` and return traffic + coordination metrics.

    ``mode`` in {fixed, maxpressure, uncoordinated, coordinated}. For the SLM
    modes, ``agent`` is injected for tests (StubAgent); when None a real SLMAgent
    is constructed (needs Foundry Local).

    ``coord_weight`` (lambda, coordinated mode only) scales the deterministic
    Channel-B incoming-release term; ``0.0`` reproduces the uncoordinated shield
    choice exactly (clean ablation). Ignored by non-coordinated modes.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")

    binary = checkBinary("sumo")
    tripinfo = os.path.join(HERE, "..", "sumo", f"tripinfo_coord_{mode}.xml")
    traci.start([binary, "-c", CFG, "--tripinfo-output", tripinfo,
                 "--seed", str(seed), "--no-warnings", "true"])
    try:
        tls = list(traci.trafficlight.getIDList())
        sl = slm_junctions or tls

        coordination = None
        if mode == "fixed":
            ctrl = FixedTimeController()
        elif mode == "maxpressure":
            ctrl = MaxPressureController(traci, tls)
        elif mode == "uncoordinated":
            used_agent = agent if agent is not None else _real_agent()
            ctrl = HybridController(traci, tls, used_agent, slm_junctions=sl)
        else:  # coordinated
            used_agent = agent if agent is not None else _real_agent()
            identities, registry, bus, checker = _build_coordination(tls)
            coordination = {"identities": identities, "registry": registry,
                            "bus": bus, "checker": checker}
            ctrl = CoordinatedController(
                traci, tls, used_agent, identities=identities, registry=registry,
                bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=sl,
                coord_weight=coord_weight, flow_window=flow_window,
            )

        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            step += 1
    finally:
        traci.close()

    metrics = parse_metrics(tripinfo)
    metrics["mode"] = mode
    metrics["seed"] = seed
    metrics["sim_steps"] = step

    if mode in ("uncoordinated", "coordinated"):
        ev = ctrl.events
        metrics["slm_decisions"] = len(ev)
        metrics["slm_model"] = getattr(ctrl.agent, "model", "unknown")
        metrics["slm_junctions"] = sorted(ctrl.slm)
        metrics["shield_overrode_none"] = sum(1 for e in ev if e["slm_phase"] is None)
        metrics["slm_differed_from_shield"] = sum(
            1 for e in ev if e["slm_phase"] is not None and e["slm_phase"] != e["shield_phase"])
    if mode == "coordinated":
        metrics["verified_messages"] = sum(len(e.get("received", [])) for e in ctrl.events
                                           if isinstance(e.get("received"), list))
        metrics["rejected_messages"] = len(coordination["bus"].rejected)
        metrics["detections"] = len(ctrl.detections)
        metrics["flagged_detections"] = sum(1 for d in ctrl.detections if d.flagged)
        # CAUSAL-PATHWAY METRIC (R2): decisions where the coordination-adjusted
        # deterministic choice differed from the plain MaxPressure choice. Proves
        # coordination is live even if travel-time is unchanged. Counted directly
        # on the controller; cross-checked against the per-event flag.
        metrics["coord_weight"] = ctrl.coord_weight
        metrics["coord_adjusted_decisions"] = ctrl.coord_adjusted_decisions
        metrics["coord_changed_events"] = sum(
            1 for e in ctrl.events if e.get("coord_changed"))
    return metrics


def _real_agent():
    """Construct the real SLMAgent (deferred import: needs Foundry Local)."""
    from slm_agent import SLMAgent
    return SLMAgent()


def sweep(modes, seeds) -> list[dict]:
    """Run every (mode, seed) pair, collect metrics, print + return them."""
    results: list[dict] = []
    for mode in modes:
        for seed in seeds:
            metrics = run(mode, seed=seed)
            results.append(metrics)
            print(f"[done] mode={mode} seed={seed} "
                  f"completed={metrics.get('completed')} "
                  f"avg_travel_time_s={metrics.get('avg_travel_time_s')}")
    return results


def _markdown_table(results: list[dict]) -> str:
    header = "| mode | seed | completed | avg_travel_time_s | avg_waiting_time_s |"
    sep = "| --- | --- | --- | --- | --- |"
    rows = [
        f"| {r.get('mode')} | {r.get('seed')} | {r.get('completed')} | "
        f"{r.get('avg_travel_time_s')} | {r.get('avg_waiting_time_s')} |"
        for r in results
    ]
    return "\n".join([header, sep, *rows])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=list(MODES), default="coordinated")
    ap.add_argument("--seeds", nargs="*", type=int, default=[42])
    ap.add_argument("--slm", nargs="*", default=None,
                    help="junction IDs the SLM controls (default: all)")
    args = ap.parse_args()

    results = sweep([args.mode], args.seeds)
    print()
    print(_markdown_table(results))
