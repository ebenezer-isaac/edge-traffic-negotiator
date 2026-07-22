"""Run the authenticated coordination layer on the REAL Euston Road (A501)
spine corridor.

``euston_spine.net.xml`` exists (4 TLS, built with SUMO ``netconvert`` from an
OSM extract of the Euston Road corridor); this runner targets it and executes
end-to-end. The ``SLM_JUNCTIONS`` ids below are re-derived from this net (not
the legacy ``lambeth_*.net.xml`` files also left in this directory, which are
the PRIOR corridor's build artifacts kept for reference only).

Dissertation goal ("The Edge Negotiator"): prove the authenticated-coordination
integrity layer GENERALISES from the 2x2 toy grid to the real Euston Road
(A501) corridor (``euston_spine.net.xml``). This runner stands up the FULL
integrity stack on the real net at the clean operating point (``--scale 1.0``):

  * one Ed25519 :class:`JunctionIdentity` per multi-green ("SLM-controllable") TLS,
  * a permissioned :class:`Registry` (every identity registered),
  * a signed :class:`MessageBus` over the REAL corridor adjacency, and
  * a :class:`ConservationChecker` reconciling claims vs observed inflows,

driving the UNMODIFIED :class:`CoordinatedController` (via a thin subclass, see
below) with the deterministic :class:`StubAgent` (no Foundry Local).

WHY A SUBCLASS (the central transfer finding)
---------------------------------------------
The grid-derived ``CoordinatedController`` recovers the directed edge between two
junctions by STRING CONVENTION: an edge id is the concatenation of the two
junction ids (``"A0A1" -> ("A0","A1")``). Three methods depend on that:

  * ``_toward_counts``     -> ``_split_edge(out_edge)`` to find the neighbour an
                              out-lane leads to,
  * ``_incoming_per_phase`` -> ``in_edge = f"{nb}{tl}"``,
  * ``_observed_inflows``  -> ``edge = f"{nb}{recipient}"``.

On the real net this convention is FALSE. TLS ids are OSM cluster strings
(``"cluster_1032792732_..._#11more"``) and edge ids are OSM way ids
(``"-634042794#2"``, ``"325568663#0"``). Verified on this machine:

  * ``_edge_of_lane`` ("325568663#0_0" -> "325568663#0") still WORKS -- lane->edge
    is a plain rsplit and is naming-agnostic.
  * ``_split_edge`` returns ``None`` for EVERY real inter-junction edge, and
    ``f"{nb}{tl}"`` never names a real edge. So on the real net the unmodified
    controller would PUBLISH empty ``toward`` payloads, record ZERO verified
    messages, ZERO claims, ZERO detections -- the coordination layer would
    silently no-op while still "running".

The brief authorises supplying the adjacency/edge map EXPLICITLY rather than
relying on name parsing. We derive both from ``euston_spine.net.xml`` with
sumolib and inject them by overriding exactly the three name-parsing methods.
Everything else (signing, registry, bus trust checks, conservation, the
Channel-A/B coordination maths, the event log) is the unmodified grid code.

Adjacency definition
---------------------
The brief's strict "two TLS are neighbours iff a SINGLE edge connects them" is
honoured AND its near-empty result reported: on this net only ONE such pair
exists (GS_227716 <-> the #4more cluster). Because the real corridor interleaves
non-signalised OSM nodes between signals, we ALSO derive the CORRIDOR-LOGICAL
adjacency: two TLS are neighbours iff a directed path of NON-signalised interior
nodes connects them with no other TLS in between (``--adjacency chain``, default).
The single-edge graph is available via ``--adjacency single`` for the strict
comparison. For every directed neighbour pair we record the edge that ENTERS the
downstream TLS -- that edge is the explicit in-edge / out-edge map the controller
needs.

    .venv/Scripts/python sumo/euston/run_corridor_coord.py
    .venv/Scripts/python sumo/euston/run_corridor_coord.py --adjacency single
"""
from __future__ import annotations

import argparse
import os
import sys

import sumolib
import traci
from sumolib import checkBinary

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.normpath(os.path.join(HERE, "..", "..", "src"))
sys.path.insert(0, SRC)

from conservation import ConservationChecker  # noqa: E402
from coordinated_controller import (  # noqa: E402
    CoordinatedController,
    StubAgent,
    edge_map_from_net,
    _edge_of_lane,
)
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from registry import Registry  # noqa: E402

# euston_spine.net.xml exists (built with netconvert; 4 TLS, see build history).
NET = os.path.join(HERE, "euston_spine.net.xml")
ROUTES = os.path.join(HERE, "base.rou.xml")
# Unique tripinfo dir to avoid collision with other running sims (per brief).
TRIPINFO_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "results", "tripinfo_corridor"))

# The 4 traffic-light junctions of euston_spine.net.xml (the "SLM-controllable"
# multi-green TLS), re-derived from the real net on 2026-07-22 (were the prior
# Lambeth OSM cluster ids). Verified against net.getTrafficLights(); run() also
# intersects this with traci.trafficlight.getIDList() so an id drift SKIPs
# rather than crashes.
SLM_JUNCTIONS = [
    "GS_cluster_110097_110098",
    "GS_6985146843",
    "GS_cluster_13249075_6985146839_6985146845",
    "cluster_2440680097_253308874_3837973624_427931760_#2more",
]


# --------------------------------------------------------------------------- #
# Topology derivation (sumolib, offline -- no TraCI needed).
# --------------------------------------------------------------------------- #
def _node_to_tls(net) -> dict[str, str]:
    """Map every TLS-controlled node id -> its TLS id."""
    node_to_tls: dict[str, str] = {}
    for t in net.getTrafficLights():
        for in_lane, _out_lane, _idx in t.getConnections():
            node_to_tls[in_lane.getEdge().getToNode().getID()] = t.getID()
    return node_to_tls


def _tls_nodes(net) -> dict[str, set[str]]:
    """TLS id -> set of node ids it controls (the junction the in-lanes feed)."""
    out: dict[str, set[str]] = {}
    for t in net.getTrafficLights():
        nodes = {in_lane.getEdge().getToNode().getID()
                 for in_lane, _o, _i in t.getConnections()}
        out[t.getID()] = nodes
    return out


def derive_topology(net, mode: str) -> tuple[dict[str, list[str]], dict[tuple[str, str], str]]:
    """Return (adjacency, in_edge_map) for the real corridor.

    Thin wrapper over the reusable ``edge_map_from_net`` helper now living in
    ``coordinated_controller`` (P1: the grid-vs-real edge resolution is generalised
    INTO the base controller; this runner no longer carries its own copy). The
    local ``_node_to_tls`` / ``_tls_nodes`` helpers are retained for any external
    caller but the derivation itself is the shared helper.

    ``adjacency``  : ``{tls_id: [neighbour_tls_id, ...]}`` (symmetrised).
    ``in_edge_map``: ``{(src_tls, dst_tls): edge_id}`` -- the edge that ENTERS
                     ``dst_tls`` carrying traffic released by ``src_tls``.
    """
    return edge_map_from_net(net, mode)


# --------------------------------------------------------------------------- #
# Real-net controller: now a THIN alias. The base CoordinatedController accepts
# an explicit ``edge_map`` (P1), so no method overrides are needed any more --
# the real-net edge resolution lives in the base class and is exercised by the
# grid path too (edge_map=None falls back to the f"{src}{dst}" convention).
# --------------------------------------------------------------------------- #
class CorridorCoordinatedController(CoordinatedController):
    """CoordinatedController on a real net.

    Kept as a named subclass for the runner's readability and for backwards
    compatibility; it simply forwards ``in_edge_map`` to the base controller's
    generalised ``edge_map`` parameter. All edge resolution is inherited.
    """

    def __init__(self, *args, in_edge_map: dict[tuple[str, str], str], **kwargs):
        super().__init__(*args, edge_map=in_edge_map, **kwargs)


# --------------------------------------------------------------------------- #
# Coordination wiring + run.
# --------------------------------------------------------------------------- #
def build_coordination(adjacency: dict[str, list[str]], slm_junctions):
    """Identities (for the SLM junctions) + registered Registry + signed bus + checker."""
    identities = {jid: JunctionIdentity(jid) for jid in slm_junctions}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, adjacency)
    checker = ConservationChecker()
    return identities, registry, bus, checker


def run(scale: float = 1.0, seed: int = 42, end: int = 3600,
        adjacency_mode: str = "chain") -> dict:
    """Run the coordinated integrity stack on the real corridor; return metrics."""
    net = sumolib.net.readNet(NET, withInternal=False)
    adjacency, in_edge_map = derive_topology(net, adjacency_mode)

    os.makedirs(TRIPINFO_DIR, exist_ok=True)
    tripinfo = os.path.join(TRIPINFO_DIR, f"corridor_coord_{adjacency_mode}_s{scale:g}_seed{seed}.xml")

    binary = checkBinary("sumo")
    traci.start([binary, "-n", NET, "-r", ROUTES,
                 "--tripinfo-output", tripinfo,
                 "--scale", str(scale),
                 "--begin", "0", "--end", str(end),
                 "--time-to-teleport", "300",
                 "--seed", str(seed),
                 "--no-step-log", "true", "--no-warnings", "true"])
    err = None
    teleports = 0
    try:
        tls = list(traci.trafficlight.getIDList())
        slm = [j for j in SLM_JUNCTIONS if j in tls]
        identities, registry, bus, checker = build_coordination(adjacency, slm)
        ctrl = CorridorCoordinatedController(
            traci, tls, StubAgent(), identities=identities, registry=registry,
            bus=bus, adjacency=adjacency, checker=checker, slm_junctions=slm,
            coord_weight=1.0, in_edge_map=in_edge_map,
        )
        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            teleports += traci.simulation.getStartingTeleportNumber()
            step += 1
    except Exception as e:  # noqa: BLE001 - capture any breakage verbatim
        import traceback
        err = f"{type(e).__name__}: {e}"
        traceback.print_exc()
    finally:
        try:
            traci.close()
        except Exception:
            pass

    metrics: dict = {
        "adjacency_mode": adjacency_mode,
        "scale": scale, "seed": seed,
        "sim_steps": step if err is None else None,
        "teleports": teleports,
        "error": err,
        "adjacency": adjacency,
        "in_edge_map": {f"{k[0]}->{k[1]}": v for k, v in in_edge_map.items()},
        "slm_junctions": sorted(ctrl.slm) if err is None else slm,
    }
    metrics.update(parse_metrics(tripinfo))
    if err is None:
        ev = ctrl.events
        metrics["slm_decisions"] = len(ev)
        metrics["verified_messages"] = sum(
            len(e.get("received", [])) for e in ev if isinstance(e.get("received"), list))
        metrics["published_nonempty"] = sum(
            1 for e in ev if e.get("published") and e["published"].get("toward"))
        metrics["rejected_messages"] = len(bus.rejected)
        metrics["rejected_by_reason"] = _count_reasons(bus.rejected)
        metrics["detections"] = len(ctrl.detections)
        metrics["flagged_detections"] = sum(1 for d in ctrl.detections if d.flagged)
        metrics["detections_by_reason"] = _count_det_reasons(ctrl.detections)
        metrics["coord_adjusted_decisions"] = ctrl.coord_adjusted_decisions
        metrics["registry_chain_ok"] = registry.verify_chain()
        # how many SLM decisions saw any incoming + emitted any toward
        metrics["decisions_with_incoming"] = sum(
            1 for e in ev if e.get("expected_incoming", 0) > 0)
    return metrics


def _count_reasons(rejected):
    out: dict[str, int] = {}
    for r in rejected:
        out[r["reason"]] = out.get(r["reason"], 0) + 1
    return out


def _count_det_reasons(detections):
    out: dict[str, int] = {}
    for d in detections:
        out[d.reason] = out.get(d.reason, 0) + 1
    return out


def parse_metrics(tripinfo_path: str) -> dict:
    import xml.etree.ElementTree as ET
    if not os.path.exists(tripinfo_path):
        return {"completed": 0}
    trips = ET.parse(tripinfo_path).getroot().findall("tripinfo")
    n = len(trips)
    if n == 0:
        return {"completed": 0}
    avg = lambda a: sum(float(t.get(a)) for t in trips) / n
    return {
        "completed": n,
        "avg_travel_time_s": round(avg("duration"), 2),
        "avg_waiting_time_s": round(avg("waitingTime"), 2),
        "avg_time_loss_s": round(avg("timeLoss"), 2),
    }


def main() -> None:
    import json
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.0)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--end", type=int, default=3600)
    ap.add_argument("--adjacency", choices=["chain", "single"], default="chain")
    args = ap.parse_args()

    result = run(scale=args.scale, seed=args.seed, end=args.end,
                 adjacency_mode=args.adjacency)
    print("\n=== corridor coordination result ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
