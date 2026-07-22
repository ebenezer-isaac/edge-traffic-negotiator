"""Vehicle-conservation plausibility check -- the detection primitive.

Idea
----
A junction ``A`` claims (in its signed neighbour message) that it released
``N`` vehicles toward neighbour ``B`` over a travel-time window. ``B``
independently observes ``M`` vehicles arriving on edge ``A->B``. Under
physical conservation of vehicles, ``N`` and ``M`` should agree to within a
small tolerance (a few vehicles still in transit / sensor jitter). A gross
disagreement is flagged:

  * ``N >> M`` (claimed far exceeds observed)  -> count-inflation spoof.
  * ``N << M`` (observed far exceeds claimed)  -> under-report / fault.
  * claim present, no observation (or vice-versa) -> missing-data fault.

This is a *consistency* check, not a *truth* check. It proves only that two
parties' reports are mutually consistent. It CANNOT identify which of two
disagreeing parties is wrong, and -- critically -- it is evadable by a
**coordinated, conservation-respecting attacker** who inflates A's claim and
B's observation in lockstep so the books still balance (the ``Xiao2026``
limit; see MASTER-SPEC.md s.6). That residual threat is what the
authentication / registry layer complements; this primitive catches
uncoordinated spoofs and faults only.

Design notes
------------
* Stateless ``evaluate`` form: the caller supplies the already-windowed
  per-edge claim and observation tallies; this module does no time-windowing
  or state accumulation, which keeps it trivially testable and deterministic.
* Immutable: ``Detection`` is a frozen dataclass; ``evaluate`` builds and
  returns new objects and never mutates its inputs.
* Inputs validated at the boundary (errors raised explicitly, never
  swallowed): tolerance must be a non-negative int; counts must be ints.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["Detection", "ConservationChecker"]

# Edge key: (src_junction, dst_junction), e.g. ("A0", "A1") for edge A0->A1.
EdgeKey = tuple[str, str]


@dataclass(frozen=True)
class Detection:
    """Per-edge verdict of the conservation check.

    Attributes
    ----------
    src, dst : str
        Endpoints of the directed edge ``src -> dst``.
    claimed : int
        Vehicles ``src`` claims it released toward ``dst`` in the window
        (0 if no claim was present).
    observed : int
        Vehicles ``dst`` independently observed arriving on edge ``src->dst``
        in the window (0 if no observation was present).
    delta : int
        ``claimed - observed``. Positive => over-report, negative =>
        under-report.
    flagged : bool
        ``True`` iff this edge is physically implausible (see ``reason``).
    reason : str
        One of: ``"ok"``, ``"inflated"``, ``"under_reported"``,
        ``"missing_claim"``, ``"missing_observation"``.
    """

    src: str
    dst: str
    claimed: int
    observed: int
    delta: int
    flagged: bool
    reason: str


class ConservationChecker:
    """Stateless evaluator for the vehicle-conservation plausibility check."""

    def __init__(self, tolerance: int = 2) -> None:
        """Create a checker.

        Parameters
        ----------
        tolerance : int
            Maximum allowed ``abs(claimed - observed)`` before an edge that
            has *both* a claim and an observation is flagged. Must be a
            non-negative integer (``bool`` rejected -- it is a stray type
            error, not a real tolerance). Vehicles still in transit and
            sensor jitter live inside this band.
        """
        # Validate at the boundary; never silently coerce.
        if isinstance(tolerance, bool) or not isinstance(tolerance, int):
            raise TypeError(f"tolerance must be an int, got {type(tolerance).__name__}")
        if tolerance < 0:
            raise ValueError(f"tolerance must be >= 0, got {tolerance}")
        self._tolerance = tolerance

    @property
    def tolerance(self) -> int:
        return self._tolerance

    def evaluate(
        self,
        claims: dict[EdgeKey, int],
        observed: dict[EdgeKey, int],
    ) -> list[Detection]:
        """Reconcile claimed outflows against observed inflows, per edge.

        For every edge present in *either* dict, produce exactly one
        ``Detection``. Returns a new list sorted by edge key for
        deterministic, reproducible output. Neither input is mutated.

        Reasons
        -------
        * ``missing_claim``       -- observation present, no claim
          (claimed treated as 0). Always flagged: B saw traffic A denies
          sending (Sybil / fabricated inflow, or A withholding).
        * ``missing_observation`` -- claim present, no observation
          (observed treated as 0). Always flagged: A says it sent traffic B
          never saw (sensor outage / fabricated outflow).
        * ``inflated``            -- both present, ``delta > tolerance``
          (claimed exceeds observed: count-inflation spoof).
        * ``under_reported``      -- both present, ``delta < -tolerance``
          (observed exceeds claimed: under-report / fault).
        * ``ok``                  -- both present, ``abs(delta) <= tolerance``.

        Parameters
        ----------
        claims : dict[(src, dst), int]
            Claimed released-vehicle counts, keyed by directed edge.
        observed : dict[(src, dst), int]
            Independently observed arrival counts, keyed by directed edge.

        Returns
        -------
        list[Detection]
            One Detection per edge, sorted ascending by ``(src, dst)``.
        """
        self._validate_counts(claims, "claims")
        self._validate_counts(observed, "observed")

        edges = set(claims.keys()) | set(observed.keys())
        detections: list[Detection] = []

        for key in sorted(edges):
            src, dst = key
            has_claim = key in claims
            has_obs = key in observed
            claimed = claims.get(key, 0)
            observed_count = observed.get(key, 0)
            delta = claimed - observed_count

            if not has_claim:
                flagged, reason = True, "missing_claim"
            elif not has_obs:
                flagged, reason = True, "missing_observation"
            elif delta > self._tolerance:
                flagged, reason = True, "inflated"
            elif delta < -self._tolerance:
                flagged, reason = True, "under_reported"
            else:
                flagged, reason = False, "ok"

            detections.append(
                Detection(
                    src=src,
                    dst=dst,
                    claimed=claimed,
                    observed=observed_count,
                    delta=delta,
                    flagged=flagged,
                    reason=reason,
                )
            )

        return detections

    @staticmethod
    def _validate_counts(counts: dict[EdgeKey, int], label: str) -> None:
        """Validate an edge->count mapping at the boundary.

        Rejects non-dict inputs, malformed keys, and non-int / negative /
        boolean counts. Vehicle counts are physically non-negative integers.
        """
        if not isinstance(counts, dict):
            raise TypeError(f"{label} must be a dict, got {type(counts).__name__}")
        for key, value in counts.items():
            if (
                not isinstance(key, tuple)
                or len(key) != 2
                or not all(isinstance(part, str) for part in key)
            ):
                raise TypeError(
                    f"{label} key must be a (src: str, dst: str) tuple, got {key!r}"
                )
            if isinstance(value, bool) or not isinstance(value, int):
                raise TypeError(
                    f"{label}[{key!r}] count must be an int, got "
                    f"{type(value).__name__}"
                )
            if value < 0:
                raise ValueError(
                    f"{label}[{key!r}] count must be >= 0, got {value}"
                )
