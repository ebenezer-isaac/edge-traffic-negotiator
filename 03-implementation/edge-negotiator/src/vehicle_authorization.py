"""Multi-authorised-vehicle authorisation classifier (MASTER-SPEC §4/§6; H2 trust).

The runtime KB that decides, for a claimed authorised vehicle (ambulance / fire /
police / maintenance / civilian / unknown), WHETHER the claim is a legitimate basis
for the requested action -- above all whether it may PREEMPT the signal. It is a
DETERMINISTIC, pure-stdlib gate grounded in ``ground_rules.yaml`` (the §A entity
taxonomy + the §C attack taxonomy + the B1/P2/P6/P8 policies); it loads the KB, it
does not hard-code the vehicle classes, and an unmatched case resolves to UNKNOWN
(never a guessed grant).

Why this exists: the emergency controller's live detector only distinguishes
``vClass=="emergency"`` from everything else -- it cannot tell an ambulance (may
preempt) from a maintenance vehicle (may NOT preempt, only reserve a lane), nor a
signed-but-wrong-class claim (signal_tampering) from a genuine one. This classifier
is the KB that makes those distinctions explicit, auditable, and testable, and is
evaluated with a categorised adversarial suite + balanced P/R/FPR/FNR (Lee).

Classification (the terminal set from the KB):
  * LEGITIMATE        -- an authorised class, a valid key of an authorising class,
    a complete claim, an action the class is allowed; ``preemption_granted`` iff
    the class is preemption-allowed AND the action is a preemption.
  * SPOOFED_OR_FAULTY -- an invalid/absent/wrong-class key (invalid_id), a valid key
    asserting a class/action it is not authorised for (signal_tampering).
  * UNKNOWN           -- a class not in the taxonomy (unknown_vehicle_type), missing
    required metadata (missing_metadata), or contradictory signals (escalate).
Each result names the KB ``policy`` (P2/P6/P8/P1/P4) and ``attack_category`` it maps
to, so a decision is auditable back to the pinned KB.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

import yaml

_HERE = os.path.dirname(os.path.abspath(__file__))
GROUND_RULES_PATH = os.path.join(_HERE, "..", "ground_rules.yaml")

# Terminal classifications (must match ground_rules.yaml `classifications`).
LEGITIMATE = "LEGITIMATE"
SPOOFED_OR_FAULTY = "SPOOFED_OR_FAULTY"
UNKNOWN = "UNKNOWN"

# Required claim metadata; any absent/None -> missing_metadata -> UNKNOWN (P8).
REQUIRED_FIELDS = ("asserted_class", "action", "key_present")


@dataclass(frozen=True)
class Entity:
    """One authorised-entity row from ground_rules.yaml §A (structured fields)."""
    cls: str
    priority: object
    preemption_allowed: bool
    actions_allowed: tuple
    authorising_key_classes: tuple
    key_required: bool


@dataclass(frozen=True)
class VehicleClaim:
    """A claim to authorise. Fields are the mechanical, boundary-validated inputs a
    junction actually has: the asserted class, the requested action, whether a key
    is present + valid + which authority class it belongs to, whether the schema is
    complete, and whether two approved reports contradict (P6)."""
    asserted_class: str | None
    action: str | None
    key_present: bool = False
    key_valid: bool = False
    key_class: str | None = None          # authority class the signing key belongs to
    metadata: dict = field(default_factory=dict)
    contradictory: bool = False

    def missing_required(self) -> list:
        miss = []
        for f in REQUIRED_FIELDS:
            v = getattr(self, f, None)
            if v is None or (isinstance(v, str) and v.strip() == ""):
                miss.append(f)
        # asserted_class/action are the schema essentials; a claim asserting a key
        # is present must also carry the key_class (else the schema is incomplete).
        if self.key_present and not self.key_class:
            miss.append("key_class")
        return miss


def _req_bool(cls: str, field_name: str, v) -> bool:
    """A KB bool field must be a real bool. A type-malformed value is a defect,
    never silently coerced -- a coerced ``key_required`` could drop the key gate
    (docstring: no silent default)."""
    if not isinstance(v, bool):
        raise ValueError(
            f"entity {cls!r} field {field_name!r} must be a bool, got "
            f"{type(v).__name__} ({v!r}); the KB must be explicit")
    return v


# Fallback preemption-action set if the KB omits the (grounded) `preemption_actions`
# list -- kept only so an older KB still loads; the loaded value takes precedence.
_DEFAULT_PREEMPTION_ACTIONS = ("preempt", "corridor", "escort_hold")


def load_kb(path: str | None = None) -> tuple[dict, tuple]:
    """Load ``({class: Entity}, preemption_actions)`` from the KB (fail-loud).

    Requires the structured authorisation fields (preemption_allowed,
    actions_allowed, authorising_key_classes, key_required); a KB row missing one
    -- or carrying a non-bool for a bool field -- is a defect (raise), never
    silently defaulted, so an unauthorised class cannot become preemption-allowed
    by omission or type coercion. ``preemption_actions`` (which actions REQUEST a
    preemption) is read from the KB so the grant logic is KB-grounded, not
    hardcoded.
    """
    p = path or GROUND_RULES_PATH
    with open(p, encoding="utf-8") as fh:
        doc = yaml.safe_load(fh) or {}
    rows = doc.get("entities") or []
    if not rows:
        raise ValueError(f"ground_rules.yaml has no `entities` taxonomy at {p}")
    out: dict[str, Entity] = {}
    for r in rows:
        cls = r.get("class")
        if not cls:
            raise ValueError(f"entity row without a class: {r!r}")
        for req in ("preemption_allowed", "actions_allowed",
                    "authorising_key_classes", "key_required"):
            if req not in r:
                raise ValueError(
                    f"entity {cls!r} missing required authorisation field {req!r} "
                    "(the KB must be explicit; no silent default)")
        out[cls] = Entity(
            cls=cls,
            priority=r.get("priority"),
            preemption_allowed=_req_bool(cls, "preemption_allowed",
                                         r.get("preemption_allowed")),
            actions_allowed=tuple(r.get("actions_allowed") or ()),
            authorising_key_classes=tuple(r.get("authorising_key_classes") or ()),
            key_required=_req_bool(cls, "key_required", r.get("key_required")),
        )
    preempt_actions = tuple(doc.get("preemption_actions")
                            or _DEFAULT_PREEMPTION_ACTIONS)
    return out, preempt_actions


def load_entities(path: str | None = None) -> dict:
    """Back-compat: the ``{class: Entity}`` map alone (see ``load_kb``)."""
    return load_kb(path)[0]


def _result(classification, *, policy, attack, preemption_granted, rationale,
            entity=None) -> dict:
    return {
        "classification": classification,
        "policy": policy,
        "attack_category": attack,
        "preemption_granted": bool(preemption_granted),
        "authorised_class": entity.cls if isinstance(entity, Entity) else None,
        "rationale": rationale,
    }


def classify(claim: VehicleClaim, entities: dict,
             preemption_actions=_DEFAULT_PREEMPTION_ACTIONS) -> dict:
    """Classify one vehicle claim against the KB. DETERMINISTIC; order mirrors the
    KB policies so the decision is auditable to a pinned policy id.

    Precedence (safety-first: any failure denies preemption):
      1. missing required metadata           -> UNKNOWN (P8, missing_metadata)
      2. asserted class not in the taxonomy   -> UNKNOWN (P8, unknown_vehicle_type)
      3. contradictory approved signals       -> UNKNOWN/escalate (P6, contradictory)
      4. a key-requiring class with no valid key -> SPOOFED_OR_FAULTY (P2, invalid_id)
      5. valid key whose authority class does NOT authorise the asserted class, OR
         an action the class is not allowed    -> SPOOFED_OR_FAULTY (P2, signal_tampering)
      6. otherwise                             -> LEGITIMATE (P4/P1), preemption iff
         the class is preemption-allowed AND the action is a preemption.
    """
    miss = claim.missing_required()
    if miss:
        return _result(UNKNOWN, policy="P8", attack="missing_metadata",
                       preemption_granted=False,
                       rationale=f"required fields absent/null: {miss}")
    entity = entities.get(claim.asserted_class)
    if entity is None:
        return _result(UNKNOWN, policy="P8", attack="unknown_vehicle_type",
                       preemption_granted=False,
                       rationale=f"asserted class {claim.asserted_class!r} not in the "
                                 "authorised-entity taxonomy")
    if claim.contradictory:
        return _result(UNKNOWN, policy="P6", attack="contradictory_signals",
                       preemption_granted=False, entity=entity,
                       rationale="two approved reports about the same entity disagree "
                                 "beyond tolerance -> escalate, no grant")
    if entity.key_required and not (claim.key_present and claim.key_valid):
        return _result(SPOOFED_OR_FAULTY, policy="P2", attack="invalid_id",
                       preemption_granted=False, entity=entity,
                       rationale="class requires a valid registered key; key "
                                 "absent/invalid/revoked (B1 fails)")
    if (entity.key_required and entity.authorising_key_classes
            and claim.key_class not in entity.authorising_key_classes):
        return _result(SPOOFED_OR_FAULTY, policy="P2", attack="signal_tampering",
                       preemption_granted=False, entity=entity,
                       rationale=f"key of authority class {claim.key_class!r} is not "
                                 f"authorised for {entity.cls!r} "
                                 f"(authorising: {list(entity.authorising_key_classes)})")
    if claim.action not in entity.actions_allowed:
        return _result(SPOOFED_OR_FAULTY, policy="P2", attack="signal_tampering",
                       preemption_granted=False, entity=entity,
                       rationale=f"action {claim.action!r} is not allowed for "
                                 f"{entity.cls!r} (allowed: {list(entity.actions_allowed)})")
    # Authorised, valid key, allowed action -> legitimate. Preemption ONLY where the
    # class is preemption-allowed AND the action is a preemption-requesting action
    # (from the KB's preemption_actions; maintenance may act -- lane_closure/
    # reservation -- but is NEVER granted preemption).
    is_preempt_action = claim.action in tuple(preemption_actions)
    granted = entity.preemption_allowed and is_preempt_action
    policy = "P4" if granted else "P1"
    return _result(LEGITIMATE, policy=policy, attack=None,
                   preemption_granted=granted, entity=entity,
                   rationale=(f"authorised {entity.cls!r} with a valid authorising key "
                              f"and an allowed action {claim.action!r}; "
                              f"preemption_allowed={entity.preemption_allowed}"))
