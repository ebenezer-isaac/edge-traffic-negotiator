"""Coordinated controller: authenticated cross-junction coordination layer.

Milestone-2 (brief Wk 3-4). Wraps the existing event-gated hybrid
(SLM proposes / MaxPressure shield disposes) with a *signed* neighbour-message
exchange so that adjacent junctions can influence one another's phase choice and
so that their claims can be reconciled against observation (conservation check).

On each SLM-junction decision (i.e. when the parent hybrid would consult the SLM),
this controller:

  (a) PUBLISHES a signed message whose payload is
      ``{"toward": {neighbour_id: {"release": <int>, "queue_forecast": <int>}}}``
      (per COORDINATION-ALGORITHM-SPEC §4.1). ``release`` is the count of vehicles
      this junction is about to release toward that neighbour THIS phase -- the
      upstream halting count on the in-lanes whose served out-lane sits on the edge
      that leads to that neighbour (edge ``XY`` => src ``X`` -> dst ``Y``; the
      out-lane's edge dst is the neighbour). ``queue_forecast`` is a short-horizon
      load forecast for that approach.

      PLACEHOLDER (documented honestly, per spec §6.2): we do not yet have a
      validated roll-forward model, so ``queue_forecast == release`` -- it carries
      no extra predictive precision today. The field exists so the wire schema and
      the conservation contract are cleanly separated (R1): conservation consumes
      ONLY ``release`` (an actual outflow), never the forecast (you cannot conserve
      a prediction). When a real forecast lands, only ``_toward_counts`` changes.

  (b) READS its inbox (verified, authorised, non-replayed neighbour messages) and
      sums the verified incoming ``release`` across neighbours to get
      ``expected_incoming``, AND attributes each neighbour's incoming release to the
      LOCAL green phases that serve its in-edge -> ``incoming_per_phase[gi]``.

  (c) Computes a DETERMINISTIC coordination-adjusted reference choice (Channel B,
      spec §2.2): ``adj_halting[gi] = green_halting[gi] + coord_weight *
      incoming_per_phase[gi]`` and takes its argmax as the shield's coordinated
      reference. With ``coord_weight == 0.0`` this reproduces today's behaviour
      exactly. It passes the per-phase incoming numbers into the SLM note so the
      prompt reflects per-phase incoming (Channel A), not just a total. The final
      ``used`` decision is the SLM proposal if valid, else the coordination-adjusted
      deterministic choice (the shield still disposes).

  (d) Feeds claims (from the inbox, ONLY the actual ``release`` -- never the
      forecast) + observed inflows (halting on the relevant in-edges) to the
      ConservationChecker and stashes any Detections on ``self.detections``.

Every SLM decision is logged exactly as the parent does; published / received /
detection info is ADDED to each event dict. All structures are rebuilt rather
than mutated (immutability rule): inputs are never mutated in place.

A tiny deterministic :class:`StubAgent` (argmax over the per-phase queue) is
provided so coordinated/uncoordinated runs are CI-able without Foundry Local.
"""
from __future__ import annotations

from conservation import ConservationChecker, Detection
from hybrid_controller import HybridController
from identity import JunctionIdentity
from message_bus import MessageBus
from registry import Registry


class StubAgent:
    """Deterministic stand-in for SLMAgent: pick the longest-queue phase.

    Mirrors :meth:`SLMAgent.choose_phase` (including the ``neighbor_note`` kwarg)
    so coordinated/uncoordinated runs are reproducible and need no Foundry Local.
    """

    model = "stub"

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = ""):  # noqa: ARG002 - note unused in stub
        if not halting_per_phase:
            return None
        return max(range(len(halting_per_phase)), key=lambda i: halting_per_phase[i])


def _edge_of_lane(lane_id: str) -> str:
    """Edge id of a lane id (``"A0A1_0"`` -> ``"A0A1"``)."""
    return lane_id.rsplit("_", 1)[0]


def _split_edge(edge_id: str, junctions: frozenset[str]) -> tuple[str, str] | None:
    """Split a grid edge id ``src+dst`` into (src, dst) using known junction ids.

    Edge ids are the concatenation of two junction ids (e.g. ``"A0A1"`` =>
    ``("A0", "A1")``). Edges touching dead-ends (``"left0A0"``, ``"A0left0"``)
    have one endpoint that is not a signalised junction; for those we return the
    split only when *both* endpoints are known junctions, else None. We test the
    prefix against the known-junction set so variable-length ids stay correct.
    """
    for jid in junctions:
        if edge_id.startswith(jid):
            rest = edge_id[len(jid):]
            if rest in junctions:
                return jid, rest
    return None


class CoordinatedController(HybridController):
    """Hybrid controller + authenticated neighbour coordination & reconciliation."""

    def __init__(self, conn, tls_ids, agent,
                 identities: dict[str, JunctionIdentity],
                 registry: Registry,
                 bus: MessageBus,
                 adjacency: dict[str, list[str]],
                 checker: ConservationChecker | None = None,
                 slm_junctions=None, gate: int = 2,
                 min_green: int = 10, yellow: int = 3,
                 coord_weight: float = 1.0):
        super().__init__(conn, tls_ids, agent, slm_junctions=slm_junctions,
                         gate=gate, min_green=min_green, yellow=yellow)
        # Read-only references; we never mutate the caller's structures.
        self.identities = dict(identities)
        self.registry = registry
        self.bus = bus
        self.adjacency = {k: tuple(v) for k, v in adjacency.items()}
        self.checker = checker if checker is not None else ConservationChecker()
        self.detections: list[Detection] = []
        # Lambda for the deterministic Channel-B coordination term (spec §2.2).
        # Validate at the boundary; coord_weight == 0.0 must reproduce today's
        # plain MaxPressure choice exactly (clean ablation / regression baseline).
        if isinstance(coord_weight, bool) or not isinstance(coord_weight, (int, float)):
            raise TypeError(
                f"coord_weight must be a number, got {type(coord_weight).__name__}")
        if coord_weight != coord_weight or coord_weight in (float("inf"), float("-inf")):
            raise ValueError("coord_weight must be finite")
        if coord_weight < 0:
            raise ValueError(f"coord_weight must be >= 0, got {coord_weight}")
        self.coord_weight = float(coord_weight)
        # Count of decisions where the coordination-adjusted deterministic choice
        # differed from the plain MaxPressure choice -- the proof the pathway is
        # CAUSAL even when travel-time is unchanged (see run_coordinated metrics).
        self.coord_adjusted_decisions = 0
        # Known signalised junctions, for parsing edge ids into (src, dst).
        self._junctions = frozenset(self.identities.keys())
        # Edge id -> set of lane ids, built ONCE from the lanes TraCI already
        # revealed to the controller (in_lanes / out_lanes of every TLS). Using
        # only known lanes avoids speculative probing that would otherwise spam
        # SUMO "lane not known" errors for single-lane grid edges.
        edge_lanes: dict[str, set[str]] = {}
        for state in self.tls.values():
            for lane in (*state["in_lanes"], *state["out_lanes"]):
                if not lane:
                    continue
                edge = _edge_of_lane(lane)
                edge_lanes = {**edge_lanes, edge: edge_lanes.get(edge, set()) | {lane}}
        self._edge_lanes = {e: tuple(sorted(lanes)) for e, lanes in edge_lanes.items()}
        # Logical decision clock: increments per SLM decision so each published
        # message gets a fresh tick (the bus replay guard keys on (recip,sender,t)).
        self._tick = 0

    def _incoming_per_phase(self, st: dict, incoming_by_neighbour: dict[str, int],
                            tl: str) -> list[int]:
        """Attribute each neighbour's incoming release to the green phases serving it.

        Incoming traffic from neighbour ``X`` arrives on edge ``X{tl}`` (src ``X``
        -> dst ``tl``), which feeds specific local in-lanes. A green phase ``gi``
        serves a movement ``i`` iff ``st["green"][gi][i]`` is in ``"Gg"``. So
        neighbour ``X``'s incoming release counts toward phase ``gi`` iff ``gi``
        gives green to *any* movement whose in-lane sits on edge ``X{tl}``.

        Returns ``incoming_per_phase`` with one entry per green phase (fresh list).
        A neighbour whose release is attributed to several phases that all serve its
        approach is counted in each such phase (the phases are mutually exclusive
        green sets, so this reflects "this phase would admit that platoon"). Each
        neighbour contributes to at least one phase only if a movement off its edge
        is greened by some phase; un-served approaches contribute nothing.
        """
        ngreen = len(st["green"])
        per_phase = [0] * ngreen
        for nb, amount in incoming_by_neighbour.items():
            if amount <= 0:
                continue
            in_edge = f"{nb}{tl}"  # edge neighbour -> this junction
            # Movement indices whose in-lane sits on this neighbour's in-edge.
            served_movements = {
                i for i, in_lane in enumerate(st["in_lanes"])
                if in_lane and _edge_of_lane(in_lane) == in_edge
            }
            if not served_movements:
                continue
            for gi in range(ngreen):
                state = st["green"][gi]
                if any(state[i] in "Gg" for i in served_movements if i < len(state)):
                    per_phase = [
                        p + amount if g == gi else p
                        for g, p in enumerate(per_phase)
                    ]
        return per_phase

    def _toward_counts(self, st: dict, gi: int) -> dict[str, int]:
        """Vehicles this junction is about to release toward each neighbour.

        For the green phase ``gi`` about to be served, sum the upstream halting
        count on each served movement's *in-lane* and attribute it to the
        neighbour the movement's *out-lane edge* leads to. Returns a fresh dict.

        This is the ACTUAL ``release`` (today's outflow), fed verbatim into the
        conservation check. It is NOT a forecast.
        """
        halting = self.c.lane.getLastStepHaltingNumber
        toward: dict[str, int] = {}
        state = st["green"][gi]
        for i, ch in enumerate(state):
            if ch not in "Gg":
                continue
            out_lane = st["out_lanes"][i]
            in_lane = st["in_lanes"][i]
            if not out_lane or not in_lane:
                continue
            split = _split_edge(_edge_of_lane(out_lane), self._junctions)
            if split is None:
                continue  # movement exits the grid (dead-end) -> no neighbour
            neighbour = split[1]
            toward = {**toward, neighbour: toward.get(neighbour, 0)
                      + halting(in_lane)}
        return toward

    def _observed_inflows(self, recipient: str, neighbours) -> dict[str, int]:
        """Observed halting vehicles on each in-edge ``neighbour->recipient``.

        Returns ``{neighbour_id: halting_on_edge(neighbour->recipient)}``: the
        independent observation ``recipient`` makes of traffic arriving from each
        neighbour, used to reconcile that neighbour's claim. Fresh dict.
        """
        halting = self.c.lane.getLastStepHaltingNumber
        observed: dict[str, int] = {}
        for nb in neighbours:
            edge = f"{nb}{recipient}"  # edge nb -> recipient
            count = 0
            for lane_id in self._edge_lanes.get(edge, ()):
                count += halting(lane_id)
            observed = {**observed, nb: count}
        return observed

    def decide(self, tl: str, st: dict) -> int:
        mp_choice = super(HybridController, self).decide(tl, st)  # MaxPressure
        if tl not in self.slm:
            return mp_choice

        halting = [self.green_halting(st, gi) for gi in range(len(st["green"]))]
        if sum(halting) < self.gate:  # event-gate: quiet -> shield only
            return mp_choice

        # Only coordinate for junctions that have an identity to sign with.
        if tl not in self.identities:
            # Fall back to the parent hybrid behaviour (still log via parent).
            return super().decide(tl, st)

        tick = self._tick
        self._tick += 1
        neighbours = self.adjacency.get(tl, ())

        # (a) PUBLISH a signed message for the phase we'd serve next. The payload
        #     separates the ACTUAL release from a short-horizon queue_forecast
        #     (R1 / spec §4.1). queue_forecast is a documented PLACEHOLDER equal to
        #     release today -- no real roll-forward model yet (spec §6.2).
        toward_release = self._toward_counts(st, mp_choice)
        toward_payload = {
            nb: {"release": rel, "queue_forecast": rel}  # placeholder: forecast == release
            for nb, rel in toward_release.items()
        }
        published = None
        try:
            msg = self.bus.publish(self.identities[tl], tick, {"toward": toward_payload})
            published = {"t": msg.t, "toward": {
                nb: dict(v) for nb, v in msg.payload.get("toward", {}).items()}}
        except Exception as exc:  # never let a transport error kill the sim
            published = {"error": type(exc).__name__}

        # (b) READ inbox: verified incoming `release` toward this junction per peer.
        #     ONLY the actual release feeds expected_incoming / claims / per-phase;
        #     queue_forecast is never conserved (R1, spec §6.2).
        received = []
        expected_incoming = 0
        incoming_by_neighbour: dict[str, int] = {}
        claims: dict[tuple[str, str], int] = {}
        try:
            for m in self.bus.inbox(tl):
                sender_toward = m.payload.get("toward", {})
                if not isinstance(sender_toward, dict):
                    continue
                entry = sender_toward.get(tl, {})
                # New shape: {"release": int, "queue_forecast": int}. Be strict at
                # the boundary -- reject anything that is not a well-formed object.
                if not isinstance(entry, dict):
                    continue
                amount = entry.get("release", 0)
                forecast = entry.get("queue_forecast", 0)
                if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
                    continue  # reject malformed/hostile release at the boundary
                if isinstance(forecast, bool) or not isinstance(forecast, int) or forecast < 0:
                    forecast = 0  # forecast is advisory only; clamp hostile values
                expected_incoming += amount
                incoming_by_neighbour = {
                    **incoming_by_neighbour,
                    m.sender: incoming_by_neighbour.get(m.sender, 0) + amount,
                }
                received = [*received, {"from": m.sender, "t": m.t,
                                        "release": amount, "queue_forecast": forecast}]
                # Claim: sender claims it released `amount` toward us (edge sender->tl).
                # CONSERVATION CONSUMES ONLY `release` (actual), never the forecast.
                key = (m.sender, tl)
                claims = {**claims, key: claims.get(key, 0) + amount}
        except Exception as exc:
            received = [{"error": type(exc).__name__}]

        # (c) Channel B: deterministic coordination-adjusted reference choice.
        #     adj_halting[gi] = green_halting[gi] + coord_weight * incoming_per_phase[gi]
        incoming_per_phase = self._incoming_per_phase(st, incoming_by_neighbour, tl)
        adj_halting = [
            halting[gi] + self.coord_weight * incoming_per_phase[gi]
            for gi in range(len(halting))
        ]
        # The coordinated deterministic choice (the shield's coordinated reference).
        # With coord_weight == 0.0 this is argmax over plain halting; to reproduce
        # the plain MaxPressure choice EXACTLY (same tie-breaking), short-circuit.
        if self.coord_weight == 0.0:
            coord_choice = mp_choice
        else:
            coord_choice = max(range(len(adj_halting)), key=lambda gi: adj_halting[gi])
        # CRUCIAL METRIC: did coordination change the deterministic choice?
        coord_changed = coord_choice != mp_choice
        if coord_changed:
            self.coord_adjusted_decisions += 1

        # (c') Channel A: build a per-phase neighbour note and consult the agent.
        if expected_incoming > 0:
            per_phase_bits = ", ".join(
                f"phase {gi} +{incoming_per_phase[gi]}"
                for gi in range(len(incoming_per_phase)) if incoming_per_phase[gi] > 0
            )
            note = (f"Incoming from neighbours toward this junction "
                    f"({expected_incoming} total): {per_phase_bits}. "
                    f"Serve the phase facing the worst combined pressure.")
        else:
            note = ""
        proposal = self.agent.choose_phase(tl, len(st["green"]), halting, neighbor_note=note)
        # Shield disposes: SLM proposal if valid else the coordination-adjusted choice.
        used = proposal if proposal is not None else coord_choice

        # (d) Reconcile claims vs observed inflows; stash Detections.
        new_detections: list[Detection] = []
        if claims:
            claim_srcs = {src for (src, _dst) in claims.keys()}
            observed_by_nb = self._observed_inflows(tl, claim_srcs)
            observed = {(src, tl): observed_by_nb.get(src, 0) for src in claim_srcs}
            try:
                new_detections = self.checker.evaluate(claims, observed)
            except Exception:
                new_detections = []
            self.detections = [*self.detections, *new_detections]

        self.events.append({
            "tls": tl, "halting": halting,
            "slm_phase": proposal, "shield_phase": mp_choice, "used": used,
            "overridden": proposal is None or proposal != mp_choice,
            "tick": tick,
            "published": published,
            "expected_incoming": expected_incoming,
            "incoming_per_phase": incoming_per_phase,
            "mp_choice": mp_choice,
            "coord_choice": coord_choice,
            "coord_changed": coord_changed,
            "received": received,
            "neighbor_note": note,
            "detections": [
                {"src": d.src, "dst": d.dst, "claimed": d.claimed,
                 "observed": d.observed, "delta": d.delta,
                 "flagged": d.flagged, "reason": d.reason}
                for d in new_detections
            ],
        })
        return used
