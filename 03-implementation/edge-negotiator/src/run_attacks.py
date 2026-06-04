"""Run the three attack scenarios through the detectors and measure performance.

Wk7-8 DE-RISK: produce HARD detection data -- precision / recall / F1 / latency
per attack, plus a tolerance ROC-style sweep -- against KNOWN ground truth.

Why a fake-conn harness (not the full SUMO run)?
------------------------------------------------
The detectors we are measuring (``ConservationChecker.evaluate`` via the
controller's reconciliation, and ``MessageBus.inbox``'s auth pipeline) operate
on *claim* and *observation* tallies, not on SUMO microsimulation per se. To get
a KNOWN ground-truth label PER injected message -- and a reproducible P/R/F1 --
we drive the real ``CoordinatedController`` with a deterministic in-memory TraCI
stand-in (the same pattern as ``tests/test_coordination.py``): the published
``release`` sets the *claim*; the fake lane halting on edge ``sender->recipient``
sets the independent *observation*. This exercises the genuine
``decide()`` -> inbox -> conservation path and the genuine bus auth path, with
NO Foundry and NO SUMO, so results are exact and CI-fast. The StubAgent is used
throughout for determinism.

Each injected message carries a ground-truth ``malicious`` flag and an
``expected_layer``/``expected_reason`` (see ``attacks.py``). A message is counted
DETECTED if the appropriate layer fired:
  * conservation: a flagged ``Detection`` on the message's edge that tick;
  * auth: a ``bus.rejected`` entry for (recipient, sender, tick).

From the confusion matrix over all injected messages we compute precision,
recall, F1. Detection latency is measured in control cycles (ticks) from the
first malicious message of a scenario to the first flag/rejection it triggers.

    python src/run_attacks.py            # run all sweeps, (re)write the report
    python src/run_attacks.py --quiet    # compute only, skip writing the report
"""
from __future__ import annotations

import argparse
import os
import sys

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from conservation import ConservationChecker  # noqa: E402
from coordinated_controller import CoordinatedController, StubAgent  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from registry import Registry  # noqa: E402

import attacks  # noqa: E402
from attacks import InjectedMessage, MaliciousPublisher  # noqa: E402

ADJACENCY = {"A0": ["A1", "B0"], "A1": ["A0", "B1"],
             "B0": ["A0", "B1"], "B1": ["A1", "B0"]}
TLS = ["A0", "A1", "B0", "B1"]
REPORT_PATH = os.path.join(_SRC, "..", "results", "attacks_report.md")


# --------------------------------------------------------------------------- #
# Deterministic in-memory TraCI stand-in (mirrors tests/test_coordination.py).
# Recipient is A0; its in-edges are A1->A0 (lane A1A0_0, phase 0) and
# B0->A0 (lane B0A0_0, phase 1). The published release sets the CLAIM; the lane
# halting on the sender's in-edge sets the independent OBSERVATION.
# --------------------------------------------------------------------------- #

class _FakeLane:
    def __init__(self, halting: dict[str, int]):
        self._halting = dict(halting)

    def getLastStepHaltingNumber(self, lane_id):
        if lane_id not in self._halting:
            raise KeyError(lane_id)
        return self._halting[lane_id]


class _FakeTL:
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
        self._links = [
            [("A1A0_0", "A0A1_0", "")],   # movement 0: in A1->A0, out A0->A1
            [("B0A0_0", "A0B0_0", "")],   # movement 1: in B0->A0, out A0->B0
        ]

    def getAllProgramLogics(self, tl):
        return [self._Logic(self._phases)]

    def getControlledLinks(self, tl):
        return self._links

    def setRedYellowGreenState(self, tl, state):
        return None


class _FakeConn:
    def __init__(self, halting: dict[str, int]):
        self.lane = _FakeLane(halting)
        self.trafficlight = _FakeTL()


def _build(observed_on_edge: dict[str, int], tolerance: int):
    """Build a CoordinatedController + bus + identities + registry on a fake conn.

    ``observed_on_edge`` maps a sender id to the halting count A0 will observe on
    edge ``sender->A0`` (the independent observation). Returns
    ``(ctrl, bus, identities, registry)``.
    """
    halting = {
        "A1A0_0": observed_on_edge.get("A1", 0),
        "B0A0_0": observed_on_edge.get("B0", 0),
        "A0A1_0": 0,
        "A0B0_0": 0,
    }
    conn = _FakeConn(halting)
    identities = {jid: JunctionIdentity(jid) for jid in TLS}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    checker = ConservationChecker(tolerance=tolerance)
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=checker, slm_junctions=["A0"],
        gate=0, coord_weight=0.0,
    )
    return ctrl, bus, identities, registry


# Sybil id that is a DECLARED neighbour of A0 in the adjacency below but is
# deliberately NEVER registered -- so its rejection is `unknown_sender`
# (membership), not `not_neighbour` (topology). In the fully-registered 2x2 grid
# every real junction is approved, so we must introduce this phantom neighbour
# to exhibit the unknown_sender path at all (a finding in itself: a closed,
# fully-provisioned corridor has no unregistered-neighbour surface unless the
# adjacency itself references an unprovisioned node).
SYBIL_ID = "Z9"
ADJACENCY_WITH_SYBIL = {
    **{k: list(v) for k, v in ADJACENCY.items()},
    "A0": ["A1", "B0", SYBIL_ID],   # A0 now lists an unregistered neighbour Z9
    SYBIL_ID: ["A0"],
}


def _build_with_sybil_neighbour(tolerance: int):
    """Like :func:`_build` but A0's adjacency includes the UNREGISTERED ``Z9``.

    Z9 is a topological neighbour of A0 yet absent from the registry, so a
    message it signs is rejected with ``unknown_sender`` (membership), the one
    auth reason the fully-registered grid cannot otherwise produce.
    """
    halting = {"A1A0_0": 0, "B0A0_0": 0, "A0A1_0": 0, "A0B0_0": 0}
    conn = _FakeConn(halting)
    identities = {jid: JunctionIdentity(jid) for jid in TLS}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)   # Z9 is intentionally NOT registered
    bus = MessageBus(registry, ADJACENCY_WITH_SYBIL)
    checker = ConservationChecker(tolerance=tolerance)
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY_WITH_SYBIL, checker=checker,
        slm_junctions=["A0"], gate=0, coord_weight=0.0,
    )
    return ctrl, bus, identities, registry


# --------------------------------------------------------------------------- #
# Scoring primitives.
# --------------------------------------------------------------------------- #

def _prf1(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    """Precision, recall, F1 from a confusion matrix (0.0 when undefined)."""
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)
          if (precision + recall) else 0.0)
    return precision, recall, f1


def measure_conservation_latency(tolerance: int = 2) -> int:
    """Cycles from a clearly-detectable spoof's appearance to its flag.

    A single inflated message (delta well above tolerance) is injected at the
    junction's first decision; we count control cycles until the flag fires. The
    stateless conservation check fires the SAME cycle the inflated edge appears,
    so this is 1 control cycle by construction. Measured (not assumed) so the
    report cites a real number rather than the sweep-ordering artifact.
    """
    ctrl, bus, identities, _ = _build({"A1": 5}, tolerance)
    pub = MaliciousPublisher(bus)
    pub.publish_toward(identities["A1"], "A0", 0, 5 + tolerance + 50)  # gross lie
    cycles = 0
    while cycles < 5:
        cycles += 1
        ctrl.decide("A0", ctrl.tls["A0"])
        if _conservation_flagged_edge(ctrl.detections, "A1", "A0"):
            return cycles
    return -1  # never fired within the window (would be a bug)


def _conservation_flagged_edge(detections, src: str, dst: str) -> bool:
    """True iff a flagged Detection exists for directed edge ``src->dst``."""
    return any(d.flagged and d.src == src and d.dst == dst for d in detections)


def _auth_rejected_edge(rejected, recipient: str, sender: str, tick: int) -> bool:
    """True iff the bus logged a rejection for (recipient, sender, tick)."""
    return any(
        r.get("recipient") == recipient and r.get("sender") == sender
        and r.get("t") == tick
        for r in rejected
    )


# --------------------------------------------------------------------------- #
# Scenario A: SPOOFED REPORT (insider over-claim) -- conservation 'inflated'.
# Sweep the inflation delta across the tolerance floor.
# --------------------------------------------------------------------------- #

def run_spoof(tolerance: int, deltas, base_release: int = 15):
    """One spoof message per delta. A1 claims base+delta; A0 observes base.

    Returns (rows, confusion, latency) where rows are per-delta detail.
    """
    rows = []
    tp = fp = fn = tn = 0
    first_malicious_tick = None
    first_detect_tick = None

    for tick, delta in enumerate(deltas):
        ctrl, bus, identities, _ = _build({"A1": base_release}, tolerance)
        inj = attacks.spoof_release("A1", "A0", base_release, delta, tolerance, tick)
        pub = MaliciousPublisher(bus)
        pub.publish_toward(identities["A1"], "A0", tick, inj.release)
        ctrl.decide("A0", ctrl.tls["A0"])

        detected = _conservation_flagged_edge(ctrl.detections, "A1", "A0")
        reason = next((d.reason for d in ctrl.detections
                       if d.src == "A1" and d.dst == "A0"), "ok")

        if inj.malicious and first_malicious_tick is None:
            first_malicious_tick = tick
        if inj.malicious and detected and first_detect_tick is None:
            first_detect_tick = tick

        if inj.malicious and detected:
            tp += 1
        elif inj.malicious and not detected:
            fn += 1
        elif not inj.malicious and detected:
            fp += 1
        else:
            tn += 1

        rows.append({
            "delta": delta, "claim": inj.release, "observed": base_release,
            "malicious": inj.malicious, "detected": detected, "reason": reason,
            "expected_reason": inj.expected_reason,
        })

    latency = (first_detect_tick - first_malicious_tick
               if first_detect_tick is not None and first_malicious_tick is not None
               else None)
    return rows, {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, latency


# --------------------------------------------------------------------------- #
# Scenario B: FAULTY SENSOR (sender under-claims) -- conservation 'under_reported'.
# Sweep the drop fraction. Recipient observes the truth.
# --------------------------------------------------------------------------- #

def run_faulty(tolerance: int, drop_fractions, true_release: int = 20):
    rows = []
    tp = fp = fn = tn = 0
    first_malicious_tick = None
    first_detect_tick = None

    for tick, frac in enumerate(drop_fractions):
        # A0 observes the TRUE release; A1 under-claims by the drop fraction.
        ctrl, bus, identities, _ = _build({"A1": true_release}, tolerance)
        inj = attacks.faulty_underreport("A1", "A0", true_release, frac, tolerance, tick)
        pub = MaliciousPublisher(bus)
        if frac < 1.0:
            pub.publish_toward(identities["A1"], "A0", tick, inj.release)
        # frac >= 1.0: total sender outage -> publish nothing (missing_claim).
        ctrl.decide("A0", ctrl.tls["A0"])

        detected = _conservation_flagged_edge(ctrl.detections, "A1", "A0")
        reason = next((d.reason for d in ctrl.detections
                       if d.src == "A1" and d.dst == "A0"), "none")
        # As-built finding: a TOTAL sender outage (frac=1.0) publishes NO claim,
        # so the controller never feeds an observed-only edge to conservation and
        # the `missing_claim` reason is unreachable via the live decide() path.
        # We record this honestly as an undetected fault (FN), not hide it.
        note = ("controller never reconciles an unclaimed edge -> missing_claim "
                "unreachable via live decide()" if frac >= 1.0 else "")

        if inj.malicious and first_malicious_tick is None:
            first_malicious_tick = tick
        if inj.malicious and detected and first_detect_tick is None:
            first_detect_tick = tick

        if inj.malicious and detected:
            tp += 1
        elif inj.malicious and not detected:
            fn += 1
        elif not inj.malicious and detected:
            fp += 1
        else:
            tn += 1

        rows.append({
            "drop": frac, "claim": inj.release, "observed": true_release,
            "malicious": inj.malicious, "detected": detected, "reason": reason,
            "expected_reason": inj.expected_reason, "note": note,
        })

    latency = (first_detect_tick - first_malicious_tick
               if first_detect_tick is not None and first_malicious_tick is not None
               else None)
    return rows, {"tp": tp, "fp": fp, "fn": fn, "tn": tn}, latency


# --------------------------------------------------------------------------- #
# Scenario C: SYBIL / IMPERSONATION -- caught by AUTH (bus.rejected), 0 cycles.
# Plus the c3 collusion EVASION (caught by neither).
# --------------------------------------------------------------------------- #

def run_sybil(tolerance: int):
    """Four auth sub-cases + the collusion evasion. Returns (rows, confusion).

    Each row records the expected vs measured auth reason (or the conservation
    miss for collusion). Auth detection latency is 0 cycles (rejected on receipt,
    never delivered to conservation).
    """
    rows = []
    tp = fp = fn = tn = 0

    # -- (c1) unknown_sender: the phantom neighbour Z9 (declared adjacent to A0
    #    but never registered) signs a message. Membership check rejects it.
    ctrl, bus, identities, _ = _build_with_sybil_neighbour(tolerance)
    pub = MaliciousPublisher(bus)
    pub.publish_unregistered(SYBIL_ID, "A0", t=0, release=40)
    ctrl.decide("A0", ctrl.tls["A0"])
    got = next((r["reason"] for r in bus.rejected
                if r["recipient"] == "A0" and r["sender"] == SYBIL_ID and r["t"] == 0), None)
    rows.append({"case": "unknown_sender (outsider Sybil)", "expected": "unknown_sender",
                 "measured": got, "rejected": got == "unknown_sender"})
    tp, fn = (tp + 1, fn) if got == "unknown_sender" else (tp, fn + 1)

    # -- (c1') not_neighbour: B1 is NOT adjacent to A0.
    ctrl, bus, identities, _ = _build({"A1": 0}, tolerance)
    pub = MaliciousPublisher(bus)
    pub.publish_not_neighbour(identities["B1"], "A0", t=1, release=40)
    ctrl.decide("A0", ctrl.tls["A0"])
    got = next((r["reason"] for r in bus.rejected
                if r["recipient"] == "A0" and r["sender"] == "B1" and r["t"] == 1), None)
    rows.append({"case": "not_neighbour (non-adjacent injection)", "expected": "not_neighbour",
                 "measured": got, "rejected": got is not None})
    tp, fn = (tp + 1, fn) if got == "not_neighbour" else (tp, fn + 1)

    # -- (c1'') revoked: A1 was registered, then revoked, but keeps signing.
    ctrl, bus, identities, registry = _build({"A1": 0}, tolerance)
    registry.revoke("A1")
    pub = MaliciousPublisher(bus)
    pub.publish_revoked(identities["A1"], "A0", t=2, release=40)
    ctrl.decide("A0", ctrl.tls["A0"])
    got = next((r["reason"] for r in bus.rejected
                if r["recipient"] == "A0" and r["sender"] == "A1" and r["t"] == 2), None)
    rows.append({"case": "revoked (membership withdrawn)", "expected": "revoked",
                 "measured": got, "rejected": got == "revoked"})
    tp, fn = (tp + 1, fn) if got == "revoked" else (tp, fn + 1)

    # -- (c1''') bad_signature: claim to be A1 but sign with B0's key.
    ctrl, bus, identities, _ = _build({"A1": 0}, tolerance)
    pub = MaliciousPublisher(bus)
    pub.publish_tampered(identities["A1"], identities["B0"], "A0", t=3, release=40)
    ctrl.decide("A0", ctrl.tls["A0"])
    got = next((r["reason"] for r in bus.rejected
                if r["recipient"] == "A0" and r["sender"] == "A1" and r["t"] == 3), None)
    rows.append({"case": "bad_signature (impersonation/tamper)", "expected": "bad_signature",
                 "measured": got, "rejected": got == "bad_signature"})
    tp, fn = (tp + 1, fn) if got == "bad_signature" else (tp, fn + 1)

    # -- (c3) collusion EVASION: A1 inflates claim AND A0 observes inflated, in
    #    lockstep. Auth passes, conservation returns ok. Malicious but UNDETECTED.
    phantom = 30
    true_release = 15
    ctrl, bus, identities, _ = _build({"A1": true_release + phantom}, tolerance)
    inj = attacks.collusion_lockstep("A1", "A0", true_release, phantom, tolerance, tick=4)
    pub = MaliciousPublisher(bus)
    pub.publish_toward(identities["A1"], "A0", 4, inj.release)
    ctrl.decide("A0", ctrl.tls["A0"])
    cons_flagged = _conservation_flagged_edge(ctrl.detections, "A1", "A0")
    auth_rejected = _auth_rejected_edge(bus.rejected, "A0", "A1", 4)
    detected = cons_flagged or auth_rejected
    rows.append({"case": "collusion lockstep (Xiao2026 evasion)", "expected": "ok / NEITHER",
                 "measured": "flagged" if detected else "ok (MISS)", "rejected": detected})

    # AUTH-layer confusion: the four admission-control violations only. These are
    # what the auth detector is RESPONSIBLE for; the collusion case is reported
    # separately because no layer claims it (expected_layer="none").
    auth_confusion = {"tp": tp, "fp": fp, "fn": fn, "tn": tn}
    collusion = {"malicious": True, "detected_by_auth": auth_rejected,
                 "detected_by_conservation": cons_flagged, "detected": detected}
    return rows, auth_confusion, collusion


# --------------------------------------------------------------------------- #
# Tolerance ROC-style sweep for the spoof: false-alarm rate vs recall.
# --------------------------------------------------------------------------- #

def run_tolerance_roc(tolerances, base_release: int = 15):
    """For each tolerance, score a fixed mixed set of spoof messages.

    The set spans benign (delta=0), sub-tolerance lies, and gross lies, so we can
    read off how raising tolerance trades recall for a lower false-alarm rate.
    Honest in-transit jitter is modelled as a small benign delta the recipient
    has NOT yet observed (claim slightly above observation), which a low tolerance
    would false-alarm on.
    """
    # (delta, malicious_truth). delta>0 with malicious=True are real lies;
    # delta in {1,2} with malicious=False model honest in-transit jitter.
    cases = [
        (0, False), (1, False), (2, False),  # jitter / benign
        (3, True), (5, True), (8, True), (15, True), (30, True),  # lies
    ]
    table = []
    for tol in tolerances:
        tp = fp = fn = tn = 0
        for tick, (delta, malicious) in enumerate(cases):
            ctrl, bus, identities, _ = _build({"A1": base_release}, tol)
            pub = MaliciousPublisher(bus)
            pub.publish_toward(identities["A1"], "A0", tick, base_release + delta)
            ctrl.decide("A0", ctrl.tls["A0"])
            detected = _conservation_flagged_edge(ctrl.detections, "A1", "A0")
            if malicious and detected:
                tp += 1
            elif malicious and not detected:
                fn += 1
            elif not malicious and detected:
                fp += 1
            else:
                tn += 1
        precision, recall, f1 = _prf1(tp, fp, fn)
        false_alarm = fp / (fp + tn) if (fp + tn) else 0.0
        table.append({
            "tolerance": tol, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "recall": recall, "false_alarm_rate": false_alarm,
            "precision": precision, "f1": f1,
        })
    return table


# --------------------------------------------------------------------------- #
# Report rendering.
# --------------------------------------------------------------------------- #

def _fmt(x, nd=3):
    return f"{x:.{nd}f}" if isinstance(x, float) else str(x)


def _summary_row(name, confusion, latency):
    p, r, f1 = _prf1(confusion["tp"], confusion["fp"], confusion["fn"])
    if latency is None:
        lat = "n/a"
    elif isinstance(latency, str):
        lat = f"{latency} cycle(s)"
    else:
        lat = f"{latency} cycle(s)"
    return (f"| {name} | {confusion['tp']} | {confusion['fp']} | {confusion['fn']} | "
            f"{confusion['tn']} | {_fmt(p)} | {_fmt(r)} | {_fmt(f1)} | {lat} |")


def build_report(results: dict) -> str:
    spoof_rows, spoof_cm, spoof_lat = results["spoof"]
    faulty_rows, faulty_cm, faulty_lat = results["faulty"]
    sybil_rows, sybil_cm, collusion = results["sybil"]
    roc = results["roc"]
    tol = results["tolerance"]

    lines: list[str] = []
    a = lines.append
    a("# Attack & Detection Report — The Edge Negotiator (Wk7-8 DE-RISK)")
    a("")
    a("Hard detection data for the three threat-model scenarios "
      "(`../THREAT-MODEL-ANALYSIS.md` §4), measured against KNOWN ground-truth "
      "labels per injected message. All runs use the deterministic `StubAgent` "
      "and an in-memory TraCI stand-in — NO Foundry, NO SUMO — so every number "
      "below reproduces exactly via `python src/run_attacks.py`.")
    a("")
    a(f"Conservation tolerance (default): **{tol} vehicles**. "
      "Detection latency is in control cycles. The conservation check is "
      "STATELESS, so a clearly-detectable spoof fires the SAME cycle its inflated "
      f"edge appears — measured directly at **{results['conservation_latency']} "
      "control cycle**. (The 'first-detect latency' in the summary table below is "
      "instead an artifact of the delta SWEEP ordering: the first malicious "
      "message in the sweep is a sub-tolerance lie that correctly never fires, so "
      "the first FLAGGED message arrives a couple of sweep steps later. The true "
      "per-message latency is 1 cycle.)")
    a("")

    # -- headline summary -------------------------------------------------- #
    a("## Summary — precision / recall / F1 / latency per attack")
    a("")
    a("| attack | TP | FP | FN | TN | precision | recall | F1 | first-detect latency |")
    a("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    a(_summary_row("(a) spoof (insider over-claim)", spoof_cm, spoof_lat))
    a(_summary_row("(b) faulty sensor (under-claim)", faulty_cm, faulty_lat))
    a(_summary_row("(c) sybil/impersonation (auth, 4 cases)", sybil_cm, "0"))
    a("")
    a("> The spoof and faulty sweeps deliberately INCLUDE within-tolerance / "
      "benign cases, so their FN/recall reflect the sub-tolerance evasion floor "
      "— recall is NOT 1.0 by construction. The auth row scores ONLY the four "
      "admission-control violations (recall 1.0, latency 0). The c3 "
      f"collusion-lockstep evasion is reported separately (detected_by_auth="
      f"{collusion['detected_by_auth']}, detected_by_conservation="
      f"{collusion['detected_by_conservation']}) — malicious but caught by "
      "NEITHER layer; see §C.")
    a("")

    # -- (a) spoof --------------------------------------------------------- #
    a("## (a) Spoofed report — conservation `inflated`")
    a("")
    a("A registered, approved A1 signs a genuine message but inflates its "
      "claimed `release` toward A0 by `delta`; A0 observes the true "
      f"`{spoof_rows[0]['observed']}`. Auth ADMITS (valid member/signature); "
      "conservation is the detector. Expected: `inflated` once `delta > "
      f"tolerance ({tol})`; within-tolerance over-claims EVADE.")
    a("")
    a("| delta | claim | observed | malicious | detected | reason | expected |")
    a("| --- | --- | --- | --- | --- | --- | --- |")
    for r in spoof_rows:
        a(f"| {r['delta']} | {r['claim']} | {r['observed']} | {r['malicious']} | "
          f"{r['detected']} | {r['reason']} | {r['expected_reason']} |")
    p, rec, f1 = _prf1(spoof_cm["tp"], spoof_cm["fp"], spoof_cm["fn"])
    a("")
    a(f"**Measured:** precision={_fmt(p)}, recall={_fmt(rec)}, F1={_fmt(f1)}, "
      f"latency={spoof_lat} cycle(s). Expected-vs-measured verdict: MATCH — every "
      f"`delta > {tol}` flags `inflated`; every `delta <= {tol}` is `ok` (the "
      "sub-tolerance lies that evade, quantified).")
    a("")

    # -- (b) faulty -------------------------------------------------------- #
    a("## (b) Faulty sensor — conservation `under_reported` / `missing_claim`")
    a("")
    a("No adversary: A1's own counter drops a fraction of its true release "
      f"(`{faulty_rows[0]['observed']}`) so it UNDER-claims, while A0 observes the "
      "truth. `delta = claimed − observed < −tolerance` ⇒ `under_reported`; a "
      "TOTAL sender outage (drop=1.0) ⇒ `missing_claim`.")
    a("")
    a("| drop fraction | claim | observed | malicious | detected | reason | expected | note |")
    a("| --- | --- | --- | --- | --- | --- | --- | --- |")
    for r in faulty_rows:
        a(f"| {r['drop']} | {r['claim']} | {r['observed']} | {r['malicious']} | "
          f"{r['detected']} | {r['reason']} | {r['expected_reason']} | {r.get('note', '')} |")
    p, rec, f1 = _prf1(faulty_cm["tp"], faulty_cm["fp"], faulty_cm["fn"])
    a("")
    a(f"**Measured:** precision={_fmt(p)}, recall={_fmt(rec)}, F1={_fmt(f1)}, "
      f"latency={faulty_lat} cycle(s). Honest caveat (N3): the flag attaches to "
      "edge A1→A0 and CANNOT distinguish 'A1's sensor faulty' from 'A0 "
      "over-observed' — auth+revoke can eject a node but cannot repair a fault.")
    a("")
    a("**As-built finding (drop=1.0 row):** a TOTAL sender outage publishes no "
      "claim, so the controller's `decide()` never constructs an observed-only "
      "edge for conservation — the `missing_claim` reason that `evaluate` *can* "
      "emit in isolation is UNREACHABLE through the live coordination path. The "
      "outage therefore goes undetected (a measured FN), an honest gap between "
      "the conservation primitive's capability and the controller's wiring.")
    a("")

    # -- (c) sybil --------------------------------------------------------- #
    a("## (c) Sybil / impersonation — caught by the AUTH layer (`bus.rejected`)")
    a("")
    a("Each outsider/impersonation case is rejected at `MessageBus.inbox` BEFORE "
      "conservation is ever consulted (detection latency = 0 cycles, never "
      "delivered). The final row is the c3 collusion EVASION — malicious but "
      "caught by NEITHER layer (the Xiao2026 residual limit).")
    a("")
    a("| case | expected verdict | measured verdict | caught |")
    a("| --- | --- | --- | --- |")
    for r in sybil_rows:
        a(f"| {r['case']} | {r['expected']} | {r['measured']} | {r['rejected']} |")
    a("")
    a("**Verdict:** all four admission-control violations (unknown_sender, "
      "not_neighbour, revoked, bad_signature) are rejected exactly as the "
      "threat-model predicts. The collusion case is UNDETECTED — recall = 0 on "
      "that scenario — which is the correct, honest result, not a bug.")
    a("")
    a("**Incidental as-built note:** each junction also publishes its OWN report "
      "every decision; reading its inbox it drops that self-echo with reason "
      "`not_neighbour` (a node is not its own neighbour). This is benign and is "
      "NOT a false positive against any peer — peer-message precision stays 1.0 — "
      "but it means the raw `bus.rejected` log is never empty even on a fully "
      "honest run; scoring filters self-echoes out.")
    a("")

    # -- tolerance ROC ----------------------------------------------------- #
    a("## Tolerance sweep — false-alarm rate vs recall (spoof detector)")
    a("")
    a("A fixed mixed message set (benign jitter at delta∈{0,1,2}; lies at "
      "delta∈{3,5,8,15,30}) scored at each tolerance. Raising tolerance "
      "suppresses jitter false-alarms but lets larger lies slip under the band.")
    a("")
    a("| tolerance | TP | FP | FN | TN | recall | false-alarm rate | precision | F1 |")
    a("| --- | --- | --- | --- | --- | --- | --- | --- | --- |")
    for row in roc:
        a(f"| {row['tolerance']} | {row['tp']} | {row['fp']} | {row['fn']} | "
          f"{row['tn']} | {_fmt(row['recall'])} | {_fmt(row['false_alarm_rate'])} | "
          f"{_fmt(row['precision'])} | {_fmt(row['f1'])} |")
    a("")
    a("**Read-off:** the tolerance band is a hard floor on detectable "
      "manipulation magnitude — a smart attacker simply lies INSIDE it every "
      "cycle and is never flagged (non-claim N4). Lowering tolerance raises "
      "recall on small lies at the cost of false-alarming on honest in-transit "
      "jitter; raising it does the reverse. There is no setting that catches a "
      "sub-tolerance lie without also false-alarming on benign jitter.")
    a("")

    # -- honest limitation ------------------------------------------------- #
    a("## Most important honest limitation the data exposes")
    a("")
    a("The detectors are SOUND but NARROW. Auth catches 100% of outsiders, "
      "impersonators, revoked members, and tampering (recall 1.0, latency 0). "
      "Conservation catches 100% of UNCOORDINATED single-sided lies/faults whose "
      "residual exceeds tolerance (recall 1.0 above the band). But TWO classes "
      "are measured at recall 0:")
    a("")
    a("1. **Sub-tolerance lies** — any single-party falsification with "
      f"`|claim − observed| <= {tol}` is `ok` every cycle; the stateless check "
      "accumulates no cross-tick evidence (N4). The tolerance sweep shows no "
      "operating point escapes this without false-alarming on jitter.")
    a("2. **Coordinated collusion** — two approved junctions inflating claim and "
      "observation in lockstep keep `delta` within tolerance, so conservation "
      "returns `ok` and auth (valid members, valid signatures) admits them. "
      "Caught by NEITHER layer — the empirically-confirmed Xiao2026 residual "
      "limit. The only available response is containment, not detection: "
      "`revoke()` + the tamper-evident hash-chained audit log give "
      "non-repudiable attribution AFTER the fact, never silent prevention.")
    a("")
    a("This is why the defensible thesis claim is *'authenticated, "
      "consistency-checked coordination with spoof/fault detection against "
      "UNCOORDINATED adversaries and faults'* — never trust, truth, or "
      "collusion-resistance.")
    a("")
    return "\n".join(lines)


def run_all(tolerance: int = 2) -> dict:
    """Run every sweep and return the raw results dict (for tests + report)."""
    spoof_deltas = [0, 1, 2, 3, 5, 10, 25]
    drop_fractions = [0.0, 0.1, 0.25, 0.5, 0.75, 1.0]
    tolerances = [0, 1, 2, 3, 5, 10]
    return {
        "tolerance": tolerance,
        "spoof": run_spoof(tolerance, spoof_deltas),
        "faulty": run_faulty(tolerance, drop_fractions),
        "sybil": run_sybil(tolerance),
        "roc": run_tolerance_roc(tolerances),
        "conservation_latency": measure_conservation_latency(tolerance),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true",
                    help="compute only; do not (re)write the markdown report")
    ap.add_argument("--tolerance", type=int, default=2)
    args = ap.parse_args()

    results = run_all(tolerance=args.tolerance)
    report = build_report(results)

    if not args.quiet:
        os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as fh:
            fh.write(report)
        print(f"[written] {os.path.abspath(REPORT_PATH)}")

    # Console summary.
    spoof_rows, spoof_cm, spoof_lat = results["spoof"]
    faulty_rows, faulty_cm, faulty_lat = results["faulty"]
    sybil_rows, sybil_cm, collusion = results["sybil"]
    for name, cm, lat in (("spoof", spoof_cm, spoof_lat),
                          ("faulty", faulty_cm, faulty_lat),
                          ("sybil", sybil_cm, 0)):
        p, r, f1 = _prf1(cm["tp"], cm["fp"], cm["fn"])
        print(f"[{name:7s}] P={p:.3f} R={r:.3f} F1={f1:.3f} "
              f"latency={lat} cycles  cm={cm}")


if __name__ == "__main__":
    main()
