"""SLM junction agent — terse phase decision via a local OpenAI-compatible endpoint
(Microsoft Foundry Local serving Phi-4-mini).

Per PROJECT-DECISION-BRIEF.md: emit ONLY a phase index, with NO chain-of-thought.
CoT is unfaithful (lit-review 2.6), so we don't request reasoning; accountability
comes from the signed audit log, not model self-narration. We prompt-and-parse with
strict validation (Foundry Local has no JSON-schema enforcement) and return None on
ANY failure so the caller falls back to the deterministic MaxPressure shield.
"""
from __future__ import annotations

import os
import re

from openai import OpenAI

SYSTEM = (
    "You are a traffic-signal controller for a single junction. "
    "Choose the green phase that best reduces waiting. "
    'Reply with ONLY compact JSON {"phase": <index>} — no words, no explanation.'
)


def discover_endpoint(alias: str = "phi-4-mini") -> tuple[str, str]:
    """Return (base_url, model_id) for the running Foundry Local service.

    Order: explicit env vars -> Foundry Local SDK -> default local port.
    Env override is handy when the SDK/catalog is unavailable but a model is loaded.
    """
    base = os.environ.get("FOUNDRY_LOCAL_ENDPOINT")
    if base:
        return base, os.environ.get("FOUNDRY_LOCAL_MODEL", alias)
    try:
        from foundry_local_sdk import FoundryLocalManager  # type: ignore

        mgr = FoundryLocalManager(alias)
        return mgr.endpoint, mgr.get_model_info(alias).id
    except Exception:
        return "http://127.0.0.1:5273/v1", os.environ.get("FOUNDRY_LOCAL_MODEL", alias)


class SLMAgent:
    """One SLM controller. `choose_phase` returns a validated phase index or None."""

    def __init__(self, alias: str = "phi-4-mini", base_url: str | None = None,
                 model: str | None = None, max_tokens: int = 16):
        if base_url is None or model is None:
            d_base, d_model = discover_endpoint(alias)
            base_url, model = base_url or d_base, model or d_model
        self.model = model
        self.max_tokens = max_tokens
        self.client = OpenAI(base_url=base_url,
                             api_key=os.environ.get("FOUNDRY_LOCAL_API_KEY", "local"))

    def choose_phase(self, junction_id: str, num_phases: int,
                     halting_per_phase: list[int]) -> int | None:
        """Ask the SLM which green phase to serve. None on any failure (-> shield)."""
        user = (f"Junction {junction_id}, phases 0..{num_phases - 1}. "
                f"Halting vehicles each phase would serve: {halting_per_phase}. "
                'Reply ONLY {"phase": N}.')
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
        match = re.search(r'"?phase"?\s*[:=]\s*(\d+)', text) or re.search(r"\b(\d+)\b", text)
        if not match:
            return None
        phase = int(match.group(1))
        return phase if 0 <= phase < num_phases else None
