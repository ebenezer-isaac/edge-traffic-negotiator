"""Integration + adversarial tests for authenticated cross-junction coordination.

Covers run_coordinated.run + CoordinatedController:
  * a StubAgent coordinated run over a SHORT sim completes and yields completed>0;
  * the signed bus actually carried >0 verified neighbour messages during the run;
  * the ConservationChecker produced structurally-valid Detection objects (>=0);
  * a SPOOFER (a registered junction publishing an inflated "toward") is caught as
    a flagged Detection;
  * the deterministic baselines (maxpressure, fixed) still run -- no regression.

src/ is inserted on sys.path so `import run_coordinated` etc. work when run as
`python -m pytest tests` from the project root. SUMO + traci are required (the
project environment has them); no Foundry Local is needed because StubAgent is
injected for the SLM modes.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from conservation import ConservationChecker, Detection  # noqa: E402
from coordinated_controller import (  # noqa: E402
    CoordinatedController, StubAgent, _split_edge, _edge_of_lane,
    edge_map_from_net,
)
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from registry import Registry  # noqa: E402
import run_coordinated  # noqa: E402

ADJACENCY = run_coordinated.ADJACENCY
SHORT_END = 200
SEED = 42


# --------------------------------------------------------------------------- #
# Pure-unit edge-parsing helpers (no SUMO needed).
# --------------------------------------------------------------------------- #

def test_edge_of_lane_strips_index():
    assert _edge_of_lane("A0A1_0") == "A0A1"
    assert _edge_of_lane("B1B0_2") == "B1B0"


def test_split_edge_between_two_junctions():
    junctions = frozenset({"A0", "A1", "B0", "B1"})
    assert _split_edge("A0A1", junctions) == ("A0", "A1")
    assert _split_edge("B1B0", junctions) == ("B1", "B0")


def test_split_edge_to_dead_end_is_none():
    junctions = frozenset({"A0", "A1", "B0", "B1"})
    # Edges to/from dead-ends have a non-junction endpoint -> not a neighbour edge.
    assert _split_edge("A0left0", junctions) is None
    assert _split_edge("left0A0", junctions) is None


# --------------------------------------------------------------------------- #
# Integration: coordinated run over a short sim with the deterministic StubAgent.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def coordinated_metrics():
    """Run one short coordinated sim with StubAgent; share across assertions."""
    return run_coordinated.run("coordinated", seed=SEED, end=SHORT_END, agent=StubAgent())


def test_coordinated_short_run_completes_with_traffic(coordinated_metrics):
    m = coordinated_metrics
    assert m["mode"] == "coordinated"
    assert m["completed"] > 0, f"expected completed>0, got {m}"
    assert m["slm_model"] == "stub"
    # avg metrics should be present and non-negative when traffic completed.
    assert m["avg_travel_time_s"] >= 0
    assert m["avg_waiting_time_s"] >= 0


def test_coordinated_bus_carried_verified_messages(coordinated_metrics):
    # The runner exposes verified_messages = sum of received-list lengths.
    assert coordinated_metrics["verified_messages"] > 0, (
        "expected the signed bus to deliver >0 verified neighbour messages")


def test_coordinated_conservation_detections_structural(coordinated_metrics):
    # >=0 detections; the count is exposed and is a non-negative int.
    assert coordinated_metrics["detections"] >= 0
    assert coordinated_metrics["flagged_detections"] >= 0
    assert coordinated_metrics["flagged_detections"] <= coordinated_metrics["detections"]


def test_coordinated_detections_are_valid_detection_objects():
    """Drive a controller directly with a fake conn so we can inspect Detections.

    Uses a minimal in-memory TraCI stand-in so this assertion needs no SUMO and
    is fully deterministic: two neighbours publish a 'toward' claim, the
    recipient observes a matching inflow, and we confirm Detection objects are
    produced with the documented structure.
    """
    detections = _run_fake_controller_once(claim=5, observe=5, tolerance=2)
    assert isinstance(detections, list)
    for d in detections:
        assert isinstance(d, Detection)
        assert isinstance(d.src, str) and isinstance(d.dst, str)
        assert isinstance(d.claimed, int) and isinstance(d.observed, int)
        assert d.delta == d.claimed - d.observed
        assert isinstance(d.flagged, bool)
        assert d.reason in {"ok", "inflated", "under_reported",
                            "missing_claim", "missing_observation"}


# --------------------------------------------------------------------------- #
# Adversarial: a registered junction publishes an INFLATED "toward" -> flagged.
# --------------------------------------------------------------------------- #

def test_spoofer_inflated_claim_is_flagged():
    """A0 spoofs a huge release toward A1; A1 observes ~nothing -> 'inflated'.

    The spoofer is a *registered* identity (so the message is authentic and
    passes the bus's crypto/membership/topology checks). The conservation layer
    is what catches the lie: claim >> observation beyond tolerance.
    """
    detections = _run_fake_controller_once(claim=99, observe=0, tolerance=2)
    flagged = [d for d in detections if d.flagged]
    assert flagged, f"expected a flagged detection, got {detections}"
    inflated = [d for d in flagged if d.reason == "inflated"]
    assert inflated, f"expected an 'inflated' detection, got {[d.reason for d in flagged]}"
    d = inflated[0]
    assert d.claimed >= 99
    assert d.delta > 0  # claimed exceeds observed (over-report)
    # The claim is "A1 releases toward A0" -> directed edge A1 -> A0.
    assert (d.src, d.dst) == ("A1", "A0")


# --------------------------------------------------------------------------- #
# R2 causal pathway: the deterministic coordination term CHANGES the choice.
# --------------------------------------------------------------------------- #

def _build_coord_pathway_controller(coord_weight: float):
    """Fake A0 where plain MaxPressure prefers phase 1, then craft incoming on
    phase 0 from A1. Returns (ctrl, bus, identities).

    Movements (per _FakeTL): movement 0 in-lane A1A0_0 (served by green phase 0),
    movement 1 in-lane B0A0_0 (served by green phase 1). We set local halting so
    plain MaxPressure (argmax over local green_halting) prefers phase 1.
    """
    halting = {
        "A1A0_0": 1,    # phase-0 local queue (small) + observed inflow edge A1->A0
        "B0A0_0": 8,    # phase-1 local queue (large) -> plain MaxPressure picks phase 1
        "A0A1_0": 0,
        "A0B0_0": 0,
        "B0A0_0_obs": 0,
    }
    conn = _FakeConn(halting)
    tls = ["A0", "A1", "B0", "B1"]
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    checker = ConservationChecker(tolerance=2)
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=["A0"], gate=0,
        coord_weight=coord_weight,
    )
    return ctrl, bus, identities


def test_coord_weight_high_changes_deterministic_choice():
    """High coord_weight + a crafted incoming forecast flips the deterministic
    choice away from plain MaxPressure -> the coordination pathway is CAUSAL."""
    ctrl, bus, identities = _build_coord_pathway_controller(coord_weight=10.0)
    # A1 announces a big platoon heading toward A0's phase-0 approach (edge A1A0).
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 50, "queue_forecast": 50}}})
    st = ctrl.tls["A0"]
    ctrl.decide("A0", st)
    ev = ctrl.events[-1]
    # Plain MaxPressure preferred phase 1 (big local queue on B0A0_0).
    assert ev["mp_choice"] == 1
    # Coordination redirected the deterministic choice to phase 0 (incoming platoon).
    assert ev["coord_choice"] == 0
    assert ev["coord_changed"] is True
    assert ctrl.coord_adjusted_decisions == 1
    # The per-phase attribution put the incoming release on phase 0, not phase 1.
    assert ev["incoming_per_phase"][0] == 50
    assert ev["incoming_per_phase"][1] == 0


def test_coord_weight_zero_reproduces_plain_maxpressure():
    """coord_weight == 0.0 must reproduce the plain MaxPressure choice exactly,
    regardless of incoming forecasts (clean ablation / no coordination effect)."""
    ctrl, bus, identities = _build_coord_pathway_controller(coord_weight=0.0)
    # Same huge incoming platoon -- but with lambda 0 it must have NO effect.
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 50, "queue_forecast": 50}}})
    st = ctrl.tls["A0"]
    ctrl.decide("A0", st)
    ev = ctrl.events[-1]
    assert ev["mp_choice"] == 1
    assert ev["coord_choice"] == ev["mp_choice"], "lambda=0 must not change the choice"
    assert ev["coord_changed"] is False
    assert ctrl.coord_adjusted_decisions == 0


def test_conservation_consumes_release_not_forecast():
    """A spoofer can inflate the (unverifiable) forecast freely, but conservation
    must key on the ACTUAL release only (R1 / spec §6.2). release within tolerance
    of observation => NOT flagged, even with a wildly inflated queue_forecast."""
    ctrl, bus, identities = _build_fake_controller(observe=5, tolerance=2)
    # Honest release (5, matching the observed 5) but a hugely inflated forecast.
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 5, "queue_forecast": 9999}}})
    st = ctrl.tls["A0"]
    ctrl.decide("A0", st)
    edge_a1_a0 = [d for d in ctrl.detections if (d.src, d.dst) == ("A1", "A0")]
    assert edge_a1_a0, "expected a detection on edge A1->A0"
    d = edge_a1_a0[0]
    assert d.claimed == 5, "conservation must use release (5), NOT queue_forecast"
    assert not d.flagged, "release matched observation -> must not flag"


def test_malformed_neighbour_entry_rejected_at_boundary():
    """A neighbour entry that is not a well-formed {release,...} object is dropped
    (no crash, no claim, no per-phase contribution)."""
    ctrl, bus, identities = _build_fake_controller(observe=0, tolerance=2)
    # Old/scalar shape and negative release are both hostile/malformed now.
    bus.publish(identities["A1"], 0, {"toward": {"A0": {"release": -3}}})
    st = ctrl.tls["A0"]
    ctrl.decide("A0", st)
    ev = ctrl.events[-1]
    assert ev["expected_incoming"] == 0
    assert all(v == 0 for v in ev["incoming_per_phase"])


def test_coordinated_run_exposes_coord_metrics(coordinated_metrics):
    """The runner surfaces the causal-pathway metric and the lambda used."""
    m = coordinated_metrics
    assert m["coord_weight"] == 1.0
    assert m["coord_adjusted_decisions"] >= 0
    assert m["coord_adjusted_decisions"] == m["coord_changed_events"]


def test_invalid_coord_weight_rejected():
    """coord_weight is validated at the boundary (no NaN/inf/negative/bool)."""
    conn = _FakeConn({"A1A0_0": 0, "B0A0_0": 1, "A0A1_0": 0, "A0B0_0": 0})
    identities = {jid: JunctionIdentity(jid) for jid in ("A0", "A1", "B0", "B1")}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    for bad in (-1.0, float("nan"), float("inf"), True):
        with pytest.raises((ValueError, TypeError)):
            CoordinatedController(
                conn, ["A0"], StubAgent(), identities=identities,
                registry=registry, bus=bus, adjacency=ADJACENCY,
                slm_junctions=["A0"], coord_weight=bad,
            )


# --------------------------------------------------------------------------- #
# Regression: deterministic baselines still run over a short sim.
# --------------------------------------------------------------------------- #

def test_maxpressure_short_run_no_regression():
    m = run_coordinated.run("maxpressure", seed=SEED, end=SHORT_END)
    assert m["mode"] == "maxpressure"
    assert m["completed"] >= 0
    assert m["sim_steps"] <= SHORT_END


def test_fixed_short_run_no_regression():
    m = run_coordinated.run("fixed", seed=SEED, end=SHORT_END)
    assert m["mode"] == "fixed"
    assert m["completed"] >= 0
    assert m["sim_steps"] <= SHORT_END


def test_run_rejects_unknown_mode():
    with pytest.raises(ValueError):
        run_coordinated.run("nonsense", end=SHORT_END)


# --------------------------------------------------------------------------- #
# Test helper: a fake TraCI connection + a direct controller decision.
# --------------------------------------------------------------------------- #

class _FakeLane:
    """Stand-in for traci.lane: per-lane halting counts from a dict."""

    def __init__(self, halting: dict[str, int]):
        self._halting = halting

    def getLastStepHaltingNumber(self, lane_id):
        if lane_id not in self._halting:
            raise KeyError(lane_id)  # mimics SUMO raising on unknown lane
        return self._halting[lane_id]


class _FakeTL:
    """Stand-in for traci.trafficlight used only at controller construction."""

    class _Phase:
        def __init__(self, state):
            self.state = state

    class _Logic:
        def __init__(self, phases):
            self.phases = phases

    def __init__(self):
        # Two green phases + their clearing yellows, alternating movements.
        # Movement 0 serves A0->A1 (NS), movement 1 serves A0->B0 (EW).
        self._phases = [
            self._Phase("Gr"),  # green: movement0
            self._Phase("yr"),  # yellow clearing movement0
            self._Phase("rG"),  # green: movement1
            self._Phase("ry"),  # yellow clearing movement1
        ]
        self._links = [
            [("A1A0_0", "A0A1_0", "")],  # in A1->A0, out A0->A1 (toward A1)
            [("B0A0_0", "A0B0_0", "")],  # in B0->A0, out A0->B0 (toward B0)
        ]

    def getAllProgramLogics(self, tl):
        return [self._Logic(self._phases)]

    def getControlledLinks(self, tl):
        return self._links

    def setRedYellowGreenState(self, tl, state):
        return None


class _FakeConn:
    def __init__(self, halting):
        self.lane = _FakeLane(halting)
        self.trafficlight = _FakeTL()


def _build_fake_controller(observe: int, tolerance: int, coord_weight: float = 1.0):
    """Build a CoordinatedController on a fake conn (no SUMO) and its bus/identities.

    A0's neighbours are A1 and B0. A0 observes `observe` halting vehicles on edge
    A1->A0 (lane "A1A0_0"). Returns ``(ctrl, bus, identities)`` so callers can
    publish crafted neighbour messages before driving ``decide``.
    """
    halting = {
        # A0's served in-lanes (drives 'toward' the controller publishes; small).
        "A1A0_0": observe,   # also the observed inflow edge A1->A0
        "B0A0_0": 1,
        # out-lanes referenced by _toward_counts / observation (any value).
        "A0A1_0": 0,
        "A0B0_0": 0,
        "B0A0_0_obs": 0,
    }
    conn = _FakeConn(halting)
    tls = ["A0", "A1", "B0", "B1"]
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    checker = ConservationChecker(tolerance=tolerance)

    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=["A0"], gate=0,
        coord_weight=coord_weight,
    )
    return ctrl, bus, identities


def _run_fake_controller_once(claim: int, observe: int, tolerance: int):
    """Build a CoordinatedController on a fake conn, publish a neighbour claim
    as A1, then run A0's decide() once and return the Detections it produced.

    A0's neighbours are A1 and B0. A1 (registered) publishes the new-shape payload
    ``toward={"A0": {"release": claim, "queue_forecast": claim}}`` at the same tick
    A0 will read. A0 observes `observe` halting vehicles on edge A1->A0 (lane
    "A1A0_0"). With claim >> observe the conservation check flags it (on `release`).
    """
    ctrl, bus, identities = _build_fake_controller(observe, tolerance)
    # A1 (a registered, authentic identity) publishes its claim for tick 0 --
    # exactly the tick A0's first decide() will read from its inbox. New payload
    # shape (R1): per-neighbour {release, queue_forecast}; only release is conserved.
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": claim, "queue_forecast": claim}}})

    st = ctrl.tls["A0"]
    ctrl.decide("A0", st)
    return list(ctrl.detections)


# --------------------------------------------------------------------------- #
# P1 -- generalised edge resolution: an OSM-style edge_map (ids that are NOT
# junction-id concatenations) must resolve toward/observed and deliver verified
# messages > 0, where the grid f"{src}{dst}" convention would no-op.
# --------------------------------------------------------------------------- #

# Real-net-style ids: TLS clusters and OSM way ids that break the grid convention.
_OSM_J = "cluster_AAA"      # the deciding junction
_OSM_N = "cluster_BBB"      # its neighbour
_OSM_K = "cluster_CCC"      # a second neighbour (phase 1 approach)
_OSM_ADJ = {_OSM_J: [_OSM_N, _OSM_K], _OSM_N: [_OSM_J], _OSM_K: [_OSM_J]}
# in-edge map: (src, dst) -> OSM way id entering dst from src.
_OSM_EDGE_MAP = {
    (_OSM_N, _OSM_J): "-634042794#2",   # N -> J  (phase-0 in-edge)
    (_OSM_J, _OSM_N): "325568663#0",    # J -> N  (phase-0 out-edge)
    (_OSM_K, _OSM_J): "243976865",      # K -> J  (phase-1 in-edge)
    (_OSM_J, _OSM_K): "-905990664",     # J -> K  (phase-1 out-edge)
}


class _OsmFakeTL:
    """Fake TL whose lane/edge ids are OSM way ids (NOT junction concatenations)."""

    class _Phase:
        def __init__(self, state):
            self.state = state

    class _Logic:
        def __init__(self, phases):
            self.phases = phases

    def __init__(self):
        self._phases = [
            self._Phase("Gr"), self._Phase("yr"),
            self._Phase("rG"), self._Phase("ry"),
        ]
        # movement 0: in N->J, out J->N (phase 0); movement 1: in K->J, out J->K.
        self._links = [
            [("-634042794#2_0", "325568663#0_0", "")],
            [("243976865_0", "-905990664_0", "")],
        ]

    def getAllProgramLogics(self, tl):
        return [self._Logic(self._phases)]

    def getControlledLinks(self, tl):
        return self._links

    def setRedYellowGreenState(self, tl, state):
        return None


class _OsmFakeConn:
    def __init__(self, halting):
        self.lane = _FakeLane(halting)
        self.trafficlight = _OsmFakeTL()


def _build_osm_controller(observe_n: int, observe_k: int = 0,
                          tolerance: int = 2, coord_weight: float = 1.0):
    """CoordinatedController on an OSM-style net via the explicit edge_map (P1)."""
    halting = {
        "-634042794#2_0": observe_n,   # N -> J in-edge (phase 0 / observation)
        "243976865_0": observe_k,      # K -> J in-edge (phase 1)
        "325568663#0_0": 0,            # J -> N out-edge
        "-905990664_0": 0,             # J -> K out-edge
    }
    conn = _OsmFakeConn(halting)
    tls = [_OSM_J, _OSM_N, _OSM_K]
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, _OSM_ADJ)
    checker = ConservationChecker(tolerance=tolerance)
    ctrl = CoordinatedController(
        conn, [_OSM_J], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=_OSM_ADJ, checker=checker, slm_junctions=[_OSM_J],
        gate=0, coord_weight=coord_weight, edge_map=_OSM_EDGE_MAP,
    )
    return ctrl, bus, identities


def test_edge_map_resolves_toward_on_osm_ids():
    """With an explicit edge_map, `toward` resolves the downstream neighbour from
    OSM out-lane ids that the grid `_split_edge` parse could never split."""
    ctrl, _bus, _idents = _build_osm_controller(observe_n=7)
    ctrl._current_tl = _OSM_J
    st = ctrl.tls[_OSM_J]
    # phase 0 serves movement 0 (in N->J, halting 7; out J->N) -> releases toward N.
    toward = ctrl._toward_counts(st, 0)
    assert toward == {_OSM_N: 7}, toward
    # The grid parse would have found NO neighbour on these OSM ids (proves the map).
    assert _split_edge("325568663#0", frozenset({_OSM_J, _OSM_N, _OSM_K})) is None


def test_edge_map_observed_inflows_on_osm_ids():
    """`_observed_inflows` reads the OSM in-edge via the map (not f'{nb}{tl}')."""
    ctrl, _bus, _idents = _build_osm_controller(observe_n=4, observe_k=9)
    observed = ctrl._observed_inflows(_OSM_J, {_OSM_N, _OSM_K})
    assert observed == {_OSM_N: 4, _OSM_K: 9}, observed


def test_edge_map_delivers_verified_messages_and_reconciles():
    """End-to-end on OSM ids: a neighbour's signed claim is delivered (verified
    messages > 0) and reconciled against the mapped observation."""
    ctrl, bus, identities = _build_osm_controller(observe_n=5, tolerance=2)
    bus.publish(identities[_OSM_N], 0,
                {"toward": {_OSM_J: {"release": 5, "queue_forecast": 5}}})
    ctrl.decide(_OSM_J, ctrl.tls[_OSM_J])
    ev = ctrl.events[-1]
    assert ev["expected_incoming"] == 5, ev
    assert len(ev["received"]) == 1 and ev["received"][0]["from"] == _OSM_N
    # Verified-messages metric (as the runners compute it) is > 0.
    verified = sum(len(e.get("received", [])) for e in ctrl.events
                   if isinstance(e.get("received"), list))
    assert verified > 0
    # Reconciliation used the mapped in-edge: claim 5 vs observed 5 -> ok, not flagged.
    edge = [d for d in ctrl.detections if (d.src, d.dst) == (_OSM_N, _OSM_J)]
    assert edge and edge[0].claimed == 5 and edge[0].observed == 5
    assert not edge[0].flagged


def test_edge_map_none_keeps_grid_behaviour_identical():
    """With NO edge_map the grid path is byte-for-byte unchanged: the standard
    grid fake controller still delivers and reconciles exactly as before."""
    dets_map_off = _run_fake_controller_once(claim=99, observe=0, tolerance=2)
    flagged = [d for d in dets_map_off if d.flagged and d.reason == "inflated"]
    assert flagged and (flagged[0].src, flagged[0].dst) == ("A1", "A0")


def test_edge_map_validates_keys_and_values():
    """edge_map is validated at the boundary (tuple[str,str] -> str)."""
    conn = _FakeConn({"A1A0_0": 0, "B0A0_0": 1, "A0A1_0": 0, "A0B0_0": 0})
    identities = {jid: JunctionIdentity(jid) for jid in ("A0", "A1", "B0", "B1")}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    for bad in ({("A", "B", "C"): "e"}, {("A", "B"): 5}, {"AB": "e"}, [("A", "B")]):
        with pytest.raises(TypeError):
            CoordinatedController(
                conn, ["A0"], StubAgent(), identities=identities, registry=registry,
                bus=bus, adjacency=ADJACENCY, slm_junctions=["A0"], edge_map=bad,
            )


# --------------------------------------------------------------------------- #
# P3 -- sensor-outage / silent-neighbour reconciliation (opt-in).
# --------------------------------------------------------------------------- #

def test_silent_neighbour_with_inflow_yields_missing_claim_when_enabled():
    """A registered neighbour that stops publishing while traffic still arrives on
    its in-edge is reconciled -> a flagged `missing_claim` detection (P3)."""
    # A0 observes inflow on edge A1->A0 but A1 publishes NOTHING this round.
    halting = {"A1A0_0": 6, "B0A0_0": 0, "A0A1_0": 0, "A0B0_0": 0}
    conn = _FakeConn(halting)
    tls = ["A0", "A1", "B0", "B1"]
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    checker = ConservationChecker(tolerance=2)
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=["A0"],
        gate=0, coord_weight=0.0, reconcile_silent_neighbours=True,
    )
    ctrl.decide("A0", ctrl.tls["A0"])
    a1 = [d for d in ctrl.detections if (d.src, d.dst) == ("A1", "A0")]
    assert a1, "silent neighbour with inflow must be reconciled"
    assert a1[0].reason == "missing_claim"
    assert a1[0].flagged and a1[0].claimed == 0 and a1[0].observed == 6


def test_silent_neighbour_default_off_is_unchanged():
    """Default (flag off): a silent neighbour is NOT reconciled (legacy behaviour,
    preserving the as-built attack-report gap)."""
    halting = {"A1A0_0": 6, "B0A0_0": 0, "A0A1_0": 0, "A0B0_0": 0}
    conn = _FakeConn(halting)
    tls = ["A0", "A1", "B0", "B1"]
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, slm_junctions=["A0"], gate=0,
        coord_weight=0.0,  # reconcile_silent_neighbours defaults False
    )
    ctrl.decide("A0", ctrl.tls["A0"])
    assert not any((d.src, d.dst) == ("A1", "A0") for d in ctrl.detections)


def test_silent_but_quiet_neighbour_not_flagged_when_enabled():
    """A silent neighbour with NO observed inflow is a genuinely idle approach and
    must NOT be flagged as a missing claim (no spurious detections)."""
    halting = {"A1A0_0": 0, "B0A0_0": 0, "A0A1_0": 0, "A0B0_0": 0}
    conn = _FakeConn(halting)
    tls = ["A0", "A1", "B0", "B1"]
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, slm_junctions=["A0"], gate=0,
        coord_weight=0.0, reconcile_silent_neighbours=True,
    )
    ctrl.decide("A0", ctrl.tls["A0"])
    assert ctrl.detections == []


# --------------------------------------------------------------------------- #
# P4 -- Channel-B override: the coordination choice can dispose over a valid SLM
# proposal when coord_override=True.
# --------------------------------------------------------------------------- #

class _FixedAgent:
    """Agent that always proposes a fixed phase (a 'reliable' SLM stand-in)."""

    model = "fixed-agent"

    def __init__(self, phase: int):
        self._phase = phase

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = ""):  # noqa: ARG002
        return self._phase


def _build_override_controller(coord_override: bool, threshold: float = 0.0):
    """A0 where plain MaxPressure prefers phase 1; the SLM always proposes phase 1
    too; a big incoming platoon on phase 0 makes the coordinated choice phase 0."""
    halting = {"A1A0_0": 1, "B0A0_0": 8, "A0A1_0": 0, "A0B0_0": 0}
    conn = _FakeConn(halting)
    tls = ["A0", "A1", "B0", "B1"]
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    checker = ConservationChecker(tolerance=2)
    ctrl = CoordinatedController(
        conn, ["A0"], _FixedAgent(1), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=["A0"],
        gate=0, coord_weight=10.0, coord_override=coord_override,
        coord_override_threshold=threshold,
    )
    return ctrl, bus, identities


def test_coord_override_changes_realized_decision_vs_slm():
    """coord_override=True + a strong incoming forecast: the coordination choice
    OVERRIDES the (valid) SLM proposal, changing the realized decision."""
    ctrl, bus, identities = _build_override_controller(coord_override=True)
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 50, "queue_forecast": 50}}})
    ctrl.decide("A0", ctrl.tls["A0"])
    ev = ctrl.events[-1]
    assert ev["slm_phase"] == 1                 # SLM proposed phase 1
    assert ev["coord_choice"] == 0              # coordination prefers phase 0
    assert ev["used"] == 0                      # override disposed -> phase 0
    assert ev["coord_overrode"] is True
    assert ctrl.coord_override_decisions == 1


def test_coord_override_off_keeps_slm_proposal():
    """Default (override off): a valid SLM proposal ALWAYS wins, even when the
    coordination choice disagrees (today's behaviour preserved)."""
    ctrl, bus, identities = _build_override_controller(coord_override=False)
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 50, "queue_forecast": 50}}})
    ctrl.decide("A0", ctrl.tls["A0"])
    ev = ctrl.events[-1]
    assert ev["slm_phase"] == 1
    assert ev["coord_choice"] == 0
    assert ev["used"] == 1                       # SLM proposal kept
    assert ev["coord_overrode"] is False
    assert ctrl.coord_override_decisions == 0


def test_coord_override_respects_threshold():
    """A high threshold suppresses the override when the margin is below it."""
    # margin = adj[0]-adj[1] = (1 + 10*50) - 8 = 493; threshold above that blocks it.
    ctrl, bus, identities = _build_override_controller(
        coord_override=True, threshold=1000.0)
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 50, "queue_forecast": 50}}})
    ctrl.decide("A0", ctrl.tls["A0"])
    ev = ctrl.events[-1]
    assert ev["used"] == 1                       # below threshold -> no override
    assert ev["coord_overrode"] is False


def test_coord_override_validation():
    """coord_override and its threshold are validated at the boundary."""
    conn = _FakeConn({"A1A0_0": 0, "B0A0_0": 1, "A0A1_0": 0, "A0B0_0": 0})
    identities = {jid: JunctionIdentity(jid) for jid in ("A0", "A1", "B0", "B1")}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    with pytest.raises(TypeError):
        CoordinatedController(
            conn, ["A0"], StubAgent(), identities=identities, registry=registry,
            bus=bus, adjacency=ADJACENCY, slm_junctions=["A0"], coord_override="yes")
    for bad in (-1.0, float("nan"), float("inf")):
        with pytest.raises((ValueError, TypeError)):
            CoordinatedController(
                conn, ["A0"], StubAgent(), identities=identities, registry=registry,
                bus=bus, adjacency=ADJACENCY, slm_junctions=["A0"],
                coord_override=True, coord_override_threshold=bad)
