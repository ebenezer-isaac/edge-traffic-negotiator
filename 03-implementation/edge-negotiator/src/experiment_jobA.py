"""Experiment Job-A runner (§3, PRIMARY SLM metric): citation-correctness + FCR of
the SLM's INTERNAL legal-reasoning note vs an UN-RIGGED template baseline, on the
NOVEL split, over controller-mediated retrieval from ``legal_corpus``.

HARD HONESTY (read before quoting any number):
  * The gold here is a POLICY-BASE-DERIVED PROXY for the §3 human-graded
    applicable-rule labels. Each case's applicable rules are the ``ground_rules``
    law_rule(s) whose ``applies_when`` situation the case's event_type instantiates
    (deterministic, ANNOTATOR-BLIND). This is NOT human grading.
  * Therefore this is a PILOT / proxy result, NOT the §12 D5 gate (which requires
    human grading of faithfulness against statute text + 2-rater kappa >= 0.6). D5
    is NOT claimed passed by this runner.
  * Numbers are whatever the real frozen Phi-4-mini emits. A high FCR (hallucinated
    or non-applicable citations) is a real, reportable finding (Dahl et al 2024), not
    something to hide or smooth.

The note is INTERNAL / counsel-gated and NEVER merged into ``assessment.py``'s
evidence pack — this runner only scores it, it does not feed the forensic channel.
"""
from __future__ import annotations

import json
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from ambiguous_decision import FlaggedCase                       # noqa: E402
from legal_corpus import (EmptyCorpusError, LegalCorpus,          # noqa: E402
                          load_corpus, retrieve_for_case)
from slm_agent import SLMAgent, probe_foundry_determinism        # noqa: E402

_PKG_ROOT = os.path.dirname(_HERE)
DATASET_PATH = os.path.join(_PKG_ROOT, "fixtures", "exp1_dataset.json")
RESULTS_DIR = os.path.join(_PKG_ROOT, "results")

# Retrieval breadth: 10 of 18 rules — brackets every proxy-gold set (verified) while
# leaving 8 distractors so a non-applicable in-corpus citation is possible (FCR).
RETRIEVAL_K = 10

# --------------------------------------------------------------------------- #
# PRE-REGISTERED pilot thresholds for the split-dominance rule (§3). PILOT values
# (not the sealed §8 pre-registration, which pins the MDE from an external harm
# threshold + a citation-gold kappa gate). Stated here so the verdict is not
# back-fitted to the observed numbers.
# --------------------------------------------------------------------------- #
FCR_CEILING_PER_NOTE = 0.20     # a note citing a non-applicable/fabricated rule ceiling
MDE_F1 = 0.10                   # min citation-F1 gain over the template to claim a win

# --------------------------------------------------------------------------- #
# PROXY GOLD: event_type (the legal SITUATION class) -> applicable statute_refs.
# Each mapping is justified by the cited law_rule's `applies_when` (in comments).
# Label-INDEPENDENT: Job A cites the law that GOVERNS the situation; the real/spoof
# veracity call is Job B, deliberately not conflated here.
# --------------------------------------------------------------------------- #
_EV_BODY = (
    "TSRGD2016-Sch14-Pt1-para5(4)-(6)",   # LR-ev-exemption: EV crosses red under exemption
    "Griffin-v-Mersey",                    # LR-griffin-calibration: EV-vs-civilian apportionment
    "Keyse-v-Commissioner",                # LR-keyse: adjusting EV apportionment on the facts
)
APPLICABLE_RULES_BY_EVENT = {
    # authorised EV asserting preemption -> the EV-exemption + apportionment body.
    "emergency_claim": frozenset(_EV_BODY),
    # multiple EV claims -> EV body + multi-party contribution between wrongdoers.
    "multi_emergency": frozenset(_EV_BODY + ("CivilLiability-Contribution-1978-s1",)),
    # EV rerouting around an incident -> EV exemption + apportionment + contribution.
    "emergency_plus_incident": frozenset((
        "TSRGD2016-Sch14-Pt1-para5(4)-(6)", "Griffin-v-Mersey",
        "CivilLiability-Contribution-1978-s1")),
    # a reported incident / red-crossing -> driver red-signal offence + contributory neg.
    "incident_claim": frozenset((
        "RTA1988-s36",                     # LR-driver-red: crossing stop line against red
        "TSRGD2016-Sch14-Pt1-para5(3)",    # LR-red-prohibition: assessing a red-signal crossing
        "LawReform-ContribNeg-1945-s1")),  # LR-contrib-negligence: injured party partly at fault
    # a flow anomaly = possible signal malfunction / conflicting green -> authority body.
    "conservation_anomaly": frozenset((
        "Gorringe-v-Calderdale",           # LR-authority-nonfeasance: assessing signal-authority fault
        "Bird-v-Pearce",                   # LR-authority-misfeasance: positively wrong/conflicting indication
        "TfL-London-signals")),            # LR-controller-tfl: identifying the responsible authority
}


def applicable_rules(case) -> frozenset:
    """Proxy-gold applicable statute_refs for a case (deterministic, annotator-blind)."""
    event_type = getattr(case, "event_type", None) or (
        case.get("event_type") if isinstance(case, dict) else None)
    return APPLICABLE_RULES_BY_EVENT.get(event_type or "", frozenset())


def build_gold(cases) -> dict:
    """Map case_id -> proxy-gold applicable statute_ref set."""
    cid = lambda c: getattr(c, "case_id", None) or c.get("case_id")  # noqa: E731
    return {cid(c): applicable_rules(c) for c in cases}


# --------------------------------------------------------------------------- #
# Dataset.
# --------------------------------------------------------------------------- #

def load_cases(split: str = "novel", path: str = DATASET_PATH) -> list:
    """Load the frozen Exp-1 dataset as ``FlaggedCase`` objects for one split."""
    with open(path, "r", encoding="utf-8") as fh:
        rows = json.load(fh)
    out = []
    for r in rows:
        if r.get("split") != split:
            continue
        out.append(FlaggedCase(
            case_id=r["case_id"], event_type=r["event_type"],
            corroboration_count=int(r["corroboration_count"]),
            residual=float(r["residual"]), persistence=int(r["persistence"]),
            neighbour_agreement=float(r["neighbour_agreement"]),
            local_sensing=bool(r["local_sensing"]), severity=float(r["severity"]),
            split=r["split"], label=r["label"]))
    return out


# --------------------------------------------------------------------------- #
# Scoring (pure; arm_fn is injectable so tests can stub the SLM).
# --------------------------------------------------------------------------- #

def score_case(cited, gold: frozenset, corpus: LegalCorpus) -> dict:
    """Per-case citation scoring against proxy gold + corpus membership (FCR).

    A citation is FALSE if it is not in the applicable gold set — this INCLUDES both
    an in-corpus-but-non-applicable rule AND a fabricated id absent from the corpus.
    Abstention (no citation) is correct-refusal ONLY where gold is empty (a genuine
    no-rule cell); where a rule applies, abstention is a miss, never correct (§3).
    """
    cited_set = list(dict.fromkeys(cited))  # dedupe, preserve order
    cset = set(cited_set)
    fabricated = [c for c in cited_set if not corpus.contains_citation(c)]
    correct = cset & gold
    false = cset - gold
    if cited_set:
        precision = len(correct) / len(cset)
    else:
        precision = 1.0 if not gold else 0.0
    recall = len(correct) / len(gold) if gold else 1.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    abstained = len(cited_set) == 0
    return {
        "cited": cited_set,
        "n_cited": len(cited_set),
        "correct": sorted(correct),
        "false": sorted(false),
        "fabricated": fabricated,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "exact_match": cset == set(gold),
        "has_false_citation": len(false) > 0,
        "has_fabrication": len(fabricated) > 0,
        "abstained": abstained,
        "correct_refusal": abstained and not gold,
    }


def aggregate(per_case: list) -> dict:
    """Aggregate per-case scores into the reported metrics."""
    n = len(per_case)
    if n == 0:
        return {"n": 0}
    total_cited = sum(p["n_cited"] for p in per_case)
    total_false = sum(len(p["false"]) for p in per_case)
    total_fab = sum(len(p["fabricated"]) for p in per_case)
    mean = lambda key: sum(p[key] for p in per_case) / n  # noqa: E731
    return {
        "n": n,
        "citation_correctness_f1": mean("f1"),
        "precision_mean": mean("precision"),
        "recall_mean": mean("recall"),
        "exact_match_rate": sum(p["exact_match"] for p in per_case) / n,
        "fcr_per_note": sum(p["has_false_citation"] for p in per_case) / n,
        "fcr_per_citation": (total_false / total_cited) if total_cited else 0.0,
        "fabrication_rate_per_note": sum(p["has_fabrication"] for p in per_case) / n,
        "fabricated_citation_count": total_fab,
        "total_citations": total_cited,
        "abstention_rate": sum(p["abstained"] for p in per_case) / n,
        "parse_failure_rate": sum(p.get("parse_failure", False) for p in per_case) / n,
    }


def score_arm(cases, gold, corpus, arm_fn, k: int = RETRIEVAL_K) -> tuple:
    """Run one arm over cases. ``arm_fn(case, retrieved) -> (cited_list, meta)``."""
    per_case = []
    for c in cases:
        retrieved = retrieve_for_case(corpus, c, k=k)
        cited, meta = arm_fn(c, retrieved)
        scored = score_case(cited, gold[c.case_id], corpus)
        scored["case_id"] = c.case_id
        scored["event_type"] = c.event_type
        scored["gold"] = sorted(gold[c.case_id])
        scored["parse_failure"] = bool(meta.get("parse_failure"))
        if "candidate_origin" in meta:
            scored["candidate_origin"] = meta["candidate_origin"]
        per_case.append(scored)
    return aggregate(per_case), per_case


# --------------------------------------------------------------------------- #
# The two arms.
# --------------------------------------------------------------------------- #

def make_slm_arm(agent: SLMAgent):
    """SLM Job-A arm. A parse/connection failure -> no note (empty cited, flagged)."""
    def arm(case, retrieved):
        note = agent.reason_note(case, retrieved)
        if note is None:
            return [], {"parse_failure": True}
        return note["cited_rules"], {"parse_failure": False,
                                     "candidate_origin": note.get("candidate_origin")}
    return arm


def template_arm(case, retrieved):
    """UN-RIGGED template baseline (§3): emit the NEAREST applicable rule's citation.

    The nearest rule = the top-ranked retrieved candidate (one citation). It is
    scored for CORRECTNESS on the same gold — a near-miss (top-1 not in gold) is a
    WRONG citation, never a free abstention. The template abstains only when
    retrieval returns nothing (a genuine no-candidate cell).
    """
    if not retrieved:
        return [], {"parse_failure": False}
    return [retrieved[0].statute_ref], {"parse_failure": False}


# --------------------------------------------------------------------------- #
# Determinism check (temp 0; §3 / §8).
# --------------------------------------------------------------------------- #

def determinism_check(agent: SLMAgent, cases, corpus, sample: int = 5,
                      k: int = RETRIEVAL_K) -> dict:
    """Re-run the SLM note on the first ``sample`` cases; report identical-citation rate."""
    checked = identical = 0
    for c in cases[:sample]:
        retrieved = retrieve_for_case(corpus, c, k=k)
        a = agent.reason_note(c, retrieved)
        b = agent.reason_note(c, retrieved)
        if a is None or b is None:
            continue
        checked += 1
        if a["cited_rules"] == b["cited_rules"]:
            identical += 1
    return {"sample": sample, "checked": checked, "identical": identical,
            "identical_rate": (identical / checked) if checked else None}


# --------------------------------------------------------------------------- #
# Split-dominance verdict (§3 pinned resolution).
# --------------------------------------------------------------------------- #

def split_dominance_verdict(slm: dict, template: dict) -> dict:
    """Apply the §3 rule: higher-correctness-but-higher-FCR -> DEMOTE unless
    FCR <= ceiling AND correctness clears the MDE over the template."""
    d_f1 = slm["citation_correctness_f1"] - template["citation_correctness_f1"]
    fcr = slm["fcr_per_note"]
    clears_mde = d_f1 >= MDE_F1
    under_ceiling = fcr <= FCR_CEILING_PER_NOTE
    if clears_mde and under_ceiling:
        verdict = "SLM_WINS"
        rationale = (f"citation-F1 gain {d_f1:+.3f} >= MDE {MDE_F1} AND "
                     f"per-note FCR {fcr:.3f} <= ceiling {FCR_CEILING_PER_NOTE}")
    elif clears_mde and not under_ceiling:
        verdict = "DEMOTE_SLM"
        rationale = (f"citation-F1 gain {d_f1:+.3f} clears MDE but per-note FCR "
                     f"{fcr:.3f} EXCEEDS ceiling {FCR_CEILING_PER_NOTE} -> default demote (§3)")
    elif abs(d_f1) < MDE_F1:
        verdict = "TIE"
        rationale = f"citation-F1 gap {d_f1:+.3f} within +/-MDE {MDE_F1}; no dominance"
    else:
        verdict = "TEMPLATE_WINS"
        rationale = (f"citation-F1 gap {d_f1:+.3f} <= -MDE; the honestly-scored "
                     f"template beats the SLM note")
    return {"verdict": verdict, "rationale": rationale, "f1_delta": d_f1,
            "slm_fcr_per_note": fcr, "fcr_ceiling": FCR_CEILING_PER_NOTE,
            "mde_f1": MDE_F1, "clears_mde": clears_mde, "under_ceiling": under_ceiling}


# --------------------------------------------------------------------------- #
# Runner.
# --------------------------------------------------------------------------- #

def run(split: str = "novel", reps: int = 3, write: bool = True) -> dict:
    """Probe Foundry (SKIP-not-abort), run both arms on ``split``, write results."""
    agent, skip = probe_foundry_determinism(reps)
    if agent is None:
        result = {"status": "SKIP", "reason": skip, "split": split}
        if write:
            _write(result)
        return result

    corpus = load_corpus()  # fail-loud on empty (§10)
    # a fresh agent sized for the longer note (the probe agent uses the small budget).
    slm = SLMAgent(base_url=None, model=agent.model, max_tokens=768)
    slm.client = agent.client

    cases = load_cases(split)
    gold = build_gold(cases)

    slm_agg, slm_pc = score_arm(cases, gold, corpus, make_slm_arm(slm))
    tpl_agg, tpl_pc = score_arm(cases, gold, corpus, template_arm)
    det = determinism_check(slm, cases, corpus)
    verdict = split_dominance_verdict(slm_agg, tpl_agg)

    result = {
        "status": "OK",
        "split": split,
        "n": len(cases),
        "model": slm.model,
        "retrieval_k": RETRIEVAL_K,
        "corpus_size": len(corpus),
        "gold_kind": "POLICY-BASE-DERIVED PROXY (annotator-blind, event_type->applies_when); "
                     "NOT human-graded; NOT the D5 gate",
        "determinism": det,
        "arms": {"slm": slm_agg, "template": tpl_agg},
        "split_dominance": verdict,
        "thresholds_pinned_pre_run": {"fcr_ceiling_per_note": FCR_CEILING_PER_NOTE,
                                      "mde_f1": MDE_F1,
                                      "note": "PILOT values, not the sealed §8 pre-registration"},
        "caveats": [
            "Gold is a policy-base-derived PROXY for the §3 human-graded applicable-rule "
            "labels; this is a PILOT (n={}), not the §12 D5 gate (needs human grading + "
            "2-rater kappa>=0.6). D5 is NOT claimed passed.".format(len(cases)),
            "Citation-correctness is measured vs the proxy gold, not statute-text "
            "faithfulness graded by qualified humans.",
            "The Job-A note is internal/counsel-gated and never enters the evidence pack.",
        ],
        "per_case": {"slm": slm_pc, "template": tpl_pc},
    }
    if write:
        _write(result)
    return result


def _write(result: dict) -> None:
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "experiment_jobA.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2)
    with open(os.path.join(RESULTS_DIR, "experiment_jobA.md"), "w", encoding="utf-8") as fh:
        fh.write(_summarize_md(result))


def _summarize_md(r: dict) -> str:
    if r.get("status") != "OK":
        return (f"# Experiment Job-A — SKIPPED\n\n"
                f"**Status:** {r.get('status')}\n\n**Reason:** {r.get('reason')}\n")
    s, t = r["arms"]["slm"], r["arms"]["template"]
    v = r["split_dominance"]
    L = [
        "# Experiment Job-A — citation-faithful legal-reasoning note (PILOT)",
        "",
        f"- **Model:** {r['model']} (frozen, Foundry Local, temperature 0)",
        f"- **Split:** {r['split']}  ·  **n = {r['n']}**  ·  corpus = {r['corpus_size']} "
        f"law_rules  ·  retrieval k = {r['retrieval_k']}",
        f"- **Gold:** {r['gold_kind']}",
        f"- **Determinism (temp 0):** {r['determinism']['identical']}/"
        f"{r['determinism']['checked']} notes byte-identical on re-run "
        f"(rate {r['determinism']['identical_rate']})",
        "",
        "> PILOT / PROXY. The gold is policy-base-derived (event_type -> applies_when), "
        "annotator-blind, NOT human-graded. This is NOT the §12 D5 gate (which needs "
        "human faithfulness grading + 2-rater kappa >= 0.6). D5 is NOT claimed passed.",
        "",
        "## Results (novel split)",
        "",
        "| Metric | SLM Job-A note | Un-rigged template |",
        "|---|---|---|",
        f"| Citation-correctness (mean F1) | {s['citation_correctness_f1']:.3f} | "
        f"{t['citation_correctness_f1']:.3f} |",
        f"| Precision (mean) | {s['precision_mean']:.3f} | {t['precision_mean']:.3f} |",
        f"| Recall (mean) | {s['recall_mean']:.3f} | {t['recall_mean']:.3f} |",
        f"| Exact-set-match rate | {s['exact_match_rate']:.3f} | {t['exact_match_rate']:.3f} |",
        f"| **FCR (per note)** | **{s['fcr_per_note']:.3f}** | {t['fcr_per_note']:.3f} |",
        f"| FCR (per citation) | {s['fcr_per_citation']:.3f} | {t['fcr_per_citation']:.3f} |",
        f"| Fabrication rate (per note) | {s['fabrication_rate_per_note']:.3f} | "
        f"{t['fabrication_rate_per_note']:.3f} |",
        f"| Fabricated citations (count) | {s['fabricated_citation_count']} | "
        f"{t['fabricated_citation_count']} |",
        f"| Abstention rate | {s['abstention_rate']:.3f} | {t['abstention_rate']:.3f} |",
        f"| Parse-failure rate (counts as failure) | {s['parse_failure_rate']:.3f} | "
        f"{t['parse_failure_rate']:.3f} |",
        "",
        "## Split-dominance verdict (§3 pinned resolution)",
        "",
        f"- Pinned PRE-RUN (pilot): FCR ceiling (per note) = {v['fcr_ceiling']}, "
        f"MDE on citation-F1 = {v['mde_f1']}",
        f"- Citation-F1 delta (SLM - template) = **{v['f1_delta']:+.3f}**  ·  "
        f"clears MDE: {v['clears_mde']}  ·  under FCR ceiling: {v['under_ceiling']}",
        f"- **Verdict: {v['verdict']}** — {v['rationale']}",
        "",
        "## Caveats",
        "",
    ]
    L += [f"- {c}" for c in r["caveats"]]
    L.append("")
    return "\n".join(L)


if __name__ == "__main__":
    out = run()
    if out.get("status") != "OK":
        print("SKIP:", out.get("reason"))
    else:
        s, t = out["arms"]["slm"], out["arms"]["template"]
        print(f"n={out['n']} model={out['model']}")
        print(f"SLM      F1={s['citation_correctness_f1']:.3f} "
              f"FCR/note={s['fcr_per_note']:.3f} fab={s['fabricated_citation_count']} "
              f"parsefail={s['parse_failure_rate']:.3f}")
        print(f"template F1={t['citation_correctness_f1']:.3f} "
              f"FCR/note={t['fcr_per_note']:.3f}")
        print("verdict:", out["split_dominance"]["verdict"],
              "|", out["split_dominance"]["rationale"])
