"""Principled, persistence-based flow-conservation anomaly detector.

Why a new module
----------------
``conservation.py``'s ``ConservationChecker.evaluate`` is a STATELESS, flat
``+/-tolerance`` comparison of a single windowed claim against a single windowed
observation. It is the detection primitive the OFFLINE attack harness
(``run_attacks.py`` / ``tests/test_attacks.py``) measures, and its P=1.0 numbers
must stay frozen, so that contract is left UNTOUCHED. This module is the
INTELLIGENT replacement wired into the LIVE coordinated feed (the
``flow_window > 0`` path): it does proper edge mass-balance, travel-time-aware
window alignment, an adaptive tolerance band, and a CUSUM persistence test so a
single transient blip never fires while a sustained spoof/fault does.

The physics: edge mass-balance over a window
--------------------------------------------
For a directed edge ``src -> dst`` over a window of length ``W`` ending at the
receiver's read time, conservation of vehicles says::

    entered  ==  exited  +  (storage_now - storage_then)

where

  * ``entered``      = distinct vehicles that ENTERED the edge in the window
                       (the sender's claimed/measured release; FlowWindow gives
                       this from ``getLastStepVehicleIDs`` diffs).
  * ``exited``       = distinct vehicles that LEFT the edge in the window
                       (arrived downstream); ``exited = entered_history -
                       Δstorage`` is recovered from the same entry log plus the
                       current on-edge count (see ``EdgeMeasurement``).
  * ``storage_now``  = vehicles CURRENTLY on the edge (in transit),
                       ``getLastStepVehicleNumber``.
  * ``storage_then`` = vehicles on the edge one window ago.

The signed residual is::

    r = entered - exited - (storage_now - storage_then)

A benign edge has ``r ~ 0`` every window: released-but-not-yet-arrived cars sit
in ``storage_now`` and are NOT counted as a discrepancy (requirement A.1). A
sender that inflates ``entered`` (count-inflation spoof) drives ``r`` positive
and KEEPS it positive; a faulty sender that under-reports drives it negative.

Travel-time-aware windowing (A.2)
---------------------------------
``entered`` and ``exited`` are not the same vehicles within one tick: a car that
entered now leaves ~``traveltime`` seconds later. We do NOT compare the same
tick. The receiver reconciles ``entered`` over the SENDER's measurement window
``[t_send - W, t_send]`` (the sender stamps ``t_send`` into its signed claim;
the controller passes it through), while ``exited`` and storage are read at the
receiver's ``now``. The window length itself is widened by the measured edge
travel time so a platoon released near the window edge is still inside the
reconciliation horizon rather than appearing as a phantom imbalance.

Adaptive tolerance (A.3)
------------------------
A flat ``+/-2`` is wrong at both ends: it false-alarms on a busy edge (where 2
cars of jitter is nothing) and misses a slow leak on a quiet edge. The allowed
per-window gap is::

    band = abs_floor
         + rel_frac      * expected_flow
         + storage_uncert * sqrt(max(storage_now, storage_then))

  * ``abs_floor`` (default 2.0): the Xiao floor -- a couple of cars of
    boundary/sensor jitter are never an attack. Keeps the offline harness's
    semantics recognisable.
  * ``rel_frac`` (default 0.15): 15% of the expected throughput. Counting error
    and entry/exit boundary effects scale with flow, so the band must too.
  * ``storage_uncert`` (default 1.0) * ``sqrt(storage)``: in-transit count is a
    snapshot; its sampling noise grows ~sqrt(N) (Poisson-like). This is the
    term that makes SPILLBACK safe -- a congested, full edge has large storage,
    so a large transient storage swing stays inside the band.

CUSUM persistence test -- the core intelligence (A.4)
-----------------------------------------------------
We do NOT flag on a single window crossing the band. We run a two-sided
tabular CUSUM on the band-normalised residual ``z = r / band``::

    S_hi = max(0, S_hi + z - slack)        # detects sustained OVER-claim
    S_lo = max(0, S_lo - z - slack)        # detects sustained UNDER-claim

``slack`` (default 0.5) is the reference value: drift smaller than half a band
per window is absorbed and the sums decay toward zero, so transient blips and
benign bias never accumulate. A flag fires when either sum exceeds ``h``
(default 3.0). With these params a sustained residual of ~1 band/window trips
the alarm in ``ceil(h / (1 - slack)) = 6`` windows; a one-window spike of even
several bands adds ``z-slack`` once and then decays -- it cannot reach ``h``
alone. Detection LATENCY (windows-to-flag) is recorded on every flag.

Edge cases (A.5), all handled explicitly and tested
----------------------------------------------------
  * ZERO/LOW flow: ``expected_flow`` floored into the band; the ``abs_floor``
    term keeps the band positive so there is never a divide-by-zero and tiny
    absolute diffs on an idle edge never accumulate.
  * SPILLBACK/congestion: detected via high ``occupancy`` and low ``mean_speed``
    relative to the free edge. A spillback window is reconciled but its residual
    is treated as MISSING (storage is changing faster than the snapshot can
    track), so a jam never feeds the CUSUM -- a full edge with throttled outflow
    is a jam, not an attack.
  * MISSING DATA / sensor dropout: a window with no measurement (or a transport
    read error upstream) is classified ``missing_data``; the CUSUM HOLDS (it
    neither accumulates nor resets) so a gap is never an attack and never erases
    accumulated evidence.
  * WARM-UP: the first ``warmup_windows`` (default 3) windows per edge prime the
    storage/flow history and never flag, so start-up transients are ignored.
  * TURNING / multi-downstream: each directed edge ``src -> dst`` is tracked
    independently keyed by its edge id, so flow is attributed to the ACTUAL
    destination edge -- a junction with several downstream edges has one
    detector state per edge.

Design constraints honoured
---------------------------
Deterministic given inputs; immutable-style (``EdgeState`` is frozen, ``update``
returns a NEW state, the detector swaps references); inputs validated at the
boundary with explicit errors; no SUMO import (the controller supplies plain
measurements, so this is unit-tested with no TraCI).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from types import MappingProxyType
from typing import Mapping

__all__ = [
    "EdgeMeasurement",
    "AdaptiveBand",
    "CusumParams",
    "EdgeVerdict",
    "EdgeState",
    "FlowConservationDetector",
]


# --------------------------------------------------------------------------- #
# Boundary validation helpers (explicit errors, never silent coercion).
# --------------------------------------------------------------------------- #

def _check_finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number, got {type(value).__name__}")
    f = float(value)
    if f != f or f in (float("inf"), float("-inf")):
        raise ValueError(f"{name} must be finite, got {value!r}")
    return f


def _check_nonneg_number(value: object, name: str) -> float:
    f = _check_finite_number(value, name)
    if f < 0:
        raise ValueError(f"{name} must be >= 0, got {f}")
    return f


def _check_nonneg_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


# --------------------------------------------------------------------------- #
# Inputs: one per-edge measurement per window.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class EdgeMeasurement:
    """One window's reconciliation evidence for a single directed edge.

    All counts are non-negative integers (vehicles are quantised). The detector
    computes the mass-balance residual from these and never mutates the input.

    Attributes
    ----------
    edge_id : str
        Directed edge id ``src->dst`` (its own key in the detector).
    entered : int
        Distinct vehicles that ENTERED the edge over the sender's window
        (the claim/measured release reconciled like-for-like).
    exited : int
        Distinct vehicles that LEFT the edge (arrived downstream) over the
        receiver's window.
    storage_now : int
        Vehicles CURRENTLY on the edge (in transit), this window.
    storage_prev : int
        Vehicles on the edge one window ago (the detector also remembers this,
        but the caller may supply a fresh independent read; when None the
        detector uses its own remembered ``storage_now`` from last window).
    occupancy : float
        Edge lane occupancy in [0, 1] (fraction of edge length covered by
        vehicles). Used for spillback classification. Defaults 0.0.
    mean_speed : float
        Edge last-step mean speed (m/s), >= 0. Used for spillback. Default 0.0.
    free_speed : float
        Edge free-flow / allowed speed (m/s), > 0 when known. A mean_speed far
        below free_speed at high occupancy is a jam. Default 0.0 (unknown ->
        speed not used, occupancy alone decides).
    """

    edge_id: str
    entered: int
    exited: int
    storage_now: int
    storage_prev: int | None = None
    occupancy: float = 0.0
    mean_speed: float = 0.0
    free_speed: float = 0.0

    def __post_init__(self) -> None:
        if not isinstance(self.edge_id, str) or not self.edge_id:
            raise TypeError("edge_id must be a non-empty str")
        _check_nonneg_int(self.entered, "entered")
        _check_nonneg_int(self.exited, "exited")
        _check_nonneg_int(self.storage_now, "storage_now")
        if self.storage_prev is not None:
            _check_nonneg_int(self.storage_prev, "storage_prev")
        occ = _check_nonneg_number(self.occupancy, "occupancy")
        if occ > 1.0:
            raise ValueError(f"occupancy must be <= 1.0, got {occ}")
        _check_nonneg_number(self.mean_speed, "mean_speed")
        _check_nonneg_number(self.free_speed, "free_speed")


# --------------------------------------------------------------------------- #
# Tunable parameter bundles (documented defaults; validated at construction).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class AdaptiveBand:
    """Adaptive-tolerance parameters: band = floor + rel*flow + unc*sqrt(stor)."""

    abs_floor: float = 2.0
    rel_frac: float = 0.15
    storage_uncert: float = 1.0

    def __post_init__(self) -> None:
        _check_nonneg_number(self.abs_floor, "abs_floor")
        _check_nonneg_number(self.rel_frac, "rel_frac")
        _check_nonneg_number(self.storage_uncert, "storage_uncert")
        if self.abs_floor <= 0:
            # A zero floor would allow a zero band -> divide-by-zero on idle
            # edges. The floor is the guarantee the band is always positive.
            raise ValueError(f"abs_floor must be > 0, got {self.abs_floor}")

    def width(self, expected_flow: float, storage_now: int,
              storage_prev: int) -> float:
        """Allowed per-window gap. Always strictly positive (abs_floor > 0)."""
        stor = max(int(storage_now), int(storage_prev), 0)
        return (self.abs_floor
                + self.rel_frac * max(float(expected_flow), 0.0)
                + self.storage_uncert * math.sqrt(stor))


@dataclass(frozen=True)
class CusumParams:
    """Two-sided tabular CUSUM parameters on band-normalised residual z=r/band.

    ``slack`` is the reference value (drift below it decays away). ``h`` is the
    decision threshold. ``warmup_windows`` windows per edge prime history and
    never flag. ``spillback_occupancy`` / ``spillback_speed_frac`` classify a jam.
    """

    slack: float = 0.5
    h: float = 3.0
    warmup_windows: int = 3
    spillback_occupancy: float = 0.55
    spillback_speed_frac: float = 0.30

    def __post_init__(self) -> None:
        _check_nonneg_number(self.slack, "slack")
        _check_nonneg_number(self.h, "h")
        _check_nonneg_int(self.warmup_windows, "warmup_windows")
        occ = _check_nonneg_number(self.spillback_occupancy, "spillback_occupancy")
        if occ > 1.0:
            raise ValueError("spillback_occupancy must be <= 1.0")
        frac = _check_nonneg_number(self.spillback_speed_frac, "spillback_speed_frac")
        if frac > 1.0:
            raise ValueError("spillback_speed_frac must be <= 1.0")
        if self.h <= 0:
            raise ValueError(f"h must be > 0, got {self.h}")

    @property
    def windows_to_flag_sustained(self) -> int:
        """Worst-case windows to flag a sustained ~1-band residual (documented)."""
        denom = 1.0 - self.slack
        if denom <= 0:
            return -1  # slack >= 1 absorbs a 1-band drift entirely (never flags)
        return math.ceil(self.h / denom)


# --------------------------------------------------------------------------- #
# Output verdict (immutable).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class EdgeVerdict:
    """Per-edge verdict for one window.

    Attributes
    ----------
    edge_id : str
    residual : float
        Signed mass-balance residual ``entered - exited - dStorage``.
    band : float
        Adaptive tolerance width this window.
    z : float
        Band-normalised residual ``residual / band``.
    s_hi, s_lo : float
        CUSUM accumulators after this window.
    status : str
        One of ``"ok"``, ``"warmup"``, ``"missing_data"``, ``"spillback"``,
        ``"flagged"``.
    reason : str
        ``"ok"`` | ``"inflated"`` (sustained over-claim) |
        ``"under_reported"`` (sustained under-claim) | ``"warmup"`` |
        ``"missing_data"`` | ``"spillback"``.
    flagged : bool
        True iff ``status == "flagged"``.
    latency_windows : int
        Windows from first non-warmup observation of the accumulating drift to
        this flag (>= 1 on a flag, -1 when not flagged).
    """

    edge_id: str
    residual: float
    band: float
    z: float
    s_hi: float
    s_lo: float
    status: str
    reason: str
    flagged: bool
    latency_windows: int


# --------------------------------------------------------------------------- #
# Per-edge running state (immutable; update returns a new state).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class EdgeState:
    """Immutable per-edge CUSUM + history state."""

    edge_id: str
    s_hi: float = 0.0
    s_lo: float = 0.0
    windows_seen: int = 0
    last_storage: int | None = None
    # Window index at which the currently-accumulating drift began (the first
    # window after the sums left zero). Used to report detection latency.
    drift_start_window: int | None = None


# --------------------------------------------------------------------------- #
# The detector.
# --------------------------------------------------------------------------- #

class FlowConservationDetector:
    """Stateful, per-edge, persistence-based flow-conservation detector.

    One instance tracks many edges (keyed by edge id). ``update`` folds one
    window's :class:`EdgeMeasurement` for one edge and returns an
    :class:`EdgeVerdict`; ``update_many`` folds a batch deterministically
    (sorted by edge id). State is immutable internally: each edge's
    :class:`EdgeState` is replaced, never mutated.
    """

    def __init__(self, band: AdaptiveBand | None = None,
                 cusum: CusumParams | None = None) -> None:
        if band is not None and not isinstance(band, AdaptiveBand):
            raise TypeError("band must be an AdaptiveBand or None")
        if cusum is not None and not isinstance(cusum, CusumParams):
            raise TypeError("cusum must be a CusumParams or None")
        self._band = band if band is not None else AdaptiveBand()
        self._cusum = cusum if cusum is not None else CusumParams()
        self._states: dict[str, EdgeState] = {}

    @property
    def band_params(self) -> AdaptiveBand:
        return self._band

    @property
    def cusum_params(self) -> CusumParams:
        return self._cusum

    def state_of(self, edge_id: str) -> EdgeState | None:
        """Read-only snapshot of an edge's state (or None if unseen)."""
        return self._states.get(edge_id)

    def states(self) -> Mapping[str, EdgeState]:
        """Read-only view of all edge states (immutable mapping)."""
        return MappingProxyType(dict(self._states))

    def _is_spillback(self, m: EdgeMeasurement) -> bool:
        """A jam: edge densely occupied AND crawling well below free speed.

        Occupancy alone is enough when no usable free_speed is known; when a
        free_speed is given we additionally require the edge to be crawling, so
        a dense-but-flowing edge (high occupancy, near free speed) is NOT a jam.
        """
        if m.occupancy < self._cusum.spillback_occupancy:
            return False
        if m.free_speed > 0:
            return m.mean_speed <= self._cusum.spillback_speed_frac * m.free_speed
        return True

    def update(self, m: EdgeMeasurement,
               missing: bool = False) -> EdgeVerdict:
        """Fold one window's measurement for ``m.edge_id``; return the verdict.

        Parameters
        ----------
        m : EdgeMeasurement
            This window's reconciliation evidence.
        missing : bool
            True when the caller could not obtain a measurement this window
            (sensor dropout / upstream read error). The CUSUM HOLDS: state is
            unchanged and the verdict is ``missing_data`` (never a flag).
        """
        if not isinstance(m, EdgeMeasurement):
            raise TypeError("m must be an EdgeMeasurement")
        if not isinstance(missing, bool):
            raise TypeError("missing must be a bool")

        prev = self._states.get(m.edge_id, EdgeState(edge_id=m.edge_id))

        # --- sensor dropout / missing window: HOLD the CUSUM, never flag. -----
        if missing:
            # State is untouched (sums + history preserved across the gap) so a
            # dropout neither accumulates evidence nor erases it.
            return EdgeVerdict(
                edge_id=m.edge_id, residual=0.0, band=0.0, z=0.0,
                s_hi=prev.s_hi, s_lo=prev.s_lo, status="missing_data",
                reason="missing_data", flagged=False, latency_windows=-1)

        # storage_prev: explicit caller value, else the remembered last storage,
        # else (first ever window) assume no change so warm-up does not invent a
        # spurious delta.
        if m.storage_prev is not None:
            storage_prev = m.storage_prev
        elif prev.last_storage is not None:
            storage_prev = prev.last_storage
        else:
            storage_prev = m.storage_now

        d_storage = m.storage_now - storage_prev
        residual = float(m.entered - m.exited - d_storage)
        # Expected flow for the relative band term: the larger of the two
        # measured throughputs (so the band is sized to the busier side).
        expected_flow = float(max(m.entered, m.exited))
        band = self._band.width(expected_flow, m.storage_now, storage_prev)
        z = residual / band  # band > 0 guaranteed (abs_floor > 0)

        windows_seen = prev.windows_seen + 1
        new_storage = m.storage_now

        # --- spillback: a jam is not an attack. Reconcile but do NOT feed the
        #     CUSUM (storage is changing faster than the snapshot can track). ---
        if self._is_spillback(m):
            new_state = replace(prev, windows_seen=windows_seen,
                                 last_storage=new_storage)
            self._states[m.edge_id] = new_state
            return EdgeVerdict(
                edge_id=m.edge_id, residual=residual, band=band, z=z,
                s_hi=prev.s_hi, s_lo=prev.s_lo, status="spillback",
                reason="spillback", flagged=False, latency_windows=-1)

        # --- warm-up: prime history, never flag, do not accumulate. -----------
        if windows_seen <= self._cusum.warmup_windows:
            new_state = replace(prev, windows_seen=windows_seen,
                                 last_storage=new_storage)
            self._states[m.edge_id] = new_state
            return EdgeVerdict(
                edge_id=m.edge_id, residual=residual, band=band, z=z,
                s_hi=prev.s_hi, s_lo=prev.s_lo, status="warmup",
                reason="warmup", flagged=False, latency_windows=-1)

        # --- two-sided tabular CUSUM on z. ------------------------------------
        slack = self._cusum.slack
        s_hi = max(0.0, prev.s_hi + z - slack)
        s_lo = max(0.0, prev.s_lo - z - slack)

        # Track when the currently-accumulating drift began (for latency). The
        # drift "starts" on the first window either sum becomes positive after
        # having been at rest; it resets when both sums fall back to zero.
        drift_start = prev.drift_start_window
        if prev.s_hi <= 0.0 and prev.s_lo <= 0.0 and (s_hi > 0.0 or s_lo > 0.0):
            drift_start = windows_seen
        elif s_hi <= 0.0 and s_lo <= 0.0:
            drift_start = None

        flagged = s_hi > self._cusum.h or s_lo > self._cusum.h
        if flagged:
            reason = "inflated" if s_hi >= s_lo else "under_reported"
            status = "flagged"
            start = drift_start if drift_start is not None else windows_seen
            latency = windows_seen - start + 1
            # On a flag, reset the firing accumulator so a sustained attack
            # re-arms and re-flags each detection interval rather than latching
            # forever (and the latency of the NEXT detection is measured fresh).
            if reason == "inflated":
                s_hi = 0.0
            else:
                s_lo = 0.0
            drift_start = None
        else:
            reason = "ok"
            status = "ok"
            latency = -1

        new_state = EdgeState(
            edge_id=m.edge_id, s_hi=s_hi, s_lo=s_lo,
            windows_seen=windows_seen, last_storage=new_storage,
            drift_start_window=drift_start)
        self._states[m.edge_id] = new_state

        return EdgeVerdict(
            edge_id=m.edge_id, residual=residual, band=band, z=z,
            s_hi=s_hi, s_lo=s_lo, status=status, reason=reason,
            flagged=flagged, latency_windows=latency)

    def update_many(
        self,
        measurements: Mapping[str, EdgeMeasurement],
        missing: Mapping[str, bool] | None = None,
    ) -> list[EdgeVerdict]:
        """Fold a batch of per-edge measurements; return verdicts sorted by edge.

        ``missing`` optionally marks edges whose measurement is absent this
        window (sensor dropout). Deterministic: edges processed in sorted order.
        """
        if not isinstance(measurements, Mapping):
            raise TypeError("measurements must be a mapping")
        miss = missing or {}
        if not isinstance(miss, Mapping):
            raise TypeError("missing must be a mapping or None")
        verdicts: list[EdgeVerdict] = []
        for edge_id in sorted(measurements.keys()):
            m = measurements[edge_id]
            verdicts.append(self.update(m, missing=bool(miss.get(edge_id, False))))
        return verdicts
