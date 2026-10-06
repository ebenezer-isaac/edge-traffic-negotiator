"""Tests for the ambiguous-case decision interface (src/ambiguous_decision.py).

Run from the project root with the venv interpreter:
    .venv/Scripts/python -m pytest tests/test_ambiguous_decision.py -v

Covers, in TDD order:
  * FlaggedCase: valid construction, frozen/immutable, every boundary
    validation (types, ranges, allowed enums).
  * RuleDisambiguator.decide: every branch of the documented logic
    (local-sensing shortcut; each AND-condition individually failing).
  * RuleDisambiguator.tune: improves-or-matches balanced accuracy on the
    anticipated split, ignores the novel split entirely, immutability
    (returns a NEW instance, never mutates self), degenerate inputs.
  * generate_dataset: determinism (same seed -> identical cases), split
    sizes and label balance, both labels in both splits, no leakage
    (label not a trivial function of any single rule feature), input
    validation.
  * evaluate: hand-built confusion-matrix arithmetic, per-split
    separation (never pooled), both decider calling conventions, and the
    edge cases (empty, all-real, all-spoof).

These tests are written to BREAK the module: happy path is minimal, the
bulk targets boundaries and the "no leakage" / "never pooled" guarantees
the experiment's validity depends on.
"""
import copy
import dataclasses
import os
import sys

import pytest

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from ambiguous_decision import (  # noqa: E402
    ESCALATE_REAL,
    REJECT,
    FlaggedCase,
    RuleDisambiguator,
    evaluate,
    generate_dataset,
)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _case(**overrides) -> FlaggedCase:
    """A valid baseline FlaggedCase with any field overridden."""
    fields = dict(
        case_id="c1",
        event_type="emergency_claim",
        corroboration_count=2,
        residual=0.3,
        persistence=3,
        neighbour_agreement=0.8,
        local_sensing=False,
        severity=0.6,
        split="anticipated",
        label="real",
    )
    fields.update(overrides)
    return FlaggedCase(**fields)


class _ConstantDecider:
    """A decider stub with a .decide method (object calling convention)."""

    def __init__(self, decision):
        self._decision = decision

    def decide(self, case):  # noqa: ARG002 - interface requires the arg
        return self._decision


class _ByIdDecider:
    """A decider stub whose answer depends on case_id (for hand-built matrices)."""

    def __init__(self, mapping):
        self._mapping = mapping

    def decide(self, case):
        return self._mapping[case.case_id]


# --------------------------------------------------------------------------- #
# FlaggedCase
# --------------------------------------------------------------------------- #

class TestFlaggedCase:
    def test_valid_construction(self):
        c = _case()
        assert c.case_id == "c1"
        assert c.label == "real"

    def test_frozen_immutable(self):
        c = _case()
        with pytest.raises(dataclasses.FrozenInstanceError):
            c.label = "spoof_or_fault"  # type: ignore[misc]

    def test_deepcopy_does_not_share_state(self):
        c = _case()
        c2 = copy.deepcopy(c)
        assert c2 == c
        assert c2 is not c

    @pytest.mark.parametrize("event_type", [
        "emergency_claim", "incident_claim", "conservation_anomaly",
        "multi_emergency", "emergency_plus_incident",
    ])
    def test_all_declared_event_types_accepted(self, event_type):
        c = _case(event_type=event_type)
        assert c.event_type == event_type

    def test_bad_event_type_rejected(self):
        with pytest.raises(ValueError):
            _case(event_type="phantom_type")

    def test_empty_case_id_rejected(self):
        with pytest.raises(TypeError):
            _case(case_id="")

    def test_non_str_case_id_rejected(self):
        with pytest.raises(TypeError):
            _case(case_id=123)

    def test_negative_corroboration_count_rejected(self):
        with pytest.raises(ValueError):
            _case(corroboration_count=-1)

    def test_float_corroboration_count_rejected(self):
        with pytest.raises(TypeError):
            _case(corroboration_count=1.5)

    def test_bool_corroboration_count_rejected(self):
        # bool is a subclass of int; must be rejected explicitly.
        with pytest.raises(TypeError):
            _case(corroboration_count=True)

    def test_negative_residual_rejected(self):
        with pytest.raises(ValueError):
            _case(residual=-0.1)

    def test_non_numeric_residual_rejected(self):
        with pytest.raises(TypeError):
            _case(residual="0.5")  # type: ignore[arg-type]

    def test_bool_residual_rejected(self):
        # bool is a subclass of int/float-compatible; must be rejected.
        with pytest.raises(TypeError):
            _case(residual=True)  # type: ignore[arg-type]

    def test_nan_residual_rejected(self):
        with pytest.raises(ValueError):
            _case(residual=float("nan"))

    def test_inf_residual_rejected(self):
        with pytest.raises(ValueError):
            _case(residual=float("inf"))

    def test_negative_persistence_rejected(self):
        with pytest.raises(ValueError):
            _case(persistence=-1)

    def test_neighbour_agreement_above_one_rejected(self):
        with pytest.raises(ValueError):
            _case(neighbour_agreement=1.5)

    def test_neighbour_agreement_below_zero_rejected(self):
        with pytest.raises(ValueError):
            _case(neighbour_agreement=-0.01)

    def test_neighbour_agreement_boundary_values_accepted(self):
        assert _case(neighbour_agreement=0.0).neighbour_agreement == 0.0
        assert _case(neighbour_agreement=1.0).neighbour_agreement == 1.0

    def test_non_bool_local_sensing_rejected(self):
        with pytest.raises(TypeError):
            _case(local_sensing=1)  # type: ignore[arg-type]

    def test_severity_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            _case(severity=1.01)
        with pytest.raises(ValueError):
            _case(severity=-0.01)

    def test_bad_split_rejected(self):
        with pytest.raises(ValueError):
            _case(split="dev")

    def test_bad_label_rejected(self):
        with pytest.raises(ValueError):
            _case(label="unknown")


# --------------------------------------------------------------------------- #
# RuleDisambiguator: construction validation
# --------------------------------------------------------------------------- #

class TestRuleDisambiguatorConstruction:
    def test_defaults(self):
        r = RuleDisambiguator()
        assert r.corr_k == 1
        assert r.residual_max == 1.0
        assert r.persistence_p == 2
        assert r.agreement_min == 0.5

    def test_negative_corr_k_rejected(self):
        with pytest.raises(ValueError):
            RuleDisambiguator(corr_k=-1)

    def test_negative_residual_max_rejected(self):
        with pytest.raises(ValueError):
            RuleDisambiguator(residual_max=-1.0)

    def test_negative_persistence_p_rejected(self):
        with pytest.raises(ValueError):
            RuleDisambiguator(persistence_p=-1)

    def test_agreement_min_out_of_range_rejected(self):
        with pytest.raises(ValueError):
            RuleDisambiguator(agreement_min=1.5)
        with pytest.raises(ValueError):
            RuleDisambiguator(agreement_min=-0.1)

    def test_frozen(self):
        r = RuleDisambiguator()
        with pytest.raises(dataclasses.FrozenInstanceError):
            r.corr_k = 5  # type: ignore[misc]


# --------------------------------------------------------------------------- #
# RuleDisambiguator.decide: known-case branch coverage
# --------------------------------------------------------------------------- #

class TestRuleDisambiguatorDecide:
    def test_rejects_non_flagged_case(self):
        r = RuleDisambiguator()
        with pytest.raises(TypeError):
            r.decide("not a case")  # type: ignore[arg-type]

    def test_local_sensing_always_escalates(self):
        r = RuleDisambiguator()
        # Every corroboration-side condition deliberately fails; local
        # sensing alone must still escalate (the OR shortcut).
        c = _case(local_sensing=True, corroboration_count=0, residual=5.0,
                   persistence=0, neighbour_agreement=0.0)
        assert r.decide(c) == ESCALATE_REAL

    def test_all_conditions_met_escalates(self):
        r = RuleDisambiguator(corr_k=1, residual_max=1.0, persistence_p=2,
                               agreement_min=0.5)
        c = _case(local_sensing=False, corroboration_count=1, residual=1.0,
                   persistence=2, neighbour_agreement=0.5)
        assert r.decide(c) == ESCALATE_REAL

    def test_insufficient_corroboration_rejects(self):
        r = RuleDisambiguator(corr_k=2, residual_max=1.0, persistence_p=2,
                               agreement_min=0.5)
        c = _case(local_sensing=False, corroboration_count=1, residual=0.1,
                   persistence=5, neighbour_agreement=0.9)
        assert r.decide(c) == REJECT

    def test_residual_out_of_band_rejects(self):
        r = RuleDisambiguator(corr_k=1, residual_max=1.0, persistence_p=2,
                               agreement_min=0.5)
        c = _case(local_sensing=False, corroboration_count=5, residual=1.01,
                   persistence=5, neighbour_agreement=0.9)
        assert r.decide(c) == REJECT

    def test_insufficient_persistence_rejects(self):
        r = RuleDisambiguator(corr_k=1, residual_max=1.0, persistence_p=3,
                               agreement_min=0.5)
        c = _case(local_sensing=False, corroboration_count=5, residual=0.1,
                   persistence=2, neighbour_agreement=0.9)
        assert r.decide(c) == REJECT

    def test_insufficient_agreement_rejects(self):
        r = RuleDisambiguator(corr_k=1, residual_max=1.0, persistence_p=2,
                               agreement_min=0.8)
        c = _case(local_sensing=False, corroboration_count=5, residual=0.1,
                   persistence=5, neighbour_agreement=0.5)
        assert r.decide(c) == REJECT

    def test_zero_corroboration_zero_sensing_rejects(self):
        r = RuleDisambiguator()
        c = _case(local_sensing=False, corroboration_count=0, residual=0.1,
                   persistence=5, neighbour_agreement=0.9)
        assert r.decide(c) == REJECT


# --------------------------------------------------------------------------- #
# RuleDisambiguator.tune
# --------------------------------------------------------------------------- #

class TestRuleDisambiguatorTune:
    def _separable_anticipated(self):
        """Anticipated-only cases perfectly separable by a strict rule."""
        real = [
            _case(case_id=f"r{i}", corroboration_count=3, residual=0.1,
                   persistence=4, neighbour_agreement=0.9, label="real")
            for i in range(6)
        ]
        spoof = [
            _case(case_id=f"s{i}", corroboration_count=0, residual=2.0,
                   persistence=0, neighbour_agreement=0.1,
                   label="spoof_or_fault")
            for i in range(6)
        ]
        return real + spoof

    def test_rejects_non_list(self):
        r = RuleDisambiguator()
        with pytest.raises(TypeError):
            r.tune("not a list")  # type: ignore[arg-type]

    def test_returns_new_instance_not_self(self):
        r = RuleDisambiguator()
        tuned = r.tune(self._separable_anticipated())
        assert tuned is not r
        assert isinstance(tuned, RuleDisambiguator)

    def test_does_not_mutate_self(self):
        r = RuleDisambiguator(corr_k=1, residual_max=1.0, persistence_p=2,
                               agreement_min=0.5)
        before = dataclasses.astuple(r)
        r.tune(self._separable_anticipated())
        assert dataclasses.astuple(r) == before

    def test_empty_anticipated_returns_equivalent_new_instance(self):
        r = RuleDisambiguator(corr_k=1, residual_max=1.0, persistence_p=2,
                               agreement_min=0.5)
        novel_only = [_case(split="novel", label="real")]
        tuned = r.tune(novel_only)
        assert tuned is not r
        assert tuned == r  # same field values, different object

    def test_empty_cases_list_returns_equivalent_new_instance(self):
        r = RuleDisambiguator()
        tuned = r.tune([])
        assert tuned is not r
        assert tuned == r

    def test_improves_or_matches_balanced_accuracy(self):
        cases = self._separable_anticipated()
        # A deliberately mistuned starting rule that misses several
        # obviously-real and obviously-spoof cases on this dev set.
        bad = RuleDisambiguator(corr_k=5, residual_max=0.05,
                                 persistence_p=10, agreement_min=0.99)
        before = _balanced_accuracy_via_evaluate(bad, cases)
        tuned = bad.tune(cases)
        after = _balanced_accuracy_via_evaluate(tuned, cases)
        assert after >= before

    def test_tune_achieves_perfect_separation_on_separable_set(self):
        cases = self._separable_anticipated()
        tuned = RuleDisambiguator(corr_k=5, residual_max=0.05,
                                   persistence_p=10, agreement_min=0.99).tune(cases)
        report = evaluate(tuned, cases)
        assert report["anticipated"]["accuracy"] == 1.0

    def test_tune_ignores_novel_split(self):
        anticipated = self._separable_anticipated()
        # Novel cases that would push thresholds in the OPPOSITE direction
        # if tune() considered them; it must not.
        misleading_novel = [
            _case(case_id=f"n{i}", split="novel", corroboration_count=0,
                  residual=2.0, persistence=0, neighbour_agreement=0.1,
                  label="real")
            for i in range(6)
        ]
        tuned_without_novel = RuleDisambiguator().tune(anticipated)
        tuned_with_novel = RuleDisambiguator().tune(anticipated + misleading_novel)
        assert tuned_without_novel == tuned_with_novel


def _balanced_accuracy_via_evaluate(rule: RuleDisambiguator, cases: list) -> float:
    report = evaluate(rule, cases)
    m = report["overall"]
    recall = m["tp"] / (m["tp"] + m["fn"]) if (m["tp"] + m["fn"]) else 0.0
    specificity = m["tn"] / (m["tn"] + m["fp"]) if (m["tn"] + m["fp"]) else 0.0
    return (recall + specificity) / 2.0


# --------------------------------------------------------------------------- #
# generate_dataset
# --------------------------------------------------------------------------- #

class TestGenerateDataset:
    def test_rejects_non_int_seed(self):
        with pytest.raises(TypeError):
            generate_dataset(seed="0")  # type: ignore[arg-type]

    def test_rejects_bool_seed(self):
        with pytest.raises(TypeError):
            generate_dataset(seed=True)  # type: ignore[arg-type]

    def test_deterministic_same_seed(self):
        a = generate_dataset(seed=0)
        b = generate_dataset(seed=0)
        assert a == b  # dataclass equality: every field, every case, in order

    def test_different_seed_changes_numeric_fields(self):
        a = generate_dataset(seed=0)
        b = generate_dataset(seed=1)
        assert a != b
        # Same shape, different jittered values somewhere.
        assert len(a) == len(b)
        assert any(x.residual != y.residual for x, y in zip(a, b))

    def test_total_size_in_documented_range(self):
        cases = generate_dataset()
        assert 60 <= len(cases) <= 120

    def test_split_sizes(self):
        cases = generate_dataset()
        anticipated = [c for c in cases if c.split == "anticipated"]
        novel = [c for c in cases if c.split == "novel"]
        assert len(anticipated) == 60
        assert len(novel) == 30
        assert len(anticipated) + len(novel) == len(cases)

    def test_anticipated_label_balance(self):
        cases = generate_dataset()
        anticipated = [c for c in cases if c.split == "anticipated"]
        real = [c for c in anticipated if c.label == "real"]
        spoof = [c for c in anticipated if c.label == "spoof_or_fault"]
        assert len(real) == 30
        assert len(spoof) == 30

    def test_novel_label_balance(self):
        cases = generate_dataset()
        novel = [c for c in cases if c.split == "novel"]
        real = [c for c in novel if c.label == "real"]
        spoof = [c for c in novel if c.label == "spoof_or_fault"]
        assert len(real) == 15
        assert len(spoof) == 15

    def test_both_labels_present_in_both_splits(self):
        cases = generate_dataset()
        for split in ("anticipated", "novel"):
            labels = {c.label for c in cases if c.split == split}
            assert labels == {"real", "spoof_or_fault"}

    def test_new_event_types_only_in_novel(self):
        cases = generate_dataset()
        for c in cases:
            if c.event_type in ("multi_emergency", "emergency_plus_incident"):
                assert c.split == "novel"

    def test_anticipated_covers_original_three_event_types(self):
        cases = generate_dataset()
        anticipated_types = {c.event_type for c in cases if c.split == "anticipated"}
        assert anticipated_types == {
            "emergency_claim", "incident_claim", "conservation_anomaly",
        }

    def test_novel_covers_all_five_event_types(self):
        cases = generate_dataset()
        novel_types = {c.event_type for c in cases if c.split == "novel"}
        assert novel_types == {
            "emergency_claim", "incident_claim", "conservation_anomaly",
            "multi_emergency", "emergency_plus_incident",
        }

    def test_case_ids_are_unique(self):
        cases = generate_dataset()
        ids = [c.case_id for c in cases]
        assert len(ids) == len(set(ids))

    def test_no_leakage_corroboration_count_alone_does_not_separate_novel(self):
        # By design, novel sparse_real and collusion_spoof both use
        # corroboration_count == 1: proves the label is not a trivial
        # function of corroboration count alone in the novel split (the
        # split meant to defeat single-feature rule thresholds).
        cases = generate_dataset()
        corr_1_novel = [c for c in cases if c.split == "novel"
                        and c.corroboration_count == 1]
        labels = {c.label for c in corr_1_novel}
        assert labels == {"real", "spoof_or_fault"}

    def test_all_cases_are_flagged_case_instances(self):
        cases = generate_dataset()
        assert all(isinstance(c, FlaggedCase) for c in cases)


# --------------------------------------------------------------------------- #
# evaluate: hand-built confusion matrix + edge cases
# --------------------------------------------------------------------------- #

class TestEvaluate:
    def test_rejects_non_list_cases(self):
        with pytest.raises(TypeError):
            evaluate(RuleDisambiguator(), "not a list")  # type: ignore[arg-type]

    def test_rejects_non_flagged_case_members(self):
        with pytest.raises(TypeError):
            evaluate(RuleDisambiguator(), ["not a case"])  # type: ignore[list-item]

    def test_rejects_decider_without_decide_or_call(self):
        cases = [_case()]
        with pytest.raises(TypeError):
            evaluate(object(), cases)

    def test_rejects_invalid_decision_value(self):
        cases = [_case()]
        bad = _ConstantDecider("maybe")
        with pytest.raises(ValueError):
            evaluate(bad, cases)

    def test_plain_callable_decider_supported(self):
        cases = [_case(label="real")]
        result = evaluate(lambda case: ESCALATE_REAL, cases)
        assert result["overall"]["accuracy"] == 1.0

    def test_object_with_decide_supported(self):
        cases = [_case(label="real")]
        result = evaluate(_ConstantDecider(ESCALATE_REAL), cases)
        assert result["overall"]["accuracy"] == 1.0

    def test_empty_case_list(self):
        result = evaluate(RuleDisambiguator(), [])
        for split in ("anticipated", "novel", "overall"):
            m = result[split]
            assert m["n"] == 0
            assert m["accuracy"] == 0.0
            assert m["precision"] == 0.0
            assert m["recall"] == 0.0
            assert m["f1"] == 0.0
            assert m["false_preemption_rate"] == 0.0

    def test_all_real_perfect_decider(self):
        cases = [_case(case_id=f"r{i}", label="real") for i in range(4)]
        result = evaluate(_ConstantDecider(ESCALATE_REAL), cases)
        m = result["overall"]
        assert m["accuracy"] == 1.0
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0
        assert m["false_preemption_rate"] == 0.0  # no spoof cases exist

    def test_all_real_decider_rejects_everything(self):
        cases = [_case(case_id=f"r{i}", label="real") for i in range(4)]
        result = evaluate(_ConstantDecider(REJECT), cases)
        m = result["overall"]
        assert m["accuracy"] == 0.0
        assert m["precision"] == 0.0  # tp+fp == 0
        assert m["recall"] == 0.0
        assert m["f1"] == 0.0
        assert m["false_preemption_rate"] == 0.0  # no spoof cases exist

    def test_all_spoof_perfect_decider(self):
        cases = [_case(case_id=f"s{i}", label="spoof_or_fault") for i in range(4)]
        result = evaluate(_ConstantDecider(REJECT), cases)
        m = result["overall"]
        assert m["accuracy"] == 1.0
        assert m["precision"] == 0.0  # no positive predictions at all
        assert m["recall"] == 0.0
        assert m["f1"] == 0.0
        assert m["false_preemption_rate"] == 0.0

    def test_all_spoof_worst_case_decider(self):
        cases = [_case(case_id=f"s{i}", label="spoof_or_fault") for i in range(4)]
        result = evaluate(_ConstantDecider(ESCALATE_REAL), cases)
        m = result["overall"]
        assert m["accuracy"] == 0.0
        assert m["false_preemption_rate"] == 1.0

    def test_hand_built_confusion_matrix(self):
        # 2 real correctly escalated (TP), 1 real wrongly rejected (FN),
        # 1 spoof wrongly escalated (FP, a false preemption), 2 spoof
        # correctly rejected (TN). All in the same split for a clean
        # by-hand check.
        cases = [
            _case(case_id="tp1", label="real"),
            _case(case_id="tp2", label="real"),
            _case(case_id="fn1", label="real"),
            _case(case_id="fp1", label="spoof_or_fault"),
            _case(case_id="tn1", label="spoof_or_fault"),
            _case(case_id="tn2", label="spoof_or_fault"),
        ]
        mapping = {
            "tp1": ESCALATE_REAL, "tp2": ESCALATE_REAL,
            "fn1": REJECT,
            "fp1": ESCALATE_REAL,
            "tn1": REJECT, "tn2": REJECT,
        }
        result = evaluate(_ByIdDecider(mapping), cases)
        m = result["overall"]
        assert m["n"] == 6
        assert m["tp"] == 2
        assert m["fn"] == 1
        assert m["fp"] == 1
        assert m["tn"] == 2
        assert m["accuracy"] == pytest.approx((2 + 2) / 6)
        assert m["precision"] == pytest.approx(2 / 3)   # tp / (tp+fp)
        assert m["recall"] == pytest.approx(2 / 3)      # tp / (tp+fn)
        expected_f1 = 2 * (2 / 3) * (2 / 3) / ((2 / 3) + (2 / 3))
        assert m["f1"] == pytest.approx(expected_f1)
        assert m["false_preemption_rate"] == pytest.approx(1 / 3)  # fp/(fp+tn)

    def test_splits_never_pooled(self):
        # Anticipated: decider is perfect. Novel: decider is always wrong.
        anticipated = [
            _case(case_id="a1", split="anticipated", label="real"),
            _case(case_id="a2", split="anticipated", label="spoof_or_fault"),
        ]
        novel = [
            _case(case_id="n1", split="novel", label="real"),
            _case(case_id="n2", split="novel", label="spoof_or_fault"),
        ]
        mapping = {
            "a1": ESCALATE_REAL, "a2": REJECT,      # both correct
            "n1": REJECT, "n2": ESCALATE_REAL,      # both wrong
        }
        result = evaluate(_ByIdDecider(mapping), anticipated + novel)
        assert result["anticipated"]["accuracy"] == 1.0
        assert result["novel"]["accuracy"] == 0.0
        # overall pools both, and must differ from either split alone.
        assert result["overall"]["accuracy"] == pytest.approx(0.5)
        assert result["overall"]["n"] == 4

    def test_only_one_split_present(self):
        cases = [_case(case_id="a1", split="anticipated", label="real")]
        result = evaluate(_ConstantDecider(ESCALATE_REAL), cases)
        assert result["anticipated"]["n"] == 1
        assert result["novel"]["n"] == 0
        assert result["novel"]["accuracy"] == 0.0
        assert result["overall"]["n"] == 1


# --------------------------------------------------------------------------- #
# End-to-end sanity: real RuleDisambiguator over the real generated dataset.
# --------------------------------------------------------------------------- #

class TestEndToEnd:
    def test_default_rule_over_generated_dataset_runs_and_reports_all_keys(self):
        cases = generate_dataset(seed=0)
        rule = RuleDisambiguator()
        report = evaluate(rule, cases)
        assert set(report.keys()) == {"anticipated", "novel", "overall"}
        for split in report.values():
            assert 0.0 <= split["accuracy"] <= 1.0
            assert 0.0 <= split["false_preemption_rate"] <= 1.0

    def test_tuned_rule_is_strong_on_anticipated_by_design(self):
        cases = generate_dataset(seed=0)
        tuned = RuleDisambiguator().tune(cases)
        report = evaluate(tuned, cases)
        # The anticipated split IS what the rule is tuned for; it should
        # do well there (this is the expected parity result, not a
        # guarantee of the same on novel).
        assert report["anticipated"]["accuracy"] >= 0.9
