"""Ambiguous-case decision interface for Experiment 1 (SLM vs reference rule).

Why this module
----------------
`MASTER-SPEC.md` §8 requires a decision an
edge SLM can be characterized against: given a FLAGGED ambiguous case (an
event a fixed per-junction rule cannot cleanly settle), classify it as
**real** (escalate: preempt / reallocate) or **spoof-or-fault** (reject: stay
deterministic, discount the claim). `FORMAL-SPECIFICATION.md` §8 gives the
escalation predicate that decides WHEN a case is flagged in the first place
(never re-implemented here, only referenced):

    A1: the conservation/CUSUM detector (§3) flags a neighbour claim this
        window, or
    A2: an authenticated emergency/incident claim has partial evidence
        (corroboration present but below the hard-accept threshold, or
        stale/inconsistent beyond the tolerance `tol`), or
    A3: two authenticated reports about the same edge contradict beyond the
        tolerance band `tol`.

Fully corroborated and zero-evidence claims never reach this module; they
resolve deterministically in NORMAL regime (`FORMAL-SPECIFICATION.md` §8,
final paragraph). This module is the CHARACTERIZATION harness core for the
cases that DO escalate: a plain data interface (`FlaggedCase`), a decider that
implements it (`RuleDisambiguator`, the well-tuned reference rule / yardstick,
not a strawman), a deterministic labelled micro-benchmark
(`generate_dataset`), and a scorer (`evaluate`) that never pools the
anticipated and novel splits into one headline number.

The SLM decider (a future `SLMDisambiguator` wired to `slm_agent.SLMAgent`) is
OUT OF SCOPE here: this module only defines the shared input/output contract
so the SLM and the rule can be compared on identical labelled data. No SUMO,
no Foundry, no LLM calls, no network I/O; pure stdlib Python.

CUSUM / plausibility-band grounding (`FORMAL-SPECIFICATION.md` §1.2, §3):
`residual` is expressed in BAND UNITS (the CUSUM's band-normalised `z`), so
`1.0` means "at the plausibility-band edge" and `>1` means "out of band",
matching the detector's own normalisation. `persistence` mirrors the
project's persistence guards (`incident_persist=3`, `abnormal_persist=2`,
CUSUM decision threshold `h=3.0`, reference slack `k=0.5`): a single-window
crossing is never enough, sustained drift is.

Design constraints honoured
---------------------------
Frozen dataclasses throughout; `RuleDisambiguator.tune` returns a NEW
instance, never mutates `self`; every constructor validates its inputs with
explicit `TypeError` / `ValueError` (never a silent coercion); dataset
generation uses a seeded `random.Random` only (no wall-clock, no global
`random` state) so the same seed always yields the same cases.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from itertools import product
from typing import Callable, Union

__all__ = [
    "FlaggedCase",
    "Decision",
    "ESCALATE_REAL",
    "REJECT",
    "RuleDisambiguator",
    "generate_dataset",
    "evaluate",
]

# --------------------------------------------------------------------------- #
# Decision type: the shared output contract for every decider (rule or SLM).
# --------------------------------------------------------------------------- #

Decision = str
ESCALATE_REAL: Decision = "escalate_real"
REJECT: Decision = "reject"
_DECISIONS = frozenset({ESCALATE_REAL, REJECT})

_EVENT_TYPES = frozenset({
    "emergency_claim",
    "incident_claim",
    "conservation_anomaly",
    "multi_emergency",
    "emergency_plus_incident",
})
_LABELS = frozenset({"real", "spoof_or_fault"})
_SPLITS = frozenset({"anticipated", "novel"})


# --------------------------------------------------------------------------- #
# Boundary validation helpers (explicit errors, never silent coercion).
# --------------------------------------------------------------------------- #

def _check_bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool, got {type(value).__name__}")
    return value


def _check_nonneg_int(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an int, got {type(value).__name__}")
    if value < 0:
        raise ValueError(f"{name} must be >= 0, got {value}")
    return value


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


def _check_unit_interval(value: object, name: str) -> float:
    f = _check_nonneg_number(value, name)
    if f > 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {f}")
    return f


def _check_nonempty_str(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise TypeError(f"{name} must be a non-empty str, got {value!r}")
    return value


# --------------------------------------------------------------------------- #
# The shared input: one flagged, ambiguous case with ground truth attached.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class FlaggedCase:
    """One flagged ambiguous case: the SAME input given to the rule and the SLM.

    Attributes
    ----------
    case_id : str
        Unique identifier (dataset generation guarantees uniqueness).
    event_type : str
        One of ``emergency_claim``, ``incident_claim``, ``conservation_anomaly``,
        ``multi_emergency``, ``emergency_plus_incident``.
    corroboration_count : int
        Independent sightings corroborating the claim, EXCLUDING the claimer
        itself (>= 0; matches the corroboration concept in
        `FORMAL-SPECIFICATION.md` §4).
    residual : float
        Conservation residual in plausibility-BAND units (>= 0); ``1.0`` sits
        at the band edge, ``>1`` is out of band (matches the CUSUM
        band-normalised ``z`` in `FORMAL-SPECIFICATION.md` §3).
    persistence : int
        Consecutive windows the anomaly / claim persisted (>= 0; the CUSUM
        persistence guard, `FORMAL-SPECIFICATION.md` §1.2/§3).
    neighbour_agreement : float
        Fraction of reporting neighbours whose reports agree, in [0, 1].
    local_sensing : bool
        True iff THIS junction physically sensed the vehicle/event itself.
    severity : float
        Claimed severity of the event, in [0, 1].
    split : str
        ``"anticipated"`` (the rule is tuned/designed for this shape) or
        ``"novel"`` (held out from rule tuning; see `generate_dataset`).
    label : str
        Ground truth: ``"real"`` or ``"spoof_or_fault"``.
    """

    case_id: str
    event_type: str
    corroboration_count: int
    residual: float
    persistence: int
    neighbour_agreement: float
    local_sensing: bool
    severity: float
    split: str
    label: str

    def __post_init__(self) -> None:
        _check_nonempty_str(self.case_id, "case_id")
        if self.event_type not in _EVENT_TYPES:
            raise ValueError(
                f"event_type must be one of {sorted(_EVENT_TYPES)}, "
                f"got {self.event_type!r}"
            )
        _check_nonneg_int(self.corroboration_count, "corroboration_count")
        _check_nonneg_number(self.residual, "residual")
        _check_nonneg_int(self.persistence, "persistence")
        _check_unit_interval(self.neighbour_agreement, "neighbour_agreement")
        _check_bool(self.local_sensing, "local_sensing")
        _check_unit_interval(self.severity, "severity")
        if self.split not in _SPLITS:
            raise ValueError(
                f"split must be one of {sorted(_SPLITS)}, got {self.split!r}"
            )
        if self.label not in _LABELS:
            raise ValueError(
                f"label must be one of {sorted(_LABELS)}, got {self.label!r}"
            )


# --------------------------------------------------------------------------- #
# The reference rule: a well-tuned, fixed-threshold yardstick (not a strawman).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class RuleDisambiguator:
    """Fixed-threshold reference rule ("the yardstick"), the same evidence the
    SLM sees.

    Decision logic (documented; not just an opaque formula)
    ---------------------------------------------------------
    A case is escalated as **real** iff EITHER:

      * ``local_sensing`` is True: this junction physically saw the event
        itself, which is ground truth by construction
        (`FORMAL-SPECIFICATION.md` §4, ``admissible_ev``: local sensing is
        always trusted); OR
      * all four corroboration-side conditions hold simultaneously:
        ``corroboration_count >= corr_k`` (enough independent witnesses),
        ``residual <= residual_max`` (the conservation signature is inside
        the plausibility band, i.e. physically consistent with a real
        event), ``persistence >= persistence_p`` (the anomaly/claim is
        sustained, not a single-window blip, per the CUSUM persistence
        guard), and ``neighbour_agreement >= agreement_min`` (the
        corroborating neighbours are not contradicting each other, per A3).

    Otherwise the case is **rejected** (treated as spoof-or-fault; stay
    deterministic, discount the claim). Every threshold is a plain
    conjunction/disjunction of the same evidence fields the SLM is given, so
    the rule is fully auditable.
    """

    corr_k: int = 1
    residual_max: float = 1.0
    persistence_p: int = 2
    agreement_min: float = 0.5

    # Small, documented tuning grid used by ``tune``. Kept deliberately small
    # (3 x 4 x 3 x 4 = 144 combinations) so tuning stays a cheap grid search
    # over a labelled dev split, not an optimizer.
    _CORR_K_GRID = (0, 1, 2)
    _RESIDUAL_MAX_GRID = (0.75, 1.0, 1.25, 1.5)
    _PERSISTENCE_P_GRID = (1, 2, 3)
    _AGREEMENT_MIN_GRID = (0.3, 0.5, 0.6, 0.75)

    def __post_init__(self) -> None:
        _check_nonneg_int(self.corr_k, "corr_k")
        _check_nonneg_number(self.residual_max, "residual_max")
        _check_nonneg_int(self.persistence_p, "persistence_p")
        _check_unit_interval(self.agreement_min, "agreement_min")

    def decide(self, case: FlaggedCase) -> Decision:
        """Classify one flagged case. See the class docstring for the logic."""
        if not isinstance(case, FlaggedCase):
            raise TypeError("case must be a FlaggedCase")
        if case.local_sensing:
            return ESCALATE_REAL
        if (
            case.corroboration_count >= self.corr_k
            and case.residual <= self.residual_max
            and case.persistence >= self.persistence_p
            and case.neighbour_agreement >= self.agreement_min
        ):
            return ESCALATE_REAL
        return REJECT

    def tune(self, cases: list) -> "RuleDisambiguator":
        """Grid-search thresholds to MAXIMISE balanced accuracy on the
        ANTICIPATED split of ``cases`` only (never the novel split; tuning on
        novel cases would erase the point of holding them out). Returns a NEW
        ``RuleDisambiguator`` (immutability); ``self`` is never mutated.

        Balanced accuracy = (recall_real + specificity_spoof) / 2, chosen
        over raw accuracy because the dataset need not be perfectly balanced
        and a threshold search should not be free to game class imbalance.

        If no anticipated cases are supplied, returns a new instance carrying
        this rule's own current thresholds unchanged (nothing to tune on).
        """
        if not isinstance(cases, list):
            raise TypeError("cases must be a list of FlaggedCase")
        anticipated = [c for c in cases if c.split == "anticipated"]
        if not anticipated:
            return RuleDisambiguator(
                corr_k=self.corr_k,
                residual_max=self.residual_max,
                persistence_p=self.persistence_p,
                agreement_min=self.agreement_min,
            )

        best = self
        best_score = _balanced_accuracy(self.decide, anticipated)
        for corr_k, residual_max, persistence_p, agreement_min in product(
            self._CORR_K_GRID,
            self._RESIDUAL_MAX_GRID,
            self._PERSISTENCE_P_GRID,
            self._AGREEMENT_MIN_GRID,
        ):
            candidate = RuleDisambiguator(
                corr_k=corr_k,
                residual_max=residual_max,
                persistence_p=persistence_p,
                agreement_min=agreement_min,
            )
            score = _balanced_accuracy(candidate.decide, anticipated)
            if score > best_score:
                best_score = score
                best = candidate
        # Always return a NEW object, even when the incumbent wins, so the
        # caller never depends on identity with ``self``.
        return RuleDisambiguator(
            corr_k=best.corr_k,
            residual_max=best.residual_max,
            persistence_p=best.persistence_p,
            agreement_min=best.agreement_min,
        )


def _balanced_accuracy(decide_fn: Callable[[FlaggedCase], Decision],
                        cases: list) -> float:
    """(recall on 'real' + specificity on 'spoof_or_fault') / 2."""
    tp = fn = fp = tn = 0
    for case in cases:
        predicted_real = decide_fn(case) == ESCALATE_REAL
        actual_real = case.label == "real"
        if actual_real and predicted_real:
            tp += 1
        elif actual_real and not predicted_real:
            fn += 1
        elif not actual_real and predicted_real:
            fp += 1
        else:
            tn += 1
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    specificity = tn / (tn + fp) if (tn + fp) else 0.0
    return (recall + specificity) / 2.0


# --------------------------------------------------------------------------- #
# Deterministic labelled micro-benchmark (curated, both splits, no leakage).
# --------------------------------------------------------------------------- #

def _round3(x: float) -> float:
    return round(x, 3)


def generate_dataset(seed: int = 0) -> list:
    """Deterministic, labelled curated micro-benchmark for Experiment 1.

    Uses ONLY a seeded ``random.Random(seed)`` (no wall-clock, no global
    ``random`` state), so the same ``seed`` always yields byte-identical
    cases. Every label comes from a DOCUMENTED generative story below, never
    from "whatever the rule would decide" (no leakage): the anticipated
    stories happen to align with a well-tuned rule's thresholds BY DESIGN
    (that is what "anticipated" means), the novel stories deliberately do
    not.

    ANTICIPATED split (60 cases: 20 per event type x 3 event types, 30
    real / 30 spoof_or_fault): the textbook patterns the rule is built for.

      * ``clear_local``: this junction physically sensed the event
        (``local_sensing=True``). Ground truth: real, unconditionally.
      * ``clear_corroborated``: no local sensing, but rich independent
        corroboration (2-4 sightings), low in-band residual, sustained
        persistence, high neighbour agreement. Ground truth: real (a
        genuinely well-attested remote event).
      * ``phantom_zero_corrob``: zero corroboration and no local sensing.
        Ground truth: spoof_or_fault (nothing independently attests it,
        regardless of anything else claimed).
      * ``in_band_fault``: residual is INSIDE the plausibility band (the
        flow signature is not actually anomalous) but corroboration is thin
        (0-1) and short-lived, and neighbours disagree. Ground truth:
        spoof_or_fault (a false/faulty flag on an otherwise unremarkable
        edge, not a genuine event).

    NOVEL split (30 cases; 15 real / 15 spoof_or_fault), held out from rule
    tuning entirely:

      * (a) held-out COMBINATIONS of the same 3 event types (18 cases, 6 per
        type): ``sparse_real`` (a genuine event on a sparsely-instrumented
        edge: exactly one corroborating sighting, borderline in-band
        residual, short persistence, and only MIXED neighbour agreement
        because most neighbours simply have no view of it, not because it is
        fake) versus ``collusion_spoof`` (a single fabricated echo
        corroboration paired with a residual that is just OUTSIDE the band,
        because the underlying flow physics still doesn't add up, and a
        similarly mixed neighbour-agreement reading). Both patterns share
        corroboration_count=1 and overlapping agreement ranges by
        construction, so corroboration count ALONE cannot separate them,
        unlike every anticipated case.
      * (b) genuinely NEW event types never seen in tuning (12 cases, 6 per
        type): ``multi_emergency`` (one of two simultaneous emergency claims
        at a junction; real = a genuine second responder in a mass-casualty
        surge, corroborated; spoof = an opportunistic phantom claim riding
        the confusion of a real first emergency, uncorroborated) and
        ``emergency_plus_incident`` (an EV claim coinciding with an incident
        report on the same corridor; real = a genuine ambulance rerouting
        around a genuine, corroborated incident; spoof = a fabricated
        incident/claim used to divert traffic, thinly and inconsistently
        attested).

    Returns a list of 90 ``FlaggedCase`` (60 anticipated, 30 novel).
    """
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError(f"seed must be an int, got {type(seed).__name__}")

    rnd = random.Random(seed)
    cases: list = []
    counter = [0]

    def next_id(tag: str) -> str:
        counter[0] += 1
        return f"{tag}-{counter[0]:03d}"

    def make(tag: str, event_type: str, corr: int, residual: float,
             persistence: int, agreement: float, local_sensing: bool,
             severity: float, split: str, label: str) -> None:
        cases.append(FlaggedCase(
            case_id=next_id(tag),
            event_type=event_type,
            corroboration_count=corr,
            residual=_round3(residual),
            persistence=persistence,
            neighbour_agreement=_round3(agreement),
            local_sensing=local_sensing,
            severity=_round3(severity),
            split=split,
            label=label,
        ))

    # ----------------------------- ANTICIPATED ---------------------------- #
    for event_type in ("emergency_claim", "incident_claim", "conservation_anomaly"):
        # 5x clear_local: real by direct sensing.
        for _ in range(5):
            make(
                "ANT-LOC", event_type,
                corr=rnd.randint(0, 2),
                residual=rnd.uniform(0.05, 0.5),
                persistence=rnd.randint(1, 4),
                agreement=rnd.uniform(0.4, 1.0),
                local_sensing=True,
                severity=rnd.uniform(0.5, 1.0),
                split="anticipated", label="real",
            )
        # 5x clear_corroborated: real, remote but well-attested.
        for _ in range(5):
            make(
                "ANT-COR", event_type,
                corr=rnd.randint(2, 4),
                residual=rnd.uniform(0.05, 0.4),
                persistence=rnd.randint(2, 5),
                agreement=rnd.uniform(0.75, 1.0),
                local_sensing=False,
                severity=rnd.uniform(0.5, 1.0),
                split="anticipated", label="real",
            )
        # 5x phantom_zero_corrob: spoof, nothing attests it.
        for _ in range(5):
            make(
                "ANT-PHT", event_type,
                corr=0,
                residual=rnd.uniform(0.3, 2.5),
                persistence=rnd.randint(0, 3),
                agreement=rnd.uniform(0.0, 0.4),
                local_sensing=False,
                severity=rnd.uniform(0.1, 0.6),
                split="anticipated", label="spoof_or_fault",
            )
        # 5x in_band_fault: spoof, in-band but thin/short-lived/disputed.
        for _ in range(5):
            make(
                "ANT-FLT", event_type,
                corr=rnd.choice((0, 1)),
                residual=rnd.uniform(0.1, 0.9),
                persistence=rnd.randint(0, 1),
                agreement=rnd.uniform(0.1, 0.45),
                local_sensing=False,
                severity=rnd.uniform(0.05, 0.4),
                split="anticipated", label="spoof_or_fault",
            )

    # -------------------------------- NOVEL ------------------------------- #
    # (a) held-out combinations of the same 3 event types.
    for event_type in ("emergency_claim", "incident_claim", "conservation_anomaly"):
        for _ in range(3):
            make(
                "NOV-SPR", event_type,
                corr=1,
                residual=rnd.uniform(0.5, 0.95),
                persistence=rnd.randint(1, 2),
                agreement=rnd.uniform(0.35, 0.6),
                local_sensing=False,
                severity=rnd.uniform(0.4, 0.8),
                split="novel", label="real",
            )
        for _ in range(3):
            make(
                "NOV-COL", event_type,
                corr=1,
                residual=rnd.uniform(1.0, 1.6),
                persistence=rnd.randint(1, 3),
                agreement=rnd.uniform(0.3, 0.55),
                local_sensing=False,
                severity=rnd.uniform(0.3, 0.7),
                split="novel", label="spoof_or_fault",
            )

    # (b) genuinely new event types, never seen in tuning.
    for _ in range(3):
        make(
            "NOV-ME-R", "multi_emergency",
            corr=rnd.randint(1, 2),
            residual=rnd.uniform(0.2, 0.8),
            persistence=rnd.randint(1, 3),
            agreement=rnd.uniform(0.5, 0.85),
            local_sensing=False,
            severity=rnd.uniform(0.6, 1.0),
            split="novel", label="real",
        )
    for _ in range(3):
        make(
            "NOV-ME-S", "multi_emergency",
            corr=0,
            residual=rnd.uniform(0.5, 2.0),
            persistence=rnd.randint(0, 2),
            agreement=rnd.uniform(0.1, 0.4),
            local_sensing=False,
            severity=rnd.uniform(0.3, 0.7),
            split="novel", label="spoof_or_fault",
        )
    for _ in range(3):
        make(
            "NOV-EI-R", "emergency_plus_incident",
            corr=rnd.randint(1, 3),
            residual=rnd.uniform(0.1, 0.7),
            persistence=rnd.randint(2, 4),
            agreement=rnd.uniform(0.6, 0.9),
            local_sensing=False,
            severity=rnd.uniform(0.5, 0.9),
            split="novel", label="real",
        )
    for _ in range(3):
        make(
            "NOV-EI-S", "emergency_plus_incident",
            corr=rnd.choice((0, 1)),
            residual=rnd.uniform(0.8, 1.8),
            persistence=rnd.randint(0, 2),
            agreement=rnd.uniform(0.2, 0.5),
            local_sensing=False,
            severity=rnd.uniform(0.2, 0.6),
            split="novel", label="spoof_or_fault",
        )

    return cases


# --------------------------------------------------------------------------- #
# Scoring: per-split metrics, never pooled into one headline number.
# --------------------------------------------------------------------------- #

_DeciderLike = Union[object, Callable[[FlaggedCase], Decision]]


def _predict(decider: _DeciderLike, case: FlaggedCase) -> Decision:
    if hasattr(decider, "decide"):
        result = decider.decide(case)
    elif callable(decider):
        result = decider(case)
    else:
        raise TypeError(
            "decider must have a .decide(case) method or be callable"
        )
    if result not in _DECISIONS:
        raise ValueError(
            f"decider returned {result!r}, expected one of {sorted(_DECISIONS)}"
        )
    return result


def _metrics_for(cases: list, decider: _DeciderLike) -> dict:
    tp = fn = fp = tn = 0
    for case in cases:
        predicted_real = _predict(decider, case) == ESCALATE_REAL
        actual_real = case.label == "real"
        if actual_real and predicted_real:
            tp += 1
        elif actual_real and not predicted_real:
            fn += 1
        elif not actual_real and predicted_real:
            fp += 1
        else:
            tn += 1

    n = len(cases)
    accuracy = (tp + tn) / n if n else 0.0
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    # Fraction of genuinely spoof_or_fault cases wrongly granted escalation.
    false_preemption_rate = fp / (fp + tn) if (fp + tn) else 0.0

    return {
        "n": n,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
        "accuracy": accuracy,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "false_preemption_rate": false_preemption_rate,
    }


def evaluate(decider: _DeciderLike, cases: list) -> dict:
    """Score ``decider`` over ``cases``, reporting PER-SPLIT and overall
    metrics. ``decider`` is either an object with a ``.decide(case)`` method
    (e.g. :class:`RuleDisambiguator`) or a plain callable ``case -> Decision``
    (e.g. a future SLM wrapper), so the SLM and the rule can be scored with
    the same function.

    Metrics (positive class = ``"real"``): accuracy, precision, recall, F1,
    and ``false_preemption_rate`` (fraction of ``spoof_or_fault`` cases
    wrongly classified ``escalate_real``, i.e. traffic control preempted for
    an event that never happened).

    Returns ``{"anticipated": {...}, "novel": {...}, "overall": {...}}``. The
    two splits are ALWAYS reported separately (per
    `MASTER-SPEC.md` §8: "never pooled into one accuracy
    number"); ``overall`` is provided in addition, never as a replacement.
    On an empty case list (or an empty split), every rate metric is 0.0
    rather than raising a ZeroDivisionError.
    """
    if not isinstance(cases, list):
        raise TypeError("cases must be a list of FlaggedCase")
    for case in cases:
        if not isinstance(case, FlaggedCase):
            raise TypeError("cases must contain only FlaggedCase instances")

    anticipated = [c for c in cases if c.split == "anticipated"]
    novel = [c for c in cases if c.split == "novel"]

    return {
        "anticipated": _metrics_for(anticipated, decider),
        "novel": _metrics_for(novel, decider),
        "overall": _metrics_for(cases, decider),
    }
