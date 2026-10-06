"""§6.2 PRODUCER WIRING tests: the controller emits the §11 message/sighting/
decision records INLINE when an AuditLog is injected, and NOTHING when it is not.

These tests are written to FAIL if the wiring is removed:
  * drop the ``log_messages`` call  -> no kind:"message" record (asserted).
  * drop the ``log_decision`` calls  -> no kind:"decision" record (asserted).
  * drop the keyless local ``log_sighting`` -> no kind:"sighting" record.
  * drop the EV-decision emission    -> the "both fire / causal" assert fails.
So they are not fake-green; they pin the actual emitted bytes.
"""
import hashlib
import json
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from audit_log import AuditLog  # noqa: E402
from conservation import ConservationChecker  # noqa: E402
from coordinated_controller import CoordinatedController, StubAgent  # noqa: E402
from identity import JunctionIdentity, verify  # noqa: E402
from message_bus import MessageBus, canonical_bytes  # noqa: E402
from registry import Registry  # noqa: E402
from system import IntegratedSystem, SystemConfig  # noqa: E402
from system_ev import flatten_entries  # noqa: E402

ADJACENCY = {
    "A0": ["A1", "B0"], "A1": ["A0", "B1"],
    "B0": ["A0", "B1"], "B1": ["A1", "B0"],
}


def _flatten(audit):
    return [{**e["event"], "seq": e["seq"], "entry_signature": e["signature"]}
            for e in audit.entries()]


def _coord_ctrl(audit_log, sim_time=7.0):
    """A CoordinatedController on A0 (grid). Halting makes MaxPressure prefer
    phase 0; the FakeConn sim clock is 7.0 so decision.t (sim) is DISTINCT from the
    logical message.t used by the bus."""
    from system_fakeconn import FakeConn
    conn = FakeConn({"A1A0_0": 5, "B0A0_0": 4, "A0A1_0": 0, "A0B0_0": 0},
                    sim_time=sim_time)
    identities = {jid: JunctionIdentity(jid) for jid in ("A0", "A1", "B0", "B1")}
    registry = Registry()
    for jid, ident in identities.items():
        registry.register(jid, ident.public_key)
    bus = MessageBus(registry, ADJACENCY)
    ctrl = CoordinatedController(
        conn, ["A0"], StubAgent(), identities=identities, registry=registry,
        bus=bus, adjacency=ADJACENCY, checker=ConservationChecker(tolerance=2),
        slm_junctions=["A0"], gate=2, coord_weight=0.0, audit_log=audit_log)
    return ctrl, bus, identities, registry


# --------------------------------------------------------------------------- #
# Coordination path: message + decision records emitted inline.
# --------------------------------------------------------------------------- #

def test_consumed_message_emits_message_record_with_sig_and_der():
    audit = AuditLog()
    ctrl, bus, identities, registry = _coord_ctrl(audit)
    # A1 (a neighbour of A0) publishes a signed coordination claim toward A0.
    # Capture the PUBLISHED message so the record's signature is checked against
    # the REAL wire signature (not just a shape check -- a hardcoded fake would
    # differ from published.signature.hex() and fail).
    published = bus.publish(identities["A1"], 0,
                            {"toward": {"A0": {"release": 5, "queue_forecast": 5}}})
    ctrl.decide("A0", ctrl.tls["A0"])

    msgs = [e for e in _flatten(audit) if e["kind"] == "message"]
    assert len(msgs) == 1, "consuming one verified message emits one kind:message"
    m = msgs[0]
    assert m["sender"] == "A1"
    # The record's sender_signature is EXACTLY the published wire signature ...
    assert m["sender_signature"] == published.signature.hex()
    # ... and it crypto-verifies against the stored DER over the signed bytes,
    # so a producer that corrupted the signature would fail this.
    der = registry.public_key("A1")
    assert verify(bytes.fromhex(m["sender_pubkey_der"]),
                  canonical_bytes(m["signed_payload"]["sender"],
                                  m["signed_payload"]["t"],
                                  m["signed_payload"]["payload"]),
                  bytes.fromhex(m["sender_signature"])) is True
    # DER + fingerprint pulled from the REGISTRY at consumption (§6.1).
    assert m["sender_pubkey_der"] == der.hex()
    assert m["sender_pubkey_fpr"] == hashlib.sha256(der).hexdigest()
    # The EXACT signed payload is stored (logical tick inside).
    assert m["signed_payload"] == {"sender": "A1", "t": 0,
                                   "payload": {"toward": {"A0": {"release": 5,
                                                                 "queue_forecast": 5}}}}


def test_coordination_decision_record_fields():
    audit = AuditLog()
    ctrl, bus, identities, _ = _coord_ctrl(audit, sim_time=7.0)
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 5, "queue_forecast": 5}}})
    used = ctrl.decide("A0", ctrl.tls["A0"])

    flat = _flatten(audit)
    msg = next(e for e in flat if e["kind"] == "message")
    decs = [e for e in flat if e["kind"] == "decision"]
    assert len(decs) == 1
    d = decs[0]
    assert d["junction"] == "A0"
    assert d["executed"] == used
    # driving_input_seqs = the FULL set of consumed signed inputs (no filter).
    assert d["driving_input_seqs"] == [[msg["seq"], "A1"]]
    # decision.t is SIM time (7.0), DISTINCT from the logical message.t (0).
    assert d["t"] == 7.0
    assert msg["signed_payload"]["t"] == 0
    # policies_applied per the §6.2 pinned coordination mapping (never empty).
    assert "membership" in d["policies_applied"]
    assert "replay" in d["policies_applied"]
    # a conservation check ran (claim vs observed) -> conservation_band present.
    assert "conservation_band" in d["policies_applied"]
    # classification is a runtime label, present + from the {LEGITIMATE,...} set.
    assert d["classification"] in ("LEGITIMATE", "SPOOFED_OR_FAULTY")


def test_audit_log_none_is_side_effect_free_but_injection_emits():
    # None (default) must not change the decision AND must emit nothing.
    ctrl_n, bus_n, ids_n, _ = _coord_ctrl(None)
    bus_n.publish(ids_n["A1"], 0,
                  {"toward": {"A0": {"release": 5, "queue_forecast": 5}}})
    used_none = ctrl_n.decide("A0", ctrl_n.tls["A0"])

    audit = AuditLog()
    ctrl_a, bus_a, ids_a, _ = _coord_ctrl(audit)
    bus_a.publish(ids_a["A1"], 0,
                  {"toward": {"A0": {"release": 5, "queue_forecast": 5}}})
    used_audit = ctrl_a.decide("A0", ctrl_a.tls["A0"])

    assert used_none == used_audit, "injecting an AuditLog must not change the decision"
    assert len(audit) > 0, "with an AuditLog injected, records ARE emitted"


# --------------------------------------------------------------------------- #
# EV incident: naive victim records a non-preempting phantom; real EV preempts.
# --------------------------------------------------------------------------- #

def test_servable_phantom_commandeers_naive_victim_but_defended_refuses():
    """HONEST exploit-then-defend triad (§6.2): a SERVABLE phantom COMMANDEERS the
    naive victim (the exploit LANDS), the SAME phantom is REFUSED by the defended
    corroboration gate, and the real EV IS preempted. FAILS if the phantom is made
    non-servable (naive would no longer preempt) OR if the defended gate is removed
    (defended would then also preempt)."""
    r = IntegratedSystem(SystemConfig()).run(enable_ev_incident=True)
    ev = r.ev_incident
    assert ev["servable_edge"] == "A1A0"  # a phase-0 approach A0 DOES serve
    # Naive victim admits + records the phantom AND is commandeered to phase 0.
    assert ev["phantom_recorded"] is True
    assert ev["phantom_admissible"] is True
    assert ev["phantom_preempted"] is True, "servable phantom commandeers the naive victim"
    assert ev["phantom_executed"] == 0 and ev["baseline"] == 1
    # The SAME servable phantom is REFUSED by the defended corroboration gate.
    assert ev["phantom_preempted_defended"] is False, "defended gate refuses the phantom"
    assert ev["phantom_executed_defended"] == ev["baseline"]
    # The real EV, sensed locally, IS preempted (causal: executed != baseline).
    assert ev["real_recorded"] is True
    assert ev["real_preempted"] is True
    assert ev["real_executed"] == 0
    # The §11 records were emitted inline (fails if the wiring is removed).
    kinds = r.audit["record_kinds"]
    assert kinds.get("message", 0) >= 1
    assert kinds.get("decision", 0) >= 2
    assert kinds.get("sighting", 0) >= 1
    assert r.audit["verify_chain"] is True
    assert json.dumps(r.to_dict())  # whole bundle stays JSON-serialisable


def test_local_ev_emits_keyless_sighting_record():
    r = IntegratedSystem(SystemConfig()).run(enable_ev_incident=True)
    sightings = [e for e in r.audit_entries if e.get("kind") == "sighting"]
    assert len(sightings) == 1
    s = sightings[0]
    # §11 KEYLESS encoding: BOTH sighter_key AND signature are null (distinct
    # encoding, NOT missing_metadata) -- the §6.4 sensor-fed-spoof surface.
    assert s["sighter_key"] is None
    assert s["entry_signature"] is None
    assert s["ev_id"] == r.ev_incident["real_ev_id"]


def test_ev_decision_is_causal_record_when_both_fire():
    r = IntegratedSystem(SystemConfig()).run(enable_ev_incident=True)
    entries = list(r.audit_entries)
    by_seq = {e["seq"]: e for e in entries}

    def ev_id_of(rec):
        if rec.get("kind") == "sighting":
            return rec.get("ev_id")
        if rec.get("kind") == "message":
            p = rec.get("signed_payload", {}).get("payload", {})
            return ((p.get("ev_claim") or {}).get("ev_id")
                    or (p.get("sighting") or {}).get("ev_id"))
        return None

    real_t = r.ev_incident["real_tick_t"]
    decs = [e for e in entries if e.get("kind") == "decision" and e.get("t") == real_t]
    assert len(decs) == 2, "a coordination decision AND an EV decision fire this tick"
    causal = [d for d in decs
              if any(ev_id_of(by_seq[s]) for s, _k in d["driving_input_seqs"])]
    assert len(causal) == 1, "exactly one decision's driving inputs carry an ev_id"
    # The causal record is the EV decision (policy corroboration, the preemption).
    assert causal[0]["policies_applied"] == ["corroboration"]
    assert causal[0]["executed"] == 0
    # The other is the coordination decision (no ev_id, not corroboration-policy).
    noncausal = [d for d in decs if d is not causal[0]]
    assert noncausal[0]["policies_applied"] != ["corroboration"]


def _ev_id_of(rec):
    """A reader's rule to recover an ev_id from a driving-input record (§6.3):
    keyless sighting -> its ev_id; message -> payload.ev_claim/sighting.ev_id."""
    if rec.get("kind") == "sighting":
        return rec.get("ev_id")
    if rec.get("kind") == "message":
        p = rec.get("signed_payload", {}).get("payload", {})
        return ((p.get("ev_claim") or {}).get("ev_id")
                or (p.get("sighting") or {}).get("ev_id"))
    return None


def test_flatten_entries_lifts_event_and_preserves_seq():
    """The reader's `flatten` contract (system_ev.flatten_entries): event.* lifted
    to the top level, envelope seq preserved, envelope signature carried."""
    audit = AuditLog()
    ctrl, bus, identities, _ = _coord_ctrl(audit)
    bus.publish(identities["A1"], 0,
                {"toward": {"A0": {"release": 5, "queue_forecast": 5}}})
    ctrl.decide("A0", ctrl.tls["A0"])
    flat = flatten_entries(audit)
    assert len(flat) == len(audit)
    for rec, raw in zip(flat, audit.entries()):
        assert rec["seq"] == raw["seq"]                     # envelope seq preserved
        for k, v in raw["event"].items():
            assert rec[k] == v                              # event.* lifted verbatim
        assert rec["entry_signature"] == raw["signature"]   # envelope sig carried


def test_reader_recovers_causal_ev_id_from_records_alone():
    """END-TO-END consumability (M3): from the FLATTENED records alone a reader
    identifies the causal EV decision and recovers its ev_id -- no runtime state,
    no classification field, purely provenance-derived (§6.3 selector)."""
    r = IntegratedSystem(SystemConfig()).run(enable_ev_incident=True)
    entries = list(r.audit_entries)  # == system_ev.flatten_entries(audit)
    by_seq = {e["seq"]: e for e in entries}
    # Every decision record's driving_input_seqs resolve to real source records.
    for d in (e for e in entries if e.get("kind") == "decision"):
        for seq, _key in d["driving_input_seqs"]:
            assert seq in by_seq, "a driving-input seq must resolve to a record"
    # The EV preempt decision (real tick) is walkable to the real EV's ev_id.
    real_t = r.ev_incident["real_tick_t"]
    ev_decs = [e for e in entries if e.get("kind") == "decision"
               and e.get("t") == real_t
               and e.get("policies_applied") == ["corroboration"]]
    assert len(ev_decs) == 1
    recovered = {_ev_id_of(by_seq[s]) for s, _k in ev_decs[0]["driving_input_seqs"]}
    recovered.discard(None)
    assert recovered == {r.ev_incident["real_ev_id"]}, (
        "a reader recovers the causal ev_id purely from the records")
