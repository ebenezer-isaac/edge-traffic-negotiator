"""Anti-starvation mechanism on ``MaxPressureController.step`` (spec §6.8 / §11
step 5 / D7), driven against the PINNED read-only oracle ``fixtures/forced_skip.json``.

The fixture (blob d1d3b432, hash-pinned by §10) is the sole source of truth for the
expected service schedules. This test LOADS it (ignoring '_'-prefixed doc keys),
builds a deterministic 2-phase diagonal ('Gr'/'rG') FakeConn where position==phase,
drives each scenario at the fixture's decision-interval model, and asserts the pinned
expectations. ``anti_starvation_violations`` is READ, never assigned (D7).

Discrimination (why a wrong mechanism fails):
  * S1  -- constant single-starve: a no-override controller never serves phase1.
  * S2  -- alternating/reset-on-win: phase1 wins on PRESSURE at interval 2 (a reset,
           not an override) and phase0 is FORCED later; a global/modulo timer that
           does not track WHICH phase starves (nor reset it on a pressure win)
           produces a DIFFERENT served schedule -> the exact-equality check fails.
  * negative_control -- toggles ONLY ``anti_starvation_enabled=False`` on the same
           S1 code path: phase1 never served AND violations>0, isolating the override.
  * over-eager max_skip=2 forces phase1 a full interval early -> schedule diverges,
           proving the pinned max_skip=3 is load-bearing.

No SUMO / Foundry / anchor dependency.
"""
import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.join(os.path.dirname(_HERE), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from controllers import MaxPressureController  # noqa: E402

_FIXTURE = os.path.join(os.path.dirname(_HERE), "fixtures", "forced_skip.json")


# --------------------------------------------------------------------------- #
# Fixture loading (read-only; loader ignores keys beginning with '_').
# --------------------------------------------------------------------------- #

def _strip_underscored(obj):
    """Recursively drop dict keys beginning with '_' (fixture doc/annotation keys)."""
    if isinstance(obj, dict):
        return {k: _strip_underscored(v) for k, v in obj.items()
                if not k.startswith("_")}
    if isinstance(obj, list):
        return [_strip_underscored(v) for v in obj]
    return obj


def _load_fixture():
    with open(_FIXTURE, encoding="utf-8") as f:
        return _strip_underscored(json.load(f))


FIX = _load_fixture()
COMMON = FIX["common"]
SCENARIOS = {s["id"]: s for s in FIX["scenarios"]}
HORIZON = 10  # decision intervals 0..9 (interval 0 = ctor's initial green)


# --------------------------------------------------------------------------- #
# Deterministic 2-phase diagonal FakeConn (position == phase), mutable halting.
# --------------------------------------------------------------------------- #

class _FakeLane:
    def __init__(self, halting: dict):
        self.halting = dict(halting)  # replaced wholesale per interval

    def getLastStepHaltingNumber(self, lane_id):
        if lane_id not in self.halting:
            raise KeyError(lane_id)  # mimics SUMO raising on an unknown lane
        return self.halting[lane_id]


class _FakeTL:
    class _Phase:
        def __init__(self, state):
            self.state = state

    class _Logic:
        def __init__(self, phases):
            self.phases = phases

    def __init__(self, common: dict):
        gp = {g["idx"]: g for g in common["green_phases"]}
        # 2-phase diagonal program: green0, yellow0, green1, yellow1. The green
        # cell 'G' of phase p sits at controlled-link position p (position==phase).
        self._phases = [
            self._Phase(gp[0]["state"]),  # "Gr"
            self._Phase("yr"),            # clears phase 0
            self._Phase(gp[1]["state"]),  # "rG"
            self._Phase("ry"),            # clears phase 1
        ]
        self._links = [
            [(gp[0]["in_lane"], gp[0]["out_lane"], "")],  # pos 0: LA -> LAo
            [(gp[1]["in_lane"], gp[1]["out_lane"], "")],  # pos 1: LB -> LBo
        ]

    def getAllProgramLogics(self, tl):
        return [self._Logic(self._phases)]

    def getControlledLinks(self, tl):
        return self._links

    def setRedYellowGreenState(self, tl, state):
        return None


class _FakeConn:
    def __init__(self, common: dict, halting: dict):
        self.lane = _FakeLane(halting)
        self.trafficlight = _FakeTL(common)


# --------------------------------------------------------------------------- #
# Interval-model driver.
# --------------------------------------------------------------------------- #

def _halting_for(scenario: dict, interval: int) -> dict:
    """Per-interval halting: a constant map, or the per-interval schedule."""
    if "halting_constant" in scenario:
        return dict(scenario["halting_constant"])
    return dict(scenario["halting_schedule"][interval])


def _yellow_runs(modes):
    """Lengths of every maximal run of 'yellow' mode across the driven trace."""
    runs, cur = [], 0
    for m in modes:
        if m == "yellow":
            cur += 1
        elif cur:
            runs.append(cur)
            cur = 0
    if cur:
        runs.append(cur)
    return runs


def _drive(scenario: dict, *, enabled: bool = True, max_skip=None, horizon=HORIZON):
    """Drive the controller through the fixture's interval model.

    Interval 0 is the ctor's initial green (phase 0), served BEFORE any decide().
    Intervals 1..N are successive boundary decisions. For each such interval the
    scenario's halting is installed just before the decision step (so ``_pressure``
    reads the intended values at the decision moment), and the served phase index +
    a switched-flag are recorded. Returns (ctrl, served, switched, modes)."""
    tl = COMMON["tls"]
    min_green = COMMON["min_green"]
    ms = COMMON["max_skip"] if max_skip is None else max_skip
    conn = _FakeConn(COMMON, _halting_for(scenario, 0))
    ctrl = MaxPressureController(
        conn, [tl], min_green=min_green, yellow=COMMON["yellow"],
        max_skip=ms, anti_starvation_enabled=enabled,
    )
    st = ctrl.tls[tl]
    served = [st["cur"]]     # interval 0 = ctor's initial phase (phase 0)
    switched = [False]
    modes = []
    interval = 1
    guard = 0
    while len(served) < horizon and guard < 100000:
        guard += 1
        # A decision fires this step iff green and t is one short of min_green
        # (step() does t += 1 then tests t >= min_green).
        pre_decision = (st["mode"] == "green" and st["t"] == min_green - 1)
        cur_before = st["cur"]
        if pre_decision:
            conn.lane.halting = _halting_for(scenario, interval)
        ctrl.step()
        modes.append(st["mode"])
        if pre_decision:
            served.append(st["cur"])
            switched.append(st["cur"] != cur_before)
            interval += 1
    assert len(served) == horizon, f"driver stalled: {served}"
    # Flush a trailing yellow clearance (a final-interval switch) so the safe-
    # transition check sees the FULL yellow run, not a horizon-truncated one.
    while st["mode"] == "yellow":
        ctrl.step()
        modes.append(st["mode"])
    return ctrl, served, switched, modes


def _assert_safe_transitions(ctrl, switched, modes):
    """Every forced/normal phase switch clears through EXACTLY one yellow of
    length `yellow`; no mid-green interrupt. One yellow run per switch."""
    runs = _yellow_runs(modes)
    assert all(r == ctrl.yellow for r in runs), runs
    assert len(runs) == sum(switched), (runs, switched)


# --------------------------------------------------------------------------- #
# A. / B. S1 constant single-starve -> phase1 forced at [3, 7].
# --------------------------------------------------------------------------- #

def test_s1_single_starve_forced_at_pinned_cadence():
    sc = SCENARIOS["S1_single_starve"]
    exp = sc["expected"]
    ctrl, served, switched, modes = _drive(sc)

    assert served == exp["served_by_interval"] == [0, 0, 0, 1, 0, 0, 0, 1, 0, 0]
    # The starved approach (phase 1) is force-served EXACTLY at [3, 7].
    p1 = [i for i, s in enumerate(served) if s == 1]
    assert p1 == exp["phase1_service_intervals"] == [3, 7]
    assert [i for i, s in enumerate(served) if s == 0] == exp["phase0_service_intervals"]
    # Violations EMERGE 0 from the correct mechanism (read, never assigned).
    assert ctrl.anti_starvation_violations == exp["anti_starvation_violations"] == 0
    _assert_safe_transitions(ctrl, switched, modes)


def test_s1_starved_phase_never_wins_pressure():
    """Establishes the starvation has teeth: with the override DISABLED (pure
    argmax) phase1 (pressure 1 vs 9, never served at init) is NEVER served."""
    sc = SCENARIOS["S1_single_starve"]
    _ctrl, served, _sw, _m = _drive(sc, enabled=False)
    assert sc["expected"]["starved_phase"] == 1
    assert 1 not in served, served


# --------------------------------------------------------------------------- #
# C. / F. S2 alternating / reset-on-win -> per-phase counter, NOT a timer.
# --------------------------------------------------------------------------- #

def test_s2_reset_on_win_discriminates_counter_from_timer():
    sc = SCENARIOS["S2_alternating_reset"]
    exp = sc["expected"]
    ctrl, served, switched, modes = _drive(sc)

    # Exact schedule: phase1 wins on PRESSURE from interval 2 (reset-on-win), then
    # phase0 starves and is FORCED at [5, 9]. A global/modulo timer or a single
    # global counter (not tracking WHICH phase starves, not reset by a pressure win)
    # cannot reproduce this exact sequence -> this equality is the discriminator.
    assert served == exp["served_by_interval"] == [0, 0, 1, 1, 1, 0, 1, 1, 1, 0]
    # Interval 2 is a reset-on-win, NOT an override: phase1's skip is only 2 there.
    assert served[exp["reset_on_win_interval"]] == 1
    assert [i for i, s in enumerate(served) if s == 0] == exp["phase0_service_intervals"]
    assert [i for i, s in enumerate(served) if s == 1] == exp["phase1_service_intervals"]
    assert ctrl.anti_starvation_violations == exp["anti_starvation_violations"] == 0
    _assert_safe_transitions(ctrl, switched, modes)


# --------------------------------------------------------------------------- #
# D. negative_control -> the override, isolated by ONE flag.
# --------------------------------------------------------------------------- #

def test_negative_control_isolates_override():
    sc = SCENARIOS["negative_control"]
    base = SCENARIOS[sc["base"]]              # S1_single_starve
    mut = sc["expected_under_mutant"]

    # Mutant: toggle ONLY anti_starvation_enabled=False; identical code path.
    ctrl_mut, served_mut, _sw, _m = _drive(base, enabled=False)
    assert mut["phase1_ever_served"] is False
    assert served_mut.count(1) == 0, served_mut
    # The counter is a LIVE signal, not 0-for-free.
    assert ctrl_mut.anti_starvation_violations >= mut["anti_starvation_violations_min"]
    assert ctrl_mut.anti_starvation_violations >= 1

    # Correct mechanism (only difference: the flag) -> violations 0 AND phase1 served.
    ctrl_ok, served_ok, _sw2, _m2 = _drive(base, enabled=True)
    assert ctrl_ok.anti_starvation_violations == \
        sc["expected_under_correct_mechanism"]["anti_starvation_violations"] == 0
    assert 1 in served_ok


# --------------------------------------------------------------------------- #
# E. / over-eager max_skip -> the pinned max_skip=3 is load-bearing.
# --------------------------------------------------------------------------- #

def test_over_eager_max_skip_two_diverges_from_pinned():
    """An over-eager max_skip=2 forces phase1 at interval 2 instead of 3 -> the
    served schedule diverges from the pinned oracle, so a mechanism that hard-codes
    the wrong threshold cannot pass the S1 check."""
    sc = SCENARIOS["S1_single_starve"]
    assert COMMON["max_skip"] == 3  # the pinned threshold
    _ctrl_ok, served_ok, _s, _m = _drive(sc)  # max_skip=3 from fixture
    assert served_ok == sc["expected"]["served_by_interval"]

    _ctrl2, served2, _s2, _m2 = _drive(sc, max_skip=2)
    assert served2 != sc["expected"]["served_by_interval"], served2
    # Concretely: phase1 forced one interval early.
    assert served2[2] == 1 and sc["expected"]["served_by_interval"][2] == 0


def test_violations_counter_is_read_only_signal():
    """D7: the counter EMERGES from the mechanism. Fresh controller starts at 0;
    after driving S1 with the override on it stays 0 (never assigned by the test)."""
    conn = _FakeConn(COMMON, _halting_for(SCENARIOS["S1_single_starve"], 0))
    ctrl = MaxPressureController(conn, [COMMON["tls"]], min_green=COMMON["min_green"],
                                 yellow=COMMON["yellow"], max_skip=COMMON["max_skip"])
    assert ctrl.anti_starvation_violations == 0
    _c, _served, _sw, _m = _drive(SCENARIOS["S1_single_starve"])
    assert _c.anti_starvation_violations == 0
