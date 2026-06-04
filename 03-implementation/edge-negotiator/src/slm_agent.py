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
    "You control one traffic-signal junction. "
    "Pick the green phase with the MOST waiting vehicles, to clear the longest queue. "
    'Reply with ONLY JSON {"phase": <index>} and nothing else.'
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
                 model: str | None = None, max_tokens: int = 16):
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
        match = re.search(r'"?phase"?\s*[:=]\s*(\d+)', text) or re.search(r"\b(\d+)\b", text)
        if not match:
            return None
        phase = int(match.group(1))
        return phase if 0 <= phase < num_phases else None
