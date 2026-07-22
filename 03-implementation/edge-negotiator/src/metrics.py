"""Throughput-controlled traffic metrics that resolve the survivorship-bias confound.

Source of truth: results/milestone2_report.md ("Caveat") + MASTER-SPEC.md.
The Milestone-2 sweep reported ``avg_travel_time_s`` averaged over *completed trips
only*. A controller that completes FEWER trips (e.g. it strands the slow, congested
vehicles unfinished at the END horizon) silently drops those slow trips from the
denominator, so its mean travel time can look *lower* purely because the slow trips
vanished -- a classic survivorship bias. This module provides metrics that do NOT
condition on completion, so a "completes fewer but faster" controller cannot post a
spurious improvement.

Why a separate module (no SUMO dependency)
------------------------------------------
Everything here is a *pure function of a parsed tripinfo file*. We never call TraCI,
never touch the network. That keeps the metrics:
  * unit-testable on hand-crafted tripinfo XML (see tests/test_metrics.py),
  * immutable (every function returns a new frozen dataclass / dict; nothing mutates
    its inputs),
  * validated at the boundary (parsing rejects malformed / negative / NaN fields).

Which SUMO outputs each metric needs
-------------------------------------
The single required output is the per-vehicle tripinfo file produced with
**three** options, so that the file describes the *whole vehicle population*, not just
the survivors:

    sumo ... --tripinfo-output trip.xml \
             --tripinfo-output.write-unfinished \
             --tripinfo-output.write-undeparted

  * default tripinfo            -> one <tripinfo> per COMPLETED trip (arrival >= 0).
  * --write-unfinished          -> also one <tripinfo> per vehicle still RUNNING at
                                   the sim end. These carry arrival="-1.00" and a
                                   ``duration`` equal to their time-in-network so far
                                   (their accrued, un-discharged delay).
  * --write-undeparted          -> also one <tripinfo> per vehicle that was LOADED but
                                   never managed to depart (insertion blocked by
                                   gridlock). These carry depart="-1.00".

With all three, ONE file lets us recover:
    loaded   = every <tripinfo> entry
    departed = entries with depart >= 0        (entered the network)
    completed= entries with arrival >= 0       (reached destination)
    running  = departed but arrival < 0        (stranded at the horizon)
    undeparted = depart < 0                    (never got in)

If a file was produced WITHOUT --write-unfinished (the legacy Milestone-2 files), it
contains ONLY completed trips; `parse_tripinfo` still works but `departed`/`running`
will be undercounted. `parse_tripinfo` records whether unfinished/undeparted vehicles
were present so callers can detect a legacy file and refuse to trust completion_rate.

Per-metric summary
------------------
  throughput            completed count                         (completed entries)
  completion_rate       completed / departed                    (needs write-unfinished)
  avg_travel_time_completed   mean duration over completed      (the OLD, biased metric)
  total_network_delay   sum of time-in-network over ALL departed vehicles, i.e.
                        completed trips' duration PLUS unfinished vehicles' accrued
                        time-in-network at the horizon -- the survivorship-robust
                        "work outstanding" number.                (needs write-unfinished)
  mean_network_delay    total_network_delay / departed           (needs write-unfinished)
  matched-set diff      avg travel time over ONLY vehicles that completed in BOTH runs
                        -- an apples-to-apples paired comparison.  (two tripinfo files)
"""
from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Mapping, Tuple

__all__ = [
    "Trip",
    "RunRecord",
    "parse_tripinfo",
    "throughput",
    "completion_rate",
    "avg_travel_time_completed",
    "total_network_delay",
    "mean_network_delay",
    "summary",
    "matched_completed_ids",
    "matched_avg_travel_time",
    "matched_diff",
    "MetricsError",
]

# tripinfo sentinel for "did not happen": SUMO writes -1.00 for arrival of an
# unfinished vehicle and for depart of an undeparted vehicle.
_SENTINEL = -1.0
# Numeric attributes we read; all must be finite and (for the non-sentinel ones)
# non-negative once we have classified the trip.
_NUM_ATTRS = ("depart", "arrival", "duration", "waitingTime", "timeLoss", "routeLength")


class MetricsError(ValueError):
    """Raised when a tripinfo file / field is malformed or violates an invariant."""


@dataclass(frozen=True)
class Trip:
    """One immutable parsed <tripinfo> record.

    ``departed`` / ``completed`` are derived classifications, not raw fields:
        departed  = depart  >= 0   (vehicle actually entered the network)
        completed = arrival >= 0   (vehicle reached its destination)
    ``duration`` is, for a completed trip, total travel time; for an unfinished
    (running) trip, time-in-network accrued up to the simulation horizon -- in BOTH
    cases it is the vehicle's contribution to total network delay.
    """

    veh_id: str
    depart: float
    arrival: float
    duration: float
    waiting_time: float
    time_loss: float
    route_length: float

    @property
    def departed(self) -> bool:
        return self.depart >= 0.0

    @property
    def completed(self) -> bool:
        return self.arrival >= 0.0

    @property
    def running(self) -> bool:
        """Departed but never arrived: stranded at the horizon."""
        return self.departed and not self.completed


@dataclass(frozen=True)
class RunRecord:
    """Immutable population view of one simulation run, parsed from one tripinfo file."""

    trips: Tuple[Trip, ...]
    # Provenance flags so callers can detect a legacy (completed-only) file:
    has_unfinished: bool  # at least one running vehicle was written
    has_undeparted: bool  # at least one undeparted vehicle was written
    source: str = ""

    # --- population partitions (computed once, returned as tuples = immutable) ---
    @property
    def completed_trips(self) -> Tuple[Trip, ...]:
        return tuple(t for t in self.trips if t.completed)

    @property
    def departed_trips(self) -> Tuple[Trip, ...]:
        return tuple(t for t in self.trips if t.departed)

    @property
    def running_trips(self) -> Tuple[Trip, ...]:
        return tuple(t for t in self.trips if t.running)

    @property
    def undeparted_trips(self) -> Tuple[Trip, ...]:
        return tuple(t for t in self.trips if not t.departed)

    def completed_durations(self) -> Mapping[str, float]:
        """{veh_id: travel-time} for completed trips only (used for matched sets)."""
        return {t.veh_id: t.duration for t in self.completed_trips}


# ---------------------------------------------------------------------------
# Parsing (boundary validation lives here -- never trust the file).
# ---------------------------------------------------------------------------
def _parse_float(attrib: Mapping[str, str], key: str, veh_id: str) -> float:
    raw = attrib.get(key)
    if raw is None:
        raise MetricsError(f"vehicle {veh_id!r}: missing required attribute {key!r}")
    try:
        val = float(raw)
    except (TypeError, ValueError):
        raise MetricsError(f"vehicle {veh_id!r}: attribute {key!r}={raw!r} is not a number")
    if math.isnan(val) or math.isinf(val):
        raise MetricsError(f"vehicle {veh_id!r}: attribute {key!r}={raw!r} is NaN/Inf")
    return val


def parse_tripinfo(path_or_string: str, *, from_string: bool = False) -> RunRecord:
    """Parse a SUMO tripinfo file (or XML string) into an immutable ``RunRecord``.

    Pass ``from_string=True`` to parse an in-memory XML string (used by tests).

    Validation performed at this boundary:
      * the document must contain a (possibly empty) set of <tripinfo> elements;
      * each <tripinfo> must have a non-empty ``id`` and finite numeric fields;
      * duplicate vehicle ids are rejected (a tripinfo file lists each vehicle once);
      * a *departed* trip must have non-negative duration/waiting/timeloss
        (sentinels are only legitimate on the dimension that "did not happen":
         arrival for running vehicles, depart for undeparted ones).
    """
    try:
        root = ET.fromstring(path_or_string) if from_string else ET.parse(path_or_string).getroot()
    except ET.ParseError as exc:
        raise MetricsError(f"could not parse tripinfo XML: {exc}") from exc

    elems = root.findall("tripinfo")
    seen: set[str] = set()
    trips: list[Trip] = []
    has_unfinished = False
    has_undeparted = False

    for el in elems:
        veh_id = el.get("id")
        if not veh_id:
            raise MetricsError("found a <tripinfo> with empty/missing id")
        if veh_id in seen:
            raise MetricsError(f"duplicate vehicle id {veh_id!r} in tripinfo")
        seen.add(veh_id)

        depart = _parse_float(el.attrib, "depart", veh_id)
        arrival = _parse_float(el.attrib, "arrival", veh_id)
        duration = _parse_float(el.attrib, "duration", veh_id)
        waiting = _parse_float(el.attrib, "waitingTime", veh_id)
        time_loss = _parse_float(el.attrib, "timeLoss", veh_id)
        route_len = _parse_float(el.attrib, "routeLength", veh_id)

        departed = depart >= 0.0
        completed = arrival >= 0.0

        if not departed:
            has_undeparted = True
        elif not completed:
            has_unfinished = True

        # Departed vehicles must have sane non-negative accrued quantities.
        if departed:
            for name, val in (("duration", duration), ("waitingTime", waiting),
                              ("timeLoss", time_loss)):
                if val < 0.0:
                    raise MetricsError(
                        f"vehicle {veh_id!r}: departed trip has negative {name}={val}")
            # An arrival, if present, cannot precede departure.
            if completed and arrival < depart:
                raise MetricsError(
                    f"vehicle {veh_id!r}: arrival {arrival} precedes depart {depart}")

        trips.append(Trip(
            veh_id=veh_id, depart=depart, arrival=arrival, duration=duration,
            waiting_time=waiting, time_loss=time_loss, route_length=route_len,
        ))

    return RunRecord(
        trips=tuple(trips),
        has_unfinished=has_unfinished,
        has_undeparted=has_undeparted,
        source="" if from_string else str(path_or_string),
    )


# ---------------------------------------------------------------------------
# Throughput-controlled metrics (pure functions of a RunRecord).
# ---------------------------------------------------------------------------
def throughput(run: RunRecord) -> int:
    """Number of trips that reached their destination (completed count).

    Needs: default tripinfo. NOT survivorship-confounded by itself -- it is a count,
    not an average -- and it is the headline measure a "completes fewer" controller
    *cannot* game: dropping slow trips lowers throughput directly.
    """
    return len(run.completed_trips)


def completion_rate(run: RunRecord) -> float:
    """completed / departed in [0, 1]. Returns NaN if nobody departed.

    Needs: tripinfo + --write-unfinished (otherwise ``departed`` is undercounted to
    equal ``completed`` and this collapses to a meaningless 1.0). Callers should check
    ``run.has_unfinished`` before trusting it; see `summary`.
    """
    departed = len(run.departed_trips)
    if departed == 0:
        return math.nan
    return len(run.completed_trips) / departed


def avg_travel_time_completed(run: RunRecord) -> float:
    """The OLD Milestone-2 metric: mean travel time over COMPLETED trips only.

    Needs: default tripinfo. Kept deliberately so reports can show the biased number
    side-by-side with the robust ones. Returns NaN when nothing completed.
    """
    comp = run.completed_trips
    if not comp:
        return math.nan
    return sum(t.duration for t in comp) / len(comp)


def total_network_delay(run: RunRecord) -> float:
    """Sum of time-in-network over ALL departed vehicles (completed + still running).

    This is the survivorship-robust aggregate. Every vehicle that entered the network
    contributes its time-in-network: a completed trip contributes its full travel
    time; a vehicle still stuck at the horizon contributes the time it has already
    spent (SUMO's ``duration`` for an unfinished trip). A controller that "improves"
    its completed-trip average merely by stranding slow vehicles gets NO credit here --
    those stranded vehicles' large accrued times stay in the sum.

    Needs: tripinfo + --write-unfinished. Without it, running vehicles are absent and
    this silently reduces to the completed-only sum -- so check ``run.has_unfinished``.
    """
    return sum(t.duration for t in run.departed_trips)


def mean_network_delay(run: RunRecord) -> float:
    """total_network_delay / number of departed vehicles. NaN if nobody departed.

    Needs: tripinfo + --write-unfinished. This is the apples-to-apples *per-vehicle*
    cost the dissertation should headline instead of avg_travel_time_completed,
    because its denominator (all departed vehicles) does not move when a controller
    strands trips.
    """
    departed = run.departed_trips
    if not departed:
        return math.nan
    return total_network_delay(run) / len(departed)


def summary(run: RunRecord) -> Dict[str, float]:
    """Bundle every scalar metric for one run into a flat dict (for sweeps/tables).

    Includes provenance flags so a consumer can tell a legacy completed-only file
    (``write_unfinished_present`` False) from a full population file.
    """
    return {
        "loaded": float(len(run.trips)),
        "departed": float(len(run.departed_trips)),
        "throughput": float(throughput(run)),
        "running_at_end": float(len(run.running_trips)),
        "undeparted": float(len(run.undeparted_trips)),
        "completion_rate": completion_rate(run),
        "avg_travel_time_completed": avg_travel_time_completed(run),
        "total_network_delay": total_network_delay(run),
        "mean_network_delay": mean_network_delay(run),
        "write_unfinished_present": float(run.has_unfinished),
        "write_undeparted_present": float(run.has_undeparted),
    }


# ---------------------------------------------------------------------------
# Matched-set (apples-to-apples) comparison helper.
# ---------------------------------------------------------------------------
def matched_completed_ids(run_a: RunRecord, run_b: RunRecord) -> Tuple[str, ...]:
    """Sorted vehicle ids that completed in BOTH runs (the matched set)."""
    a = set(run_a.completed_durations().keys())
    b = set(run_b.completed_durations().keys())
    return tuple(sorted(a & b))


def matched_avg_travel_time(run: RunRecord, ids: Tuple[str, ...]) -> float:
    """Mean travel time of ``run`` over the given vehicle id set. NaN if empty.

    Validates that every requested id actually completed in ``run`` (no silent
    fallback to a partial mean, which would reintroduce a bias).
    """
    if not ids:
        return math.nan
    durations = run.completed_durations()
    missing = [i for i in ids if i not in durations]
    if missing:
        raise MetricsError(
            f"matched_avg_travel_time: {len(missing)} id(s) not completed in run "
            f"(e.g. {missing[:5]})")
    return sum(durations[i] for i in ids) / len(ids)


def matched_diff(run_a: RunRecord, run_b: RunRecord) -> Dict[str, float]:
    """Apples-to-apples comparison: avg travel time over vehicles completed in BOTH.

    This is the survivorship-bias antidote for travel time specifically. By
    restricting to the *same vehicles* in both runs, a controller cannot win merely by
    dropping a different (slower) subset from its average.

    Returns:
        {
          "n_matched": #vehicles completed in both,
          "avg_a": mean travel time of run_a over the matched set,
          "avg_b": mean travel time of run_b over the matched set,
          "diff_a_minus_b": avg_a - avg_b,   (negative => a is faster on shared trips)
          "n_only_a": #completed only in a,
          "n_only_b": #completed only in b,
        }
    """
    ids = matched_completed_ids(run_a, run_b)
    a_only = set(run_a.completed_durations()) - set(run_b.completed_durations())
    b_only = set(run_b.completed_durations()) - set(run_a.completed_durations())
    avg_a = matched_avg_travel_time(run_a, ids)
    avg_b = matched_avg_travel_time(run_b, ids)
    diff = (avg_a - avg_b) if (ids) else math.nan
    return {
        "n_matched": float(len(ids)),
        "avg_a": avg_a,
        "avg_b": avg_b,
        "diff_a_minus_b": diff,
        "n_only_a": float(len(a_only)),
        "n_only_b": float(len(b_only)),
    }
