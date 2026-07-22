"""Fault-finding tests for the SLM Job-A pipeline (§3): legal corpus, controller-
mediated retrieval, the proxy gold-builder, and citation/FCR scoring.

PURE: the SLM call is STUBBED (no Foundry). These pin the LOGIC that must not
silently regress — a fabricated citation IS caught as FCR, the template's near-miss
is scored WRONG (not a free abstention), and an empty corpus FAILS LOUD.
"""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import pytest  # noqa: E402

import experiment_jobA as ex  # noqa: E402
import legal_corpus as lc  # noqa: E402
from ambiguous_decision import FlaggedCase  # noqa: E402
from legal_corpus import EmptyCorpusError, LegalCorpus, load_corpus  # noqa: E402
from slm_agent import SLMAgent  # noqa: E402


# --------------------------------------------------------------------------- #
# Fixtures.
# --------------------------------------------------------------------------- #

def _case(event_type="emergency_claim", case_id="T-001", label="real",
          split="novel", **kw):
    base = dict(corroboration_count=1, residual=0.5, persistence=2,
                neighbour_agreement=0.5, local_sensing=False, severity=0.6)
    base.update(kw)
    return FlaggedCase(case_id=case_id, event_type=event_type, split=split,
                       label=label, **base)


@pytest.fixture(scope="module")
def corpus():
    return load_corpus()


# --------------------------------------------------------------------------- #
# 1. Corpus loads + is non-empty.
# --------------------------------------------------------------------------- #

def test_corpus_loads_nonempty(corpus):
    assert len(corpus) == 18
    assert len(corpus.statute_refs()) == 18
    # every rule carries the canonical citation key + situation condition.
    for r in corpus.rules:
        assert r.statute_ref and r.applies_when and r.text


def test_corpus_statute_refs_are_the_citation_universe(corpus):
    assert corpus.contains_citation("Griffin-v-Mersey")
    assert not corpus.contains_citation("Totally-Made-Up-Statute-999")


# --------------------------------------------------------------------------- #
# 2. Empty corpus fails loud (§10 golden rule).
# --------------------------------------------------------------------------- #

def test_empty_corpus_fails_loud():
    with pytest.raises(EmptyCorpusError):
        LegalCorpus.build([])


def test_load_corpus_empty_yaml_fails_loud(tmp_path):
    p = tmp_path / "empty.yaml"
    p.write_text("version: 1\nlaw_rules: []\n", encoding="utf-8")
    with pytest.raises(EmptyCorpusError):
        load_corpus(ground_rules_path=str(p), kb_path=str(tmp_path / "none.md"))


def test_load_corpus_malformed_rule_fails_loud(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("law_rules:\n  - id: LR-x\n    text: no statute_ref here\n",
                 encoding="utf-8")
    with pytest.raises(EmptyCorpusError):
        load_corpus(ground_rules_path=str(p), kb_path=str(tmp_path / "none.md"))


# --------------------------------------------------------------------------- #
# 3. Retrieval returns the right rule for a known case.
# --------------------------------------------------------------------------- #

def test_retrieval_surfaces_ev_rule_for_emergency(corpus):
    retrieved = {r.statute_ref for r in ex.retrieve_for_case(corpus, _case("emergency_claim"),
                                                             k=ex.RETRIEVAL_K)}
    assert "TSRGD2016-Sch14-Pt1-para5(4)-(6)" in retrieved  # the EV exemption
    assert "Griffin-v-Mersey" in retrieved                   # apportionment anchor


def test_retrieval_surfaces_authority_rule_for_conservation_anomaly(corpus):
    retrieved = {r.statute_ref for r in ex.retrieve_for_case(corpus, _case("conservation_anomaly"),
                                                             k=ex.RETRIEVAL_K)}
    assert "Gorringe-v-Calderdale" in retrieved
    assert "Bird-v-Pearce" in retrieved


def test_retrieval_is_deterministic(corpus):
    a = [r.rule_id for r in ex.retrieve_for_case(corpus, _case("incident_claim"), k=8)]
    b = [r.rule_id for r in ex.retrieve_for_case(corpus, _case("incident_claim"), k=8)]
    assert a == b


def test_retrieval_covers_every_event_type_gold(corpus):
    # every proxy-gold rule must be retrievable at RETRIEVAL_K, else recall is
    # capped by retrieval, not by the SLM (a silent confound).
    for event_type, gold in ex.APPLICABLE_RULES_BY_EVENT.items():
        retrieved = {r.statute_ref for r in ex.retrieve_for_case(
            corpus, _case(event_type), k=ex.RETRIEVAL_K)}
        assert gold <= retrieved, f"{event_type}: {gold - retrieved} not retrieved"


# --------------------------------------------------------------------------- #
# 4. Gold-builder maps a known case to the right statute_ref.
# --------------------------------------------------------------------------- #

def test_gold_builder_emergency_maps_to_ev_exemption():
    gold = ex.applicable_rules(_case("emergency_claim"))
    assert "TSRGD2016-Sch14-Pt1-para5(4)-(6)" in gold
    assert "Keyse-v-Commissioner" in gold


def test_gold_builder_incident_maps_to_red_offence():
    gold = ex.applicable_rules(_case("incident_claim"))
    assert gold == {"RTA1988-s36", "TSRGD2016-Sch14-Pt1-para5(3)",
                    "LawReform-ContribNeg-1945-s1"}


def test_gold_builder_is_label_independent():
    # Job A cites the governing law for the SITUATION; the real/spoof veracity call
    # is Job B and must NOT change the applicable-rule gold.
    assert ex.applicable_rules(_case("emergency_claim", label="real")) == \
           ex.applicable_rules(_case("emergency_claim", label="spoof_or_fault"))


def test_gold_builder_unknown_event_type_is_empty():
    class Weird:
        event_type = "not_a_known_type"
        case_id = "W-1"
    assert ex.applicable_rules(Weird()) == frozenset()


# --------------------------------------------------------------------------- #
# 5. A citation NOT in the corpus is counted as an FCR hit (fabrication caught).
# --------------------------------------------------------------------------- #

def test_fabricated_citation_is_fcr_and_fabrication(corpus):
    gold = frozenset({"TSRGD2016-Sch14-Pt1-para5(4)-(6)"})
    scored = ex.score_case(["Made-Up-Statute-2099"], gold, corpus)
    assert scored["has_fabrication"] is True       # not in corpus -> fabrication
    assert scored["has_false_citation"] is True    # and therefore a false citation
    assert scored["fabricated"] == ["Made-Up-Statute-2099"]
    assert scored["precision"] == 0.0


def test_in_corpus_but_non_applicable_is_false_not_fabrication(corpus):
    # a REAL corpus rule that does not apply to this gold is a false citation but
    # NOT a fabrication (it exists) — the two must be distinguished.
    gold = frozenset({"TSRGD2016-Sch14-Pt1-para5(4)-(6)"})
    scored = ex.score_case(["Gorringe-v-Calderdale"], gold, corpus)
    assert scored["has_false_citation"] is True
    assert scored["has_fabrication"] is False
    assert scored["fabricated"] == []


def test_correct_citation_scores_clean(corpus):
    gold = frozenset({"TSRGD2016-Sch14-Pt1-para5(4)-(6)", "Griffin-v-Mersey"})
    scored = ex.score_case(["TSRGD2016-Sch14-Pt1-para5(4)-(6)", "Griffin-v-Mersey"],
                           gold, corpus)
    assert scored["has_false_citation"] is False
    assert scored["exact_match"] is True
    assert scored["f1"] == 1.0


def test_aggregate_fcr_per_note_counts_notes_with_any_false(corpus):
    gold = frozenset({"Griffin-v-Mersey"})
    pc = [ex.score_case(["Griffin-v-Mersey"], gold, corpus),          # clean
          ex.score_case(["Griffin-v-Mersey", "FAKE-1"], gold, corpus),  # 1 false
          ex.score_case(["Bird-v-Pearce"], gold, corpus)]              # 1 false
    agg = ex.aggregate(pc)
    assert agg["fcr_per_note"] == pytest.approx(2 / 3)


# --------------------------------------------------------------------------- #
# 6. The template baseline scores a near-miss as WRONG, not abstention.
# --------------------------------------------------------------------------- #

def test_template_nearmiss_is_wrong_not_abstention(corpus):
    # Construct retrieval where top-1 is NOT in gold: the template must cite it
    # (a wrong citation), never abstain.
    top1 = corpus.by_statute_ref("Poole-BC-v-GN")   # authority rule, not EV gold
    gold = frozenset({"Griffin-v-Mersey"})
    cited, meta = ex.template_arm(_case("emergency_claim"), (top1,))
    scored = ex.score_case(cited, gold, corpus)
    assert cited == ["Poole-BC-v-GN"]
    assert scored["abstained"] is False              # NOT an abstention
    assert scored["has_false_citation"] is True      # scored WRONG
    assert scored["correct_refusal"] is False


def test_template_abstains_only_on_no_candidates(corpus):
    cited, meta = ex.template_arm(_case("emergency_claim"), ())
    assert cited == []


def test_abstention_correct_only_on_genuine_no_rule_cell(corpus):
    # gold empty (genuine no-rule cell) + no citation -> correct refusal.
    scored = ex.score_case([], frozenset(), corpus)
    assert scored["correct_refusal"] is True
    assert scored["has_false_citation"] is False
    # gold non-empty + abstention -> a MISS, never correct.
    scored2 = ex.score_case([], frozenset({"Griffin-v-Mersey"}), corpus)
    assert scored2["correct_refusal"] is False
    assert scored2["recall"] == 0.0


# --------------------------------------------------------------------------- #
# 7. End-to-end scoring with a STUBBED SLM (no Foundry) + parse-failure handling.
# --------------------------------------------------------------------------- #

class _StubAgent:
    """Deterministic stub: cites the first retrieved rule + one fabrication."""
    def reason_note(self, case, retrieved, note_max_tokens=768):
        cited = [retrieved[0].statute_ref, "Hallucinated-Statute-42"] if retrieved else []
        return {"candidate_origin": "unknown", "cited_rules": cited,
                "reasoning": "stub", "fault_weight_note": "qualitative"}


class _NoneAgent:
    def reason_note(self, case, retrieved, note_max_tokens=768):
        return None  # simulate a parse/connection failure


def test_slm_arm_scores_with_stub(corpus):
    cases = [_case("emergency_claim", case_id="E-1")]
    gold = ex.build_gold(cases)
    agg, pc = ex.score_arm(cases, gold, corpus, ex.make_slm_arm(_StubAgent()))
    assert agg["n"] == 1
    assert agg["fabrication_rate_per_note"] == 1.0   # the stub always fabricates one
    assert pc[0]["parse_failure"] is False


def test_slm_arm_parse_failure_counts_as_failure(corpus):
    cases = [_case("emergency_claim", case_id="E-2")]
    gold = ex.build_gold(cases)
    agg, pc = ex.score_arm(cases, gold, corpus, ex.make_slm_arm(_NoneAgent()))
    assert agg["parse_failure_rate"] == 1.0
    assert pc[0]["abstained"] is True
    assert agg["recall_mean"] == 0.0                 # a failure tanks recall (§8)


# --------------------------------------------------------------------------- #
# 8. Split-dominance verdict logic (§3 pinned resolution).
# --------------------------------------------------------------------------- #

def test_split_dominance_demotes_high_fcr_win():
    slm = {"citation_correctness_f1": 0.80, "fcr_per_note": 0.50}
    tpl = {"citation_correctness_f1": 0.50}
    v = ex.split_dominance_verdict(slm, tpl)
    assert v["verdict"] == "DEMOTE_SLM"   # higher F1 but FCR over ceiling


def test_split_dominance_slm_wins_clean():
    slm = {"citation_correctness_f1": 0.80, "fcr_per_note": 0.05}
    tpl = {"citation_correctness_f1": 0.50}
    assert ex.split_dominance_verdict(slm, tpl)["verdict"] == "SLM_WINS"


def test_split_dominance_tie_within_mde():
    slm = {"citation_correctness_f1": 0.52, "fcr_per_note": 0.0}
    tpl = {"citation_correctness_f1": 0.50}
    assert ex.split_dominance_verdict(slm, tpl)["verdict"] == "TIE"


# --------------------------------------------------------------------------- #
# 9. SLM note parser (pure) — grounding + robustness.
# --------------------------------------------------------------------------- #

def test_parse_note_extracts_shape():
    txt = ('here is the note {"candidate_origin": "attacker-key", '
           '"cited_rules": ["RTA1988-s36", "RTA1988-s36"], '
           '"reasoning": "short", "fault_weight_note": "high"} trailing')
    note = SLMAgent._parse_note(txt)
    assert note["cited_rules"] == ["RTA1988-s36"]   # deduped
    assert note["candidate_origin"] == "attacker-key"


def test_parse_note_none_on_garbage():
    assert SLMAgent._parse_note("no json here") is None
    assert SLMAgent._parse_note('{"reasoning": "x"}') is None  # missing cited_rules


def test_parse_note_clamps_reasoning_to_120_words():
    long = " ".join(["word"] * 200)
    txt = '{"cited_rules": [], "reasoning": "%s"}' % long
    note = SLMAgent._parse_note(txt)
    assert len(note["reasoning"].split()) == 120


# --------------------------------------------------------------------------- #
# 10. CAG reason-then-classify (§2/§3): the CONTROLLER derives the cited set.
# --------------------------------------------------------------------------- #

def test_cag_controller_derives_cited_from_applies_yes_only(corpus):
    in_corpus = corpus.statute_refs()
    txt = (
        '{"rule_judgments": ['
        '{"id": "Griffin-v-Mersey", "applies": "yes", "why": "EV apportionment"},'
        '{"id": "RTA1988-s36", "applies": "no", "why": "no civilian red-crossing"},'
        '{"id": "Keyse-v-Commissioner", "applies": "yes", "why": "adjust on facts"}],'
        '"candidate_origin": "emergency_claim",'
        '"cited_rules": ["RTA1988-s36"],'          # model free-text is WRONG on purpose
        '"reasoning": "note", "fault_weight_note": "qualitative"}'
    )
    note = SLMAgent._derive_cited_from_judgments(txt, in_corpus)
    # only the applies:"yes" ids, in judgment order — NOT the model's free-text list.
    assert note["cited_rules"] == ["Griffin-v-Mersey", "Keyse-v-Commissioner"]
    assert note["model_cited_rules"] == ["RTA1988-s36"]
    assert note["cited_consistent"] is False        # free-text disagreed with derived
    assert note["fabrication_attempts"] == []


def test_cag_reason_then_classify_ignores_freetext_cited_for_scoring(corpus):
    # even when the model's free-text cited_rules lists a fabricated id, the SCORED
    # (controller-derived) set never contains it — reason-then-classify decouples them.
    in_corpus = corpus.statute_refs()
    txt = (
        '{"rule_judgments": ['
        '{"id": "Bird-v-Pearce", "applies": "yes", "why": "conflicting green"}],'
        '"cited_rules": ["Totally-Fabricated-Ref-777", "Bird-v-Pearce"],'
        '"reasoning": "x", "fault_weight_note": "y"}'
    )
    note = SLMAgent._derive_cited_from_judgments(txt, in_corpus)
    assert note["cited_rules"] == ["Bird-v-Pearce"]              # derived, clean
    assert "Totally-Fabricated-Ref-777" in note["model_cited_rules"]
    scored = ex.score_case(note["cited_rules"], frozenset({"Bird-v-Pearce"}), corpus)
    assert scored["has_fabrication"] is False                   # nothing fabricated scored


def test_cag_controller_drops_and_counts_out_of_corpus_applies_yes(corpus):
    # a model that judges a FABRICATED / out-of-corpus id as applicable: the controller
    # DROPS it from cited AND records it as a fabrication attempt (never scored).
    in_corpus = corpus.statute_refs()
    txt = (
        '{"rule_judgments": ['
        '{"id": "Griffin-v-Mersey", "applies": "yes", "why": "real rule"},'
        '{"id": "Made-Up-Statute-2099", "applies": "yes", "why": "hallucinated"}],'
        '"cited_rules": [], "reasoning": "r", "fault_weight_note": "f"}'
    )
    note = SLMAgent._derive_cited_from_judgments(txt, in_corpus)
    assert note["cited_rules"] == ["Griffin-v-Mersey"]          # in-corpus kept
    assert note["fabrication_attempts"] == ["Made-Up-Statute-2099"]  # dropped + counted
    # and the scored set carries NO fabrication (the drop happened pre-scoring).
    scored = ex.score_case(note["cited_rules"], frozenset({"Griffin-v-Mersey"}), corpus)
    assert scored["fabricated"] == []


def test_cag_parser_none_without_rule_judgments():
    # reason-then-classify REQUIRES the per-rule judgment array; a bare cited-only
    # object (the old RAG shape) is a parse failure for the CAG path.
    assert SLMAgent._derive_cited_from_judgments(
        '{"cited_rules": ["Griffin-v-Mersey"]}', frozenset({"Griffin-v-Mersey"})) is None
    assert SLMAgent._derive_cited_from_judgments("no json", frozenset()) is None


def test_cag_parser_accepts_boolean_applies(corpus):
    # some models emit a JSON boolean rather than "yes"/"no"; both must work.
    in_corpus = corpus.statute_refs()
    txt = ('{"rule_judgments": [{"id": "Bird-v-Pearce", "applies": true, "why": "x"},'
           '{"id": "Griffin-v-Mersey", "applies": false, "why": "y"}]}')
    note = SLMAgent._derive_cited_from_judgments(txt, in_corpus)
    assert note["cited_rules"] == ["Bird-v-Pearce"]


class _StubCagAgent:
    """Deterministic CAG stub: judges the first rule applicable + fabricates one id."""
    def reason_note_cag(self, case, candidates, note_max_tokens=1536):
        first = candidates[0].statute_ref if candidates else None
        judgments = []
        if first:
            judgments.append({"id": first, "applies": True, "why": "stub"})
        judgments.append({"id": "Stub-Fabricated-Id", "applies": True, "why": "stub"})
        cited = [first] if first else []
        return {"rule_judgments": judgments, "candidate_origin": "unknown",
                "cited_rules": cited, "model_cited_rules": cited,
                "cited_consistent": True,
                "fabrication_attempts": ["Stub-Fabricated-Id"],
                "reasoning": "stub", "fault_weight_note": "qualitative"}


def test_cag_arm_scores_controller_derived_and_surfaces_attempts(corpus):
    cases = [_case("conservation_anomaly", case_id="C-1")]
    gold = ex.build_gold(cases)
    agg, pc = ex.score_arm(cases, gold, corpus, ex.make_cag_arm(_StubCagAgent()),
                           candidate_fn=ex.cag_candidates)
    assert agg["n"] == 1
    # scored fabrication is 0 (the fabricated id was dropped by the controller)...
    assert agg["fabricated_citation_count"] == 0
    assert agg["fabrication_rate_per_note"] == 0.0
    # ...but the DROPPED attempt is surfaced per-case for transparency.
    assert pc[0]["fabrication_attempts"] == 1
    assert pc[0]["parse_failure"] is False


def test_cag_candidates_returns_whole_corpus(corpus):
    cands = ex.cag_candidates(corpus, _case("emergency_claim"))
    assert len(cands) == 18                                  # whole corpus, no top-k
    assert {r.statute_ref for r in cands} == set(corpus.statute_refs())
