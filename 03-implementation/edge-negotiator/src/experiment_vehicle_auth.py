"""Categorised adversarial evaluation of the multi-authorised-vehicle classifier
(MASTER-SPEC §4/§6; Lee's balanced-eval requirement).

Builds a BALANCED, CATEGORISED dataset of vehicle-authorisation claims -- valid
claims per authorised class + one instance family per attack category
(unknown-vehicle / invalid-id / signal-tampering / missing-metadata /
contradictory) -- labels each with its expected classification AND the
safety-critical outcome (should preemption be GRANTED?), runs the deterministic
``vehicle_authorization.classify`` over it, and reports:

  * per-CATEGORY classification accuracy (every adversarial family handled);
  * a confusion matrix on the safety-critical GRANT/DENY decision, with
    P / R / FPR / FNR (Lee). Positive class = "should be DENIED preemption" (the
    thing the gate must catch): a FALSE NEGATIVE is an illegitimate claim that was
    GRANTED preemption (the dangerous error); a FALSE POSITIVE is a genuine EV
    wrongly DENIED.

The classifier is a deterministic KB gate (sub-millisecond, no model), so this is
a correctness/coverage evaluation, not a latency study; the whole-dataset wall time
is reported for completeness.
"""
from __future__ import annotations

import json
import os
import sys
from time import perf_counter

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from vehicle_authorization import (  # noqa: E402
    _DEFAULT_PREEMPTION_ACTIONS, LEGITIMATE, SPOOFED_OR_FAULTY, UNKNOWN,
    VehicleClaim, classify, load_kb,
)

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))


def _case(category, claim, expected_class, expect_grant, note=""):
    return {"category": category, "claim": claim, "expected_class": expected_class,
            "expect_grant": expect_grant, "note": note}


def build_dataset() -> list:
    """A balanced, categorised set of labelled authorisation claims.

    Valid families (legitimate) span every authorised class + a genuine non-preempt
    action (fire lane-hold, maintenance lane-closure, civilian normal). Attack
    families span the KB attack taxonomy. Multiple instances per family so an
    accuracy is meaningful and a single hard-coded pass cannot satisfy it.
    """
    C = []
    # --- VALID: authorised emergency classes that SHOULD be granted preemption ---
    for i in range(3):
        C.append(_case("valid_ambulance",
                       VehicleClaim(asserted_class="ambulance", action="preempt",
                                    key_present=True, key_valid=True, key_class="emergency"),
                       LEGITIMATE, True, f"genuine ambulance preempt #{i}"))
    for i in range(3):
        C.append(_case("valid_police",
                       VehicleClaim(asserted_class="police", action="escort_hold",
                                    key_present=True, key_valid=True, key_class="emergency"),
                       LEGITIMATE, True, f"genuine police escort #{i}"))
    for i in range(2):
        C.append(_case("valid_fire",
                       VehicleClaim(asserted_class="fire", action="preempt",
                                    key_present=True, key_valid=True, key_class="emergency"),
                       LEGITIMATE, True, f"genuine fire preempt #{i}"))
    # --- VALID but NON-preempt (legitimate, must NOT be granted preemption) ---
    C.append(_case("valid_fire_lanehold",
                   VehicleClaim(asserted_class="fire", action="lane_hold",
                                key_present=True, key_valid=True, key_class="emergency"),
                   LEGITIMATE, False, "fire lane-hold at scene: legit, not a preempt"))
    for i in range(2):
        C.append(_case("valid_maintenance_hold",
                       VehicleClaim(asserted_class="maintenance", action="lane_closure",
                                    key_present=True, key_valid=True, key_class="works"),
                       LEGITIMATE, False, f"maintenance lane closure #{i}: no preemption"))
    C.append(_case("valid_civilian",
                   VehicleClaim(asserted_class="civilian", action="normal"),
                   LEGITIMATE, False, "civilian normal traffic"))
    # --- ATTACK: unknown vehicle type -> UNKNOWN, deny ---
    for cls in ("drone", "tram", "hovercraft"):
        C.append(_case("unknown_vehicle",
                       VehicleClaim(asserted_class=cls, action="preempt",
                                    key_present=True, key_valid=True, key_class="emergency"),
                       UNKNOWN, False, f"unknown class {cls}"))
    # --- ATTACK: invalid id (key absent / invalid / revoked) -> SPOOFED, deny ---
    C.append(_case("invalid_id",
                   VehicleClaim(asserted_class="ambulance", action="preempt",
                                key_present=False, key_valid=False),
                   SPOOFED_OR_FAULTY, False, "ambulance claim with NO key"))
    C.append(_case("invalid_id",
                   VehicleClaim(asserted_class="ambulance", action="preempt",
                                key_present=True, key_valid=False, key_class="emergency"),
                   SPOOFED_OR_FAULTY, False, "ambulance claim with an INVALID/revoked key"))
    C.append(_case("invalid_id",
                   VehicleClaim(asserted_class="police", action="preempt",
                                key_present=True, key_valid=False, key_class="emergency"),
                   SPOOFED_OR_FAULTY, False, "police claim with an invalid key"))
    # --- ATTACK: signal tampering (valid key, WRONG authority class / action) ---
    C.append(_case("signal_tampering",
                   VehicleClaim(asserted_class="ambulance", action="preempt",
                                key_present=True, key_valid=True, key_class="works"),
                   SPOOFED_OR_FAULTY, False, "maintenance(works) key asserting ambulance preempt"))
    C.append(_case("signal_tampering",
                   VehicleClaim(asserted_class="police", action="preempt",
                                key_present=True, key_valid=True, key_class="works"),
                   SPOOFED_OR_FAULTY, False, "works key asserting police preempt"))
    C.append(_case("signal_tampering",
                   VehicleClaim(asserted_class="maintenance", action="preempt",
                                key_present=True, key_valid=True, key_class="works"),
                   SPOOFED_OR_FAULTY, False, "maintenance asserting preempt (action not allowed)"))
    # --- ATTACK: missing metadata -> UNKNOWN, deny ---
    C.append(_case("missing_metadata",
                   VehicleClaim(asserted_class=None, action="preempt",
                                key_present=True, key_valid=True, key_class="emergency"),
                   UNKNOWN, False, "asserted_class absent"))
    C.append(_case("missing_metadata",
                   VehicleClaim(asserted_class="ambulance", action=None,
                                key_present=True, key_valid=True, key_class="emergency"),
                   UNKNOWN, False, "action absent"))
    C.append(_case("missing_metadata",
                   VehicleClaim(asserted_class="ambulance", action="preempt",
                                key_present=True, key_valid=True, key_class=None),
                   UNKNOWN, False, "key present but key_class absent"))
    # --- ATTACK: contradictory signals -> UNKNOWN/escalate, deny ---
    for i in range(2):
        C.append(_case("contradictory",
                       VehicleClaim(asserted_class="ambulance", action="preempt",
                                    key_present=True, key_valid=True, key_class="emergency",
                                    contradictory=True),
                       UNKNOWN, False, f"two approved reports disagree #{i}"))
    return C


def _confusion(cases: list, entities: dict,
               preemption_actions=_DEFAULT_PREEMPTION_ACTIONS) -> dict:
    """Confusion matrix on the safety-critical GRANT/DENY decision + P/R/FPR/FNR.

    Positive = "should be DENIED preemption". TP: correctly denied. FN: GRANTED but
    should have been denied (the dangerous error). FP: denied but should have been
    granted (a genuine EV wrongly refused). TN: correctly granted.
    """
    tp = fp = fn = tn = 0
    for c in cases:
        r = classify(c["claim"], entities, preemption_actions)
        granted = r["preemption_granted"]
        should_grant = c["expect_grant"]
        should_deny = not should_grant
        denied = not granted
        if should_deny and denied:
            tp += 1
        elif should_deny and granted:
            fn += 1
        elif should_grant and denied:
            fp += 1
        else:
            tn += 1

    def _ratio(num, den):
        return (num / den) if den else None
    return {
        "positive_class": "should be DENIED preemption",
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "false_positive_rate": _ratio(fp, fp + tn),
        "false_negative_rate": _ratio(fn, fn + tp),
        "dangerous_false_grants": fn,  # illegitimate claims granted preemption
    }


def _per_category(cases: list, entities: dict,
                  preemption_actions=_DEFAULT_PREEMPTION_ACTIONS) -> dict:
    """Per-category classification accuracy + a preemption-outcome tally."""
    out: dict = {}
    for c in cases:
        r = classify(c["claim"], entities, preemption_actions)
        cat = c["category"]
        bucket = out.setdefault(cat, {"n": 0, "class_correct": 0, "grant_correct": 0,
                                      "misses": []})
        bucket["n"] += 1
        class_ok = r["classification"] == c["expected_class"]
        grant_ok = r["preemption_granted"] == c["expect_grant"]
        bucket["class_correct"] += int(class_ok)
        bucket["grant_correct"] += int(grant_ok)
        if not (class_ok and grant_ok):
            bucket["misses"].append(
                {"note": c["note"], "expected_class": c["expected_class"],
                 "got_class": r["classification"], "expect_grant": c["expect_grant"],
                 "got_grant": r["preemption_granted"], "attack": r["attack_category"]})
    return out


def run() -> dict:
    entities, preemption_actions = load_kb()
    cases = build_dataset()
    t0 = perf_counter()
    for c in cases:  # warm the classify path + measure wall time
        classify(c["claim"], entities, preemption_actions)
    wall_s = perf_counter() - t0

    confusion = _confusion(cases, entities, preemption_actions)
    per_cat = _per_category(cases, entities, preemption_actions)
    total = len(cases)
    class_correct = sum(b["class_correct"] for b in per_cat.values())
    grant_correct = sum(b["grant_correct"] for b in per_cat.values())
    all_correct = all(b["class_correct"] == b["n"] and b["grant_correct"] == b["n"]
                      for b in per_cat.values())

    result = {
        "experiment": "H2_vehicle_authorisation_categorised_eval",
        "gate": "multi-authorised-vehicle KB (§4/§6) + Lee balanced categorised eval",
        "classifier": "deterministic KB gate (vehicle_authorization.classify)",
        "dataset_size": total,
        "categories": sorted({c["category"] for c in cases}),
        "class_accuracy": class_correct / total if total else None,
        "grant_accuracy": grant_correct / total if total else None,
        "all_correct": all_correct,
        "confusion_grant_deny": confusion,
        "per_category": per_cat,
        "wall_time_s_total": wall_s,
        "notes": [
            "Balanced across authorised classes + every KB attack family; positive "
            "class is 'should be DENIED preemption' so recall measures catching "
            "illegitimate claims and FNR measures dangerous false grants.",
            "Deterministic KB gate: no model, sub-ms per claim; correctness/coverage "
            "eval, not a latency study.",
            "maintenance/civilian are LEGITIMATE entities but are NEVER granted "
            "preemption (preemption_allowed=false) -- a correct deny is not a miss.",
        ],
    }

    os.makedirs(RESULTS, exist_ok=True)
    json_path = os.path.join(RESULTS, "experiment_vehicle_auth.json")
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    md_path = os.path.join(RESULTS, "experiment_vehicle_auth.md")
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(render_md(result))
    _print_summary(result, json_path, md_path)
    return result


def _fmt(v, nd=3):
    if v is None:
        return "n/a"
    if isinstance(v, float):
        return f"{v:.{nd}f}"
    return str(v)


def render_md(r: dict) -> str:
    cm = r["confusion_grant_deny"]
    lines = ["# H2: multi-authorised-vehicle authorisation -- categorised eval", ""]
    lines.append(f"**{'PASS' if r['all_correct'] else 'FAIL'}** -- deterministic KB gate "
                 f"over {r['dataset_size']} balanced categorised claims.")
    lines.append("")
    lines.append(f"- Classifier: {r['classifier']}")
    lines.append(f"- Class accuracy: {_fmt(r['class_accuracy'])}  |  "
                 f"grant/deny accuracy: {_fmt(r['grant_accuracy'])}")
    lines.append("")
    lines.append("## Safety-critical confusion (positive = should be DENIED preemption)")
    lines.append("")
    lines.append(f"- TP {cm['tp']}  FP {cm['fp']}  FN {cm['fn']}  TN {cm['tn']}")
    lines.append(f"- Precision {_fmt(cm['precision'])}  |  Recall {_fmt(cm['recall'])}  |  "
                 f"FPR {_fmt(cm['false_positive_rate'])}  |  FNR {_fmt(cm['false_negative_rate'])}")
    lines.append(f"- **Dangerous false grants (illegitimate claim granted preemption): "
                 f"{cm['dangerous_false_grants']}**")
    lines.append("")
    lines.append("## Per-category coverage")
    lines.append("")
    lines.append("| Category | n | class correct | grant correct |")
    lines.append("|---|---|---|---|")
    for cat in sorted(r["per_category"]):
        b = r["per_category"][cat]
        lines.append(f"| {cat} | {b['n']} | {b['class_correct']}/{b['n']} | "
                     f"{b['grant_correct']}/{b['n']} |")
    lines.append("")
    lines.append("## Notes")
    lines.append("")
    for n in r["notes"]:
        lines.append(f"- {n}")
    lines.append("")
    return "\n".join(lines)


def _print_summary(r: dict, json_path: str, md_path: str) -> None:
    cm = r["confusion_grant_deny"]
    print("=" * 72)
    print(f"H2 VEHICLE-AUTHORISATION CATEGORISED EVAL: {'PASS' if r['all_correct'] else 'FAIL'}")
    print(f"  dataset={r['dataset_size']} class_acc={_fmt(r['class_accuracy'])} "
          f"grant_acc={_fmt(r['grant_accuracy'])}")
    print(f"  P={_fmt(cm['precision'])} R={_fmt(cm['recall'])} "
          f"FPR={_fmt(cm['false_positive_rate'])} FNR={_fmt(cm['false_negative_rate'])} "
          f"dangerous_false_grants={cm['dangerous_false_grants']}")
    print("=" * 72)
    print(f"  wrote: {json_path}")
    print(f"  wrote: {md_path}")


if __name__ == "__main__":
    res = run()
    raise SystemExit(0 if res["all_correct"] else 1)
