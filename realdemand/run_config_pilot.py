"""Pilot: coordination and prediction configs on real Euston demand, same 6 cells as the
downstream pilot.

ARM=claude  -> Claude Sonnet 5.5 via the Claude Code CLI (subscription), parallel cells.
ARM=student -> qwen3-0.6b v2 generalist (local Foundry id "qwen3-0.6b-ft1", trained on all four
               formats incl. coordination/prediction; v1 is sota-only so it is not used here),
               sequential on the GPU.

Both use exactly what SLMAgent sends on these configs: the queue-only SYSTEM prompt and
build_myopic_user(junction, halting, neighbor_note), where the CoordinatedController's note
carries incoming-from-neighbours (coordination) plus approaching vehicles (prediction).
TimingAgent(forward_note=True) as in the dissertation's coordination/prediction arms.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import run_scoot_sweep_claude as base  # REPO path + chdir; model defaults to Sonnet 5.5
from experiment_traffic import TimingAgent, run_arm  # noqa: E402
from slm_agent import SYSTEM, SLMAgent, build_myopic_user, discover_endpoint  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ARM = os.environ.get("ARM", "claude")
TAG = {"claude": "sonnet", "student": "qwenv2"}[ARM]
OUT = os.path.join(HERE, "results", f"scoot_config_pilot_{TAG}.json")
LOG = os.path.join(HERE, "logs", f"scoot_config_pilot_{TAG}.log")
REPLIES = os.path.join(HERE, "results", "claude_replies", f"scoot_config_pilot_{TAG}")
CELLS = ["2026-05-12|17", "2026-05-12|18", "2026-05-14|08", "2026-05-13|11",
         "2026-05-13|21", "2026-05-12|22"]
CONFIGS = ["coordination", "prediction"]
STUDENT_ID = "qwen3-0.6b-ft1"  # local cache name holding v2 (see ft-model-provenance)
WORKERS = int(os.environ.get("PILOT_WORKERS", "3"))


class ClaudeNoteAgent(base.ClaudeCLIAgent):
    """Mirror of SLMAgent.choose_phase's note path, answered by Claude."""

    def _ask(self, user: str) -> str:
        cmd = [base.CLAUDE, "-p", "--model", base.MODEL, "--system-prompt", SYSTEM,
               "--tools", "", "--no-session-persistence", "--strict-mcp-config",
               "--setting-sources", "", "--effort", "low", "--output-format", "json"]
        last = ""
        for attempt in range(base.RETRIES):
            try:
                r = subprocess.run(cmd, input=user, capture_output=True, text=True,
                                   encoding="utf-8", timeout=180)
                d = json.loads(r.stdout)
                if not d.get("is_error") and isinstance(d.get("result"), str):
                    return d["result"]
                last = str(d.get("result") or d)[:300]
            except Exception as e:  # noqa: BLE001
                last = f"{type(e).__name__}: {e}"[:300]
            time.sleep(min(30 * 2 ** attempt, 600))
        raise base.CellAbort(f"claude call failed {base.RETRIES}x: {last}")

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = "", phase_context=None):
        if phase_context is not None:
            raise base.CellAbort("note configs must not send phase_context")
        user = build_myopic_user(junction_id, halting_per_phase, neighbor_note)
        t0 = time.time()
        text = self._ask(user)
        phase = SLMAgent._parse(text, num_phases)
        with open(self.reply_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"user": user, "reply": text, "phase": phase,
                                 "s": round(time.time() - t0, 2)}) + "\n")
        return phase


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def summarise(cfg, key, cell, r, t0):
    m, ds = r["metrics"], r.get("decision_stats", {}) or {}
    return {"arm": f"{cfg}:{TAG}", "config": cfg, "day": cell["day"], "hour": cell["hour"],
            "frac": cell["frac"], "delay_s": round(m["mean_network_delay_s"], 2),
            "completed": m["completed"], "departed": m["departed"],
            "teleports": m["teleports"], "decision_stats": ds,
            "runtime_s": round(time.time() - t0, 1)}


def run_claude_cell(cfg: str, key: str, cell: dict):
    os.chdir(base.REPO)
    reply_log = os.path.join(REPLIES, f"{cfg}_{key.replace('|', '_')}.jsonl")
    if os.path.exists(reply_log):
        os.remove(reply_log)
    t0 = time.time()
    try:
        r = run_arm(f"{TAG}{cfg}_{key.replace('|', '_')}",
                    TimingAgent(ClaudeNoteAgent(reply_log), forward_note=True),
                    seed=1, end=base.END, config=cfg, net=base.NET, routes=base.routes_for(cell))
    except Exception as e:  # noqa: BLE001
        return cfg, key, {"arm": f"{cfg}:{TAG}", "error": f"{type(e).__name__}: {e}"}
    return cfg, key, summarise(cfg, key, cell, r, t0)


def save(res):
    tmp = OUT + ".tmp"
    json.dump(res, open(tmp, "w", encoding="utf-8"), indent=2)
    os.replace(tmp, OUT)


def main() -> int:
    os.makedirs(REPLIES, exist_ok=True)
    mp = {k.split("|", 1)[1]: c for k, c in base.SWEEP["cells"].items() if k.startswith("maxpressure|")}
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"meta": {}, "cells": {}}
    res["meta"] = {"arm": TAG, "configs": CONFIGS, "cells": CELLS, "seed": 1, "end": base.END,
                   "prompt": "SYSTEM (queue-only) + build_myopic_user(+neighbour note)",
                   "model": base.MODEL if ARM == "claude" else STUDENT_ID}
    todo = [(c, k) for c in CONFIGS for k in CELLS
            if "delay_s" not in res["cells"].get(f"{c}|{k}", {})]
    log(f"start {TAG}: {len(todo)} cells")
    if ARM == "claude":
        with ProcessPoolExecutor(max_workers=WORKERS, max_tasks_per_child=1) as ex:
            for f in as_completed([ex.submit(run_claude_cell, c, k, mp[k]) for c, k in todo]):
                cfg, key, cell = f.result()
                res["cells"][f"{cfg}|{key}"] = cell
                log(f"{cfg} {key} " + (f"ERROR {cell['error']}" if "error" in cell else
                                       f"delay={cell['delay_s']} tp={cell['teleports']} ({cell['runtime_s']}s)"))
                save(res)
    else:
        r = subprocess.run(["foundry", "model", "load", STUDENT_ID], capture_output=True, text=True, timeout=600)
        log(f"load {STUDENT_ID}: {(r.stdout + r.stderr).strip().splitlines()[-1:]}")
        url, _ = discover_endpoint()
        agent = SLMAgent(base_url=url, model=STUDENT_ID)
        if agent.choose_phase("PROBE", 2, [8, 0]) is None:
            log(f"ABORT: {STUDENT_ID} gave no valid phase on probe")
            return 1
        for cfg, key in todo:
            cell, t0 = mp[key], time.time()
            try:
                rr = run_arm(f"{TAG}{cfg}_{key.replace('|', '_')}", TimingAgent(agent, forward_note=True),
                             seed=1, end=base.END, config=cfg, net=base.NET, routes=base.routes_for(cell))
                out = summarise(cfg, key, cell, rr, t0)
                log(f"{cfg} {key} delay={out['delay_s']} tp={out['teleports']} ({out['runtime_s']}s)")
            except Exception as e:  # noqa: BLE001
                out = {"arm": f"{cfg}:{TAG}", "error": f"{type(e).__name__}: {e}"}
                log(f"{cfg} {key} ERROR {out['error']}")
            res["cells"][f"{cfg}|{key}"] = out
            save(res)
    log(f"DONE cells={sum('delay_s' in v for v in res['cells'].values())}/{len(CONFIGS) * len(CELLS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
