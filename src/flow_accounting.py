"""Windowed per-edge flow accounting -- like-for-like conservation evidence.

Why this exists
---------------
The conservation check reconciles a SENDER's claimed released-vehicle count
against a RECEIVER's independently-observed arrival count on the same directed
edge ``src->dst``. For that reconciliation to be meaningful, BOTH quantities
must be the SAME physical thing measured over the SAME (travel-time-aligned)
window: *actual vehicles that traversed the edge*.

The earlier live wiring compared mismatched quantities -- a forecast (upstream
*halting* count on the about-to-green approach) against the neighbour's
*instantaneous* halting count on the inbound edge at the same tick. Those are
different quantities at misaligned times, so even perfectly benign flow produced
large deltas and constant spurious ``inflated`` / ``under_reported`` flags.

What this measures instead
--------------------------
For each directed edge we watch, every simulated second we read the set of
vehicle ids currently ON that edge (``traci.edge.getLastStepVehicleIDs``). A
vehicle id that is present this step but was NOT present last step has just
ENTERED the edge -- i.e. it was released by the upstream junction onto the edge.
We accumulate those entry events into a bounded, time-stamped sliding window.

A junction's ``released`` toward a neighbour over the last ``window`` seconds is
then the number of distinct vehicles that ENTERED edge ``self->neighbour`` in
that window. The neighbour's independently-``observed`` inflow from a peer is the
number of distinct vehicles that ENTERED edge ``peer->self`` in the matched
window. Both endpoints derive their figure from the SAME physical accumulation
on the SAME edge, so benign flow balances to zero residual (no flag), while a
forged/inflated claim or a dropped report still diverges (flag).

Design
------
* IMMUTABLE-STYLE: ``observe`` returns a NEW ``FlowWindow`` rather than mutating;
  the controller swaps its reference. ``released_in_window`` is pure.
* BOUNDED: the window only retains entry events newer than ``window`` seconds;
  ``prune`` drops the rest, so memory is O(vehicles-per-window-per-edge), never
  unbounded. The previous-step id set is the only other state and is per-edge.
* DETERMINISTIC + SUMO-FREE TESTABLE: ``observe`` takes the current time and a
  ``{edge_id: frozenset[vehicle_id]}`` snapshot, so it is exercised without
  TraCI in unit tests; the controller supplies the snapshot from TraCI live.
* EXPLICIT ERRORS at the boundary: time must be a finite non-negative number,
  the snapshot a dict of edge-id -> iterable of str ids.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Iterable, Mapping

__all__ = ["FlowWindow"]


def _validate_time(t: float) -> float:
    if isinstance(t, bool) or not isinstance(t, (int, float)):
        raise TypeError(f"time must be a number, got {type(t).__name__}")
    if t != t or t in (float("inf"), float("-inf")):
        raise ValueError("time must be finite")
    if t < 0:
        raise ValueError(f"time must be >= 0, got {t}")
    return float(t)


@dataclass(frozen=True)
class FlowWindow:
    """Immutable sliding-window record of per-edge vehicle ENTRY events.

    Attributes
    ----------
    window : float
        Sliding-window length in seconds used to COUNT entries in
        ``released_in_window``. Must be > 0.
    retain : float
        Retention horizon in seconds (``>= window``). Entry events older than
        ``now - retain`` are pruned. Retention is kept LONGER than the counting
        window so a claim measured at an earlier tick stays reconcilable when the
        receiver reads it a few decisions later (the publish->reconcile lag):
        ``released_in_window(edge, t_send)`` must still see the same entries the
        sender saw at ``t_send``, even though ``now > t_send``. Bounded, so memory
        stays O(vehicles in the retention horizon).
    last_seen : Mapping[str, frozenset[str]]
        Per-edge set of vehicle ids present on the edge at the previous
        ``observe`` step. Used to diff for new entries. Read-only mapping.
    entries : tuple[tuple[float, str, str], ...]
        Chronological log of ``(time, edge_id, vehicle_id)`` ENTRY events still
        inside the window. Bounded by ``window``.
    exits : tuple[tuple[float, str, str], ...]
        Chronological log of ``(time, edge_id, vehicle_id)`` EXIT events still
        inside the retention horizon. A vehicle present on an edge last step but
        absent this step LEFT the edge (arrived downstream / continued past it).
        Used by the mass-balance detector as the edge's ``exited`` count; the
        edge's current ``storage`` is just ``len(last_seen[edge])``. Bounded.
    """

    window: float = 30.0
    retain: float = 0.0
    last_seen: Mapping[str, frozenset[str]] = field(
        default_factory=lambda: MappingProxyType({}))
    entries: tuple[tuple[float, str, str], ...] = ()
    exits: tuple[tuple[float, str, str], ...] = ()

    def __post_init__(self) -> None:
        # Validate the window once at construction (frozen -> set via object).
        if isinstance(self.window, bool) or not isinstance(self.window, (int, float)):
            raise TypeError(
                f"window must be a number, got {type(self.window).__name__}")
        if self.window != self.window or self.window in (float("inf"), float("-inf")):
            raise ValueError("window must be finite")
        if self.window <= 0:
            raise ValueError(f"window must be > 0, got {self.window}")
        object.__setattr__(self, "window", float(self.window))
        # Default retention = 4x window: generous enough that a claim measured at
        # an earlier tick stays fully reconcilable across several decision cycles
        # of publish->reconcile lag (so the receiver's window matches the
        # sender's exactly, not a partially-pruned subset), while staying bounded.
        if isinstance(self.retain, bool) or not isinstance(self.retain, (int, float)):
            raise TypeError(
                f"retain must be a number, got {type(self.retain).__name__}")
        retain = float(self.retain) if self.retain and self.retain > 0 else 4.0 * self.window
        if retain != retain or retain in (float("inf"), float("-inf")):
            raise ValueError("retain must be finite")
        if retain < self.window:
            raise ValueError(
                f"retain ({retain}) must be >= window ({self.window})")
        object.__setattr__(self, "retain", retain)

    def observe(
        self,
        now: float,
        snapshot: Mapping[str, Iterable[str]],
    ) -> "FlowWindow":
        """Return a NEW window folding in this step's per-edge vehicle ids.

        ``snapshot`` maps each watched edge id to the iterable of vehicle ids
        currently on that edge (``traci.edge.getLastStepVehicleIDs``). A vehicle
        id present now but absent from ``last_seen`` for that edge is a fresh
        ENTRY (released onto the edge this step) and is appended with timestamp
        ``now``. Events older than ``now - window`` are pruned. Inputs are
        validated and never mutated.
        """
        now = _validate_time(now)
        if not isinstance(snapshot, Mapping):
            raise TypeError(
                f"snapshot must be a mapping, got {type(snapshot).__name__}")

        new_last: dict[str, frozenset[str]] = {}
        fresh: list[tuple[float, str, str]] = []
        fresh_exits: list[tuple[float, str, str]] = []
        for edge_id, ids in snapshot.items():
            if not isinstance(edge_id, str):
                raise TypeError(
                    f"snapshot key must be an edge-id str, got {edge_id!r}")
            current = frozenset(self._as_id_set(edge_id, ids))
            previous = self.last_seen.get(edge_id, frozenset())
            for vid in current - previous:  # newly arrived on this edge
                fresh.append((now, edge_id, vid))
            for vid in previous - current:  # left the edge this step (exited)
                fresh_exits.append((now, edge_id, vid))
            new_last[edge_id] = current

        # Keep edges we did not see this step (their last_seen still valid until
        # they reappear) so a watched edge that is momentarily empty does not
        # spuriously re-count the same vehicle as a new entry next step.
        for edge_id, prev in self.last_seen.items():
            if edge_id not in new_last:
                new_last[edge_id] = prev

        # Prune by the RETENTION horizon (>= window) so in-flight claims measured
        # at an earlier tick remain reconcilable; counting still uses `window`.
        cutoff = now - self.retain
        kept = tuple(e for e in (*self.entries, *fresh) if e[0] >= cutoff)
        kept_exits = tuple(
            e for e in (*self.exits, *fresh_exits) if e[0] >= cutoff)
        return FlowWindow(
            window=self.window,
            retain=self.retain,
            last_seen=MappingProxyType(new_last),
            entries=kept,
            exits=kept_exits,
        )

    def released_in_window(self, edge_id: str, now: float) -> int:
        """Distinct vehicles that ENTERED ``edge_id`` within the last ``window`` s.

        Pure: counts unique vehicle ids in the window for that edge. ``now``
        defines the window's right edge so a stale call still respects the
        window length.
        """
        if not isinstance(edge_id, str):
            raise TypeError(f"edge_id must be a str, got {type(edge_id).__name__}")
        now = _validate_time(now)
        cutoff = now - self.window
        seen: set[str] = set()
        for t, eid, vid in self.entries:
            # Count entries inside the window [now - window, now]. The upper bound
            # matters when `now` is an EARLIER reference time than the latest
            # observation (the receiver reconciling over the sender's window):
            # entries that arrived after the sender measured must not be counted.
            if eid == edge_id and cutoff <= t <= now:
                seen.add(vid)
        return len(seen)

    def exited_in_window(self, edge_id: str, now: float) -> int:
        """Distinct vehicles that LEFT ``edge_id`` within the last ``window`` s.

        Pure mirror of :meth:`released_in_window` over the EXIT log -- the
        downstream-arrival side of the edge mass balance. ``now`` defines the
        window's right edge so a stale call still respects the window length.
        """
        if not isinstance(edge_id, str):
            raise TypeError(f"edge_id must be a str, got {type(edge_id).__name__}")
        now = _validate_time(now)
        cutoff = now - self.window
        seen: set[str] = set()
        for t, eid, vid in self.exits:
            if eid == edge_id and cutoff <= t <= now:
                seen.add(vid)
        return len(seen)

    def storage_now(self, edge_id: str) -> int:
        """Vehicles CURRENTLY on ``edge_id`` (the in-transit edge storage).

        Pure: the size of the most recent per-edge presence set. Zero for an
        edge never observed. This is the snapshot term in the mass balance.
        """
        if not isinstance(edge_id, str):
            raise TypeError(f"edge_id must be a str, got {type(edge_id).__name__}")
        return len(self.last_seen.get(edge_id, frozenset()))

    @staticmethod
    def _as_id_set(edge_id: str, ids: Iterable[str]) -> set[str]:
        if isinstance(ids, (str, bytes)):
            raise TypeError(
                f"snapshot[{edge_id!r}] must be an iterable of ids, not a string")
        out: set[str] = set()
        for vid in ids:
            if not isinstance(vid, str):
                raise TypeError(
                    f"snapshot[{edge_id!r}] vehicle id must be a str, got {vid!r}")
            out.add(vid)
        return out
