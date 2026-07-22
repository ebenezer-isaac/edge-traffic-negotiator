"""Scaling harness for the authenticated cross-junction coordination stack.

De-risks SCALING for *The Edge Negotiator*. The full stack (Ed25519 identities,
permissioned Registry, signed MessageBus, ConservationChecker, CoordinatedController)
was validated on a 2x2 grid (4 TLS) and the real Euston Road (A501) substrate. This
harness characterises how that stack scales on synthetic grids of INCREASING size
-- 2x2 (4 TLS), 3x3 (9 TLS), 4x4 (16 TLS) -- using the DETERMINISTIC StubAgent so
there is NO Foundry Local dependency: every run is fast and bit-reproducible.

What it measures, per (grid, seed):
  * total run wall-clock (s)               -- end-to-end sim + controller loop
  * controller wall-clock (s)              -- summed time inside ctrl.step()
  * per-decision wall-clock (ms)           -- controller time / SLM decisions
  * decisions                              -- number of SLM/coordination decisions
  * verified_messages                      -- inbox()-delivered signed neighbour msgs
  * rejected_messages                      -- bus rejections
  * reconciliations / detections           -- ConservationChecker evaluations / flags
  * coord_adjusted_decisions               -- causal-pathway proof (Channel B)
  * throughput-controlled traffic metrics  -- via metrics.summary() over a tripinfo
    written WITH --write-unfinished + --write-undeparted (whole population).

KEY QUESTION (P2): MessageBus.inbox() was recently indexed (per-recipient scan
cursor) to remove an O(n^2) full-buffer rescan. Does coordination wall-clock now
grow ~LINEARLY in TLS count (4 -> 9 -> 16)? This harness reports the growth so the
answer is data-backed.

Usage:
    .venv/Scripts/python src/run_scaling.py                 # default seeds
    .venv/Scripts/python src/run_scaling.py --seeds 42 7 13
    .venv/Scripts/python src/run_scaling.py --grids 2x2 3x3 # subset

This module is OWNED by the scaling study; it does not edit existing src/. It
builds its own per-grid adjacency from the net (sumolib), reusing the existing
CoordinatedController + StubAgent unchanged.
"""
from __future__ import annotations

import argparse
import os
import time

import sumolib
import traci
from sumolib import checkBinary

from conservation import ConservationChecker
from coordinated_controller import CoordinatedController, StubAgent
from identity import JunctionIdentity
from message_bus import MessageBus
from metrics import parse_tripinfo, summary
from registry import Registry

HERE = os.path.dirname(os.path.abspath(__file__))
SUMO_DIR = os.path.join(HERE, "..", "sumo")
TRIPINFO_DIR = os.path.join(HERE, "..", "results", "tripinfo_scaling")

# Grid -> (sumocfg path, net path). 2x2 reuses the existing Wk1-2 scenario; the
# 3x3 / 4x4 nets+cfgs are owned by this scaling study (sumo/grid3x3, sumo/grid4x4).
GRIDS = {
    "2x2": (os.path.join(SUMO_DIR, "grid2x2.sumocfg"),
            os.path.join(SUMO_DIR, "networks", "grid2x2.net.xml")),
    "3x3": (os.path.join(SUMO_DIR, "grid3x3", "grid3x3.sumocfg"),
            os.path.join(SUMO_DIR, "grid3x3", "grid3x3.net.xml")),
    "4x4": (os.path.join(SUMO_DIR, "grid4x4", "grid4x4.sumocfg"),
            os.path.join(SUMO_DIR, "grid4x4", "grid4x4.net.xml")),
}


def build_grid_adjacency(net_path: str, tls_ids) -> dict[str, list[str]]:
    """Neighbour adjacency for a grid net, from the net itself (not hardcoded).

    Two signalised junctions are neighbours iff a single network edge directly
    connects one's node to the other's. Grid edge ids are the ``{src}{dst}``
    junction-id concatenation, so the controller's grid name-parsing path resolves
    toward/observed/per-phase correctly and NO explicit edge_map is needed. We
    still derive adjacency from the net (robust to any grid size) rather than
    assume a formula. Returns a fresh ``{jid: sorted([neighbour, ...])}``.
    """
    net = sumolib.net.readNet(net_path)
    tls = set(tls_ids)
    adj: dict[str, set[str]] = {t: set() for t in tls}
    for edge in net.getEdges():
        if edge.getID().startswith(":"):
            continue
        f = edge.getFromNode().getID()
        t = edge.getToNode().getID()
        if f in tls and t in tls and f != t:
            adj[f].add(t)
            adj[t].add(f)
    return {k: sorted(v) for k, v in adj.items()}


def _build_coordination(tls, adjacency):
    """One Ed25519 identity per junction, all registered, a signed bus + checker."""
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, adjacency)
    checker = ConservationChecker()
    return identities, registry, bus, checker


def run_grid(grid: str, seed: int = 42, end: int = 1000) -> dict:
    """Run the coordinated stack (StubAgent) on one grid+seed; return scaling metrics.

    Times the controller separately from SUMO: ``ctrl.step()`` is wrapped so the
    controller wall-clock (the part that includes inbox()/publish()/reconcile) is
    isolated from SUMO stepping. Per-decision wall-clock = controller time / number
    of coordination decisions (events). The tripinfo is written for the WHOLE
    vehicle population (write-unfinished + write-undeparted) so metrics.summary()'s
    throughput-controlled numbers are trustworthy.
    """
    if grid not in GRIDS:
        raise ValueError(f"grid must be one of {sorted(GRIDS)}, got {grid!r}")
    cfg, net_path = GRIDS[grid]

    os.makedirs(TRIPINFO_DIR, exist_ok=True)
    tripinfo = os.path.join(TRIPINFO_DIR, f"tripinfo_{grid}_seed{seed}.xml")

    binary = checkBinary("sumo")
    t_start = time.perf_counter()
    traci.start([binary, "-c", cfg,
                 "--tripinfo-output", tripinfo,
                 "--tripinfo-output.write-unfinished",
                 "--tripinfo-output.write-undeparted",
                 "--seed", str(seed), "--no-warnings", "true"])
    try:
        tls = list(traci.trafficlight.getIDList())
        adjacency = build_grid_adjacency(net_path, tls)
        identities, registry, bus, checker = _build_coordination(tls, adjacency)
        agent = StubAgent()  # deterministic; no Foundry Local
        ctrl = CoordinatedController(
            traci, tls, agent, identities=identities, registry=registry,
            bus=bus, adjacency=adjacency, checker=checker, slm_junctions=tls,
            coord_weight=1.0,
        )

        ctrl_time = 0.0
        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            t0 = time.perf_counter()
            ctrl.step()
            ctrl_time += time.perf_counter() - t0
            step += 1
    finally:
        traci.close()
    total_time = time.perf_counter() - t_start

    # --- coordination metrics (off the controller / bus) ---
    events = ctrl.events
    decisions = len(events)
    verified_messages = sum(len(e.get("received", [])) for e in events
                            if isinstance(e.get("received"), list))
    rejected_messages = len(bus.rejected)
    detections = len(ctrl.detections)
    flagged = sum(1 for d in ctrl.detections if d.flagged)

    # --- throughput-controlled traffic metrics (whole population) ---
    run_record = parse_tripinfo(tripinfo)
    traffic = summary(run_record)

    per_decision_ms = (ctrl_time / decisions * 1000.0) if decisions else float("nan")

    return {
        "grid": grid,
        "tls_count": len(tls),
        "seed": seed,
        "sim_steps": step,
        "total_wall_s": round(total_time, 3),
        "ctrl_wall_s": round(ctrl_time, 3),
        "per_decision_ms": round(per_decision_ms, 4),
        "decisions": decisions,
        "verified_messages": verified_messages,
        "rejected_messages": rejected_messages,
        "reconciliations": detections,        # ConservationChecker evaluations stashed
        "flagged_detections": flagged,
        "coord_adjusted_decisions": ctrl.coord_adjusted_decisions,
        # throughput-controlled traffic metrics (metrics.py)
        "loaded": int(traffic["loaded"]),
        "departed": int(traffic["departed"]),
        "throughput": int(traffic["throughput"]),
        "running_at_end": int(traffic["running_at_end"]),
        "undeparted": int(traffic["undeparted"]),
        "completion_rate": round(traffic["completion_rate"], 4),
        "mean_network_delay_s": round(traffic["mean_network_delay"], 2),
        "total_network_delay_s": round(traffic["total_network_delay"], 1),
        "avg_travel_time_completed_s": round(traffic["avg_travel_time_completed"], 2),
    }


def sweep(grids, seeds) -> list[dict]:
    results: list[dict] = []
    for grid in grids:
        for seed in seeds:
            r = run_grid(grid, seed=seed)
            results.append(r)
            print(f"[done] grid={r['grid']} tls={r['tls_count']} seed={seed} "
                  f"total_wall_s={r['total_wall_s']} "
                  f"per_decision_ms={r['per_decision_ms']} "
                  f"decisions={r['decisions']} "
                  f"verified_msgs={r['verified_messages']} "
                  f"throughput={r['throughput']} "
                  f"completion_rate={r['completion_rate']}")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Scaling study for the coordination stack.")
    ap.add_argument("--grids", nargs="*", default=["2x2", "3x3", "4x4"],
                    choices=list(GRIDS))
    ap.add_argument("--seeds", nargs="*", type=int, default=[42, 7, 13])
    args = ap.parse_args()

    results = sweep(args.grids, args.seeds)
    print("\n=== scaling results (raw) ===")
    for r in results:
        print(r)
