"""Emergency / exploit-then-defend controller for The Edge Negotiator.

Layers an EMERGENCY-VEHICLE exception handler on top of the authenticated
coordination controller, and demonstrates the project's headline security
result: a signed-but-spoofed emergency claim cannot commandeer the signal,
because preemption is gated on *corroboration* (independent physical sensing),
not on the signature alone.

This is the guarded-exception-handler architecture from the canonical spec:

  * NORMAL ticks run the parent's MaxPressure + authenticated coordination
    (unchanged: this file calls ``super().decide`` first).
  * An EMERGENCY trigger fires when a junction sees an emergency vehicle. The
    deterministic shield then enforces preemption -- but only for an
    *admissible* trigger.

Admissibility (``_admissible_ev``), straight from FORMAL-SPECIFICATION.md §4:

  * ``source == "local_sensing"``  -> admissible. The junction's OWN detector
    sees the emergency vehicle on an in-lane; you cannot spoof a physical
    vehicle into a junction's own sensor.
  * ``source == "advance_claim"``  -> admissible ONLY IF the signed claim is
    authenticated (the bus already verified the signature + membership) AND
    *corroborated* by an INDEPENDENT upstream sighting of the same vehicle
    (a different junction that physically saw it) or by local sensing.

The attack we defend: a compromised-but-approved insider (it holds a valid
key, so signatures pass) sends a signed ``ev_claim`` for a PHANTOM ambulance to
a downstream neighbour, trying to grab green and starve cross traffic. The
neighbour authenticates it (valid signature) but finds NO corroborating
sighting and sees no vehicle locally, so preemption is WITHHELD and the signal
stays on MaxPressure. The real ambulance, sensed locally as it traverses, is
preempted normally. Signing alone does not stop the insider; corroboration does.

EV messages ride a SEPARATE signed bus (``ev_bus``) from the coordination bus so
the two tick-spaces never collide; both enforce the same signature + membership
+ adjacency + replay checks. Sightings and advance-claims are signed exactly
like coordination messages.
"""
from __future__ import annotations

from audit_records import EV_POLICIES, log_decision, log_messages, log_sighting
from coordinated_controller import CoordinatedController
from identity import JunctionIdentity
from message_bus import MessageBus
from net_topology import edge_of_lane as _edge_of_lane
from registry import Registry


class EmergencyController(CoordinatedController):
    """CoordinatedController + emergency-vehicle preemption with a corroboration gate."""

    def __init__(self, *args, ev_bus: MessageBus,
                 ev_horizon: float = 195.0, verbose: bool = True,
                 narrate_junctions=None,
                 corroboration_required: bool = True,
                 preemption_enabled: bool = True,
                 advance_claims_enabled: bool = True,
                 disambiguator=None, **kwargs):
        super().__init__(*args, **kwargs)
        # Independent signed channel for EV sightings + advance-claims.
        if not isinstance(ev_bus, MessageBus):
            raise TypeError("ev_bus must be a MessageBus")
        self.ev_bus = ev_bus
        # Mode switches for the exploit-then-defend comparison:
        #   defended          : corroboration_required=True,  preemption_enabled=True
        #   naive             : corroboration_required=False, preemption_enabled=True (victim)
        #   nopreempt         : preemption_enabled=False                             (plain MaxPressure)
        #   maxpressure_preempt: advance_claims_enabled=False (local-sensing preemption
        #                        only, NO cross-junction coordination; the non-AI floor)
        self.corroboration_required = bool(corroboration_required)
        self.preemption_enabled = bool(preemption_enabled)
        self.advance_claims_enabled = bool(advance_claims_enabled)
        # Optional disambiguator for the TRIGGERED regime: a callable
        # (FlaggedCase -> "escalate_real"|"reject") that decides an ambiguous
        # advance-claim in place of the deterministic gate. None (default) keeps
        # admissibility fully deterministic, so all existing modes are unchanged.
        # This is where the SLM (or the reference rule) becomes CAUSAL.
        if disambiguator is not None and not callable(disambiguator):
            raise TypeError("disambiguator must be callable or None")
        self.disambiguator = disambiguator
        # Causal-pathway metrics for the triggered regime (analogue of
        # coord_adjusted_decisions): how often an escalated decision ran, and
        # how often it actually changed the executed phase.
        self.escalations = 0
        self.escalation_changed_decisions = 0
        if isinstance(ev_horizon, bool) or not isinstance(ev_horizon, (int, float)):
            raise TypeError("ev_horizon must be a number")
        if not (ev_horizon > 0):
            raise ValueError("ev_horizon must be > 0")
        self.ev_horizon = float(ev_horizon)
        self.verbose = verbose
        self._narrate = (frozenset(narrate_junctions)
                         if narrate_junctions is not None else None)
        # Logical clock for the EV bus (kept separate from the coord _tick).
        self._ev_tick = 0
        # Corroboration store: ev_id -> {junction_id: (edge, t)} of signed
        # sightings this controller has RECEIVED from neighbours.
        self._sightings: dict[str, dict[str, tuple[str, int]]] = {}
        # Structured EV event log for the demo summary (and tests).
        self.ev_events: list[dict] = []
        # Latch so a single ambulance preemption is announced once per junction.
        self._ev_latched: set[tuple[str, str]] = set()

    # -- local EV sensing ----------------------------------------------------

    def _sense_local_ev(self, tl: str, st: dict) -> tuple[str, str] | None:
        """Return (ev_id, in_edge) for an emergency vehicle on an in-lane within
        ev_horizon of the stop line, else None. Pure observation; never raises."""
        get_class = getattr(self.c.vehicle, "getVehicleClass", None)
        if get_class is None:
            return None
        seen: set[str] = set()
        for in_lane in st["in_lanes"]:
            if not in_lane or in_lane in seen:
                continue
            seen.add(in_lane)
            try:
                vids = self.c.lane.getLastStepVehicleIDs(in_lane)
                lane_len = float(self.c.lane.getLength(in_lane))
            except Exception:
                continue
            for vid in vids:
                try:
                    if get_class(vid) != "emergency":
                        continue
                    pos = float(self.c.vehicle.getLanePosition(vid))
                except Exception:
                    continue
                if (lane_len - pos) <= self.ev_horizon:
                    return (vid, _edge_of_lane(in_lane))
        return None

    def _phase_serving(self, st: dict, ev_edge: str) -> int | None:
        """Index of a green phase that greens a movement off ``ev_edge`` (or None)."""
        for gi, state in enumerate(st["green"]):
            for i, ch in enumerate(state):
                in_lane = st["in_lanes"][i]
                if ch in "Gg" and in_lane and _edge_of_lane(in_lane) == ev_edge:
                    return gi
        return None

    # -- EV signed channel ---------------------------------------------------

    def _ev_publish(self, tl: str, payload: dict) -> None:
        """Sign + publish an EV message from ``tl`` on the EV bus (own tick)."""
        ident = self.identities.get(tl)
        if ident is None:
            return
        try:
            self.ev_bus.publish(ident, self._ev_tick, payload)
        except Exception:
            pass
        self._ev_tick += 1

    def _ingest_ev_inbox(self, tl: str) -> tuple[list[dict], list]:
        """Read verified EV messages for ``tl``; update the sighting store.

        Returns ``(claims, driving_pairs)``: ``claims`` = authenticated
        advance-claims addressed to ``tl`` (each ``{"from","ev_id","approach_edge",
        "t"}``); ``driving_pairs`` = the ``[seq, sighter_key]`` of EVERY consumed
        verified EV message (§6.2 -- sightings AND claims), for the EV decision's
        driving_input_seqs. §6.2: STOP DISCARDING ``m.signature`` -- each consumed
        message is logged as a §11 kind:"message" record (its .signature.hex() +
        the registry DER at consumption); for a sighting the (seq, sighter_key) is
        also what the corroboration store references. Sightings are still folded
        into ``self._sightings`` for the corroboration recompute.
        """
        claims: list[dict] = []
        driving_pairs: list = []
        try:
            messages = self.ev_bus.inbox(tl)
        except Exception:
            return claims, driving_pairs
        for m in messages:
            # §6.2: log the verified message (was discarding m.signature here).
            msg_pairs = log_messages(self.audit_log, self.registry,
                                     self.identities, tl, [m])
            driving_pairs = [*driving_pairs, *msg_pairs]
            payload = m.payload if isinstance(m.payload, dict) else {}
            sighting = payload.get("sighting")
            if isinstance(sighting, dict):
                ev_id = sighting.get("ev_id")
                edge = sighting.get("edge")
                if isinstance(ev_id, str) and isinstance(edge, str):
                    by_j = dict(self._sightings.get(ev_id, {}))
                    by_j[m.sender] = (edge, m.t)
                    self._sightings = {**self._sightings, ev_id: by_j}
            claim = payload.get("ev_claim")
            if isinstance(claim, dict) and claim.get("target") == tl:
                ev_id = claim.get("ev_id")
                edge = claim.get("approach_edge")
                if isinstance(ev_id, str) and isinstance(edge, str):
                    claims.append({"from": m.sender, "ev_id": ev_id,
                                   "approach_edge": edge, "t": m.t})
        return claims, driving_pairs

    def _corroborated(self, ev_id: str, claimer: str, tl: str,
                      local_ev: tuple[str, str] | None) -> bool:
        """True iff an INDEPENDENT source confirms ``ev_id`` (not the claimer).

        Independent = this junction's own local sensing of that vehicle, OR a
        signed sighting of the same vehicle from a junction other than the one
        making the claim. A phantom vehicle satisfies neither.
        """
        if local_ev is not None and local_ev[0] == ev_id:
            return True
        for junction in self._sightings.get(ev_id, {}):
            if junction != claimer and junction != tl:
                return True
        return False

    def _admissible_ev(self, source: str, ev_id: str, claimer: str | None,
                       tl: str, local_ev: tuple[str, str] | None) -> bool:
        """FORMAL-SPEC §4 admissibility: local sensing trusted; a claim needs
        authentication (already done by the bus) AND corroboration."""
        if source == "local_sensing":
            return True
        if source == "advance_claim":
            if not self.corroboration_required:
                return True  # naive victim: trusts any authenticated claim
            return self._corroborated(ev_id, claimer or "", tl, local_ev)
        return False

    def inject_phantom_claim(self, from_junction: str, target: str,
                             ev_id: str, approach_edge: str) -> None:
        """Demo attack hook: a COMPROMISED-but-approved ``from_junction`` signs an
        ``ev_claim`` for a phantom EV approaching ``target``. The signature is
        valid (genuine member key), so the bus delivers it; only corroboration
        stops it. Called from the demo orchestration at a scripted time."""
        self._ev_publish(from_junction, {"ev_claim": {
            "ev_id": ev_id, "target": target, "approach_edge": approach_edge}})

    # -- decision ------------------------------------------------------------

    def decide(self, tl: str, st: dict) -> int:
        used = super().decide(tl, st)  # normal coordinated / MaxPressure choice
        if tl not in self.slm or tl not in self.identities:
            return used
        if not self.preemption_enabled:
            return used  # nopreempt mode: plain MaxPressure + coordination

        # driving_input_seqs for THIS EV decision: the FULL set of consumed signed
        # EV inputs (from the inbox) PLUS the keyless local sighting (a [seq, null]
        # pair -- §11 keyless encoding: sighting_key AND signature both null).
        ev_driving_pairs: list = []

        local_ev = self._sense_local_ev(tl, st)
        # Publish a signed sighting + advance-claims downstream when we see one.
        # Advance-claims are the cross-junction coordination; maxpressure_preempt
        # disables them (local-sensing preemption only).
        local_sighting_seq = None
        if local_ev is not None:
            ev_id, ev_edge = local_ev
            # §6.2: the junction's OWN sensor reading is a KEYLESS local sighting
            # (§6.4 sensor-fed-spoof surface) -> a §11 kind:"sighting" record with
            # sighter_key null (its signature is the null envelope sig, issuer=None).
            local_sighting_seq = log_sighting(
                self.audit_log, ev_id, ev_edge, self._sim_time())
            self._ev_publish(tl, {"sighting": {"ev_id": ev_id, "edge": ev_edge,
                                               "t": self._ev_tick}})
            if self.advance_claims_enabled:
                for nb in self.adjacency.get(tl, ()):  # pre-position neighbours
                    self._ev_publish(tl, {"ev_claim": {
                        "ev_id": ev_id, "target": nb,
                        "approach_edge": self._edge_id(tl, nb) or ""}})

        if self.advance_claims_enabled:
            claims, ingest_pairs = self._ingest_ev_inbox(tl)
            ev_driving_pairs = [*ev_driving_pairs, *ingest_pairs]
        else:
            claims = []
        if local_sighting_seq is not None:
            ev_driving_pairs = [*ev_driving_pairs, [local_sighting_seq, None]]

        # Build the highest-priority admissible EV trigger. Local sensing wins.
        trig = None
        if local_ev is not None:
            trig = {"source": "local_sensing", "ev_id": local_ev[0],
                    "approach_edge": local_ev[1], "claimer": None}
        elif claims:
            c0 = claims[0]
            trig = {"source": "advance_claim", "ev_id": c0["ev_id"],
                    "approach_edge": c0["approach_edge"], "claimer": c0["from"]}

        if trig is None:
            return used

        # Admissibility. Local sensing is always deterministic. An advance claim
        # is decided by the disambiguator (SLM or reference rule) when one is
        # configured AND this is a genuinely ambiguous case; otherwise by the
        # deterministic corroboration gate. The shield still applies: the
        # disambiguator can never force preemption the gate would refuse on
        # zero evidence (it only arbitrates the ambiguous middle).
        det_admissible = self._admissible_ev(
            trig["source"], trig["ev_id"], trig["claimer"], tl, local_ev)
        escalated = False
        if trig["source"] == "advance_claim" and self.disambiguator is not None:
            escalated = True
            self.escalations += 1
            case = self._build_flagged_case(trig, tl, local_ev)
            try:
                decision = self.disambiguator(case)
            except Exception:
                decision = None
            # SAFETY: the disambiguator arbitrates the ambiguous middle but can
            # only WITHHOLD, never ADD preemption. A claim the deterministic gate
            # refuses stays refused (a broken or hostile disambiguator can never
            # force a phantom green); a gate-admitted claim it rejects is withheld.
            # So preemption always still requires the deterministic gate.
            admissible = det_admissible and (decision == "escalate_real")
        else:
            admissible = det_admissible

        preempt = (self._phase_serving(st, trig["approach_edge"])
                   if admissible else None)
        executed = preempt if preempt is not None else used
        if escalated and executed != used:
            self.escalation_changed_decisions += 1

        ev = {"tl": tl, "t": int(self._sim_time()), "source": trig["source"],
              "ev_id": trig["ev_id"], "claimer": trig["claimer"],
              "approach_edge": trig["approach_edge"], "admissible": admissible,
              "escalated": escalated,
              "corroborated": (trig["source"] == "local_sensing"
                               or self._corroborated(trig["ev_id"],
                                                     trig["claimer"] or "", tl,
                                                     local_ev)),
              "preempt_phase": preempt, "mp_used": used, "executed": executed}
        self.ev_events.append(ev)
        self._narrate_ev(ev)

        # §6.2 item 4 + item 5 (CAUSAL RECORD RULE, PINNED): emit the §11
        # kind:"decision" for this EV preempt/withhold (today the EV path emitted
        # no decision record). When an EV junction fires BOTH a coordination
        # decision (super().decide, above) AND this EV decision the SAME tick, the
        # EV decision is the CAUSAL one for attribution -- recognised downstream by
        # its driving inputs carrying an ev_id (the ev-claim message OR the keyless
        # sighting), which the coordination decision's inputs never carry. The EV
        # decision applies policy `corroboration`; classification is the RUNTIME EV
        # label (LEGITIMATE iff admissible else SPOOFED_OR_FAULTY), DISTINCT from
        # ORIGIN (assessment.py MUST NOT read it for origin).
        log_decision(self.audit_log, self.identities, tl, ev_driving_pairs,
                     self._sim_time(), executed,
                     "LEGITIMATE" if admissible else "SPOOFED_OR_FAULTY",
                     list(EV_POLICIES))
        return executed

    def _build_flagged_case(self, trig: dict, tl: str, local_ev):
        """Assemble a FlaggedCase from the live EV state for the disambiguator.

        Live EV triggers do not carry a conservation residual (that path is for
        routine release claims), so residual/persistence are reported as 0; the
        curated Experiment-1 dataset is where those features vary. split/label
        are placeholders (deciders never read them)."""
        from ambiguous_decision import FlaggedCase
        seen = self._sightings.get(trig["ev_id"], {})
        indep = [j for j in seen if j != (trig["claimer"] or "") and j != tl]
        corr = len(indep)
        return FlaggedCase(
            case_id=f"live-{tl}-{trig['ev_id']}-{int(self._sim_time())}",
            event_type="emergency_claim",
            corroboration_count=corr,
            residual=0.0, persistence=0,
            neighbour_agreement=1.0 if corr > 0 else 0.0,
            local_sensing=local_ev is not None and local_ev[0] == trig["ev_id"],
            severity=0.5, split="novel", label="real")

    def _narrate_ev(self, ev: dict) -> None:
        if not self.verbose:
            return
        if self._narrate is not None and ev["tl"] not in self._narrate:
            return
        tl, t = ev["tl"], ev["t"]
        if ev["source"] == "local_sensing":
            key = (tl, ev["ev_id"])
            if key in self._ev_latched:
                return
            self._ev_latched.add(key)
            print(f"[t={t}s | {tl}] EMERGENCY sensed LOCALLY ({ev['ev_id']} on "
                  f"{ev['approach_edge']}) -> ADMISSIBLE -> PREEMPT phase "
                  f"{ev['preempt_phase']} (own sensor, cannot be spoofed)")
        else:  # advance_claim
            if ev["admissible"]:
                print(f"[t={t}s | {tl}] signed EV claim from {ev['claimer']} "
                      f"({ev['ev_id']}) CORROBORATED by independent sighting "
                      f"-> PREEMPT phase {ev['preempt_phase']}")
            else:
                print(f"[t={t}s | {tl}] signed EV claim from {ev['claimer']} "
                      f"({ev['ev_id']}): authenticated (valid signature, approved "
                      f"member) but NOT corroborated by an independent sighting "
                      f"or local vehicle -> PREEMPTION WITHHELD -> stays on "
                      f"MaxPressure (phase {ev['mp_used']}). A SPOOFED claim is "
                      f"stopped here; a real one simply waits until a junction "
                      f"physically confirms it -- the gate needs evidence, not intent.")
