"""Coordinated controller: authenticated cross-junction coordination layer.

Wraps the event-gated hybrid (SLM proposes /
MaxPressure shield disposes) with a *signed* neighbour-message exchange so
adjacent junctions influence one another's phase choice and reconcile their
claims against observation (conservation check). On each SLM-junction decision:

  (a) PUBLISHES a signed ``{"toward": {nb: {"release", "queue_forecast"}}}``
      message (COORDINATION-ALGORITHM-SPEC §4.1). ``release`` = vehicles released
      toward that neighbour this phase. ``queue_forecast`` is a documented
      PLACEHOLDER equal to ``release`` (no roll-forward model yet, spec §6.2);
      conservation consumes ONLY ``release`` (R1), never a forecast.
  (b) READS its inbox (verified/authorised/non-replayed messages), sums incoming
      ``release`` (``expected_incoming``) and attributes it to the green phases
      serving each in-edge (``incoming_per_phase[gi]``).
  (c) Channel B (spec §2.2): ``adj_halting[gi] = green_halting[gi] + coord_weight
      * incoming_per_phase[gi]``; ``coord_weight == 0.0`` reproduces today's
      choice exactly. ``used`` = SLM proposal if valid else the coord choice.
  (d) Feeds claims + observed inflows to the ConservationChecker; Detections land
      on ``self.detections``.

Every SLM decision is logged on ``self.events`` (published/received/detection
info added). With ``audit_log`` injected (§6.2), the §11 message/decision records
are ALSO emitted inline. All structures are rebuilt, never mutated in place.
:class:`StubAgent` (argmax over the per-phase queue) makes runs CI-able w/o Foundry.
"""
from __future__ import annotations

from audit_records import coordination_policies, log_decision, log_messages
from conservation import ConservationChecker, Detection
from flow_accounting import FlowWindow
from flow_conservation import EdgeMeasurement, FlowConservationDetector
from hybrid_controller import HybridController, served_by
from identity import JunctionIdentity
from message_bus import MessageBus
# Topology helpers live in net_topology (file-size limit). edge_map_from_net is
# RE-EXPORTED for backward compatibility: callers still import it from this
# module. The two private grid helpers keep their leading-underscore names here.
from net_topology import edge_map_from_net  # noqa: F401
from net_topology import edge_of_lane as _edge_of_lane
from net_topology import split_edge as _split_edge
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
                 coord_weight: float = 1.0,
                 edge_map: dict[tuple[str, str], str] | None = None,
                 coord_override: bool = False,
                 coord_override_threshold: float = 0.0,
                 reconcile_silent_neighbours: bool = False,
                 flow_window: float = 0.0, *, audit_log=None):
        super().__init__(conn, tls_ids, agent, slm_junctions=slm_junctions,
                         gate=gate, min_green=min_green, yellow=yellow)
        # §6.2 producer wiring: keyword-only AuditLog injection. None (default) =
        # today's behaviour, byte-for-byte (emit NOTHING); when present, decide()
        # emits the §11 message/decision records inline as it consumes + decides.
        self.audit_log = audit_log
        # Read-only references; we never mutate the caller's structures.
        self.identities = dict(identities)
        self.registry = registry
        self.bus = bus
        self.adjacency = {k: tuple(v) for k, v in adjacency.items()}
        self.checker = checker if checker is not None else ConservationChecker()
        self.detections: list[Detection] = []
        # Set by decide() each call so edge_map resolvers know the deciding junction.
        self._current_tl: str | None = None
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

        # P1 -- generalised edge resolution. When an explicit edge_map is given
        # (maps (src_junction, dst_junction) -> edge_id, the edge ENTERING dst
        # from src) we resolve toward/observed/per-phase via the map instead of
        # the grid f"{src}{dst}" string convention. When None we FALL BACK to the
        # grid name-parsing (existing behaviour unchanged). This makes coordination
        # work on real OSM nets whose edge ids are not junction-id concatenations.
        if edge_map is not None:
            if not isinstance(edge_map, dict):
                raise TypeError("edge_map must be a dict or None")
            for key, eid in edge_map.items():
                if (not isinstance(key, tuple) or len(key) != 2
                        or not all(isinstance(p, str) for p in key)):
                    raise TypeError(
                        f"edge_map key must be a (src: str, dst: str) tuple, got {key!r}")
                if not isinstance(eid, str):
                    raise TypeError(
                        f"edge_map[{key!r}] must be an edge-id str, got {type(eid).__name__}")
            self._edge_map: dict[tuple[str, str], str] | None = dict(edge_map)
            # Invert: per junction, edge-id -> downstream neighbour it leads to.
            # The in-edge of (tl -> nb) is exactly an edge tl releases toward nb.
            out_to_nb: dict[str, dict[str, str]] = {}
            for (src, dst), eid in self._edge_map.items():
                out_to_nb = {**out_to_nb,
                             src: {**out_to_nb.get(src, {}), eid: dst}}
            self._out_edge_to_neighbour = {k: dict(v) for k, v in out_to_nb.items()}
        else:
            self._edge_map = None
            self._out_edge_to_neighbour = {}

        # P4 -- Channel-B override. When True, if the coordination-adjusted choice
        # disagrees with a valid SLM proposal by more than the threshold (in
        # adjusted-pressure units), the shield's coordination choice WINS (true
        # "shield disposes"). Default False preserves today's behaviour exactly.
        if not isinstance(coord_override, bool):
            raise TypeError("coord_override must be a bool")
        if (isinstance(coord_override_threshold, bool)
                or not isinstance(coord_override_threshold, (int, float))):
            raise TypeError("coord_override_threshold must be a number")
        if (coord_override_threshold != coord_override_threshold
                or coord_override_threshold in (float("inf"), float("-inf"))):
            raise ValueError("coord_override_threshold must be finite")
        if coord_override_threshold < 0:
            raise ValueError("coord_override_threshold must be >= 0")
        self.coord_override = coord_override
        self.coord_override_threshold = float(coord_override_threshold)
        # Count of decisions where coord_override actually flipped the realized
        # decision away from a valid SLM proposal (proof the override is causal).
        self.coord_override_decisions = 0

        # P3 -- sensor-outage / silent-neighbour reconciliation. OPT-IN (default
        # False) so existing wiring is UNCHANGED. When True, decide() feeds an
        # observed-only edge to the checker for every registered, approved
        # neighbour that went silent AND on whose in-edge traffic is observed --
        # so a fully-silent neighbour makes `missing_claim` reachable live.
        if not isinstance(reconcile_silent_neighbours, bool):
            raise TypeError("reconcile_silent_neighbours must be a bool")
        self.reconcile_silent_neighbours = reconcile_silent_neighbours
        # WINDOWED ACTUAL-FLOW ACCOUNTING (the false-positive fix). flow_window > 0
        # compares LIKE-FOR-LIKE actual flow (distinct vehicles that ENTERED edge
        # self->neighbour over the window) via the intelligent detector below;
        # flow_window == 0 (DEFAULT) runs the legacy instantaneous-halting feed +
        # flat ConservationChecker verbatim, so existing tests are byte-for-byte.
        if isinstance(flow_window, bool) or not isinstance(flow_window, (int, float)):
            raise TypeError(
                f"flow_window must be a number, got {type(flow_window).__name__}")
        if flow_window != flow_window or flow_window in (float("inf"), float("-inf")):
            raise ValueError("flow_window must be finite")
        if flow_window < 0:
            raise ValueError(f"flow_window must be >= 0, got {flow_window}")
        self.flow_window_s = float(flow_window)
        # The sliding-window accumulator is only built (and only fed in step())
        # when windowing is enabled. Immutable: step() swaps the reference.
        self._flow: FlowWindow | None = (
            FlowWindow(window=self.flow_window_s) if self.flow_window_s > 0 else None)
        # INTELLIGENT DETECTOR (Part A): in windowed mode the live feed reconciles
        # via the mass-balance + adaptive-band + CUSUM persistence detector
        # (flow_conservation), one instance tracking all watched edges by edge id.
        self._fc_detector: FlowConservationDetector | None = (
            FlowConservationDetector() if self._flow is not None else None)
        # Edges we watch for entry events: every in-edge (peer->junction) and
        # out-edge (junction->peer) implied by the adjacency, resolved once.
        self._watched_edges = self._resolve_watched_edges()
        # Per-edge congestion metadata for the windowed detector's spillback test:
        # edge_id -> (occupancy_fraction, mean_speed_m_s, free_speed_m_s). Empty
        # until step() refreshes it; the legacy path never reads it. Free speed is
        # read ONCE from each watched edge's lanes (best-effort, transport-safe).
        self._edge_meta: dict[str, tuple[float, float, float]] = {}
        self._edge_free_speed: dict[str, float] = {}
        if self._flow is not None:
            self._edge_free_speed = self._read_free_speeds()

    def _edge_id(self, src: str, dst: str) -> str | None:
        """Edge id carrying traffic released by ``src`` toward ``dst`` (or None).

        Uses the explicit edge_map when present, else the grid ``f"{src}{dst}"``
        convention. Returns None when no such edge is known.
        """
        if self._edge_map is not None:
            return self._edge_map.get((src, dst))
        return f"{src}{dst}"

    def _resolve_watched_edges(self) -> tuple[str, ...]:
        """All directed edges between a coordinated junction and its neighbours.

        We watch both directions (in and out) for every (junction, neighbour)
        pair so a junction can report its own out-edge release AND observe each
        peer's in-edge arrival. Fresh, deduplicated, sorted tuple.
        """
        edges: set[str] = set()
        for tl, nbs in self.adjacency.items():
            if tl not in self.slm:
                continue
            for nb in nbs:
                for a, b in ((tl, nb), (nb, tl)):
                    eid = self._edge_id(a, b)
                    if eid:
                        edges.add(eid)
        return tuple(sorted(edges))

    def _read_free_speeds(self) -> dict[str, float]:
        """Best-effort free-flow speed (m/s) per watched edge, read once.

        Free speed is the max allowed lane speed on the edge. We read it via the
        edge's known lanes (``_edge_lanes``); when an edge has no known lanes or
        the read errors we leave it absent (the detector then falls back to the
        occupancy-only spillback test for that edge). Never raises.
        """
        out: dict[str, float] = {}
        get_max = getattr(getattr(self.c, "lane", None), "getMaxSpeed", None)
        if get_max is None:
            return out
        for eid in self._watched_edges:
            best = 0.0
            for lane in self._edge_lanes.get(eid, ()):
                try:
                    best = max(best, float(get_max(lane)))
                except Exception:
                    continue
            if best > 0:
                out[eid] = best
        return out

    def step(self) -> None:
        """Advance the TLS one second AND fold this step into the flow window.

        When windowing is enabled we snapshot the vehicle ids on every watched
        edge via TraCI and accumulate entry events BEFORE delegating to the
        parent step (the parent only re-times phases; the flow read must happen
        every simulated second to catch each entry exactly once). Transport
        errors never kill the sim -- a failed read leaves the window untouched
        for that edge this step.
        """
        if self._flow is not None and self._watched_edges:
            snapshot: dict[str, frozenset[str]] = {}
            get_ids = self.c.edge.getLastStepVehicleIDs
            for eid in self._watched_edges:
                try:
                    snapshot[eid] = frozenset(get_ids(eid))
                except Exception:
                    continue  # unknown/erroring edge: skip it this step
            if snapshot:
                now = float(self.c.simulation.getTime())
                self._flow = self._flow.observe(now, snapshot)
            # Refresh per-edge congestion metadata (occupancy / speed) so the
            # detector can classify spillback. Each read is independent; a failed
            # read leaves that edge's metadata untouched for this step. Stored as
            # the LATEST snapshot (a frozen, per-edge tuple) -- never mutated.
            self._refresh_edge_meta()
        super().step()

    def _refresh_edge_meta(self) -> None:
        """Snapshot last-step occupancy / mean-speed / free-speed per watched edge.

        Used only by the windowed detector's spillback test. Transport errors per
        edge are swallowed (the sim must never die on a presentation read); the
        edge simply keeps its previous metadata. Rebuilds the dict immutably.
        """
        meta = dict(self._edge_meta)
        for eid in self._watched_edges:
            try:
                occ = float(self.c.edge.getLastStepOccupancy(eid))
                spd = float(self.c.edge.getLastStepMeanSpeed(eid))
            except Exception:
                continue
            free = self._edge_free_speed.get(eid, 0.0)
            meta = {**meta, eid: (occ, spd, free)}
        self._edge_meta = meta

    def _incoming_per_phase(self, st: dict, incoming_by_neighbour: dict[str, int],
                            tl: str) -> list[int]:
        """Attribute each neighbour's incoming release to the green phases serving it.

        Incoming traffic from neighbour ``X`` arrives on edge ``X{tl}`` (src ``X``
        -> dst ``tl``), which feeds specific local in-lanes. A green phase ``gi``
        serves a movement ``i`` iff ``st["green"][gi][i]`` is in ``"Gg"``. So
        neighbour ``X``'s incoming release counts toward phase ``gi`` iff ``gi``
        gives green to *any* movement whose in-lane sits on edge ``X{tl}``.

        Returns ``incoming_per_phase`` (one entry per green phase, fresh list). A
        neighbour is counted in EACH green phase serving its approach; un-served
        approaches contribute nothing.
        """
        ngreen = len(st["green"])
        per_phase = [0] * ngreen
        for nb, amount in incoming_by_neighbour.items():
            if amount <= 0:
                continue
            if self._edge_map is not None:
                in_edge = self._edge_map.get((nb, tl))  # explicit nb -> tl edge
                if in_edge is None:
                    continue
            else:
                in_edge = f"{nb}{tl}"  # grid: edge neighbour -> this junction
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
        """Vehicles this junction released toward each neighbour (for the claim).

        WINDOWED MODE (``flow_window > 0``): the ``release`` toward each
        neighbour is the number of DISTINCT vehicles that actually ENTERED edge
        ``self->neighbour`` over the last ``flow_window`` seconds -- an ACTUAL
        flow over a matched window, the like-for-like quantity the neighbour
        independently re-measures on the same edge. This is what removes the
        benign false positives.

        LEGACY MODE (``flow_window == 0``, default): for the green phase ``gi``
        about to be served, sum the upstream halting count on each served
        movement's *in-lane* and attribute it to the neighbour the movement's
        *out-lane edge* leads to (the original instantaneous feed). Preserved
        verbatim so the controlled attack harness is unchanged.

        Returns a fresh dict either way; never a forecast.
        """
        if self._flow is not None:
            return self._windowed_toward_counts(st, gi)
        halting = self.c.lane.getLastStepHaltingNumber
        # Resolver: out-lane edge -> downstream neighbour. With an explicit
        # edge_map use the inverted out-edge map for this junction; otherwise
        # fall back to grid name-parsing via _split_edge.
        out_map = (self._out_edge_to_neighbour.get(self._current_tl, {})
                   if self._edge_map is not None else None)
        toward: dict[str, int] = {}
        state = st["green"][gi]
        for i, ch in enumerate(state):
            if ch not in "Gg":
                continue
            out_lane = st["out_lanes"][i]
            in_lane = st["in_lanes"][i]
            if not out_lane or not in_lane:
                continue
            if out_map is not None:
                neighbour = out_map.get(_edge_of_lane(out_lane))
                if neighbour is None:
                    continue  # movement does not lead to a signalised neighbour
            else:
                split = _split_edge(_edge_of_lane(out_lane), self._junctions)
                if split is None:
                    continue  # movement exits the grid (dead-end) -> no neighbour
                neighbour = split[1]
            toward = {**toward, neighbour: toward.get(neighbour, 0)
                      + halting(in_lane)}
        return toward

    def _windowed_toward_counts(self, st: dict, gi: int) -> dict[str, int]:
        """Windowed actual-flow ``release`` toward each neighbour (flow mode).

        For each neighbour this junction's served movements lead to, the release
        is the count of distinct vehicles that ENTERED edge ``self->neighbour``
        over the last ``flow_window`` seconds (an actual, matched-window flow).
        We resolve the served neighbours exactly as the legacy path does (so the
        attribution is identical), then read the windowed entry count per edge
        rather than instantaneous halting. Returns a fresh dict.
        """
        flow = self._flow
        assert flow is not None  # only called when windowing is enabled
        now = float(self.c.simulation.getTime())
        out_map = (self._out_edge_to_neighbour.get(self._current_tl, {})
                   if self._edge_map is not None else None)
        neighbours: set[str] = set()
        state = st["green"][gi]
        for i, ch in enumerate(state):
            if ch not in "Gg":
                continue
            out_lane = st["out_lanes"][i]
            in_lane = st["in_lanes"][i]
            if not out_lane or not in_lane:
                continue
            if out_map is not None:
                nb = out_map.get(_edge_of_lane(out_lane))
                if nb is None:
                    continue
            else:
                split = _split_edge(_edge_of_lane(out_lane), self._junctions)
                if split is None:
                    continue
                nb = split[1]
            neighbours.add(nb)
        toward: dict[str, int] = {}
        for nb in neighbours:
            edge = self._edge_id(self._current_tl, nb)
            if edge is None:
                continue
            toward = {**toward, nb: flow.released_in_window(edge, now)}
        return toward

    def _observed_inflows(self, recipient: str, neighbours,
                          meas_t: dict[str, int] | None = None) -> dict[str, int]:
        """Independent observation of arrivals on each in-edge ``neighbour->recipient``.

        WINDOWED MODE (``flow_window > 0``): count of distinct vehicles that
        ENTERED edge ``neighbour->recipient`` over the window ending at the
        SENDER's measurement time (``meas_t[nb]``, clamped <= now; else ``now``).
        Aligning to the sender's claim window removes decision-tick misalignment.

        LEGACY MODE (default): instantaneous halting summed over the in-edge's
        lanes (the original feed), preserved for the controlled attack harness.

        Returns ``{neighbour_id: count}`` (fresh dict) either way.
        """
        if self._flow is not None:
            now = float(self.c.simulation.getTime())
            mt = meas_t or {}
            observed: dict[str, int] = {}
            for nb in neighbours:
                edge = self._edge_id(nb, recipient)
                # Reconcile over the sender's window when supplied (clamped so a
                # stale/forged future timestamp cannot reach beyond the present).
                ref_t = float(min(mt[nb], now)) if nb in mt else now
                observed = {**observed, nb: (
                    self._flow.released_in_window(edge, ref_t) if edge else 0)}
            return observed
        halting = self.c.lane.getLastStepHaltingNumber
        observed = {}
        for nb in neighbours:
            if self._edge_map is not None:
                edge = self._edge_map.get((nb, recipient))  # explicit nb -> recipient
            else:
                edge = f"{nb}{recipient}"  # grid: edge nb -> recipient
            count = 0
            if edge is not None:
                for lane_id in self._edge_lanes.get(edge, ()):
                    count += halting(lane_id)
            observed = {**observed, nb: count}
        return observed

    def _windowed_reconcile(self, tl: str, claims: dict[tuple[str, str], int],
                            observed: dict[tuple[str, str], int],
                            claim_meas_t: dict[str, int]) -> list[Detection]:
        """Run the intelligent mass-balance detector on this window's edges.

        For each reconciled directed edge ``src->tl`` we build an
        :class:`EdgeMeasurement`:

          * ``entered`` = the sender's reconciled `release` (the count-inflation
            surface); ``exited`` = vehicles that LEFT edge ``src->tl`` over the
            matched window; ``storage_now`` = vehicles in transit (not a
            discrepancy); occupancy/speed feed the spillback test.

        Each :class:`EdgeVerdict` maps to a :class:`Detection` (``claimed`` =
        entered, ``observed`` = exited) so every existing consumer is unchanged.
        Returns a fresh list; never mutates inputs.
        """
        flow = self._flow
        det = self._fc_detector
        assert flow is not None and det is not None
        now = float(self.c.simulation.getTime())
        measurements: dict[str, EdgeMeasurement] = {}
        edge_to_key: dict[str, tuple[str, str]] = {}
        for (src, dst) in sorted(set(claims.keys()) | set(observed.keys())):
            edge = self._edge_id(src, dst)
            if edge is None:
                continue
            ref_t = float(min(claim_meas_t[src], now)) if src in claim_meas_t else now
            ref_t = max(0.0, ref_t)
            entered_n = int(claims.get((src, dst), 0))
            exited_n = int(flow.exited_in_window(edge, ref_t))
            storage = int(flow.storage_now(edge))
            occ_pct, spd, free = self._edge_meta.get(edge, (0.0, 0.0, 0.0))
            # SUMO occupancy is a percentage; the detector wants a [0,1] fraction.
            occ = max(0.0, min(1.0, occ_pct / 100.0))
            measurements[edge] = EdgeMeasurement(
                edge_id=edge, entered=entered_n, exited=exited_n,
                storage_now=storage, occupancy=occ, mean_speed=max(0.0, spd),
                free_speed=max(0.0, free))
            edge_to_key[edge] = (src, dst)
        if not measurements:
            return []
        verdicts = det.update_many(measurements)
        out: list[Detection] = []
        for v in verdicts:
            src, dst = edge_to_key[v.edge_id]
            claimed = int(measurements[v.edge_id].entered)
            obs = int(measurements[v.edge_id].exited)
            out.append(Detection(
                src=src, dst=dst, claimed=claimed, observed=obs,
                delta=claimed - obs, flagged=v.flagged, reason=v.reason))
        return out

    def decide(self, tl: str, st: dict) -> int:
        # Record the deciding junction so the edge_map resolvers know whose
        # out-edge map to use (harmless for the grid fallback path).
        self._current_tl = tl
        mp_choice = super(HybridController, self).decide(tl, st)  # MaxPressure
        if tl not in self.slm:
            self._served_ctx = {"tl": tl, "recorded": mp_choice, "event_index": None,
                                "gate_skipped": False, "mp_choice": mp_choice,
                                "slm_phase": None, "halting": None, "emitted": False}
            return mp_choice

        halting = [self.green_halting(st, gi) for gi in range(len(st["green"]))]
        if sum(halting) < self.gate:  # event-gate: quiet -> shield only
            # Gate-skipped: no §11 decision emitted here. If step()'s anti-starvation
            # override then changes the served phase, _on_served closes the hole.
            self._served_ctx = {"tl": tl, "recorded": mp_choice, "event_index": None,
                                "gate_skipped": True, "mp_choice": mp_choice,
                                "slm_phase": None,
                                "halting": [int(h) for h in halting], "emitted": False}
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
        # In windowed mode the claim is an ACTUAL flow over a window ending NOW;
        # we stamp that measurement time into the signed payload so the receiver
        # can reconcile over the SAME window (removing decision-tick misalignment,
        # the residual benign false-positive source). meas_t is an int second so
        # it stays inside the canonical-JSON signing contract. In legacy mode the
        # field is absent and the receiver falls back to its own window.
        meas_t = int(self.c.simulation.getTime()) if self._flow is not None else None
        toward_payload = {
            nb: ({"release": rel, "queue_forecast": rel, "meas_t": meas_t}
                 if meas_t is not None
                 else {"release": rel, "queue_forecast": rel})
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
        # Verified bus messages consumed THIS decision (§6.2), kept separate from
        # `received` because the §11 message record needs the raw NeighborMessage
        # (.signature + sender for the registry DER lookup at consumption).
        verified_msgs: list = []
        expected_incoming = 0
        incoming_by_neighbour: dict[str, int] = {}
        claims: dict[tuple[str, str], int] = {}
        # Per-source sender measurement time (windowed mode only) so the observed
        # side reconciles over the SAME window the claim was measured over.
        claim_meas_t: dict[str, int] = {}
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
                # Sender's measurement time (windowed mode); validated, else ignored.
                mt = entry.get("meas_t")
                windowed = (self._flow is not None
                            and isinstance(mt, int) and not isinstance(mt, bool)
                            and mt >= 0)
                if windowed:
                    claim_meas_t = {**claim_meas_t, m.sender: mt}
                expected_incoming += amount
                incoming_by_neighbour = {
                    **incoming_by_neighbour,
                    m.sender: incoming_by_neighbour.get(m.sender, 0) + amount,
                }
                received = [*received, {"from": m.sender, "t": m.t,
                                        "release": amount, "queue_forecast": forecast}]
                verified_msgs = [*verified_msgs, m]
                # Claim: sender claims it released `amount` toward us (edge sender->tl).
                # CONSERVATION CONSUMES ONLY `release` (actual), never the forecast.
                #
                # In WINDOWED mode each message's `release` is an ABSOLUTE count of
                # vehicles over the sender's sliding window, so two messages read in
                # one inbox scan are overlapping windowed snapshots, NOT additive
                # increments: the LATEST message's count (paired with its meas_t)
                # is the claim to reconcile. Summing them would double-count the
                # window overlap and spuriously inflate the claim (the residual
                # benign false positive). In LEGACY mode releases are per-decision
                # increments and remain additive (attack harness semantics intact).
                key = (m.sender, tl)
                if windowed:
                    claims = {**claims, key: amount}  # latest absolute snapshot
                else:
                    claims = {**claims, key: claims.get(key, 0) + amount}
        except Exception as exc:
            received = [{"error": type(exc).__name__}]

        # §6.2: append a §11 kind:"message" record per consumed verified message
        # (its .signature.hex() + the sender_pubkey_der/fpr pulled from the
        # registry AT CONSUMPTION) and capture the envelope seqs as this
        # decision's driving_input_seqs. Done OUTSIDE the inbox try so an emit
        # bug surfaces rather than being swallowed as a transport error.
        driving_pairs = log_messages(self.audit_log, self.registry,
                                     self.identities, tl, verified_msgs)

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
        # P4 -- Channel-B override. Default: a VALID SLM proposal always wins
        # (coordination inert). With coord_override=True, if the coordinated choice
        # disagrees with a valid proposal by more than the threshold in adjusted
        # pressure, the shield's coordination choice wins (true "shield disposes").
        coord_overrode = False
        if (self.coord_override and proposal is not None
                and 0 <= coord_choice < len(adj_halting)
                and 0 <= proposal < len(adj_halting)
                and coord_choice != proposal):
            margin = adj_halting[coord_choice] - adj_halting[proposal]
            if margin > self.coord_override_threshold:
                used = coord_choice
                coord_overrode = True
                self.coord_override_decisions += 1

        # (d) Reconcile claims vs observed inflows; stash Detections. P3: when
        # reconcile_silent_neighbours is on, we observe EVERY approved neighbour's
        # in-edge, so one with observed inflow but NO claim yields `missing_claim`;
        # a silent AND idle approach contributes nothing (no spurious detection).
        new_detections: list[Detection] = []
        claim_srcs = {src for (src, _dst) in claims.keys()}
        if self.reconcile_silent_neighbours:
            # Registered, currently-approved neighbours we expected a claim from.
            expected_srcs = {
                nb for nb in neighbours
                if nb in self.identities and self.registry.is_approved(nb)
            }
        else:
            expected_srcs = set()  # legacy: only reconcile edges that have a claim
        observe_srcs = claim_srcs | expected_srcs
        if observe_srcs:
            observed_by_nb = self._observed_inflows(tl, observe_srcs, claim_meas_t)
            # Feed claim edges always; for silent (no-claim) neighbours feed an
            # observed-only edge ONLY where there is ACTUAL inflow, so a genuinely
            # quiet approach is not flagged as a missing claim every round.
            observed = {
                (src, tl): observed_by_nb.get(src, 0)
                for src in observe_srcs
                if src in claim_srcs or observed_by_nb.get(src, 0) > 0
            }
            if claims or observed:
                try:
                    if self._fc_detector is not None:
                        # WINDOWED (Part A): principled mass-balance + adaptive
                        # band + CUSUM persistence detector. `claims` is the
                        # sender's reconciled `entered` (release) per edge over
                        # its window; the flow window supplies `exited`, current
                        # storage, and metadata for spillback.
                        new_detections = self._windowed_reconcile(
                            tl, claims, observed, claim_meas_t)
                    else:
                        # LEGACY (flow_window == 0): flat ConservationChecker --
                        # the frozen offline-harness contract, byte-for-byte.
                        new_detections = self.checker.evaluate(claims, observed)
                except Exception:
                    new_detections = []
                self.detections = [*self.detections, *new_detections]

        # The SERVED phase (post anti-starvation): step() will serve exactly this
        # (best = _anti_starvation_choice(tl, st, decide()==used)), so the §11
        # record's executed must be `served`, not the pre-override `used`
        # (MASTER-SPEC §4 H2). Pure read; no traffic-control effect.
        served = self._anti_starvation_choice(tl, st, used)
        self.events.append({
            "tls": tl, "halting": halting,
            "slm_phase": proposal, "shield_phase": mp_choice, "used": used,
            "served": served,
            "served_by": served_by(proposal, mp_choice, used, served),
            "overridden": proposal is None or proposal != mp_choice,
            "tick": tick,
            "published": published,
            "expected_incoming": expected_incoming,
            "incoming_per_phase": incoming_per_phase,
            "mp_choice": mp_choice,
            "coord_choice": coord_choice,
            "coord_changed": coord_changed,
            "coord_overrode": coord_overrode,
            "received": received,
            "neighbor_note": note,
            "detections": [
                {"src": d.src, "dst": d.dst, "claimed": d.claimed,
                 "observed": d.observed, "delta": d.delta,
                 "flagged": d.flagged, "reason": d.reason}
                for d in new_detections
            ],
        })

        # §6.2: emit the §11 kind:"decision" record inline. driving_input_seqs =
        # the FULL set of consumed signed inputs (no materiality filter); junction
        # = the deciding tl; t = SIM time (distinct clock from the signed logical
        # message.t); executed = the used phase; classification is a RUNTIME label
        # from detections[].flagged (DISTINCT from ORIGIN -- assessment.py MUST NOT
        # read it for origin); policies per §6.2 (detection "ran" iff >=1 Detection).
        classification = ("SPOOFED_OR_FAULTY"
                          if any(d.flagged for d in new_detections)
                          else "LEGITIMATE")
        log_decision(self.audit_log, self.identities, tl, driving_pairs,
                     self._sim_time(), served, classification,
                     coordination_policies(bool(new_detections)))
        self._served_ctx = {"tl": tl, "recorded": used,
                            "event_index": len(self.events) - 1,
                            "gate_skipped": False, "mp_choice": mp_choice,
                            "slm_phase": proposal,
                            "halting": [int(h) for h in halting],
                            "emitted": True}
        return used

    def _on_served(self, tl: str, st: dict, best: int) -> None:
        """Record the SERVED phase (post anti-starvation) for accountability.

        First repairs the decision event's ``served`` (parent, HybridController).
        Then closes the §11 gate-skip hole: when NO §11 decision record was emitted
        this interval (gate-skipped / non-SLM path) AND the override changed the
        served phase, emit a §11 kind:"decision" of the SERVED phase so the signed
        chain never omits a served-phase change (MASTER-SPEC §4 H2 / §6.2). Its
        driving_input_seqs is [] (no signed inputs were consumed on a gate-skip),
        classification LEGITIMATE (no detection ran), policies the coordination
        base (membership/replay). The full-path record already carries the served
        phase (executed = served, set in decide()), so it needs no correction."""
        ctx = self._served_ctx
        super()._on_served(tl, st, best)
        if (self.audit_log is not None and ctx and ctx.get("tl") == tl
                and not ctx.get("emitted") and ctx.get("event_index") is None
                and best != ctx.get("recorded")):
            log_decision(self.audit_log, self.identities, tl, [],
                         self._sim_time(), best, "LEGITIMATE",
                         coordination_policies(False))

    def _sim_time(self) -> float:
        """Simulation-clock read for decision.t (§6.2). DISTINCT from the logical
        per-message tick that rides inside a signed message.t. Never raises."""
        try:
            return float(self.c.simulation.getTime())
        except Exception:
            return 0.0
