"""Tests for the intelligent flow-conservation detector (src/flow_conservation.py).

Run from the project root with the venv interpreter:
    .venv/Scripts/python -m pytest tests/test_flow_conservation.py -v

Two layers:

  * UNIT -- drive ``FlowConservationDetector`` directly with synthetic per-window
    ``EdgeMeasurement`` streams (no SUMO, fully deterministic). These exercise the
    mass-balance residual, the adaptive band, the CUSUM persistence rule, and
    EVERY required edge case (zero/low flow, spillback, sensor dropout, warm-up,
    multi-downstream, divide-by-zero safety) and their adversarial boundaries.

  * LIVE-STYLE -- run the genuine coordinated controller over real SUMO at the
    demo's windowed feed across several seeds and assert the benign false-positive
    rate is ~0 (the headline Part-A property). Marked so it is skipped cleanly if
    SUMO/traci is unavailable in the runner.

These tests are written to BREAK the detector: the happy path is minimal; the
bulk targets boundaries, persistence vs. transience, and the documented
edge-case classifications.
"""
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from flow_conservation import (  # noqa: E402
    AdaptiveBand,
    CusumParams,
    EdgeMeasurement,
    EdgeVerdict,
    FlowConservationDetector,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _balanced(edge="A->B", flow=10, storage=4, **kw):
    """A perfectly-conserving window: entered == exited, no storage change."""
    return EdgeMeasurement(edge_id=edge, entered=flow, exited=flow,
                           storage_now=storage, storage_prev=storage, **kw)


def _run_stream(det, measurements):
    """Fold a list of measurements for one edge; return the verdicts."""
    return [det.update(m) for m in measurements]


def _first_flag(verdicts):
    for v in verdicts:
        if v.flagged:
            return v
    return None


# --------------------------------------------------------------------------- #
# Mass-balance residual + warm-up
# --------------------------------------------------------------------------- #

def test_balanced_flow_never_flags_after_warmup():
    """A perfectly-conserving edge produces residual 0 and never flags."""
    det = FlowConservationDetector()
    verdicts = _run_stream(det, [_balanced() for _ in range(40)])
    assert all(v.residual == 0.0 for v in verdicts)
    assert not any(v.flagged for v in verdicts)
    # Warm-up windows are labelled and do not flag.
    warm = det.cusum_params.warmup_windows
    assert all(v.status == "warmup" for v in verdicts[:warm])
    assert all(v.status == "ok" for v in verdicts[warm:])


def test_in_transit_vehicles_are_not_a_discrepancy():
    """Released-but-not-yet-arrived cars sit in storage, not in the residual.

    Window 1: 12 enter, 0 exit yet, storage rises 0->12. residual =
    12 - 0 - 12 = 0. The platoon is in transit, NOT a discrepancy.
    """
    det = FlowConservationDetector(cusum=CusumParams(warmup_windows=0))
    v = det.update(EdgeMeasurement("A->B", entered=12, exited=0,
                                   storage_now=12, storage_prev=0))
    assert v.residual == 0.0
    assert not v.flagged


def test_storage_delta_balances_arrivals():
    """Cars arriving drain storage and exit; residual stays ~0."""
    det = FlowConservationDetector(cusum=CusumParams(warmup_windows=0))
    # 12 in transit from last window now leave; 0 new enter. exited 12,
    # storage 12->0. residual = 0 - 12 - (0 - 12) = 0.
    v = det.update(EdgeMeasurement("A->B", entered=0, exited=12,
                                   storage_now=0, storage_prev=12))
    assert v.residual == 0.0
    assert not v.flagged


# --------------------------------------------------------------------------- #
# Adaptive tolerance (band)
# --------------------------------------------------------------------------- #

def test_band_is_always_positive_no_divide_by_zero():
    """Even a totally idle edge has a strictly positive band (abs_floor>0)."""
    det = FlowConservationDetector()
    v = det.update(EdgeMeasurement("A->B", entered=0, exited=0, storage_now=0))
    assert v.band > 0.0
    assert v.z == 0.0  # residual 0 / positive band


def test_band_scales_with_flow_and_storage():
    """Band grows with expected flow and with storage (sqrt term)."""
    band = AdaptiveBand(abs_floor=2.0, rel_frac=0.15, storage_uncert=1.0)
    quiet = band.width(expected_flow=0, storage_now=0, storage_prev=0)
    busy = band.width(expected_flow=100, storage_now=0, storage_prev=0)
    stored = band.width(expected_flow=0, storage_now=100, storage_prev=0)
    assert quiet == pytest.approx(2.0)
    assert busy == pytest.approx(2.0 + 0.15 * 100)
    assert stored == pytest.approx(2.0 + 1.0 * 10.0)  # sqrt(100)=10


def test_abs_floor_must_be_positive():
    with pytest.raises(ValueError):
        AdaptiveBand(abs_floor=0.0)


# --------------------------------------------------------------------------- #
# SUSTAINED spoof -> flagged within K windows, bounded latency
# --------------------------------------------------------------------------- #

def test_sustained_inflation_is_flagged_within_bound():
    """A sender inflating `entered` every window persistently flags `inflated`.

    Each window claims +8 extra entries that never appear downstream and are not
    in storage -> a steady positive residual ~ one band. The CUSUM accumulates
    and flags within the documented worst-case window count.
    """
    det = FlowConservationDetector()
    # entered inflated by 8 over true exited=10; storage steady (no real cars
    # held), so residual ~ +8 each window, band ~ 2 + 0.15*18 + sqrt(4) ~ 6.7.
    spoof = EdgeMeasurement("A->B", entered=18, exited=10,
                            storage_now=4, storage_prev=4)
    verdicts = _run_stream(det, [spoof for _ in range(20)])
    flag = _first_flag(verdicts)
    assert flag is not None, "a sustained over-claim MUST flag"
    assert flag.reason == "inflated"
    assert flag.residual > 0
    # Latency is bounded and reported (windows from drift start to the flag).
    assert 1 <= flag.latency_windows <= det.cusum_params.windows_to_flag_sustained + 1


def test_sustained_underreport_is_flagged_under_reported():
    """A faulty sender under-reporting `entered` persistently flags under_reported."""
    det = FlowConservationDetector()
    # Truth ~18 exit downstream but sender claims only 6 entered; storage steady.
    fault = EdgeMeasurement("A->B", entered=6, exited=18,
                            storage_now=4, storage_prev=4)
    verdicts = _run_stream(det, [fault for _ in range(20)])
    flag = _first_flag(verdicts)
    assert flag is not None
    assert flag.reason == "under_reported"
    assert flag.residual < 0


def test_documented_sustained_latency_matches_param():
    """The worst-case windows-to-flag derived from (h, slack) is the documented 6."""
    p = CusumParams(slack=0.5, h=3.0)
    assert p.windows_to_flag_sustained == 6


# --------------------------------------------------------------------------- #
# TRANSIENT blip -> NOT flagged (persistence works)
# --------------------------------------------------------------------------- #

def test_single_transient_blip_does_not_flag():
    """One window with a large residual, then benign, must NOT flag.

    The CUSUM adds (z - slack) once, then the benign windows subtract slack each
    step and the sum decays to zero. A lone spike cannot reach h on its own.
    """
    det = FlowConservationDetector()
    stream = [_balanced() for _ in range(6)]
    # one large blip: claim 40 extra that vanish
    stream.append(EdgeMeasurement("A->B", entered=50, exited=10,
                                  storage_now=4, storage_prev=4))
    stream += [_balanced() for _ in range(15)]
    verdicts = _run_stream(det, stream)
    assert not any(v.flagged for v in verdicts), \
        "a single transient blip must not flag (persistence rule)"
    # The CUSUM must have decayed back to rest after the blip.
    assert det.state_of("A->B").s_hi == 0.0
    assert det.state_of("A->B").s_lo == 0.0


def test_two_blips_far_apart_do_not_accumulate():
    """Spikes separated by enough benign windows decay between them -> no flag."""
    det = FlowConservationDetector()
    blip = EdgeMeasurement("A->B", entered=40, exited=10,
                           storage_now=4, storage_prev=4)
    stream = ([_balanced() for _ in range(5)] + [blip]
              + [_balanced() for _ in range(10)] + [blip]
              + [_balanced() for _ in range(10)])
    verdicts = _run_stream(det, stream)
    assert not any(v.flagged for v in verdicts)


# --------------------------------------------------------------------------- #
# SPILLBACK / congestion -> NOT flagged as attack
# --------------------------------------------------------------------------- #

def test_spillback_high_storage_low_outflow_not_flagged():
    """A jammed edge (full, crawling, throttled outflow) is spillback, not attack.

    Many cars on the edge, almost none exiting (downstream blocked), storage
    swinging -- a flat detector would scream `under_reported` forever. Ours
    classifies it `spillback` and never feeds the CUSUM.
    """
    det = FlowConservationDetector()
    jam = EdgeMeasurement("A->B", entered=2, exited=0, storage_now=40,
                          storage_prev=38, occupancy=0.9, mean_speed=0.4,
                          free_speed=13.9)
    verdicts = _run_stream(det, [jam for _ in range(30)])
    assert all(v.status == "spillback" for v in verdicts), \
        [v.status for v in verdicts[:5]]
    assert not any(v.flagged for v in verdicts)
    # CUSUM never accumulated during the jam.
    assert det.state_of("A->B").s_hi == 0.0
    assert det.state_of("A->B").s_lo == 0.0


def test_dense_but_flowing_edge_is_not_spillback():
    """High occupancy at near-free speed is heavy traffic, NOT a jam.

    With a known free_speed, spillback requires the edge to be CRAWLING; a dense
    edge moving near free speed is reconciled normally (so a real spoof on a busy
    arterial is still catchable).
    """
    det = FlowConservationDetector(cusum=CusumParams(warmup_windows=0))
    v = det.update(EdgeMeasurement("A->B", entered=20, exited=20, storage_now=30,
                                   storage_prev=30, occupancy=0.7,
                                   mean_speed=12.0, free_speed=13.9))
    assert v.status != "spillback"


# --------------------------------------------------------------------------- #
# LOW / ZERO flow -> no spurious flag, no divide-by-zero
# --------------------------------------------------------------------------- #

def test_zero_flow_idle_edge_never_flags():
    """A perpetually idle edge accumulates nothing and never flags."""
    det = FlowConservationDetector()
    verdicts = _run_stream(det, [
        EdgeMeasurement("A->B", entered=0, exited=0, storage_now=0)
        for _ in range(50)])
    assert not any(v.flagged for v in verdicts)
    assert all(v.band > 0 for v in verdicts)  # no divide-by-zero


def test_low_flow_tiny_diff_does_not_flag():
    """A 1-vehicle jitter on a near-idle edge stays inside the floor band."""
    det = FlowConservationDetector()
    # alternate +1 / -1 residual: well inside abs_floor=2, sums decay.
    stream = []
    for i in range(40):
        e, x = (1, 0) if i % 2 == 0 else (0, 1)
        stream.append(EdgeMeasurement("A->B", entered=e, exited=x,
                                      storage_now=0, storage_prev=0))
    verdicts = _run_stream(det, stream)
    assert not any(v.flagged for v in verdicts)


# --------------------------------------------------------------------------- #
# SENSOR DROPOUT / missing window -> missing_data, not attack; CUSUM holds
# --------------------------------------------------------------------------- #

def test_missing_window_is_classified_missing_data():
    det = FlowConservationDetector()
    v = det.update(_balanced(), missing=True)
    assert v.status == "missing_data"
    assert v.reason == "missing_data"
    assert not v.flagged


def test_dropout_holds_cusum_and_never_flags():
    """A run of missing windows neither accumulates nor erases evidence.

    We build up some CUSUM with sustained inflation, interleave a long dropout,
    and confirm the dropout windows are missing_data (no flag) and the state is
    preserved across the gap (sums unchanged by the gap itself).
    """
    det = FlowConservationDetector()
    spoof = EdgeMeasurement("A->B", entered=18, exited=10,
                            storage_now=4, storage_prev=4)
    # prime a little drift without flagging yet (warmup + 2 real windows)
    for _ in range(det.cusum_params.warmup_windows + 2):
        det.update(spoof)
    s_hi_before = det.state_of("A->B").s_hi
    # long dropout
    for _ in range(10):
        v = det.update(spoof, missing=True)
        assert v.status == "missing_data" and not v.flagged
    assert det.state_of("A->B").s_hi == s_hi_before, "dropout must HOLD the CUSUM"


def test_dropout_does_not_break_eventual_detection():
    """After a dropout gap, sustained spoof still flags (evidence preserved)."""
    det = FlowConservationDetector()
    spoof = EdgeMeasurement("A->B", entered=18, exited=10,
                            storage_now=4, storage_prev=4)
    seen_flag = False
    for i in range(30):
        v = det.update(spoof, missing=(5 <= i < 10))
        if v.flagged:
            seen_flag = True
    assert seen_flag


# --------------------------------------------------------------------------- #
# TURNING / multi-downstream: per-edge independent state
# --------------------------------------------------------------------------- #

def test_multi_downstream_edges_are_independent():
    """A spoof on one downstream edge does not flag a benign sibling edge."""
    det = FlowConservationDetector()
    spoof = EdgeMeasurement("A->B", entered=18, exited=10,
                            storage_now=4, storage_prev=4)
    benign = _balanced(edge="A->C")
    flagged_edges = set()
    for _ in range(20):
        for m in (spoof, benign):
            v = det.update(m)
            if v.flagged:
                flagged_edges.add(v.edge_id)
    assert "A->B" in flagged_edges
    assert "A->C" not in flagged_edges


def test_update_many_is_deterministic_and_sorted():
    det = FlowConservationDetector()
    ms = {"B->A": _balanced(edge="B->A"), "A->B": _balanced(edge="A->B")}
    verdicts = det.update_many(ms)
    assert [v.edge_id for v in verdicts] == ["A->B", "B->A"]  # sorted


# --------------------------------------------------------------------------- #
# Boundary validation (explicit errors, never swallowed)
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("kw", [
    {"entered": -1}, {"exited": -1}, {"storage_now": -1},
    {"entered": 1.5}, {"entered": True}, {"occupancy": 1.5},
    {"mean_speed": -1.0}, {"edge_id": ""},
])
def test_measurement_rejects_bad_input(kw):
    base = dict(edge_id="A->B", entered=1, exited=1, storage_now=1)
    base.update(kw)
    with pytest.raises((TypeError, ValueError)):
        EdgeMeasurement(**base)


def test_detector_rejects_non_measurement():
    det = FlowConservationDetector()
    with pytest.raises(TypeError):
        det.update("not a measurement")  # type: ignore[arg-type]


def test_cusum_params_validate():
    with pytest.raises(ValueError):
        CusumParams(h=0.0)
    with pytest.raises(ValueError):
        CusumParams(spillback_occupancy=2.0)


def test_states_view_is_read_only():
    det = FlowConservationDetector()
    det.update(_balanced())
    states = det.states()
    with pytest.raises(TypeError):
        states["A->B"] = None  # type: ignore[index]


# --------------------------------------------------------------------------- #
# LIVE-STYLE: benign multi-seed run -> ~0 false positives (headline property)
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def _live():
    """Import the live runner + StubAgent, skipping cleanly without SUMO/traci."""
    try:
        import run_coordinated as rc
        from coordinated_controller import StubAgent
    except Exception as exc:  # pragma: no cover - environment-dependent
        pytest.skip(f"live runner unavailable: {exc}")
    return rc, StubAgent


@pytest.mark.parametrize("seed", [1, 7, 13, 42, 99])
def test_benign_live_run_has_zero_false_positives(_live, seed):
    """Genuine coordinated controller over real SUMO, windowed feed, benign demand.

    The intelligent detector must raise ~0 flags on honest flow. We assert ZERO
    flagged detections per seed (the headline Part-A false-positive property),
    across several seeds so it is not a single-seed fluke.
    """
    rc, StubAgent = _live
    metrics = rc.run(mode="coordinated", agent=StubAgent(), seed=seed,
                     end=600, coord_weight=1.0, flow_window=30.0)
    assert metrics["flagged_detections"] == 0, \
        f"seed {seed}: benign run flagged {metrics['flagged_detections']} (expected 0)"
    # Sanity: the windowed path actually ran reconciliations (not a no-op pass).
    assert metrics["detections"] > 0


# --------------------------------------------------------------------------- #
# WINDOWED-PATH ATTACK PROOF: a sustained inflated claim through the genuine
# CoordinatedController._windowed_reconcile flags within K windows, while the
# benign honest claim on the same path never flags. No SUMO -- a deterministic
# in-memory conn that drives step() (flow window) and decide() (reconcile).
# --------------------------------------------------------------------------- #

class _WindowedFakeConn:
    """Minimal in-memory conn exercising the windowed detector end-to-end.

    Recipient A0; in-edge A1->A0 carries the reconciled claim from A1. Each
    simulated step advances a clock; `on_edge` is the set of real vehicle ids
    currently on edge A1A0 (the honest flow). The malicious publisher injects an
    INFLATED `release` claim that exceeds the real flow, so entered (claim) >>
    exited, a sustained positive residual the CUSUM must catch.
    """

    def __init__(self, on_edge_per_step):
        self._on_edge_per_step = on_edge_per_step
        self._t = 0
        self._cur_on_edge = frozenset()
        self.simulation = self._Sim(self)
        self.edge = self._Edge(self)
        self.lane = self._Lane(self)
        self.trafficlight = self._TL()

    def advance(self):
        self._cur_on_edge = frozenset(
            self._on_edge_per_step(self._t))
        self._t += 1

    class _Sim:
        def __init__(self, c): self._c = c
        def getTime(self): return float(self._c._t)

    class _Edge:
        def __init__(self, c): self._c = c
        def getLastStepVehicleIDs(self, eid):
            return tuple(self._c._cur_on_edge) if eid == "A1A0" else ()
        def getLastStepOccupancy(self, eid): return 5.0   # light, not spillback
        def getLastStepMeanSpeed(self, eid): return 12.0  # near free speed

    class _Lane:
        def __init__(self, c): self._c = c
        def getLastStepHaltingNumber(self, lane_id): return 1
        def getMaxSpeed(self, lane_id): return 13.9

    class _TL:
        class _Phase:
            def __init__(self, state): self.state = state
        class _Logic:
            def __init__(self, phases): self.phases = phases
        def __init__(self):
            self._phases = [self._Phase("Gr"), self._Phase("yr"),
                            self._Phase("rG"), self._Phase("ry")]
            self._links = [[("A1A0_0", "A0A1_0", "")],
                           [("B0A0_0", "A0B0_0", "")]]
        def getAllProgramLogics(self, tl): return [self._Logic(self._phases)]
        def getControlledLinks(self, tl): return self._links
        def setRedYellowGreenState(self, tl, state): return None
        def setParameter(self, tl, k, v): return None


def _build_windowed(on_edge_per_step):
    from conservation import ConservationChecker
    from coordinated_controller import CoordinatedController, StubAgent
    from identity import JunctionIdentity
    from message_bus import MessageBus
    from registry import Registry

    adjacency = {"A0": ["A1", "B0"], "A1": ["A0", "B1"],
                 "B0": ["A0", "B1"], "B1": ["A1", "B0"]}
    tls = ["A0", "A1", "B0", "B1"]
    conn = _WindowedFakeConn(on_edge_per_step)
    identities = {jid: JunctionIdentity(jid) for jid in tls}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, adjacency)
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=adjacency, checker=ConservationChecker(),
        slm_junctions=["A0"], gate=0, coord_weight=0.0, flow_window=30.0)
    return ctrl, conn, bus, identities


def test_windowed_sustained_spoof_is_flagged_live():
    """Through the genuine windowed decide() path, a sustained inflated claim
    flags `inflated` within a bounded number of decision windows."""
    try:
        from attacks import MaliciousPublisher
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"attacks unavailable: {exc}")

    # A small honest flow on A1->A0: a couple of cars rotating through.
    def honest_flow(t):
        return {f"v{(t // 3)}"} if t % 6 < 3 else set()

    ctrl, conn, bus, identities = _build_windowed(honest_flow)
    pub = MaliciousPublisher(bus)
    flagged_window = None
    for tick in range(40):
        conn.advance()
        ctrl.step()
        # Inject a grossly inflated claim from A1 toward A0 every decision tick.
        pub.publish_toward(identities["A1"], "A0", tick, release=60)
        ctrl.decide("A0", ctrl.tls["A0"])
        if any(d.flagged and (d.src, d.dst) == ("A1", "A0")
               for d in ctrl.detections):
            flagged_window = tick
            break
    assert flagged_window is not None, \
        "a sustained inflated claim must flag through the live windowed path"
    flag = next(d for d in ctrl.detections
                if d.flagged and (d.src, d.dst) == ("A1", "A0"))
    assert flag.reason == "inflated"


def test_windowed_honest_claim_never_flags_live():
    """The same live path with an HONEST claim (matching the real flow) never
    flags -- the windowed false-positive guarantee end-to-end."""
    try:
        from attacks import MaliciousPublisher
    except Exception as exc:  # pragma: no cover
        pytest.skip(f"attacks unavailable: {exc}")

    def honest_flow(t):
        return {f"v{(t // 3)}"} if t % 6 < 3 else set()

    ctrl, conn, bus, identities = _build_windowed(honest_flow)
    pub = MaliciousPublisher(bus)
    for tick in range(40):
        conn.advance()
        ctrl.step()
        # Honest: claim exactly the windowed release A1 actually measures.
        true_release = ctrl._flow.released_in_window("A1A0", float(conn._t))
        pub.publish_toward(identities["A1"], "A0", tick, release=true_release)
        ctrl.decide("A0", ctrl.tls["A0"])
    assert not any(d.flagged and (d.src, d.dst) == ("A1", "A0")
                   for d in ctrl.detections), \
        "an honest windowed claim must never flag"
