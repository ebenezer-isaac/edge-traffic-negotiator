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
    "Pick the green phase with the MOST waiting vehicles, to clear the longest queue. "
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
JOB_A_CONTENT_DEFERRED = True  # citation-faithful CONTENT lands in the §9/Job-A phase


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
        self.client = OpenAI(base_url=base_url,
                             api_key=os.environ.get("FOUNDRY_LOCAL_API_KEY", "local"))

    def choose_phase(self, junction_id: str, num_phases: int,
                     halting_per_phase: list[int],
                     neighbor_note: str = "") -> int | None:
        """Ask the SLM which green phase to serve. None on any failure (-> shield).

        ``neighbor_note`` (optional) is a concise coordination hint from adjacent
        junctions (e.g. "Neighbours about to send ~7 vehicles toward you."). When
        non-empty it is appended to the user prompt so cross-junction coordination
        can influence the choice; default "" leaves the prompt identical to before.
        """
        per_phase = ", ".join(f"phase {i} = {n}" for i, n in enumerate(halting_per_phase))
        user = (f"Junction {junction_id}. Waiting vehicles per phase: {per_phase}. "
                'Which phase should get green now? Reply ONLY {"phase": <index>}.')
        if neighbor_note:
            user = f"{user} {neighbor_note}"
        try:
            resp = self.client.chat.completions.create(
                model=self.model, temperature=0, max_tokens=self.max_tokens,
                messages=[{"role": "system", "content": SYSTEM},
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
