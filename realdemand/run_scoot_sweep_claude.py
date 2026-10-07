"""Real-demand Euston sweep: frontier reference arm (Claude Sonnet 5.5) under the sota config.

Identical harness to run_scoot_sweep_sota.py (same 72 demand files, config="sota",
TimingAgent(forward_note=True), same shield + anti-starvation, seed 1, end from scoot_sweep_v2),
but each phase decision is answered by Claude Sonnet 5.5 through the Claude Code CLI in headless
mode (subscription auth, not an API key). Same system prompt (SYSTEM_DELAY_AWARE) and user prompt
(build_delay_aware_user) as the students; no tools, effort=low.

Caveats recorded in meta: cloud model (reference ceiling, not a deployable on-device arm);
not deterministic (no temperature control via the CLI).

A failed call is retried; a call that still fails ABORTS its cell (no silent shield fallback),
so every stored cell is fully Sonnet-decided. Cells run in parallel worker processes.
Resumable; every reply is logged to scoot_sweep_sonnet_replies/<cell>.jsonl.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from concurrent.futures import ProcessPoolExecutor, as_completed

REPO = os.environ.get("EDGE_NEGOTIATOR_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "src"))
os.chdir(REPO)

from calibrate_demand import subsample  # noqa: E402
from experiment_traffic import NullAgent, TimingAgent, run_arm  # noqa: E402
from slm_agent import SYSTEM_DELAY_AWARE, SLMAgent, build_delay_aware_user  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SWEEP = json.load(open(os.path.join(HERE, "results", "scoot_sweep_v2.json"), encoding="utf-8"))
# Model is env-selectable (workers inherit the env); default stays Sonnet 5.5 with its original paths.
MODEL = os.environ.get("CLAUDE_ARM_MODEL", "claude-sonnet-5-5")
TAG = {"claude-sonnet-5-5": "sonnet", "claude-haiku-4-5": "haiku"}[MODEL]
OUT = os.path.join(HERE, "results", f"scoot_sweep_{TAG}.json")
LOG = os.path.join(HERE, "logs", f"scoot_sweep_{TAG}.log")
REPLIES = os.path.join(HERE, "results", "claude_replies", f"sota_{TAG}")
NET = os.path.join(REPO, "sumo", "euston", "euston_spine.net.xml")
BASE = os.path.join(REPO, "sumo", "euston", "base_hourly.rou.xml")
END = SWEEP["meta"]["end"]
ROUTES_DIR = os.path.join(tempfile.gettempdir(), "scoot_sonnet_routes")
# The Claude Code CLI binary. On Windows point CLAUDE_BIN at claude.exe itself (the npm .cmd shim
# re-quotes the multi-line system prompt and breaks it).
CLAUDE = os.environ.get("CLAUDE_BIN") or shutil.which("claude") or "claude"
LABEL = f"sota:{MODEL}"
WORKERS = int(os.environ.get("SONNET_WORKERS", "4"))
RETRIES = 6


class CellAbort(RuntimeError):
    pass


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


class ClaudeCLIAgent:
    """Same choose_phase contract as SLMAgent (sota path), answered by Claude via the CLI."""

    def __init__(self, reply_log: str):
        self.model = MODEL
        self.reply_log = reply_log

    def _ask(self, user: str) -> str:
        cmd = [CLAUDE, "-p", "--model", MODEL, "--system-prompt", SYSTEM_DELAY_AWARE,
               "--tools", "", "--no-session-persistence", "--strict-mcp-config",
               "--setting-sources", "", "--effort", "low", "--output-format", "json"]
        last = ""
        for attempt in range(RETRIES):
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
        raise CellAbort(f"claude call failed {RETRIES}x: {last}")

    def choose_phase(self, junction_id, num_phases, halting_per_phase,
                     neighbor_note: str = "", phase_context=None):
        if phase_context is None:
            raise CellAbort("sota arm expects phase_context")
        user = build_delay_aware_user(junction_id, phase_context)
        t0 = time.time()
        text = self._ask(user)
        phase = SLMAgent._parse(text, num_phases)
        with open(self.reply_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"user": user, "reply": text, "phase": phase,
                                 "s": round(time.time() - t0, 2)}) + "\n")
        return phase


def routes_for(cell) -> str:
    return os.path.join(ROUTES_DIR, f"{cell['day'][-2:]}_{cell['hour']:02d}.rou.xml")


def run_cell(key: str, cell: dict) -> tuple[str, dict]:
    os.chdir(REPO)
    reply_log = os.path.join(REPLIES, key.replace("|", "_") + ".jsonl")
    if os.path.exists(reply_log):
        os.remove(reply_log)  # a cell restarts from scratch
    t0 = time.time()
    try:
        r = run_arm(f"{TAG}_{key.replace('|', '_')}", TimingAgent(ClaudeCLIAgent(reply_log), forward_note=True),
                    seed=1, end=END, config="sota", net=NET, routes=routes_for(cell))
    except Exception as e:  # noqa: BLE001
        return key, {"arm": LABEL, "day": cell["day"], "hour": cell["hour"],
                     "error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc()[-1500:]}
    m, ds = r["metrics"], r.get("decision_stats", {}) or {}
    return key, {"arm": LABEL, "model_id": MODEL, "day": cell["day"], "hour": cell["hour"],
                 "frac": cell["frac"], "delay_s": round(m["mean_network_delay_s"], 2),
                 "completed": m["completed"], "departed": m["departed"],
                 "teleports": m["teleports"], "decision_stats": ds,
                 "runtime_s": round(time.time() - t0, 1)}


def main() -> int:
    os.makedirs(REPLIES, exist_ok=True)
    os.makedirs(ROUTES_DIR, exist_ok=True)
    mp = {k.split("|", 1)[1]: c for k, c in SWEEP["cells"].items() if k.startswith("maxpressure|")}
    for c in mp.values():
        if not os.path.exists(routes_for(c)):
            subsample(BASE, routes_for(c), c["frac"], seed=7)
    for key in ("2026-05-12|06", "2026-05-14|22"):
        r = run_arm(f"{TAG}check_{key.replace('|', '_')}", NullAgent(), seed=1, end=END, net=NET,
                    routes=routes_for(mp[key]))
        got = round(r["metrics"]["mean_network_delay_s"], 2)
        log(f"determinism {key}: stored {mp[key]['delay_s']} reproduced {got}")
        if got != mp[key]["delay_s"]:
            log("ABORT: demand files differ from the original sweep")
            return 1

    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"meta": {}, "cells": {}}
    res["meta"] = {"source": "scoot_sweep_v2.json demand files", "config": "sota", "forward_note": True,
                   "end": END, "seed": 1, "arm": LABEL, "model": MODEL,
                   "transport": "claude code CLI headless (-p), subscription auth, effort=low, no tools",
                   "caveats": ["cloud frontier reference, not on-device / Foundry Local",
                               "not deterministic: no temperature control via the CLI",
                               "a failed call aborts its cell; no shield fallback for transport errors"]}
    todo = [k for k in sorted(mp) if "delay_s" not in res["cells"].get(f"{LABEL}|{k}", {})]
    log(f"start {LABEL}: {len(todo)} cells, {WORKERS} workers")
    done = 0
    with ProcessPoolExecutor(max_workers=WORKERS, max_tasks_per_child=1) as ex:
        futs = [ex.submit(run_cell, k, mp[k]) for k in todo]
        for f in as_completed(futs):
            key, cell = f.result()
            res["cells"][f"{LABEL}|{key}"] = cell
            done += 1
            if "error" in cell:
                log(f"[{done}/{len(todo)}] {key} ERROR {cell['error']}")
            else:
                log(f"[{done}/{len(todo)}] {key} delay={cell['delay_s']} ({cell['runtime_s']}s)")
            tmp = OUT + ".tmp"
            json.dump(res, open(tmp, "w", encoding="utf-8"), indent=2)
            os.replace(tmp, OUT)
    ok = sum("delay_s" in v for v in res["cells"].values())
    log(f"DONE cells={ok}/{len(mp)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
