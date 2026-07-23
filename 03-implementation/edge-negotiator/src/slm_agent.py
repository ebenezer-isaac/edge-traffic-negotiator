"""SLM junction agent — a local OpenAI-compatible endpoint (Microsoft Foundry
Local serving Phi-4-mini). Two jobs: the terse phase decision (choose_phase),
and the disambiguation / Job-A reasoning note over a flagged case.

Accountability comes from the SIGNED AUDIT LOG, never from model self-narration.
Reasoning, where produced (the Job-A internal note, §6 CoT row / §3), is treated
as a NON-EVIDENTIAL, firewalled, counsel-gated artifact that is VALIDATED against
the cited statute and NEVER trusted on its face; it is not a determination of
fault and never enters the evidence pack. max_tokens is sized to allow that note.
We prompt-and-parse with strict validation (Foundry Local has no JSON-schema
enforcement) and return None on ANY failure so the caller falls back to the
deterministic MaxPressure shield.
"""
from __future__ import annotations

import os
import re

from openai import OpenAI

SYSTEM = (
    "You control one traffic-signal junction. "
    "You will be given the number of waiting vehicles for each green phase. "
    "Decide which phase to serve next. "
    'Reply with ONLY JSON {"phase": <index>} and nothing else.'
)

# Delay-aware myopic prompt (SOTA-informed, single junction, own-approach info only).
# Encodes two levers MaxPressure structurally lacks, both targeting DELAY rather than
# throughput and both grounded in the LLM-TSC literature:
#   * WAITING-TIME PRIORITY (LLMLight, arXiv:2312.16044): MaxPressure privileges only
#     instantaneous queue length and is memoryless on how long vehicles have waited,
#     which inflates average waiting time; prioritising phases whose vehicles have
#     ALREADY waited long attacks the delay metric directly.
#   * SWITCHING HYSTERESIS / STOP REDUCTION (EvolveSignal, arXiv:2509.03335): every
#     phase switch forces vehicles to stop and restart; the discovered delay-optimal
#     policy cut stops ~47%. Keeping the current phase unless another is clearly
#     worse-off reduces stops and hence delay.
# Output stays terse (single JSON, no long chain-of-thought) so per-decision latency
# remains inside the real-time interval.
SYSTEM_DELAY_AWARE = (
    "You control ONE traffic-signal junction (this junction only; no neighbour "
    "information). For each green phase you are given: the number of waiting "
    "(queued) vehicles, the TOTAL accumulated waiting time of those vehicles in "
    "seconds, and whether it is the phase currently green. Choose the phase to serve "
    "next to MINIMISE total vehicle waiting time and unnecessary stops -- not simply "
    "the longest queue.\n"
    "Guidance: (1) prefer a phase that has BOTH many waiting vehicles AND a high "
    "accumulated waiting time, because long-waiting vehicles contribute the most "
    "delay; (2) never leave a phase that has already waited a long time unserved "
    "(avoid starvation); (3) keep the CURRENT phase unless another phase is clearly "
    "worse-off, because switching makes a whole queue stop and restart, adding delay. "
    'Reply with ONLY JSON {"phase": <index>} and nothing else.'
)

# Prompt for the ambiguous-case disambiguation job (Experiment 1). The model
# judges a flagged event as real or fake/faulty from partial evidence, the one
# decision a fixed per-junction rule cannot cleanly settle. We give qualitative
# judgment guidance (the DIRECTION each signal points) and a few worked examples
# so the small model can calibrate, but NOT the reference rule's numeric
# thresholds, that would collapse the SLM into the rule and void the comparison.
SYSTEM_DISAMBIG = (
    "You are the disambiguation check at a road junction. A neighbour has "
    "reported an emergency or incident and you must decide if it is REAL (act on "
    "it) or FAKE or FAULTY (ignore it). Weigh ALL the evidence together, do not "
    "default to one answer.\n"
    "More likely REAL: an independent junction also saw it, or this junction saw "
    "it directly; the reported counts are physically plausible; the anomaly "
    "persisted over several windows; neighbours agree.\n"
    "More likely FAKE or FAULTY: no independent source saw it; the reported "
    "flow is implausibly high for the road (far more than it can physically "
    "carry); it did not persist; neighbours disagree.\n"
    "A direct local sighting is strong evidence it is real. Zero independent "
    "corroboration with implausible counts is strong evidence it is fake. On "
    "mixed or conflicting evidence, judge on balance. "
    'Reply with ONLY JSON {"decision": "real"} or {"decision": "fake"}.'
)

# Worked examples (hand-crafted, NOT drawn from the evaluation dataset, so no
# leakage). They teach the judgment pattern, not the rule's thresholds.
_DISAMBIG_FEWSHOT = [
    ("Event type: emergency_claim. Independent junctions that also saw it: 2. "
     "This junction saw it directly: no. Conservation residual (nonneg; higher "
     "= more anomalous): 0.40. Windows the anomaly persisted: 3. Fraction of "
     "neighbours whose reports agree: 0.90. Reported severity: 0.80.", "real"),
    ("Event type: emergency_claim. Independent junctions that also saw it: 0. "
     "This junction saw it directly: no. Conservation residual (nonneg; higher "
     "= more anomalous): 1.80. Windows the anomaly persisted: 1. Fraction of "
     "neighbours whose reports agree: 0.20. Reported severity: 0.90.", "fake"),
    ("Event type: incident_claim. Independent junctions that also saw it: 0. "
     "This junction saw it directly: yes. Conservation residual (nonneg; higher "
     "= more anomalous): 0.60. Windows the anomaly persisted: 4. Fraction of "
     "neighbours whose reports agree: 0.50. Reported severity: 0.70.", "real"),
]


# Job-A output SHAPE (§3 / §6 CoT row) — the INTERNAL, non-evidential, counsel-
# gated reasoning note. The SHAPE is pinned now; the citation-faithful CONTENT
# (statute-grounded reasoning + candidate_origin selection over a retrieved
# corpus) is DEFERRED to the §9/Job-A build (Job-A CONTENT deferred). This note
# NEVER enters the evidence pack and is NEVER a determination of legal fault;
# `reasoning` is validated against `cited_rules` and never trusted on its face.
JOB_A_NOTE_SHAPE = {
    "candidate_origin": "str — an ORIGIN label (attacker-key/…/unknown); names a KEY, never a person",
    "cited_rules": "list[str] — statute/rule ids the reasoning is grounded in (validated against the retrieved corpus)",
    "reasoning": "str, <=120 words — rationale; VALIDATED against cited_rules, never trusted on its face",
    "fault_weight_note": "str — a qualitative, NON-numeric note; not a confidence or probability",
}
# Citation-faithful CONTENT is now BUILT (`reason_note` below, wired to the
# controller-mediated `legal_corpus` retrieval + the `experiment_jobA` runner). The
# note remains INTERNAL / non-evidential / counsel-gated and never enters the pack.
JOB_A_CONTENT_DEFERRED = False
JOB_A_CONTENT_BUILT = True

# Job-A system prompt (§3). The model writes the INTERNAL, non-evidential note over
# the retrieved statute text. GROUNDING is explicit: it must cite ONLY the citation
# ids it is given (a cited id NOT among them is a hallucination, §3 / Dahl 2024). It
# never sees the ground-truth label; it must reason about which law governs.
SYSTEM_JOB_A = (
    "You are counsel's INTERNAL legal-reasoning assistant for a signalised-junction "
    "incident on Euston Road (A501), London. You are given (1) a set of RETRIEVED "
    "UK traffic-law rules, each with a citation id, and (2) the facts of a flagged "
    "event. Write a SHORT internal note identifying which rules govern fault for "
    "this situation.\n"
    "STRICT GROUNDING: cite ONLY the citation ids from the RETRIEVED RULES list "
    "verbatim. NEVER invent, guess, or cite an id that is not in that list. If no "
    "provided rule applies, return an empty cited_rules list. Cite every provided "
    "rule that genuinely applies; do NOT cite a rule merely because it was "
    "retrieved.\n"
    "The note is INTERNAL and NON-EVIDENTIAL: it is not a determination of fault. "
    "candidate_origin names a KEY or situation, never a person.\n"
    'Reply with ONLY a JSON object, no prose around it: '
    '{"candidate_origin": "<label>", "cited_rules": ["<id>", ...], '
    '"reasoning": "<=120 words", "fault_weight_note": "<qualitative, non-numeric>"}'
)


# Job-A CAG system prompt (§2/§3 amended). WHOLE-CORPUS-IN-CONTEXT: the model is
# given the COMPLETE policy set (all 18 rules, no retrieval) — Lee's guidance that
# policies are placed explicitly in front of the model, not guessed. REASON-THEN-
# CLASSIFY: the model first emits a per-rule applicability JUDGMENT for EVERY rule
# (the reasoning stage, each `why` grounded in that rule's "applies when"); the
# CONTROLLER then DERIVES the cited set from the judgments (classification stage).
# The model's own free-text cited_rules is kept ONLY as a consistency-check flag and
# is NEVER the scored output.
SYSTEM_JOB_A_CAG = (
    "You are counsel's INTERNAL legal-reasoning assistant for a signalised-junction "
    "incident on Euston Road (A501), London. You are given (1) the COMPLETE set of UK "
    "traffic-law rules that make up the policy corpus, each with a citation id, and "
    "(2) the facts of a flagged event.\n"
    "REASON THEN CLASSIFY. First, for EVERY rule in the corpus, judge whether it "
    "applies to THIS event: output one object per rule {\"id\": \"<citation id, "
    "copied verbatim>\", \"applies\": \"yes\" or \"no\", \"why\": \"<=20 words, "
    "grounded in that rule's 'applies when'\"}. Judge every rule; do not skip any.\n"
    "STRICT GROUNDING: use ONLY the citation ids from the corpus verbatim. NEVER "
    "invent, guess, abbreviate, or misspell an id. candidate_origin names a KEY or "
    "situation, never a person.\n"
    "The note is INTERNAL and NON-EVIDENTIAL: it is not a determination of fault.\n"
    'Reply with ONLY a JSON object, no prose around it: '
    '{"rule_judgments": [{"id": "<id>", "applies": "yes|no", "why": "<=20 words"}, ...], '
    '"candidate_origin": "<label>", "cited_rules": ["<id>", ...], '
    '"reasoning": "<=120 words", "fault_weight_note": "<qualitative, non-numeric>"}'
)


def _service_endpoint() -> str | None:
    """Parse `foundry service status` for the running OpenAI-compatible endpoint."""
    import subprocess

    try:
        out = subprocess.run(["foundry", "service", "status"], capture_output=True,
                             text=True, timeout=15).stdout
        m = re.search(r"127\.0\.0\.1:(\d+)", out)
        return f"http://127.0.0.1:{m.group(1)}/v1" if m else None
    except Exception:
        return None


def _first_model(base: str) -> str | None:
    """Return the first model id the local service is currently serving."""
    import json
    import urllib.request

    try:
        with urllib.request.urlopen(f"{base}/models", timeout=10) as resp:
            return json.load(resp)["data"][0]["id"]
    except Exception:
        return None


def discover_endpoint(alias: str = "phi-4-mini") -> tuple[str, str]:
    """Resolve (base_url, model_id): env vars -> `foundry service status` -> defaults.

    The Foundry Local port changes when the service restarts, so we auto-detect it.
    Env vars FOUNDRY_LOCAL_ENDPOINT / FOUNDRY_LOCAL_MODEL override discovery.
    """
    base = (os.environ.get("FOUNDRY_LOCAL_ENDPOINT")
            or _service_endpoint() or "http://127.0.0.1:5273/v1")
    model = os.environ.get("FOUNDRY_LOCAL_MODEL") or _first_model(base) or alias
    return base, model


class SLMAgent:
    """One SLM controller. `choose_phase` returns a validated phase index or None."""

    def __init__(self, alias: str = "phi-4-mini", base_url: str | None = None,
                 model: str | None = None, max_tokens: int = 256):
        if base_url is None or model is None:
            d_base, d_model = discover_endpoint(alias)
            base_url, model = base_url or d_base, model or d_model
        self.model = model
        self.max_tokens = max_tokens
        # Qwen3 models default to a <think> reasoning trace that costs ~7 s/decision
        # (measured) -- far too slow for the ~10 s real-time control interval, and it
        # buries the JSON. Qwen3's documented soft switch `/no_think` disables it,
        # dropping latency to ~0.3 s with a clean JSON reply (measured). Auto-append
        # it for qwen3 only; the suffix is empty for every other model, so their
        # prompts are byte-for-byte unchanged.
        self.think_suffix = " /no_think" if "qwen3" in (model or "").lower() else ""
        self.client = OpenAI(base_url=base_url,
                             api_key=os.environ.get("FOUNDRY_LOCAL_API_KEY", "local"))

    def choose_phase(self, junction_id: str, num_phases: int,
                     halting_per_phase: list[int],
                     neighbor_note: str = "",
                     phase_context: list | None = None) -> int | None:
        """Ask the SLM which green phase to serve. None on any failure (-> shield).

        ``neighbor_note`` (optional) is a concise coordination hint from adjacent
        junctions (e.g. "Neighbours about to send ~7 vehicles toward you."). When
        non-empty it is appended to the user prompt so cross-junction coordination
        can influence the choice; default "" leaves the prompt identical to before.

        ``phase_context`` (optional) switches to the SOTA DELAY-AWARE myopic mode: a
        list with one dict per phase ``{"queue": int, "waiting": float, "current":
        bool}`` (own-junction info only). When given, the richer waiting-time +
        current-phase state is sent under ``SYSTEM_DELAY_AWARE`` so the model can beat
        MaxPressure on DELAY (waiting-time priority + switching hysteresis). Default
        None leaves the prompt byte-for-byte identical to the queue-only behaviour.
        """
        if phase_context is not None:
            return self._choose_phase_delay_aware(junction_id, num_phases,
                                                  phase_context)
        per_phase = ", ".join(f"phase {i} = {n}" for i, n in enumerate(halting_per_phase))
        user = (f"Junction {junction_id}. Waiting vehicles per phase: {per_phase}. "
                'Which phase should get green now? Reply ONLY {"phase": <index>}.')
        if neighbor_note:
            user = f"{user} {neighbor_note}"
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0, max_tokens=self.max_tokens,
                messages=[{"role": "system", "content": SYSTEM + self.think_suffix},
                          {"role": "user", "content": user}],
            )
            return self._parse(resp.choices[0].message.content or "", num_phases)
        except Exception:
            return None

    def _choose_phase_delay_aware(self, junction_id: str, num_phases: int,
                                  phase_context: list) -> int | None:
        """Delay-aware myopic decision (SYSTEM_DELAY_AWARE). Builds a per-phase state
        line with queue + accumulated waiting time (s) + current-phase marker. None
        on failure."""
        parts = []
        for i, ctx in enumerate(phase_context):
            q = int(ctx.get("queue", 0))
            w = float(ctx.get("waiting", 0.0))
            cur = " (CURRENT)" if ctx.get("current") else ""
            parts.append(f"phase {i}: queued={q}, wait={w:.0f}s{cur}")
        user = (f"Junction {junction_id}. " + "; ".join(parts)
                + '. Which phase should get green now? Reply ONLY {"phase": <index>}.')
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0, max_tokens=self.max_tokens,
                messages=[{"role": "system",
                           "content": SYSTEM_DELAY_AWARE + self.think_suffix},
                          {"role": "user", "content": user}],
            )
            return self._parse(resp.choices[0].message.content or "", num_phases)
        except Exception:
            return None

    @staticmethod
    def _parse(text: str, num_phases: int) -> int | None:
        # Prefer a phase index INSIDE a JSON object (the requested reply shape) so
        # the emitted JSON wins over any leading prose digit the model may now add
        # under the larger max_tokens budget; then a keyed "phase": N; then a bare
        # int. This keeps parsing robust after max_tokens was raised for Job A.
        braced = re.search(r'\{[^{}]*"?phase"?\s*[:=]\s*(\d+)[^{}]*\}', text)
        match = (braced or re.search(r'"?phase"?\s*[:=]\s*(\d+)', text)
                 or re.search(r"\b(\d+)\b", text))
        if not match:
            return None
        phase = int(match.group(1))
        return phase if 0 <= phase < num_phases else None

    def classify_case(self, case) -> str | None:
        """Disambiguate a flagged ambiguous case (Experiment 1).

        ``case`` is any object exposing the ``ambiguous_decision.FlaggedCase``
        fields. Returns ``"escalate_real"`` or ``"reject"`` (the module's Decision
        values), or None on any parse/connection failure so the caller can treat
        an unusable answer conservatively (reject = no preemption). Temperature 0.
        """
        user = (self._case_evidence(case) + ' Is this event real? Reply ONLY '
                '{"decision": "real"} or {"decision": "fake"}.')
        messages = [{"role": "system", "content": SYSTEM_DISAMBIG}]
        for ex_user, ex_dec in _DISAMBIG_FEWSHOT:  # worked examples for calibration
            messages.append({"role": "user", "content": ex_user
                             + ' Reply ONLY {"decision": "real"} or {"decision": "fake"}.'})
            messages.append({"role": "assistant", "content": '{"decision": "%s"}' % ex_dec})
        messages.append({"role": "user", "content": user})
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0, max_tokens=self.max_tokens,
                messages=messages,
            )
            return self._parse_decision(resp.choices[0].message.content or "")
        except Exception:
            return None

    @staticmethod
    def _case_evidence(case) -> str:
        """Format a FlaggedCase as neutral evidence text (shared by few-shot and
        the live query so the framing is identical)."""
        return (
            f"Event type: {case.event_type}. "
            f"Independent junctions that also saw it: {case.corroboration_count}. "
            f"This junction saw it directly: {'yes' if case.local_sensing else 'no'}. "
            f"Conservation residual (nonneg; higher = more anomalous): "
            f"{case.residual:.2f}. "
            f"Windows the anomaly persisted: {case.persistence}. "
            f"Fraction of neighbours whose reports agree: {case.neighbour_agreement:.2f}. "
            f"Reported severity: {case.severity:.2f}."
        )

    def reason_note(self, case, retrieved_rules, note_max_tokens: int = 768):
        """Job A (§3): the citation-faithful INTERNAL legal-reasoning note.

        ``case`` exposes the ``FlaggedCase`` fields (event facts). ``retrieved_rules``
        is the controller-mediated candidate list (``legal_corpus.LawRule`` objects,
        or any object with ``.statute_ref``/``.applies_when``/``.text``); the model
        may cite ONLY from it. Returns the note dict matching ``JOB_A_NOTE_SHAPE`` or
        ``None`` on ANY failure (connection / parse / shape) so the caller falls back
        to NO note. Temperature 0. The note is NON-EVIDENTIAL and counsel-gated; it
        never enters the evidence pack.
        """
        rules_block = self._format_retrieved_rules(retrieved_rules)
        if not rules_block:
            return None  # no corpus retrieved -> no grounded note (fail-loud upstream)
        user = (
            "RETRIEVED RULES (cite ONLY these ids):\n" + rules_block
            + "\n\nFLAGGED EVENT FACTS:\n" + self._case_evidence(case)
            + "\n\nWrite the internal note now as the specified JSON object."
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0, max_tokens=note_max_tokens,
                timeout=90,  # bound each call: a stalled generation -> None (a failure), never a hang
                messages=[{"role": "system", "content": SYSTEM_JOB_A},
                          {"role": "user", "content": user}],
            )
            return self._parse_note(resp.choices[0].message.content or "")
        except Exception:
            return None

    def reason_note_cag(self, case, corpus_rules, note_max_tokens: int = 1536):
        """Job A CAG reason-then-classify (§2/§3 amended): the FAIR re-test.

        ``corpus_rules`` is the WHOLE corpus (``corpus.all_rules()`` — all 18 rules,
        no retrieval). The model emits a per-rule applicability judgment for EVERY
        rule (reasoning stage). The CONTROLLER then DERIVES ``cited_rules`` as the
        in-corpus ids judged ``applies == "yes"`` (classification stage); an id judged
        applicable but NOT in the corpus is a FABRICATION — logged and DROPPED, never
        scored. The model's own free-text ``cited_rules`` is retained only as a
        consistency-check flag. Returns the note dict or ``None`` on ANY failure
        (connection / parse / shape). Temperature 0; call bounded to 90 s. The note is
        NON-EVIDENTIAL and counsel-gated; it never enters the evidence pack.

        note_max_tokens defaults higher than ``reason_note`` because the per-rule
        judgment array over 18 rules is a larger emission than a bare cited list.
        """
        rules_block = self._format_retrieved_rules(corpus_rules)
        if not rules_block:
            return None  # empty corpus -> no grounded note (fail-loud upstream)
        in_corpus = []
        for r in corpus_rules:
            ref = getattr(r, "statute_ref", None)
            if ref is None and isinstance(r, dict):
                ref = r.get("statute_ref")
            if ref:
                in_corpus.append(ref)
        user = (
            "COMPLETE RULE CORPUS (cite ONLY these ids, verbatim):\n" + rules_block
            + "\n\nFLAGGED EVENT FACTS:\n" + self._case_evidence(case)
            + "\n\nJudge EVERY rule, then write the internal note as the specified "
              "JSON object."
        )
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0, max_tokens=note_max_tokens,
                timeout=90,  # bound each call: a stalled generation -> None, never a hang
                messages=[{"role": "system", "content": SYSTEM_JOB_A_CAG},
                          {"role": "user", "content": user}],
            )
            return self._derive_cited_from_judgments(
                resp.choices[0].message.content or "", frozenset(in_corpus))
        except Exception:
            return None

    @staticmethod
    def _derive_cited_from_judgments(text: str, in_corpus: frozenset):
        """Parse a CAG reason-then-classify note; the CONTROLLER derives the cited set.

        The SCORED ``cited_rules`` = the in-corpus ids judged ``applies == "yes"``
        (dedupe, order-stable). Ids judged applicable but absent from ``in_corpus`` are
        FABRICATIONS — collected in ``fabrication_attempts`` and DROPPED (never scored).
        The model's own free-text ``cited_rules`` is parsed separately and kept only as
        ``model_cited_rules`` + a ``cited_consistent`` flag. Returns None if the object
        is absent/unparseable or has no ``rule_judgments`` list.
        """
        obj = SLMAgent._extract_json_object(text)
        if obj is None:
            return None
        judgments_raw = obj.get("rule_judgments")
        if not isinstance(judgments_raw, list):
            return None  # reason-then-classify REQUIRES the per-rule judgment array
        judgments: list = []
        cited: list = []
        fabrication_attempts: list = []
        for j in judgments_raw:
            if not isinstance(j, dict):
                continue
            jid = j.get("id")
            jid = jid.strip() if isinstance(jid, str) else ""
            applies_raw = j.get("applies")
            if isinstance(applies_raw, bool):
                applies = applies_raw
            elif isinstance(applies_raw, str):
                applies = applies_raw.strip().lower() in ("yes", "true", "applies", "y")
            else:
                applies = False
            why = j.get("why")
            why = why.strip() if isinstance(why, str) else ""
            words = why.split()
            if len(words) > 20:
                why = " ".join(words[:20])
            judgments.append({"id": jid, "applies": bool(applies), "why": why})
            if applies and jid:
                if jid in in_corpus:
                    if jid not in cited:
                        cited.append(jid)
                elif jid not in fabrication_attempts:
                    fabrication_attempts.append(jid)  # applicable but not in corpus -> drop
        # the model's OWN free-text cited list — a CONSISTENCY FLAG only, never scored.
        model_cited: list = []
        raw_model = obj.get("cited_rules")
        if isinstance(raw_model, str) and raw_model.strip():
            raw_model = [raw_model]
        if isinstance(raw_model, list):
            for c in raw_model:
                if isinstance(c, str) and c.strip() and c.strip() not in model_cited:
                    model_cited.append(c.strip())
        reasoning = obj.get("reasoning")
        reasoning = reasoning.strip() if isinstance(reasoning, str) else ""
        rwords = reasoning.split()
        if len(rwords) > 120:
            reasoning = " ".join(rwords[:120])
        origin = obj.get("candidate_origin")
        fwn = obj.get("fault_weight_note")
        return {
            "rule_judgments": judgments,
            "candidate_origin": origin.strip() if isinstance(origin, str) else "unknown",
            "cited_rules": cited,                       # CONTROLLER-DERIVED = the scored output
            "model_cited_rules": model_cited,           # consistency-check flag only
            "cited_consistent": set(model_cited) == set(cited),
            "fabrication_attempts": fabrication_attempts,  # judged-applicable but out-of-corpus, dropped
            "reasoning": reasoning,
            "fault_weight_note": fwn.strip() if isinstance(fwn, str) else "",
        }

    @staticmethod
    def _format_retrieved_rules(retrieved_rules) -> str:
        """Render the candidate rules as a numbered, citation-id-labelled block."""
        lines = []
        for i, r in enumerate(retrieved_rules or []):
            ref = getattr(r, "statute_ref", None)
            if ref is None and isinstance(r, dict):
                ref = r.get("statute_ref")
            if not ref:
                continue
            applies = getattr(r, "applies_when", "") or (
                r.get("applies_when", "") if isinstance(r, dict) else "")
            text = getattr(r, "text", "") or (
                r.get("text", "") if isinstance(r, dict) else "")
            lines.append(f'{i + 1}. citation id: "{ref}"\n'
                         f'   applies when: {applies}\n'
                         f'   rule: {text}')
        return "\n".join(lines)

    @staticmethod
    def _parse_note(text: str):
        """Strict-ish JSON parse of a Job-A note. None on any failure.

        Extracts the first balanced JSON object, validates the four required keys,
        and coerces ``cited_rules`` to a list of non-empty strings (deduped, order
        preserved). ``reasoning`` is clamped to 120 words. Returns None if the object
        is absent, unparseable, or missing ``cited_rules``.
        """
        import json

        obj = SLMAgent._extract_json_object(text)
        if obj is None:
            return None
        raw_cited = obj.get("cited_rules")
        if not isinstance(raw_cited, list):
            # a single string is a tolerable near-miss; anything else is a failure.
            if isinstance(raw_cited, str) and raw_cited.strip():
                raw_cited = [raw_cited]
            else:
                return None
        cited: list = []
        for c in raw_cited:
            if isinstance(c, str) and c.strip() and c.strip() not in cited:
                cited.append(c.strip())
        reasoning = obj.get("reasoning")
        reasoning = reasoning.strip() if isinstance(reasoning, str) else ""
        words = reasoning.split()
        if len(words) > 120:
            reasoning = " ".join(words[:120])
        origin = obj.get("candidate_origin")
        fwn = obj.get("fault_weight_note")
        return {
            "candidate_origin": origin.strip() if isinstance(origin, str) else "unknown",
            "cited_rules": cited,
            "reasoning": reasoning,
            "fault_weight_note": fwn.strip() if isinstance(fwn, str) else "",
        }

    @staticmethod
    def _extract_json_object(text: str):
        """Return the first balanced top-level ``{...}`` parsed as JSON, or None."""
        import json

        if not text:
            return None
        start = text.find("{")
        while start != -1:
            depth = 0
            in_str = False
            esc = False
            for i in range(start, len(text)):
                ch = text[i]
                if in_str:
                    if esc:
                        esc = False
                    elif ch == "\\":
                        esc = True
                    elif ch == '"':
                        in_str = False
                    continue
                if ch == '"':
                    in_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        try:
                            obj = json.loads(text[start:i + 1])
                        except (ValueError, TypeError):
                            break
                        return obj if isinstance(obj, dict) else None
            start = text.find("{", start + 1)
        return None

    @staticmethod
    def _parse_decision(text: str) -> str | None:
        """Map the model's reply to a Decision string, or None if unparseable."""
        t = text.lower()
        # Prefer a decision INSIDE a JSON object (the requested reply shape) so the
        # emitted JSON wins over any surrounding prose under the larger max_tokens
        # budget; then a keyed decision anywhere.
        braced = re.search(
            r'\{[^{}]*"?decision"?\s*[:=]\s*"?(real|fake|faulty|reject|escalate|true|false)', t)
        m = braced or re.search(
            r'"?decision"?\s*[:=]\s*"?(real|fake|faulty|reject|escalate|true|false)', t)
        tok = m.group(1) if m else None
        if tok is None:
            has_real = ("real" in t) or ("true" in t)
            has_fake = ("fake" in t) or ("faulty" in t) or ("reject" in t) or ("false" in t)
            if has_real and not has_fake:
                tok = "real"
            elif has_fake and not has_real:
                tok = "fake"
        if tok in ("real", "escalate", "true"):
            return "escalate_real"
        if tok in ("fake", "faulty", "reject", "false"):
            return "reject"
        return None


# --------------------------------------------------------------------------- #
# Shared fail-loud probe (MASTER-SPEC §10 golden rule + D3 + §11 step 6).
# --------------------------------------------------------------------------- #
def probe_foundry_determinism(reps: int = 3):
    """Prove the REAL SLM's precondition BEFORE any real-model gate runs.

    Two-dimension precondition, per the §10 golden rule ("a gate that cannot
    prove its precondition [real model answered] must SKIP-with-a-recorded-skip
    or ABORT, never emit a green result") and D3 ("`real_model=true` guard
    ABORTS/SKIPS-with-record, never a null"):

      1. REACHABILITY -- construct an ``SLMAgent`` and make a cheap live call
         (``client.models.list()``); a dead/absent Foundry Local fails here.
      2. TEMP-0 DETERMINISM -- call a canned decision (phase 0 has all the
         waiting vehicles, phase 1 has none) ``reps`` times. If any call returns
         None the model did not answer a well-formed decision; if the answers
         are not all identical the model is non-deterministic at temp 0. Either
         way the real-model precondition is UNPROVEN.

    SKIP-not-ABORT: this NEVER raises. On any failure it returns
    ``(None, reason)`` so the caller records the skip and returns cleanly,
    instead of letting ``choose_phase`` silently return None every call and the
    sweep complete as a DEGRADED all-shield result masquerading as a real-model
    measurement. On success it returns ``(agent, None)`` -- the SAME constructed
    agent, so the caller reuses it (no double-construct, no second endpoint
    discovery).
    """
    # reps < 2 cannot detect non-determinism (len(set) is trivially 1), which
    # would SILENTLY vacate dimension 2 -> refuse it rather than degrade to a
    # reachability-only probe a future caller might not notice.
    if reps < 2:
        return None, "determinism probe needs reps >= 2 (reps<2 cannot detect non-determinism)"
    # --- dimension 1: construct + reachability ----------------------------- #
    try:
        agent = SLMAgent()
        agent.client.models.list()  # cheap real call: dead service fails HERE
    except Exception as exc:  # noqa: BLE001 -- SKIP-not-abort: never raise
        return None, (f"Foundry Local not reachable ({type(exc).__name__}). "
                      "Start it: `foundry service start` and load phi-4-mini.")

    # --- dimension 2: temp-0 determinism on a canned decision -------------- #
    seen: list[int] = []
    for _ in range(reps):
        try:
            phase = agent.choose_phase("PROBE", 2, [8, 0])
        except Exception as exc:  # noqa: BLE001 -- SKIP-not-abort: never raise
            return None, (f"probe decision raised {type(exc).__name__}: {exc}")
        if phase is None:
            return None, "model did not answer a well-formed decision"
        seen.append(phase)
    if len(set(seen)) != 1:
        return None, (f"non-deterministic at temp 0 over {reps} reps: "
                      f"{sorted(set(seen))}")
    return agent, None
