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
from time import perf_counter

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from ambiguous_decision import FlaggedCase                       # noqa: E402
from legal_corpus import (EmptyCorpusError, LegalCorpus,          # noqa: E402
                          load_corpus, retrieve_for_case)
from slm_agent import SLMAgent, probe_foundry_determinism        # noqa: E402
from slm_latency import summarize_latency                        # noqa: E402

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


def rag_candidates(corpus, case, k: int = RETRIEVAL_K):
    """RAG candidate set: controller-mediated TF-IDF top-k retrieval (the comparator)."""
    return retrieve_for_case(corpus, case, k=k)


def cag_candidates(corpus, case):
    """CAG candidate set: the WHOLE corpus (all 18 rules, no retrieval) — §2/§3."""
    return corpus.all_rules()


def score_arm(cases, gold, corpus, arm_fn, candidate_fn=None,
              k: int = RETRIEVAL_K) -> tuple:
    """Run one arm over cases. ``arm_fn(case, candidates) -> (cited_list, meta)``.

    ``candidate_fn(corpus, case) -> rules`` selects the rules placed in front of the
    arm. Default = RAG top-k retrieval (backward-compatible); pass ``cag_candidates``
    for the whole-corpus CAG arm.
    """
    if candidate_fn is None:
        candidate_fn = lambda corpus, case: rag_candidates(corpus, case, k=k)  # noqa: E731
    per_case = []
    for c in cases:
        candidates = candidate_fn(corpus, c)
        cited, meta = arm_fn(c, candidates)
        scored = score_case(cited, gold[c.case_id], corpus)
        scored["case_id"] = c.case_id
        scored["event_type"] = c.event_type
        scored["gold"] = sorted(gold[c.case_id])
        scored["parse_failure"] = bool(meta.get("parse_failure"))
        if "candidate_origin" in meta:
            scored["candidate_origin"] = meta["candidate_origin"]
        if "fabrication_attempts" in meta:
            scored["fabrication_attempts"] = meta["fabrication_attempts"]
        if "cited_consistent" in meta:
            scored["cited_consistent"] = meta["cited_consistent"]
        per_case.append(scored)
    return aggregate(per_case), per_case


# --------------------------------------------------------------------------- #
# The two arms.
# --------------------------------------------------------------------------- #

def make_slm_arm(agent: SLMAgent, latencies=None):
    """SLM Job-A RAG arm. A parse/connection failure -> no note (empty cited, flagged).

    ``latencies`` (optional list) collects per-call Job-A wall-clock latency (seconds)
    for §8 profiling; the timing wraps ONLY the ``reason_note`` call.
    """
    def arm(case, retrieved):
        t0 = perf_counter()
        note = agent.reason_note(case, retrieved)
        if latencies is not None:
            latencies.append(perf_counter() - t0)
        if note is None:
            return [], {"parse_failure": True}
        return note["cited_rules"], {"parse_failure": False,
                                     "candidate_origin": note.get("candidate_origin")}
    return arm


def make_cag_arm(agent: SLMAgent, latencies=None):
    """SLM Job-A CAG reason-then-classify arm (the fair re-test, §2/§3).

    Scores the CONTROLLER-DERIVED cited set (in-corpus ids judged applicable), NOT the
    model's free-text list. ``fabrication_attempts`` (judged-applicable ids the
    controller DROPPED as out-of-corpus) is surfaced in meta for transparency; those
    ids never reach scoring. ``latencies`` collects per-call Job-A latency.
    """
    def arm(case, candidates):
        t0 = perf_counter()
        note = agent.reason_note_cag(case, candidates)
        if latencies is not None:
            latencies.append(perf_counter() - t0)
        if note is None:
            return [], {"parse_failure": True}
        return note["cited_rules"], {
            "parse_failure": False,
            "candidate_origin": note.get("candidate_origin"),
            "fabrication_attempts": len(note.get("fabrication_attempts", [])),
            "cited_consistent": bool(note.get("cited_consistent")),
        }
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
                      k: int = RETRIEVAL_K, cag: bool = False) -> dict:
    """Re-run the SLM note on the first ``sample`` cases; report identical-citation rate.

    ``cag=True`` profiles the CAG reason-then-classify arm over the whole corpus;
    otherwise the RAG top-k arm. The controller-derived ``cited_rules`` is compared.
    """
    checked = identical = 0
    for c in cases[:sample]:
        if cag:
            candidates = corpus.all_rules()
            a = agent.reason_note_cag(c, candidates)
            b = agent.reason_note_cag(c, candidates)
        else:
            candidates = retrieve_for_case(corpus, c, k=k)
            a = agent.reason_note(c, candidates)
            b = agent.reason_note(c, candidates)
        if a is None or b is None:
            continue
        checked += 1
        if a["cited_rules"] == b["cited_rules"]:
            identical += 1
    return {"sample": sample, "checked": checked, "identical": identical,
            "identical_rate": (identical / checked) if checked else None,
            "arm": "cag" if cag else "rag"}


def cag_minus_rag_delta(cag: dict, rag: dict, cag_fab_attempts: int) -> dict:
    """CAG-minus-RAG delta block: does whole-corpus reason-then-classify move the needle?

    ``dF1`` and ``dFCR_per_note`` are CAG minus RAG (positive dF1 = CAG better;
    negative dFCR = CAG cleaner). ``dfabrication`` compares SCORED fabrication rate
    (CAG's is ~0 by construction — the controller drops out-of-corpus ids); the raw
    ``cag_fabrication_attempts`` the controller dropped is reported alongside so the
    drop-to-zero is not mistaken for the model never fabricating.
    """
    return {
        "dF1": cag["citation_correctness_f1"] - rag["citation_correctness_f1"],
        "dFCR_per_note": cag["fcr_per_note"] - rag["fcr_per_note"],
        "dfabrication_rate_per_note": (cag["fabrication_rate_per_note"]
                                       - rag["fabrication_rate_per_note"]),
        "cag_scored_fabrication_count": cag["fabricated_citation_count"],
        "rag_scored_fabrication_count": rag["fabricated_citation_count"],
        "cag_fabrication_attempts_dropped_by_controller": cag_fab_attempts,
        "note": ("CAG scored-fabrication is ~0 BY CONSTRUCTION: the reason-then-classify "
                 "controller drops any judged-applicable id absent from the 18-rule "
                 "corpus. cag_fabrication_attempts_dropped_by_controller counts what the "
                 "model tried to fabricate before the drop."),
    }


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

def _load_committed_rag():
    """Reuse the committed RAG-arm run (arms.slm/template) if present + OK, else None."""
    path = os.path.join(RESULTS_DIR, "experiment_jobA.json")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            old = json.load(fh)
    except (OSError, ValueError):
        return None
    if old.get("status") != "OK":
        return None
    arms = old.get("arms") or {}
    # accept either the new (slm_rag) or the legacy (slm) key for the RAG arm.
    rag = arms.get("slm_rag") or arms.get("slm")
    tpl = arms.get("template")
    if not rag or not tpl:
        return None
    pc = old.get("per_case") or {}
    return {"rag_agg": rag, "tpl_agg": tpl,
            "rag_pc": pc.get("slm_rag") or pc.get("slm"),
            "tpl_pc": pc.get("template")}


def run(split: str = "novel", reps: int = 3, write: bool = True,
        reuse_rag: bool = True, det_sample: int = 3) -> dict:
    """Probe Foundry (SKIP-not-abort), run the 3 arms on ``split``, write results.

    Arms: ``slm_rag`` (TF-IDF k=10 comparator — reused from the committed run when
    ``reuse_rag`` and available, else re-run live), ``slm_cag`` (the NEW whole-corpus
    reason-then-classify fair re-test, always run live), ``template`` (un-rigged
    baseline, re-run live — cheap, deterministic). Emits TWO split-dominance verdicts
    and the cag_minus_rag delta. Records per-call Job-A latency (§8).
    """
    committed = _load_committed_rag() if reuse_rag else None
    # RAG reuse must be recorded before the file is overwritten.
    agent, skip = probe_foundry_determinism(reps)
    if agent is None:
        result = {"status": "SKIP", "reason": skip, "split": split}
        if write:
            _write(result)
        return result

    corpus = load_corpus()  # fail-loud on empty (§10)
    slm = SLMAgent(base_url=None, model=agent.model, max_tokens=768)
    slm.client = agent.client

    cases = load_cases(split)
    gold = build_gold(cases)

    # --- RAG comparator arm (reuse or re-run) ---------------------------------- #
    rag_latency = None
    if committed is not None:
        rag_agg, rag_pc = committed["rag_agg"], committed["rag_pc"]
        rag_source = "REUSED from the committed run (not re-run this session)"
    else:
        rag_lat: list = []
        rag_agg, rag_pc = score_arm(cases, gold, corpus, make_slm_arm(slm, rag_lat),
                                    candidate_fn=rag_candidates)
        rag_latency = summarize_latency(rag_lat, warmup=1)
        rag_source = "RE-RUN live this session (no committed run to reuse)"

    # --- CAG reason-then-classify arm (always live) — the fair re-test ---------- #
    cag_lat: list = []
    cag_agg, cag_pc = score_arm(cases, gold, corpus, make_cag_arm(slm, cag_lat),
                                candidate_fn=cag_candidates)
    cag_job_a_latency = summarize_latency(cag_lat, warmup=1)
    cag_fab_attempts = sum(p.get("fabrication_attempts", 0) for p in cag_pc)
    cag_consistent = sum(1 for p in cag_pc if p.get("cited_consistent"))

    # --- template baseline (re-run live; cheap, deterministic) ----------------- #
    tpl_agg, tpl_pc = score_arm(cases, gold, corpus, template_arm,
                                candidate_fn=rag_candidates)

    det_cag = determinism_check(slm, cases, corpus, sample=det_sample, cag=True)

    verdict_rag = split_dominance_verdict(rag_agg, tpl_agg)
    verdict_cag = split_dominance_verdict(cag_agg, tpl_agg)
    delta = cag_minus_rag_delta(cag_agg, rag_agg, cag_fab_attempts)

    result = {
        "status": "OK",
        "split": split,
        "n": len(cases),
        "model": slm.model,
        "corpus_presentation": "CAG (whole-corpus-in-context, all 18 rules) is PRIMARY; "
                               "TF-IDF k=10 RAG retained as head-to-head comparator (§2/§3)",
        "retrieval_k": RETRIEVAL_K,
        "corpus_size": len(corpus),
        "rag_arm_source": rag_source,
        "gold_kind": "POLICY-BASE-DERIVED PROXY (annotator-blind, event_type->applies_when); "
                     "NOT human-graded; NOT the D5 gate",
        "determinism_cag": det_cag,
        "cag_cited_consistent_with_model_freetext": {
            "n_consistent": cag_consistent, "n": len(cag_pc),
            "note": "how often the model's own free-text cited_rules matched the "
                    "controller-derived set; a DIAGNOSTIC, not scored."},
        "job_a_latency": cag_job_a_latency,          # PRIMARY (CAG) per-call Job-A latency
        "job_a_latency_rag": rag_latency,            # None when the RAG arm was reused
        "arms": {"slm_rag": rag_agg, "slm_cag": cag_agg, "template": tpl_agg},
        "split_dominance_rag": verdict_rag,
        "split_dominance_cag": verdict_cag,
        "cag_minus_rag": delta,
        "thresholds_pinned_pre_run": {"fcr_ceiling_per_note": FCR_CEILING_PER_NOTE,
                                      "mde_f1": MDE_F1,
                                      "note": "PILOT values, not the sealed §8 pre-registration"},
        "caveats": [
            "Gold is a policy-base-derived PROXY for the §3 human-graded applicable-rule "
            "labels; this is a PILOT (n={}), not the §12 D5 gate (needs human grading + "
            "2-rater kappa>=0.6). D5 is NOT claimed passed.".format(len(cases)),
            "Citation-correctness is measured vs the proxy gold, not statute-text "
            "faithfulness graded by qualified humans.",
            "CAG scored-fabrication is ~0 BY CONSTRUCTION (the reason-then-classify "
            "controller drops out-of-corpus ids); see cag_minus_rag for the raw "
            "fabrication ATTEMPTS the controller dropped.",
            "The Job-A note is internal/counsel-gated and never enters the evidence pack.",
        ],
        "per_case": {"slm_rag": rag_pc, "slm_cag": cag_pc, "template": tpl_pc},
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


def _fmt_lat(lat: dict) -> str:
    """Render a latency summary dict as an inline P50/P95/P99 string."""
    if not lat or lat.get("n", 0) == 0:
        return "no measurable samples"
    f = lambda x: f"{x:.2f}s" if isinstance(x, (int, float)) else "n/a"  # noqa: E731
    return (f"n={lat['n']} (warmup {lat['warmup_discarded']} discarded) · "
            f"P50 {f(lat['p50'])} · P95 {f(lat['p95'])} · P99 {f(lat['p99'])} · "
            f"max {f(lat['max'])} · mean {f(lat['mean'])}")


def _summarize_md(r: dict) -> str:
    if r.get("status") != "OK":
        return (f"# Experiment Job-A — SKIPPED\n\n"
                f"**Status:** {r.get('status')}\n\n**Reason:** {r.get('reason')}\n")
    rag, cag, t = r["arms"]["slm_rag"], r["arms"]["slm_cag"], r["arms"]["template"]
    vr, vc = r["split_dominance_rag"], r["split_dominance_cag"]
    d = r["cag_minus_rag"]
    det = r["determinism_cag"]
    row = lambda label, k, fmt="{:.3f}": (  # noqa: E731
        f"| {label} | " + " | ".join(fmt.format(a[k]) if not isinstance(a[k], str)
                                      else a[k] for a in (rag, cag, t)) + " |")
    L = [
        "# Experiment Job-A — citation-faithful legal-reasoning note (PILOT)",
        "",
        f"- **Model:** {r['model']} (frozen, Foundry Local, temperature 0)",
        f"- **Split:** {r['split']}  ·  **n = {r['n']}**  ·  corpus = {r['corpus_size']} "
        f"law_rules",
        f"- **Corpus presentation:** {r['corpus_presentation']}",
        f"- **RAG arm source:** {r['rag_arm_source']}",
        f"- **Gold:** {r['gold_kind']}",
        f"- **CAG determinism (temp 0):** {det['identical']}/{det['checked']} notes "
        f"identical-citation on re-run (rate {det['identical_rate']})",
        "",
        "> PILOT / PROXY. The gold is policy-base-derived (event_type -> applies_when), "
        "annotator-blind, NOT human-graded. This is NOT the §12 D5 gate (which needs "
        "human faithfulness grading + 2-rater kappa >= 0.6). D5 is NOT claimed passed.",
        "",
        "## 3-way results (novel split)",
        "",
        "| Metric | SLM RAG (k=10) | **SLM CAG (primary)** | Un-rigged template |",
        "|---|---|---|---|",
        row("Citation-correctness (mean F1)", "citation_correctness_f1"),
        row("Precision (mean)", "precision_mean"),
        row("Recall (mean)", "recall_mean"),
        row("Exact-set-match rate", "exact_match_rate"),
        row("FCR (per note)", "fcr_per_note"),
        row("FCR (per citation)", "fcr_per_citation"),
        row("Fabrication rate (per note, SCORED)", "fabrication_rate_per_note"),
        row("Fabricated citations (count, SCORED)", "fabricated_citation_count", "{}"),
        row("Abstention rate", "abstention_rate"),
        row("Parse-failure rate (counts as failure)", "parse_failure_rate"),
        "",
        "## Split-dominance verdicts (§3 pinned resolution)",
        "",
        f"- Pinned PRE-RUN (pilot): FCR ceiling (per note) = {vc['fcr_ceiling']}, "
        f"MDE on citation-F1 = {vc['mde_f1']}",
        f"- **RAG vs template:** F1 delta = **{vr['f1_delta']:+.3f}** · clears MDE: "
        f"{vr['clears_mde']} · under FCR ceiling: {vr['under_ceiling']} → "
        f"**{vr['verdict']}** ({vr['rationale']})",
        f"- **CAG vs template:** F1 delta = **{vc['f1_delta']:+.3f}** · clears MDE: "
        f"{vc['clears_mde']} · under FCR ceiling: {vc['under_ceiling']} → "
        f"**{vc['verdict']}** ({vc['rationale']})",
        "",
        "## CAG − RAG delta (does whole-corpus reason-then-classify move the needle?)",
        "",
        f"- ΔF1 (CAG − RAG) = **{d['dF1']:+.3f}**",
        f"- ΔFCR per note (CAG − RAG) = **{d['dFCR_per_note']:+.3f}**",
        f"- Δfabrication rate per note (CAG − RAG, SCORED) = "
        f"**{d['dfabrication_rate_per_note']:+.3f}**",
        f"- CAG fabrication ATTEMPTS dropped by the controller = "
        f"**{d['cag_fabrication_attempts_dropped_by_controller']}** "
        f"(scored fabrication count: CAG {d['cag_scored_fabrication_count']} vs "
        f"RAG {d['rag_scored_fabrication_count']})",
        f"- {d['note']}",
        "",
        "## Per-job latency (§8 FLPerformance nearest-rank; D-lat)",
        "",
        f"- **Job A (CAG reason-then-classify):** {_fmt_lat(r['job_a_latency'])}",
    ]
    if r.get("job_a_latency_rag"):
        L.append(f"- **Job A (RAG, this session):** {_fmt_lat(r['job_a_latency_rag'])}")
    L += [
        f"- Method: {r['job_a_latency'].get('method')}",
        "- Small-N caveat: at N < 100 the nearest-rank P99 index collapses to the last "
        "sample, so Job-A P99 is effectively the observed MAX. Reported with N + warmup.",
        "- Architectural finding: the tens-of-seconds Job-A P99 is the quantitative "
        "justification for the §3/§4 invariant that the SLM is post-hoc, non-evidential, "
        "counsel-gated and NEVER on the real-time gate path.",
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
        rag, cag, t = (out["arms"]["slm_rag"], out["arms"]["slm_cag"],
                       out["arms"]["template"])
        print(f"n={out['n']} model={out['model']}")
        for name, a in (("SLM RAG ", rag), ("SLM CAG ", cag), ("template", t)):
            print(f"{name} F1={a['citation_correctness_f1']:.3f} "
                  f"FCR/note={a['fcr_per_note']:.3f} "
                  f"fab={a['fabricated_citation_count']} "
                  f"parsefail={a['parse_failure_rate']:.3f}")
        print("RAG verdict:", out["split_dominance_rag"]["verdict"])
        print("CAG verdict:", out["split_dominance_cag"]["verdict"],
              "|", out["split_dominance_cag"]["rationale"])
        d = out["cag_minus_rag"]
        print(f"CAG-RAG: dF1={d['dF1']:+.3f} dFCR={d['dFCR_per_note']:+.3f} "
              f"fab_attempts_dropped={d['cag_fabrication_attempts_dropped_by_controller']}")
        la = out["job_a_latency"]
        print(f"Job-A latency: n={la['n']} P50={la['p50']} P95={la['p95']} P99={la['p99']}")
