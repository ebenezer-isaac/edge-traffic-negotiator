"""Legal corpus + CONTROLLER-MEDIATED retrieval for the SLM Job-A note (§2 RAG row,
§3, §9).

The corpus is the small, curated policy base: the 18 ``law_rules`` of
``ground_rules.yaml`` (the machine gold, cross-linked by ``statute_ref``) enriched
with the cited-law KB prose of ``01-research/uk-traffic-law.md`` (matched by
``statute_ref == that file's id``). Each entry is a ``LawRule``
``{rule_id, statute_ref, applies_when, text, ...}``.

Retrieval is CONTROLLER-MEDIATED (§2/§3): the SLM does NOT tool-call. Given a case
the controller derives a deterministic query and ranks the corpus by a tiny local
TF-IDF (pure stdlib — a curated corpus of 18 rules does NOT need embeddings), then
hands the top-k candidate rules to the SLM, which may cite ONLY from them
(grounding). A cited id absent from the corpus is a fabrication (§3 / Dahl 2024).

Golden rule (§10): an EMPTY corpus FAILS LOUD (``EmptyCorpusError``) — a retrieval
step that cannot prove its precondition (a corpus was loaded) must never emit a
green result. The KB-prose enrichment is best-effort (a missing KB file degrades
retrieval text but never empties the corpus); the law_rules are the hard floor.

Immutable style: ``LawRule`` and ``LegalCorpus`` are frozen; retrieval returns a
fresh tuple and never mutates the corpus.
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass, field
from functools import lru_cache

import yaml

__all__ = [
    "LawRule",
    "LegalCorpus",
    "EmptyCorpusError",
    "load_corpus",
    "case_query_terms",
    "retrieve_for_case",
    "GROUND_RULES_PATH",
    "UK_LAW_KB_PATH",
]

_HERE = os.path.dirname(os.path.abspath(__file__))
_PKG_ROOT = os.path.dirname(_HERE)                       # 03-implementation/edge-negotiator
_REPO_ROOT = os.path.dirname(os.path.dirname(_PKG_ROOT))  # e:/assignments/edge-traffic-negotiator

GROUND_RULES_PATH = os.path.join(_PKG_ROOT, "ground_rules.yaml")
UK_LAW_KB_PATH = os.path.join(_REPO_ROOT, "01-research", "uk-traffic-law.md")


class EmptyCorpusError(ValueError):
    """Raised when the corpus would be empty — the §10 fail-loud precondition."""


# --------------------------------------------------------------------------- #
# One retrievable rule.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class LawRule:
    """One retrievable law rule.

    ``statute_ref`` is the CANONICAL citation key (1:1 with the ``uk-traffic-law.md``
    id, §9) — this is what a Job-A note's ``cited_rules`` must resolve to. ``rule_id``
    is the file-local ``LR-*`` id. ``text`` is the yaml rule text, optionally
    appended with the KB plain-language prose for richer retrieval.
    """

    rule_id: str
    statute_ref: str
    applies_when: str
    text: str
    binding: str = ""
    fault_weight: str = ""
    source: str = ""
    note: str = ""
    kb_text: str = ""

    def retrieval_document(self) -> str:
        """The concatenated text the retriever indexes for this rule."""
        return " ".join(p for p in (
            self.statute_ref, self.applies_when, self.text, self.note, self.kb_text,
        ) if p)


# --------------------------------------------------------------------------- #
# Tokenisation + a tiny local TF-IDF (pure stdlib, deterministic).
# --------------------------------------------------------------------------- #

_STOPWORDS = frozenset({
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "at", "by", "for",
    "is", "it", "its", "as", "be", "with", "that", "this", "any", "not", "no",
    "must", "may", "are", "was", "who", "where", "when", "than", "from", "into",
    "only", "but", "if", "so", "each", "his", "her", "they", "them", "which",
})


def _tokenize(text: str) -> list[str]:
    """Lowercase alphanumeric tokens (len >= 3), stopwords removed. Deterministic."""
    if not text:
        return []
    raw = re.findall(r"[a-z0-9]+", text.lower())
    return [t for t in raw if len(t) >= 3 and t not in _STOPWORDS]


# --------------------------------------------------------------------------- #
# The corpus.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class LegalCorpus:
    """An immutable, indexed collection of ``LawRule`` with TF-IDF retrieval."""

    rules: tuple = ()
    _idf: dict = field(default_factory=dict, compare=False, repr=False)
    _doc_tf: tuple = field(default=(), compare=False, repr=False)

    # ---- construction ---- #
    @staticmethod
    def build(rules) -> "LegalCorpus":
        rules = tuple(rules)
        if not rules:
            raise EmptyCorpusError(
                "legal corpus is empty — no law_rules loaded (fail-loud, §10 golden rule)"
            )
        n = len(rules)
        doc_tf: list[dict] = []
        df: dict = {}
        for r in rules:
            toks = _tokenize(r.retrieval_document())
            tf: dict = {}
            for t in toks:
                tf[t] = tf.get(t, 0) + 1
            doc_tf.append(tf)
            for t in set(toks):
                df[t] = df.get(t, 0) + 1
        # smoothed idf; every term positive so a match always helps.
        idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        return LegalCorpus(rules=rules, _idf=idf, _doc_tf=tuple(doc_tf))

    # ---- lookups ---- #
    def __len__(self) -> int:
        return len(self.rules)

    def statute_refs(self) -> frozenset:
        """Every ``statute_ref`` in the corpus (the valid citation universe)."""
        return frozenset(r.statute_ref for r in self.rules)

    def by_statute_ref(self, statute_ref: str):
        for r in self.rules:
            if r.statute_ref == statute_ref:
                return r
        return None

    def contains_citation(self, statute_ref: str) -> bool:
        """True iff ``statute_ref`` names a real rule in the corpus (else fabrication)."""
        return any(r.statute_ref == statute_ref for r in self.rules)

    # ---- retrieval ---- #
    def retrieve(self, query_terms, k: int = 8) -> tuple:
        """Top-``k`` rules by TF-IDF over the derived query. Deterministic.

        Ranking: descending TF-IDF score, tie-broken by ``rule_id`` ascending, so
        the same query always yields the same ordered candidates.
        """
        if k <= 0:
            raise ValueError(f"k must be >= 1, got {k}")
        q = query_terms if isinstance(query_terms, (list, tuple)) else _tokenize(str(query_terms))
        q_counts: dict = {}
        for t in q:
            q_counts[t] = q_counts.get(t, 0) + 1
        scored = []
        for r, tf in zip(self.rules, self._doc_tf):
            score = 0.0
            for t, qc in q_counts.items():
                if t in tf:
                    score += qc * tf[t] * self._idf.get(t, 0.0)
            scored.append((score, r))
        scored.sort(key=lambda sr: (-sr[0], sr[1].rule_id))
        return tuple(r for _s, r in scored[:k])


# --------------------------------------------------------------------------- #
# Loaders.
# --------------------------------------------------------------------------- #

def _parse_kb_prose(md_path: str) -> dict:
    """Map ``uk-traffic-law.md`` id -> plain_language prose (best-effort, fail-soft).

    The KB entries are pseudo-JSON code blocks with unquoted keys; a full JSON parse
    is not possible, so we regex the two fields we need. A missing/garbled file
    returns ``{}`` (retrieval loses the extra prose but the corpus is never emptied).
    """
    try:
        with open(md_path, "r", encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return {}
    out: dict = {}
    # Each block: id: "X", ... plain_language: "Y", ... (single-line quoted values).
    for m in re.finditer(r'id:\s*"([^"]+)"', text):
        rid = m.group(1)
        tail = text[m.end():m.end() + 4000]
        pm = re.search(r'plain_language:\s*"((?:[^"\\]|\\.)*)"', tail)
        if pm:
            out.setdefault(rid, pm.group(1))
    return out


def load_corpus(ground_rules_path: str | None = None,
                kb_path: str | None = None) -> LegalCorpus:
    """Load the law_rules from ``ground_rules.yaml`` + enrich with the KB prose.

    Fails loud (``EmptyCorpusError``) if the yaml has no ``law_rules`` — the §10
    precondition. KB enrichment is best-effort.
    """
    gr_path = ground_rules_path or GROUND_RULES_PATH
    kb = kb_path or UK_LAW_KB_PATH
    with open(gr_path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    law_rules = (data or {}).get("law_rules") or []
    if not law_rules:
        raise EmptyCorpusError(
            f"no law_rules in {gr_path} — fail-loud, cannot retrieve over an empty corpus"
        )
    prose = _parse_kb_prose(kb)
    rules = []
    for lr in law_rules:
        statute_ref = str(lr.get("statute_ref", "")).strip()
        rule_id = str(lr.get("id", "")).strip()
        if not statute_ref or not rule_id:
            # a malformed rule is a corpus defect: fail loud rather than silently drop.
            raise EmptyCorpusError(
                f"law_rule missing id/statute_ref: {lr!r} (corpus integrity, §10)"
            )
        rules.append(LawRule(
            rule_id=rule_id,
            statute_ref=statute_ref,
            applies_when=str(lr.get("applies_when", "")),
            text=str(lr.get("text", "")),
            binding=str(lr.get("binding", "")),
            fault_weight=str(lr.get("fault_weight", "")),
            source=str(lr.get("source", "")),
            note=str(lr.get("note", "")),
            kb_text=prose.get(statute_ref, ""),
        ))
    return LegalCorpus.build(rules)


@lru_cache(maxsize=1)
def _default_corpus() -> LegalCorpus:
    return load_corpus()


# --------------------------------------------------------------------------- #
# Controller-mediated query derivation (case -> query terms).
# --------------------------------------------------------------------------- #
# The controller (NOT the SLM) turns a case into retrieval terms. Terms are keyed on
# the event_type (the legal SITUATION class) so the candidate set brackets the
# governing body of law + plausible distractors. This is deliberately GENERIC (not a
# copy of the gold map) so retrieval is a candidate generator, not an oracle.
_EVENT_QUERY_TERMS = {
    "emergency_claim": (
        "emergency vehicle ambulance crosses red signal exemption "
        "apportionment endangerment give way conflict civilian"
    ),
    "multi_emergency": (
        "emergency vehicle ambulance red signal exemption apportionment "
        "multiple parties contribution wrongdoers conflict"
    ),
    "emergency_plus_incident": (
        "emergency vehicle ambulance red signal exemption apportionment "
        "incident reroute multiple parties contribution contributory"
    ),
    "incident_claim": (
        "driver crosses stop line red signal prohibition offence incident "
        "contributory negligence collision fault"
    ),
    "conservation_anomaly": (
        "signal malfunction fault authority conflicting green wrong indication "
        "nonfeasance misfeasance responsible controller anomaly"
    ),
}
_GENERIC_TERMS = "junction traffic signal fault liability road user"


def case_query_terms(case) -> list:
    """Deterministic retrieval terms for a case (controller-mediated).

    Uses the event_type situation class + a generic junction-law tail. Never reads
    the ground-truth label (Job A cites the governing law for the situation; the
    real/spoof veracity judgment is Job B, kept separate).
    """
    event_type = getattr(case, "event_type", None) or (
        case.get("event_type") if isinstance(case, dict) else None
    )
    terms = _EVENT_QUERY_TERMS.get(event_type or "", "")
    return _tokenize(f"{terms} {_GENERIC_TERMS}")


def retrieve_for_case(corpus: LegalCorpus, case, k: int = 8) -> tuple:
    """Controller-mediated top-k retrieval for a case."""
    return corpus.retrieve(case_query_terms(case), k=k)
