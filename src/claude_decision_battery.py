"""Cross-model junction-decision battery: score frontier CLOUD models (Claude Haiku/Sonnet/Opus,
run via in-session subagents -- no API key in this env) against the local on-device SLMs on
IDENTICAL junction states sampled from the real scenarios. Open-loop by necessity (a subagent
can't be called per-decision inside the SUMO process), but every model chooses on the exact same
inputs in the exact same delay-aware prompt, so it is a fair head-to-head of decision quality.

Pipeline:
  1. sample_states(): run each map with a SamplingAgent that LOGS every (junction, num_phases,
     halting_per_phase, phase_context) the SLM would see and returns None (-> MaxPressure shield
     decides). Pure-CPU SUMO, no SLM/GPU. Records what MaxPressure actually did too. Samples a
     diverse spread per map -> results/decision_states.json.
  2. build_prompt(): the byte-identical delay-aware user prompt slm_agent uses, per state.
  3. local SLM choices: SLMAgent.choose_phase on each state for a few representative local models.
  4. Claude choices: emit results/claude_battery_prompt.json (the states + prompts) for a subagent
     to answer; ingest the subagent's [{id, phase}] back and score.
  5. score(): pairwise agreement + agreement-with-MaxPressure + a delay-aware greedy reference
     (serve the phase with the highest accumulated waiting time -- the myopic delay-optimal move).

DEMAND HONESTY unchanged (§8): descriptive decision-quality comparison, not a live-demand claim.
"""
from __future__ import annotations

import argparse
import json
import os

_SRC = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(_SRC), "results")

from experiment_topology import _topologies  # noqa: E402
from experiment_traffic import run_arm  # noqa: E402


class SamplingAgent:
    """Logs every decision context the SLM would receive, then returns None so the deterministic
    MaxPressure shield actually decides (a realistic, SLM-free trajectory). model attr keeps
    run_arm's controller_model label sane."""

    model = "sampling-probe(null)"

    def __init__(self):
        self.samples = []

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = "", phase_context=None):
        pc = None
        if phase_context is not None:
            pc = [{"queue": int(p.get("queue", 0)), "waiting": float(p.get("waiting", 0.0)),
                   "current": bool(p.get("current", False))} for p in phase_context]
        self.samples.append({"junction": junction_id, "num_phases": int(num_phases),
                             "halting_per_phase": [int(x) for x in halting_per_phase],
                             "phase_context": pc,
                             "neighbor_note": neighbor_note or ""})
        return None


def _diverse(samples, k):
    """Pick k states spread across queue-imbalance (unique halting vectors, spread by total load)."""
    seen, uniq = set(), []
    for s in samples:
        key = tuple(s["halting_per_phase"])
        if key in seen or sum(key) == 0:
            continue
        seen.add(key)
        uniq.append(s)
    uniq.sort(key=lambda s: sum(s["halting_per_phase"]))
    if len(uniq) <= k:
        return uniq
    step = len(uniq) / k
    return [uniq[int(i * step)] for i in range(k)]


def sample_states(per_map=20, end=1200, gate=2, seed=42):
    tops = [t for t in _topologies() if os.path.exists(t["net"]) and os.path.exists(t["routes"])]
    out = []
    sid = 0
    for t in tops:
        agent = SamplingAgent()
        run_arm(f"sample_{t['label']}", agent, seed=seed, end=end, gate=gate,
                config="sota", net=t["net"], routes=t["routes"])
        picked = _diverse(agent.samples, per_map)
        for s in picked:
            out.append({"id": sid, "topology": t["label"], **s})
            sid += 1
        print(f"  {t['label']}: {len(agent.samples)} decisions -> {len(picked)} sampled", flush=True)
    p = os.path.join(RESULTS, "decision_states.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"n": len(out), "per_map": per_map, "seed": seed, "states": out}, fh, indent=2)
    print(f"wrote {len(out)} states -> {p}", flush=True)
    return out


# CANONICALISED (MASTER-SPEC §14.3 step 2, 2026-08-06): the battery now labels/trains on the
# byte-identical LIVE controller prompt from slm_agent (its module-level builders), replacing a
# paraphrased format (queue=/waiting_s=/", CURRENT" + a different system text) that the controller
# never sends. The historical n=80 results (results/decision_battery_full.json et al.) were scored
# under the OLD format and remain valid as their own recorded experiment; every new labeling round
# uses the live format below.
from slm_agent import (SYSTEM_DELAY_AWARE as SYSTEM,  # noqa: E402
                       build_delay_aware_user, build_myopic_user)


def build_prompt(state):
    pc = state.get("phase_context")
    if pc:
        return build_delay_aware_user(state["junction"], pc)
    return build_myopic_user(state["junction"], state["halting_per_phase"])


def greedy_ref(state):
    """Delay-aware myopic reference: serve the phase with the greatest accumulated waiting (fall
    back to longest queue when waiting is unavailable)."""
    pc = state.get("phase_context")
    if pc:
        return max(range(len(pc)), key=lambda i: (pc[i]["waiting"], pc[i]["queue"]))
    h = state["halting_per_phase"]
    return max(range(len(h)), key=lambda i: h[i])


def emit_claude_prompt():
    p = os.path.join(RESULTS, "decision_states.json")
    with open(p, encoding="utf-8") as fh:
        states = json.load(fh)["states"]
    tasks = [{"id": s["id"], "topology": s["topology"], "prompt": build_prompt(s)} for s in states]
    outp = os.path.join(RESULTS, "claude_battery_prompt.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump({"system": SYSTEM, "n": len(tasks), "tasks": tasks}, fh, indent=2)
    print(f"wrote {len(tasks)} decision tasks -> {outp}", flush=True)
    return outp


def score_local(models):
    """Have local SLMs choose on each sampled state (GPU; ~fast, few models x ~80 states)."""
    from slm_agent import SLMAgent, discover_endpoint
    from experiment_frontier import CATALOG
    with open(os.path.join(RESULTS, "decision_states.json"), encoding="utf-8") as fh:
        states = json.load(fh)["states"]
    base, _ = discover_endpoint()
    choices = {}
    for m in models:
        agent = SLMAgent(base_url=base, model=CATALOG.get(m, m))
        picks = {}
        for s in states:
            picks[s["id"]] = agent.choose_phase(s["junction"], s["num_phases"],
                                                s["halting_per_phase"],
                                                phase_context=s.get("phase_context"))
        choices[m] = picks
        n_ok = sum(1 for v in picks.values() if v is not None)
        print(f"  {m}: {n_ok}/{len(states)} well-formed", flush=True)
    outp = os.path.join(RESULTS, "decision_choices_local.json")
    with open(outp, "w", encoding="utf-8") as fh:
        json.dump(choices, fh, indent=2)
    print(f"wrote local choices -> {outp}", flush=True)
    return choices


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Cross-model junction-decision battery.")
    ap.add_argument("--step", choices=["sample", "emit", "local"], required=True)
    ap.add_argument("--per-map", type=int, default=20)
    ap.add_argument("--models", nargs="*", default=["qwen2.5-0.5b", "qwen3-4b", "phi-4-mini"])
    ns = ap.parse_args()
    if ns.step == "sample":
        sample_states(per_map=ns.per_map)
    elif ns.step == "emit":
        emit_claude_prompt()
    elif ns.step == "local":
        score_local(ns.models)
