"""The Edge Negotiator — END-TO-END INTEGRATED SYSTEM.

This is the centerpiece that ASSEMBLES every separately-tested part into one
runnable pipeline. It does NOT re-implement any subsystem; it composes their
PUBLIC APIs with explicit, swappable choices, and wires the audit log at the
documented integration point (results/audit_log_design.md §7).

The parts it composes (all imported, none edited)
-------------------------------------------------
  * identity.JunctionIdentity / verify        — per-junction Ed25519 identity
  * registry.Registry  |  registry_service.RegistryService  — permissioned allowlist
  * message_bus.MessageBus  |  run_mqtt_coord.MqttBusAdapter — signed neighbour bus
  * conservation.ConservationChecker          — the detection primitive
  * coordinated_controller.CoordinatedController / StubAgent / edge_map_from_net
  * slm_agent.SLMAgent                         — the real SLM (Foundry Local)
  * audit_log.AuditLog / verify_inclusion      — hash-chain + Ed25519 + Merkle anchor
  * metrics.parse_tripinfo / summary           — survivorship-robust traffic metrics
  * attacks.MaliciousPublisher + injectors     — the three threat-model scenarios

Swappable backends (SystemConfig)
---------------------------------
  transport : "inprocess" (MessageBus)        | "mqtt"   (MqttBusAdapter, live broker)
  registry  : "memory"    (Registry)          | "besu"   (RegistryService, live node)
  agent     : "stub"      (StubAgent)         | "slm"    (SLMAgent, live Foundry)
  network   : "grid2x2"   (string-convention) | "euston" (edge_map_from_net)
  audit     : on/off       — every decision appended+signed, registry events mirrored
  attacks   : optional injectors run during the sim

The DEFAULT config (inprocess / memory / stub / grid2x2 / audit-on / no attacks)
runs with NO Docker / NO Foundry / NO SUMO, so it is CI-able. Each non-default
backend is opt-in and LIVE-GATED: it raises a clear error (or its run() skips)
when the broker / node / SUMO / Foundry is absent.

Audit-log wiring (§6.2 producer wiring — the seam is now IN the producer)
-------------------------------------------------------------------------
The AuditLog is INJECTED into the controller (keyword-only ``audit_log=``), which
emits the §11 message/decision/sighting records INLINE as it consumes messages
and decides (``coordinated_controller`` / ``emergency_controller``). The earlier
``_drain_audit`` post-hoc ``.events`` mirror is DELETED (it double-wrote decisions
in a legacy shape). Registry register/revoke events are still mirrored into the
same chain FIRST (``_mirror_registry``). ``enable_ev_incident=True`` additionally
stages a naive-victim phantom-claim + real-EV incident over an EmergencyController.
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field, replace
from typing import Any, Callable

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from attacks import MaliciousPublisher  # noqa: E402
from audit_log import AuditLog, verify_inclusion  # noqa: E402
from conservation import ConservationChecker, Detection  # noqa: E402
from coordinated_controller import (  # noqa: E402
    CoordinatedController,
    StubAgent,
    edge_map_from_net,
)
from identity import JunctionIdentity  # noqa: E402
from message_bus import MessageBus  # noqa: E402
from registry import Registry  # noqa: E402
from system_fakeconn import (  # noqa: E402
    FakeConn, NoObsConn, initial_halting,
    group_attacks, coordination_counts, fake_traffic_summary,
    sumo_traffic_summary, config_dict,
)

# Valid enum values for each swappable choice (closed sets — validated at boundary).
_TRANSPORTS = ("inprocess", "mqtt")
_REGISTRIES = ("memory", "besu")
_AGENTS = ("stub", "slm")
_NETWORKS = ("grid2x2", "euston")

# Grid 2x2 adjacency (same as run_coordinated.ADJACENCY) — kept local so the CI
# default path has NO import-time SUMO dependency.
_GRID_ADJACENCY = {
    "A0": ["A1", "B0"], "A1": ["A0", "B1"],
    "B0": ["A0", "B1"], "B1": ["A1", "B0"],
}
_GRID_TLS = ("A0", "A1", "B0", "B1")


# --------------------------------------------------------------------------- #
# Attack specification (immutable). A run can inject a list of these; each is
# expanded into a MaliciousPublisher call at its tick during the fake-conn run.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AttackSpec:
    """One injectable attack, reusing attacks.py's MaliciousPublisher transforms.

    ``kind`` selects the transform:
      * ``"spoof"``        — sender over-claims ``release`` toward recipient
                             (auth admits; conservation flags ``inflated``).
      * ``"under_report"`` — sender under-claims (conservation ``under_reported``).
      * ``"not_neighbour"``— a non-adjacent registered junction injects (auth).
      * ``"revoked"``      — a revoked-but-signing junction injects (auth).
      * ``"bad_signature"``— impersonation: signed with the wrong key (auth).

    ``sender`` / ``recipient`` name the directed edge. ``release`` is the claimed
    count; ``observed`` (spoof/under_report) is what the recipient independently
    sees on that in-edge (set on the fake conn). ``signer`` (bad_signature only)
    is the junction whose key actually signs the forged frame.
    """

    kind: str
    sender: str
    recipient: str
    release: int = 0
    observed: int = 0
    signer: str | None = None
    tick: int = 0

    _KINDS = ("spoof", "under_report", "not_neighbour", "revoked", "bad_signature")

    def __post_init__(self) -> None:
        if self.kind not in self._KINDS:
            raise ValueError(f"attack kind must be one of {self._KINDS}, got {self.kind!r}")
        for name in ("sender", "recipient"):
            v = getattr(self, name)
            if not isinstance(v, str) or not v:
                raise ValueError(f"attack {name} must be a non-empty string")
        for name in ("release", "observed", "tick"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise ValueError(f"attack {name} must be a non-negative int, got {v!r}")
        if self.kind == "bad_signature" and not self.signer:
            raise ValueError("bad_signature attack requires a 'signer' junction id")


# --------------------------------------------------------------------------- #
# Immutable configuration. Validated entirely at construction.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SystemConfig:
    """Immutable, validated configuration for one integrated run.

    The default instance is the CI-able config: inprocess transport, in-memory
    registry, StubAgent, the 2x2 grid, audit ON, no attacks — runs with no
    Docker, no Foundry, no SUMO.
    """

    transport: str = "inprocess"
    registry: str = "memory"
    agent: str = "stub"
    network: str = "grid2x2"
    audit: bool = True
    attacks: tuple[AttackSpec, ...] = ()
    # Run controls.
    seed: int = 42
    end: int = 200                 # sim steps (SUMO) — ignored by the fake-conn path
    rounds: int = 40               # decide() rounds for the CI fake-conn path
    coord_weight: float = 1.0
    tolerance: int = 2
    gate: int = 2
    # Live-backend connection details (only consulted when the backend is selected).
    mqtt_host: str = "127.0.0.1"
    mqtt_port: int = 1883
    besu_rpc: str = "http://127.0.0.1:8545"
    # When True the SUMO microsimulation drives the run (real tripinfo metrics);
    # when False the deterministic fake-conn harness drives decide() directly
    # (no SUMO — the CI path). Auto-defaults: True for the SUMO-only backends.
    use_sumo: bool = False

    def __post_init__(self) -> None:
        if self.transport not in _TRANSPORTS:
            raise ValueError(f"transport must be one of {_TRANSPORTS}, got {self.transport!r}")
        if self.registry not in _REGISTRIES:
            raise ValueError(f"registry must be one of {_REGISTRIES}, got {self.registry!r}")
        if self.agent not in _AGENTS:
            raise ValueError(f"agent must be one of {_AGENTS}, got {self.agent!r}")
        if self.network not in _NETWORKS:
            raise ValueError(f"network must be one of {_NETWORKS}, got {self.network!r}")
        if not isinstance(self.audit, bool):
            raise TypeError("audit must be a bool")
        if not isinstance(self.attacks, tuple) or any(
            not isinstance(a, AttackSpec) for a in self.attacks
        ):
            raise TypeError("attacks must be a tuple of AttackSpec")
        for name in ("seed", "end", "rounds", "tolerance", "gate", "mqtt_port"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int):
                raise TypeError(f"{name} must be an int, got {type(v).__name__}")
        if self.end <= 0 or self.rounds <= 0:
            raise ValueError("end and rounds must be positive")
        if self.tolerance < 0 or self.gate < 0:
            raise ValueError("tolerance and gate must be >= 0")
        if isinstance(self.coord_weight, bool) or not isinstance(self.coord_weight, (int, float)):
            raise TypeError("coord_weight must be a number")
        if self.coord_weight != self.coord_weight or self.coord_weight in (
            float("inf"), float("-inf")
        ):
            raise ValueError("coord_weight must be finite")
        if self.coord_weight < 0:
            raise ValueError("coord_weight must be >= 0")
        # The MQTT transport and the euston network only run under the SUMO
        # microsimulation; selecting either IMPLIES the SUMO path (see
        # ``requires_sumo``), so no explicit ``use_sumo`` flag is needed and these
        # configs are valid as-is — they just route through ``_run_sumo``.

    @property
    def requires_sumo(self) -> bool:
        """True iff this config drives the real SUMO microsimulation."""
        return self.use_sumo or self.transport == "mqtt" or self.network == "euston"

    @property
    def is_default(self) -> bool:
        """True iff this is the fully CI-able default (no live dependency)."""
        return (
            self.transport == "inprocess" and self.registry == "memory"
            and self.agent == "stub" and self.network == "grid2x2"
            and not self.requires_sumo
        )


# --------------------------------------------------------------------------- #
# Immutable result bundle.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SystemResult:
    """The single result object a system RUN produces.

    Bundles traffic metrics, coordination counts, the signed audit-log integrity
    proof (verify_chain + Merkle root + a sample inclusion proof), and — when
    attacks were injected — the per-attack detection outcome.
    """

    config: dict
    traffic: dict
    coordination: dict
    audit: dict
    attack_outcomes: tuple[dict, ...] = ()
    backends: dict = field(default_factory=dict)
    # Populated only by the enable_ev_incident run: the FLATTENED §11 records
    # (event.* lifted + envelope seq preserved) and a small incident summary, so
    # a test can verify the ACTUAL emitted records, not a self-reported outcome.
    audit_entries: tuple[dict, ...] = ()
    ev_incident: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Flat, JSON-serialisable dict of the whole bundle (for run_system CLI)."""
        return {
            "config": self.config,
            "backends": self.backends,
            "traffic": self.traffic,
            "coordination": self.coordination,
            "audit": self.audit,
            "attack_outcomes": list(self.attack_outcomes),
            "audit_entries": list(self.audit_entries),
            "ev_incident": self.ev_incident,
        }


# --------------------------------------------------------------------------- #
# The orchestrator.
# --------------------------------------------------------------------------- #

class IntegratedSystem:
    """Compose the tested parts into one runnable pipeline per a SystemConfig.

    Immutable: the config is frozen and the system holds no mutable run state
    between runs — each :meth:`run` builds fresh identities / registry / bus /
    controller / audit log and returns a new :class:`SystemResult`.
    """

    def __init__(self, config: SystemConfig | None = None) -> None:
        self.config = config if config is not None else SystemConfig()
        if not isinstance(self.config, SystemConfig):
            raise TypeError("config must be a SystemConfig")

    # -- public entrypoint ---------------------------------------------------- #

    def run(self, *, enable_ev_incident: bool = False) -> SystemResult:
        """Execute one configured run and return the result bundle.

        ``enable_ev_incident`` (keyword-only, default False = unchanged) stages a
        NAIVE-victim (corroboration_required=False) scripted phantom-claim + real
        EV incident (§6.2) over the grid, emitting the §11 EV records inline.
        """
        if enable_ev_incident:
            return self._run_ev_incident()
        if self.config.requires_sumo:
            return self._run_sumo()
        return self._run_fake()

    # ===================================================================== #
    # Shared assembly: identities + registry + bus.
    # ===================================================================== #

    def _build_identities(self, tls) -> dict[str, JunctionIdentity]:
        return {jid: JunctionIdentity(jid) for jid in tls}

    def _build_registry(self, identities: dict[str, JunctionIdentity]):
        """Build the chosen registry backend, fully populated, + an audit mirror.

        Returns ``(registry, registry_events)`` where ``registry_events`` is the
        ordered list of register/revoke event dicts to mirror into the AuditLog
        (the brief: "registry changes are mirrored into the same chain"). For the
        in-memory Registry the events ARE ``registry.audit_log``; for the
        event-sourced RegistryService they are its cache audit log.
        """
        cfg = self.config
        if cfg.registry == "memory":
            registry = Registry()
            for jid, ident in identities.items():
                registry.register(jid, ident.public_key)
            return registry, list(registry.audit_log)

        # besu — live-gated, opt-in. Built over a real node via RegistryService.
        registry = self._build_besu_registry(identities)
        return registry, list(registry.audit_log)

    def _build_besu_registry(self, identities: dict[str, JunctionIdentity]):
        """Stand up a RegistryService over a live Besu node (raises if absent)."""
        from besu_registry import BesuRegistry  # deferred: needs web3 + a node
        from registry_service import BesuEventSource, RegistryService

        besu = BesuRegistry(rpc_url=self.config.besu_rpc)
        service = RegistryService(BesuEventSource(besu)).start()
        # Register every junction off-loop, then flush so the cache reflects them.
        handles = [service.register(jid, ident.public_key)
                   for jid, ident in identities.items()]
        for h in handles:
            h.await_commit(timeout=30.0)
        service.refresh()
        return service

    # ===================================================================== #
    # CI path: deterministic fake-conn harness (no SUMO / Foundry / Docker).
    # Mirrors tests/test_coordination.py + run_attacks.py fake conn.
    # ===================================================================== #

    def _run_fake(self) -> SystemResult:
        cfg = self.config
        adjacency = {k: list(v) for k, v in _GRID_ADJACENCY.items()}
        tls = list(_GRID_TLS)
        identities = self._build_identities(tls)
        registry, registry_events = self._build_registry(identities)
        bus = MessageBus(registry, adjacency)
        checker = ConservationChecker(tolerance=cfg.tolerance)
        agent = self._build_agent()
        audit = AuditLog() if cfg.audit else None

        # Mirror registry membership changes into the audit chain FIRST (so the
        # allowlist provenance precedes the decisions it authorised).
        registry_appended = self._mirror_registry(audit, registry_events, identities)

        conn = FakeConn(initial_halting())
        ctrl = CoordinatedController(
            conn, ["A0"], agent, identities=identities, registry=registry,
            bus=bus, adjacency=adjacency, checker=checker, slm_junctions=["A0"],
            gate=cfg.gate, coord_weight=cfg.coord_weight, audit_log=audit,
        )

        publisher = MaliciousPublisher(bus)
        attacks_by_tick = group_attacks(cfg.attacks)
        injected_records: list[dict] = []

        # Drive A0's decide() over `rounds` ticks. On each tick: (1) an honest
        # neighbour (A1) publishes a benign claim matching what A0 observes, so the
        # conservation books balance on a clean run; (2) any attack scheduled for
        # this tick is injected; (3) A0 decides -- the injected AuditLog emits the
        # §11 message/decision records INLINE (no post-hoc _drain_audit mirror).
        for tick in range(cfg.rounds):
            self._inject_tick(publisher, identities, registry, conn,
                              attacks_by_tick.get(tick, ()), tick, injected_records)
            ctrl.decide("A0", ctrl.tls["A0"])

        traffic = fake_traffic_summary(cfg.rounds, len(ctrl.events))
        coordination = coordination_counts(ctrl, bus)
        audit_bundle = self._audit_bundle(audit, registry_appended)
        attack_outcomes = self._score_attacks(cfg.attacks, ctrl, bus, injected_records)

        return SystemResult(
            config=config_dict(cfg),
            traffic=traffic,
            coordination=coordination,
            audit=audit_bundle,
            attack_outcomes=tuple(attack_outcomes),
            backends=self._backends(live=False),
        )

    def _inject_tick(self, publisher, identities, registry, conn, specs, tick,
                     injected_records) -> None:
        """Publish honest baseline traffic + any scheduled attacks for this tick.

        A junction publishes AT MOST ONCE per tick (the bus replay guard keys on
        ``(recipient, sender, tick)``, so a second publish from the same sender
        that tick would be dropped as a replay). So the honest baseline is only
        emitted by A1 on ticks where A1 is NOT itself an attack sender — on an
        attack tick the attack IS A1's message for that tick.
        """
        attack_senders = {spec.sender for spec in specs}
        if "A1" not in attack_senders:
            # Honest baseline: A1 truthfully claims what A0 will observe on A1->A0.
            honest_release = conn.lane.observed_for("A1")
            publisher.publish_toward(identities["A1"], "A0", tick, honest_release)

        for spec in specs:
            self._inject_one(publisher, identities, registry, conn, spec, tick,
                             injected_records)

    def _inject_one(self, publisher, identities, registry, conn, spec, tick,
                    injected_records) -> None:
        """Expand one AttackSpec into the matching MaliciousPublisher call."""
        if spec.kind in ("spoof", "under_report"):
            # The recipient's independent observation is set on the fake conn so
            # conservation has a real number to reconcile the claim against.
            conn.lane.set_observed(spec.sender, spec.observed)
            publisher.publish_toward(identities[spec.sender], spec.recipient,
                                     tick, spec.release)
        elif spec.kind == "not_neighbour":
            publisher.publish_not_neighbour(identities[spec.sender], spec.recipient,
                                            tick, spec.release)
        elif spec.kind == "revoked":
            # Caller-side: revoke before inbox so membership is gone at verify time.
            try:
                registry.revoke(spec.sender)
            except Exception:
                pass
            publisher.publish_revoked(identities[spec.sender], spec.recipient,
                                      tick, spec.release)
        elif spec.kind == "bad_signature":
            publisher.publish_tampered(identities[spec.sender], identities[spec.signer],
                                       spec.recipient, tick, spec.release)
        injected_records.append({
            "kind": spec.kind, "sender": spec.sender, "recipient": spec.recipient,
            "release": spec.release, "observed": spec.observed, "tick": tick,
        })

    # ===================================================================== #
    # EV incident path (§6.2): naive-victim phantom claim + real EV.
    # ===================================================================== #

    def _run_ev_incident(self) -> SystemResult:
        """Stage the §6.2 naive-victim phantom + real-EV incident (see system_ev)."""
        from system_ev import run_ev_incident
        return run_ev_incident(self)

    # ===================================================================== #
    # SUMO path: real microsimulation -> real tripinfo metrics.
    # ===================================================================== #

    def _run_sumo(self) -> SystemResult:
        import traci
        from sumolib import checkBinary

        cfg = self.config
        net_path, cfg_args, adjacency, edge_map = self._sumo_network()

        binary = checkBinary("sumo")
        tripinfo = os.path.join(
            _SRC, "..", "sumo", f"tripinfo_system_{cfg.network}.xml")
        traci.start([binary, *cfg_args, "--tripinfo-output", tripinfo,
                     "--tripinfo-output.write-unfinished", "true",
                     "--seed", str(cfg.seed), "--no-warnings", "true",
                     "--no-step-log", "true"])

        transports = {}
        ctrl = None
        bus = None
        audit = AuditLog() if cfg.audit else None
        registry_appended = 0
        publisher = None
        injected_records: list[dict] = []
        attacks_by_tick = group_attacks(cfg.attacks)
        try:
            tls = list(traci.trafficlight.getIDList())
            identities = self._build_identities(tls)
            registry, registry_events = self._build_registry(identities)
            registry_appended = self._mirror_registry(audit, registry_events, identities)
            checker = ConservationChecker(tolerance=cfg.tolerance)
            agent = self._build_agent()

            bus, transports = self._build_bus(tls, identities, registry, adjacency)
            publisher = MaliciousPublisher(self._underlying_bus(bus, transports))
            ctrl = CoordinatedController(
                traci, tls, agent, identities=identities, registry=registry,
                bus=bus, adjacency=adjacency, checker=checker, slm_junctions=tls,
                gate=cfg.gate, coord_weight=cfg.coord_weight, edge_map=edge_map,
                audit_log=audit,
            )

            step = 0
            while traci.simulation.getMinExpectedNumber() > 0 and step < cfg.end:
                traci.simulationStep()
                # Inject any attacks scheduled at this step (by tick==step).
                for spec in attacks_by_tick.get(step, ()):
                    self._inject_sumo_attack(publisher, identities, registry, spec,
                                             step, injected_records)
                # ctrl.step() -> decide() per junction, which emits the §11 records
                # inline via the injected AuditLog (no post-hoc _drain_audit mirror).
                ctrl.step()
                step += 1
        finally:
            try:
                traci.close()
            finally:
                for tr in transports.values():
                    try:
                        tr.disconnect()
                    except Exception:
                        pass

        traffic = sumo_traffic_summary(tripinfo)
        coordination = coordination_counts(ctrl, bus, transports)
        audit_bundle = self._audit_bundle(audit, registry_appended)
        attack_outcomes = self._score_attacks(
            cfg.attacks, ctrl, self._underlying_bus(bus, transports), injected_records)

        return SystemResult(
            config=config_dict(cfg),
            traffic=traffic,
            coordination=coordination,
            audit=audit_bundle,
            attack_outcomes=tuple(attack_outcomes),
            backends=self._backends(live=True, transports=transports),
        )

    def _inject_sumo_attack(self, publisher, identities, registry, spec, step,
                            injected_records) -> None:
        if spec.sender not in identities:
            return
        try:
            self._inject_one(publisher, identities, registry, NoObsConn(), spec,
                             step, injected_records)
        except Exception:
            # An attack injection error must never kill the sim; record nothing.
            pass

    def _sumo_network(self):
        """Resolve (config args, adjacency, edge_map) for the chosen network."""
        cfg = self.config
        if cfg.network == "grid2x2":
            sumocfg = os.path.join(_SRC, "..", "sumo", "grid2x2.sumocfg")
            adjacency = {k: list(v) for k, v in _GRID_ADJACENCY.items()}
            return sumocfg, ["-c", sumocfg], adjacency, None

        # euston — derive adjacency + edge_map from the real net (brief).
        # euston_spine.net.xml exists (4 TLS, built with netconvert); junction
        # ids are re-derived from it via edge_map_from_net below. This path is
        # live-gated via ``requires_sumo`` (needs SUMO/sumolib installed).
        import sumolib
        net = os.path.join(_SRC, "..", "sumo", "euston", "euston_spine.net.xml")
        routes = os.path.join(_SRC, "..", "sumo", "euston", "base.rou.xml")
        adjacency, edge_map = edge_map_from_net(sumolib.net.readNet(net), mode="chain")
        adjacency = {k: list(v) for k, v in adjacency.items()}
        return net, ["-n", net, "-r", routes, "--time-to-teleport", "300"], adjacency, edge_map

    def _build_bus(self, tls, identities, registry, adjacency):
        """Build the chosen transport. Returns (bus, transports)."""
        if self.config.transport == "inprocess":
            return MessageBus(registry, adjacency), {}
        # mqtt — live-gated.
        return self._build_mqtt_bus(tls, identities, registry, adjacency)

    def _build_mqtt_bus(self, tls, identities, registry, adjacency):
        from mqtt_transport import MqttTransport, MqttTransportError
        from run_mqtt_coord import _PerJunctionAdapter, broker_reachable

        cfg = self.config
        if not broker_reachable(cfg.mqtt_host, cfg.mqtt_port):
            raise MqttTransportError(
                f"no MQTT broker reachable at {cfg.mqtt_host}:{cfg.mqtt_port}")
        transports = {}
        try:
            for jid in tls:
                jbus = MessageBus(registry, adjacency)
                tr = MqttTransport(jid, jbus, host=cfg.mqtt_host, port=cfg.mqtt_port,
                                   client_id=f"edge-system-{jid}")
                tr.connect()
                transports[jid] = tr
        except Exception:
            for tr in transports.values():
                try:
                    tr.disconnect()
                except Exception:
                    pass
            raise
        return _PerJunctionAdapter(transports), transports

    @staticmethod
    def _underlying_bus(bus, transports):
        """The bus a MaliciousPublisher should publish through.

        For inprocess this IS the MessageBus. For MQTT the publisher would need a
        single bus; attacks over a live broker are out of scope for this assembly
        (auth/conservation are transport-agnostic and proven on the inprocess
        path), so we publish into the deciding junction's receiver-side bus when
        present, else the bus itself.
        """
        if transports:
            first = next(iter(transports.values()))
            return first.bus
        return bus

    # ===================================================================== #
    # Agent backend.
    # ===================================================================== #

    def _build_agent(self):
        if self.config.agent == "stub":
            return StubAgent()
        from slm_agent import SLMAgent  # deferred: needs Foundry Local
        return SLMAgent()

    # ===================================================================== #
    # Audit-log wiring (the documented integration point).
    # ===================================================================== #

    def _mirror_registry(self, audit: AuditLog | None, registry_events,
                         identities) -> int:
        """Mirror register/revoke events into the audit chain (brief §7.2 option 1).

        Each registry event is appended tagged ``kind="registry"`` and signed by
        the affected junction's identity (when available), so identity/registry
        changes share the SAME tamper-evident chain as the decisions. Returns the
        number of registry entries appended.
        """
        if audit is None:
            return 0
        appended = 0
        for ev in registry_events:
            jid = ev.get("junction_id")
            event = {
                "kind": "registry",
                "action": ev.get("action"),
                "junction_id": jid,
                "pubkey_sha256": ev.get("pubkey_sha256"),
                # NB: the registry's own "seq" is renamed — "seq" is a RESERVED
                # AuditLog envelope key, so we carry it as "registry_seq".
                "registry_seq": ev.get("seq"),
            }
            audit.append(event, issuer=identities.get(jid))
            appended += 1
        return appended

    @staticmethod
    def _record_kinds(audit: AuditLog) -> dict:
        """Per-kind count of the inline-emitted records (the §6.2 bundle-count fix:
        it reflects the producer's message/sighting/decision/registry records, not
        the deleted _drain_audit mirror)."""
        kinds: dict[str, int] = {}
        for e in audit.entries():
            k = e["event"].get("kind")
            kinds[k] = kinds.get(k, 0) + 1
        return kinds

    def _audit_bundle(self, audit: AuditLog | None, registry_entries: int) -> dict:
        """Produce verify_chain + Merkle root + a sample inclusion proof."""
        if audit is None:
            return {"enabled": False}
        n = len(audit)
        kinds = self._record_kinds(audit)
        bundle: dict[str, Any] = {
            "enabled": True,
            "entries": n,
            "registry_entries": registry_entries,
            # ACCURATE per-kind counts (the §6.2 fix): decision_entries is now ONLY
            # the kind:"decision" records; non_registry_entries carries the sum
            # identity (message + sighting + decision) = n - registry_entries.
            "decision_entries": kinds.get("decision", 0),
            "non_registry_entries": n - registry_entries,
            "record_kinds": kinds,
            "verify_chain": audit.verify_chain(),
        }
        if n == 0:
            bundle["merkle_root"] = None
            bundle["inclusion_proof_valid"] = None
            return bundle
        root = audit.merkle_root(0, n)
        bundle["merkle_root"] = root
        # Sample inclusion proof for the LAST entry (proves a specific decision
        # is in the anchored batch from only the on-chain root).
        sample_index = n - 1
        entry_hash = audit.entries()[sample_index]["hash"]
        branch = audit.inclusion_proof(sample_index, 0, n)
        bundle["sample_inclusion"] = {
            "index": sample_index,
            "verified": verify_inclusion(entry_hash, branch, root),
            "branch_len": len(branch),
        }
        bundle["inclusion_proof_valid"] = bundle["sample_inclusion"]["verified"]
        # Cross-check: every signed entry verifies against the registered keys.
        return bundle

    # ===================================================================== #
    # Attack scoring.
    # ===================================================================== #

    def _score_attacks(self, specs, ctrl, bus, injected_records) -> list[dict]:
        """Score each injected attack against the live detectors' detection results.

        For conservation attacks (spoof / under_report): a flagged ``Detection``
        on the edge counts as detected. For auth attacks (not_neighbour / revoked
        / bad_signature): a matching ``bus.rejected`` entry counts as detected.
        Also report whether the attack was captured in the audit log (a flagged
        detection appears in the signed decision events).
        """
        outcomes: list[dict] = []
        detections = list(ctrl.detections) if ctrl is not None else []
        rejected = list(bus.rejected) if bus is not None else []
        for spec in specs:
            if spec.kind in ("spoof", "under_report"):
                flagged = [d for d in detections
                           if d.flagged and (d.src, d.dst) == (spec.sender, spec.recipient)]
                detected = bool(flagged)
                reason = flagged[0].reason if flagged else "ok"
                layer = "conservation"
                in_audit = self._attack_in_audit(ctrl, spec)
            else:
                # Match the rejection for THIS attack's (recipient, sender, tick)
                # specifically — the honest baseline's benign self-rescan also
                # logs replays on other ticks for the same sender, which are not
                # this attack's detection result.
                hits = [r for r in rejected
                        if r.get("recipient") == spec.recipient
                        and r.get("sender") == spec.sender
                        and r.get("t") == spec.tick]
                detected = bool(hits)
                reason = hits[0]["reason"] if hits else "admitted"
                layer = "auth"
                # Auth rejections are dropped BEFORE the decision, so they are not
                # in the per-decision audit chain — they live in bus.rejected.
                in_audit = False
            outcomes.append({
                "kind": spec.kind, "sender": spec.sender, "recipient": spec.recipient,
                "expected_layer": layer, "detected": detected, "reason": reason,
                "captured_in_audit": in_audit,
            })
        return outcomes

    @staticmethod
    def _attack_in_audit(ctrl, spec) -> bool:
        """True iff a flagged detection for this attack landed in a logged event.

        The controller embeds its per-round detections inside each decision event
        (``event["detections"]``), which the audit log mirrors verbatim — so a
        flagged spoof/fault is captured in the signed, hash-chained record.
        """
        if ctrl is None:
            return False
        for event in ctrl.events:
            for d in event.get("detections", ()):
                if (d.get("flagged") and d.get("src") == spec.sender
                        and d.get("dst") == spec.recipient):
                    return True
        return False

    # ===================================================================== #
    # Backend provenance.
    # ===================================================================== #

    def _backends(self, *, live: bool, transports=None) -> dict:
        cfg = self.config
        return {
            "transport": cfg.transport,
            "registry": cfg.registry,
            "agent": cfg.agent,
            "network": cfg.network,
            "run_path": "sumo" if cfg.requires_sumo else "fake_conn",
            "live": live,
            "mqtt_clients": len(transports) if transports else 0,
        }
