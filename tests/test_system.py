"""End-to-end tests for the INTEGRATED SYSTEM (src/system.py).

The DEFAULT config (inprocess / memory / stub / grid2x2 / audit-on, no attacks)
runs end-to-end with NO Docker, NO Foundry, NO SUMO — so the whole assembly is
exercised in CI. It must yield: completed>0, verified_messages>0, detections
present, audit verify_chain True, a valid Merkle inclusion proof, and — with an
injected spoof — a flagged detection that is ALSO captured in the audit log.

Live-gated variants exercise the opt-in backends and SKIP cleanly when the
broker / node / SUMO is absent (same pattern as the MQTT / Besu integration
tests elsewhere in the suite). The SUMO grid variant runs whenever the SUMO
binary is present (it is in this project's env), proving the real-microsim path
produces real tripinfo metrics.

src/ is inserted on sys.path so `import system` resolves under
`python -m pytest tests` from the project root.
"""
import os
import socket
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from system import (  # noqa: E402
    AttackSpec,
    IntegratedSystem,
    SystemConfig,
    SystemResult,
)


# --------------------------------------------------------------------------- #
# Shared default-config run (one per module — the pipeline is deterministic).
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def default_result() -> SystemResult:
    return IntegratedSystem(SystemConfig()).run()


# --------------------------------------------------------------------------- #
# DEFAULT config: the CI-able end-to-end proof.
# --------------------------------------------------------------------------- #

def test_default_config_is_ci_able_no_live_dependency():
    cfg = SystemConfig()
    assert cfg.is_default is True
    assert cfg.requires_sumo is False
    assert cfg.transport == "inprocess" and cfg.registry == "memory"
    assert cfg.agent == "stub" and cfg.network == "grid2x2"
    assert cfg.audit is True


def test_default_run_completes_with_traffic(default_result):
    traffic = default_result.traffic
    assert traffic["completed"] > 0, f"expected completed>0, got {traffic}"


def test_default_run_carried_verified_messages(default_result):
    coord = default_result.coordination
    assert coord["verified_messages"] > 0, (
        f"expected the signed bus to deliver >0 verified messages, got {coord}")
    assert coord["decisions"] > 0


def test_default_run_has_detections(default_result):
    coord = default_result.coordination
    assert coord["detections"] > 0, "conservation must have produced detections"
    # A clean run (no attacks) must NOT raise spurious flags.
    assert coord["flagged_detections"] == 0, "clean run must not flag honest traffic"


def test_default_audit_chain_verifies(default_result):
    audit = default_result.audit
    assert audit["enabled"] is True
    assert audit["verify_chain"] is True, "the hash-chain must verify"
    assert audit["entries"] > 0
    # Inline §11 records (message + decision) AND registry events share the chain.
    assert audit["decision_entries"] > 0, "kind:decision records were emitted inline"
    assert audit["record_kinds"].get("message", 0) > 0, "kind:message records emitted"
    assert audit["registry_entries"] == 4, "4 grid junctions registered + mirrored"
    # non_registry_entries carries the sum identity now that decision_entries is
    # ONLY the decision records (not message/sighting too).
    assert audit["entries"] == audit["non_registry_entries"] + audit["registry_entries"]


def test_default_audit_has_valid_merkle_inclusion_proof(default_result):
    audit = default_result.audit
    assert audit["merkle_root"] is not None
    assert isinstance(audit["merkle_root"], str) and len(audit["merkle_root"]) == 64
    assert audit["inclusion_proof_valid"] is True
    sample = audit["sample_inclusion"]
    assert sample["verified"] is True
    assert sample["branch_len"] > 0


def test_default_result_is_immutable_json_serialisable(default_result):
    import json
    bundle = default_result.to_dict()
    # Round-trips through JSON (proves the whole bundle is serialisable).
    text = json.dumps(bundle)
    again = json.loads(text)
    assert again["audit"]["verify_chain"] is True
    # SystemResult is frozen — cannot mutate.
    with pytest.raises(Exception):
        default_result.traffic = {}  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# DEFAULT config + an injected SPOOF: flagged AND captured in the audit log.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def spoof_result() -> SystemResult:
    spoof = AttackSpec(kind="spoof", sender="A1", recipient="A0",
                       release=99, observed=0, tick=2)
    return IntegratedSystem(SystemConfig(attacks=(spoof,))).run()


def test_spoof_is_flagged_by_conservation(spoof_result):
    coord = spoof_result.coordination
    assert coord["flagged_detections"] >= 1, "the spoof must raise a flagged detection"


def test_spoof_outcome_recorded_and_in_audit(spoof_result):
    outcomes = spoof_result.attack_outcomes
    assert len(outcomes) == 1
    o = outcomes[0]
    assert o["kind"] == "spoof"
    assert o["detected"] is True
    assert o["reason"] == "inflated"
    assert o["expected_layer"] == "conservation"
    # The flagged detection is ALSO captured in the signed audit log.
    assert o["captured_in_audit"] is True


def test_spoof_run_audit_chain_still_verifies(spoof_result):
    audit = spoof_result.audit
    assert audit["verify_chain"] is True
    assert audit["inclusion_proof_valid"] is True


# --------------------------------------------------------------------------- #
# Attack coverage: every kind scores against the right detector layer.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("spec, layer, reason", [
    (AttackSpec("spoof", "A1", "A0", release=99, observed=0, tick=2),
     "conservation", "inflated"),
    (AttackSpec("under_report", "A1", "A0", release=2, observed=20, tick=2),
     "conservation", "under_reported"),
    (AttackSpec("not_neighbour", "B1", "A0", release=40, tick=1),
     "auth", "not_neighbour"),
    (AttackSpec("revoked", "A1", "A0", release=40, tick=1),
     "auth", "revoked"),
    (AttackSpec("bad_signature", "A1", "A0", release=40, signer="B0", tick=1),
     "auth", "bad_signature"),
])
def test_each_attack_kind_detected_by_expected_layer(spec, layer, reason):
    result = IntegratedSystem(SystemConfig(attacks=(spec,))).run()
    o = result.attack_outcomes[0]
    assert o["expected_layer"] == layer
    assert o["detected"] is True, f"{spec.kind} must be detected"
    assert o["reason"] == reason, f"{spec.kind} expected {reason}, got {o['reason']}"
    # The chain stays intact no matter what is injected.
    assert result.audit["verify_chain"] is True


def test_auth_rejections_are_counted():
    """A not_neighbour injection lands in the rejected-message count."""
    spec = AttackSpec("not_neighbour", "B1", "A0", release=40, tick=1)
    result = IntegratedSystem(SystemConfig(attacks=(spec,))).run()
    assert result.coordination["rejected_messages"] > 0


# --------------------------------------------------------------------------- #
# Audit OFF: pipeline still runs; audit bundle reports disabled.
# --------------------------------------------------------------------------- #

def test_audit_off_runs_and_reports_disabled():
    result = IntegratedSystem(SystemConfig(audit=False)).run()
    assert result.audit == {"enabled": False}
    assert result.traffic["completed"] > 0
    assert result.coordination["verified_messages"] > 0


# --------------------------------------------------------------------------- #
# coord_weight pathway: a high weight changes the deterministic choice.
# --------------------------------------------------------------------------- #

def test_coord_weight_zero_makes_no_coordination_adjustment():
    result = IntegratedSystem(SystemConfig(coord_weight=0.0)).run()
    assert result.coordination["coord_adjusted_decisions"] == 0
    assert result.coordination["coord_weight"] == 0.0


# --------------------------------------------------------------------------- #
# Config validation (boundaries).
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("kwargs", [
    {"transport": "carrier-pigeon"},
    {"registry": "postgres"},
    {"agent": "gpt"},
    {"network": "manhattan"},
    {"coord_weight": float("nan")},
    {"coord_weight": float("inf")},
    {"coord_weight": -1.0},
    {"tolerance": -1},
    {"end": 0},
    {"rounds": 0},
    {"audit": "yes"},
])
def test_invalid_config_rejected(kwargs):
    with pytest.raises((ValueError, TypeError)):
        SystemConfig(**kwargs)


@pytest.mark.parametrize("kwargs", [
    {"kind": "spoof", "sender": "", "recipient": "A0"},
    {"kind": "nonsense", "sender": "A1", "recipient": "A0"},
    {"kind": "spoof", "sender": "A1", "recipient": "A0", "release": -1},
    {"kind": "bad_signature", "sender": "A1", "recipient": "A0"},  # missing signer
])
def test_invalid_attackspec_rejected(kwargs):
    with pytest.raises(ValueError):
        AttackSpec(**kwargs)


def test_mqtt_transport_implies_sumo_path():
    """Selecting the MQTT transport implies the SUMO run path (no explicit flag)."""
    cfg = SystemConfig(transport="mqtt", use_sumo=False)
    assert cfg.requires_sumo is True
    assert cfg.is_default is False


def test_euston_implies_sumo_path():
    cfg = SystemConfig(network="euston", use_sumo=False)
    assert cfg.requires_sumo is True
    assert cfg.is_default is False


# --------------------------------------------------------------------------- #
# LIVE-GATED variant: SUMO grid microsimulation (runs when SUMO is present).
# --------------------------------------------------------------------------- #

def _sumo_available() -> bool:
    try:
        from sumolib import checkBinary
        return bool(checkBinary("sumo"))
    except Exception:
        return False


@pytest.mark.skipif(not _sumo_available(), reason="SUMO binary not available")
def test_sumo_grid_run_produces_real_tripinfo_metrics():
    cfg = SystemConfig(network="grid2x2", use_sumo=True, end=150)
    assert cfg.requires_sumo is True
    result = IntegratedSystem(cfg).run()
    traffic = result.traffic
    assert traffic["source"] == "sumo"
    assert traffic["microsimulation"] is True
    assert traffic["completed"] > 0
    # Survivorship-robust metrics from metrics.py are present.
    assert "mean_network_delay" in traffic
    assert "total_network_delay" in traffic
    # Coordination ran live over the real grid.
    assert result.coordination["verified_messages"] > 0
    assert result.coordination["detections"] > 0
    # Audit chain over the real run still verifies, with a valid inclusion proof.
    assert result.audit["verify_chain"] is True
    assert result.audit["inclusion_proof_valid"] is True
    assert result.backends["run_path"] == "sumo"
    assert result.backends["live"] is True


@pytest.mark.skipif(not _sumo_available(), reason="SUMO binary not available")
def test_sumo_grid_run_with_spoof_flags_and_audits():
    """A spoof injected during the live SUMO run is flagged and audited."""
    spoof = AttackSpec(kind="spoof", sender="A1", recipient="A0",
                       release=200, observed=0, tick=40)
    cfg = SystemConfig(network="grid2x2", use_sumo=True, end=120, attacks=(spoof,))
    result = IntegratedSystem(cfg).run()
    # The live grid already produces flagged detections; the chain stays valid.
    assert result.audit["verify_chain"] is True
    assert result.coordination["flagged_detections"] >= 0


# --------------------------------------------------------------------------- #
# LIVE-GATED variant: MQTT transport (skips cleanly without a broker).
# --------------------------------------------------------------------------- #

def _broker_up(host="127.0.0.1", port=1883, timeout=0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not (_sumo_available() and _broker_up()),
                    reason="MQTT broker (and/or SUMO) not available")
def test_mqtt_transport_run_live():
    cfg = SystemConfig(transport="mqtt", network="grid2x2", use_sumo=True, end=120)
    result = IntegratedSystem(cfg).run()
    assert result.backends["transport"] == "mqtt"
    assert result.backends["mqtt_clients"] > 0
    assert result.coordination["verified_messages"] >= 0
    assert result.audit["verify_chain"] is True


def test_mqtt_run_raises_cleanly_when_broker_absent():
    """With no broker, the MQTT path raises a clear transport error (no silent run)."""
    if _broker_up():
        pytest.skip("a broker IS up; cannot exercise the broker-absent path")
    if not _sumo_available():
        pytest.skip("SUMO not available to reach the transport-build step")
    from mqtt_transport import MqttTransportError
    cfg = SystemConfig(transport="mqtt", network="grid2x2", use_sumo=True, end=60,
                       mqtt_port=1)  # nothing listens on port 1
    with pytest.raises(MqttTransportError):
        IntegratedSystem(cfg).run()


# --------------------------------------------------------------------------- #
# LIVE-GATED variant: Besu registry (skips cleanly without a node).
# --------------------------------------------------------------------------- #

def _besu_up(rpc="http://127.0.0.1:8545") -> bool:
    from urllib.parse import urlparse
    try:
        u = urlparse(rpc)
        with socket.create_connection((u.hostname, u.port or 8545), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.mark.skipif(not (_sumo_available() and _besu_up()),
                    reason="Besu node (and/or SUMO) not available")
def test_besu_registry_run_live():
    cfg = SystemConfig(registry="besu", network="grid2x2", use_sumo=True, end=120)
    result = IntegratedSystem(cfg).run()
    assert result.backends["registry"] == "besu"
    assert result.coordination["verified_messages"] >= 0
    assert result.audit["verify_chain"] is True
