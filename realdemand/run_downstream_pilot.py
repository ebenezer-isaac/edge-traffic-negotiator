"""Pilot: does giving the decider DOWNSTREAM occupancy (the signal MaxPressure has and the SLM
prompt lacks) improve closed-loop delay on real Euston demand?

Arm: Claude Sonnet 5.5 via the Claude Code CLI (same transport as run_scoot_sweep_sonnet.py),
sota config, plus one extra per-phase field `exit_queued` = vehicles halted on the distinct exit
lanes that phase discharges into (same halting reader MaxPressure's pressure term uses).
Control: the plain Sonnet sota arm on the same cells (scoot_sweep_sonnet.json).
Cells: the 6 hours where the headline 0.6B student lost most to MaxPressure.

The thesis code path is untouched: downstream counts are captured by wrapping
MaxPressureController.green_waiting in this process only (decide() calls it once per phase,
in order, immediately before choose_phase).
"""
from __future__ import annotations

import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import run_scoot_sweep_claude as base  # sets REPO path + chdir; model defaults to Sonnet 5.5
from controllers import MaxPressureController  # noqa: E402
from experiment_traffic import TimingAgent, run_arm  # noqa: E402
from slm_agent import SYSTEM_DELAY_AWARE  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "results", "scoot_downstream_pilot.json")
LOG = os.path.join(HERE, "logs", "scoot_downstream_pilot.log")
REPLIES = os.path.join(HERE, "results", "claude_replies", "scoot_downstream_pilot")
LABEL = "sota+downstream:claude-sonnet-5-5"
CELLS = ["2026-05-12|17", "2026-05-12|18", "2026-05-14|08", "2026-05-13|11",
         "2026-05-13|21", "2026-05-12|22"]
WORKERS = int(os.environ.get("PILOT_WORKERS", "3"))

SYSTEM_DS = SYSTEM_DELAY_AWARE.replace(
    "Reply with ONLY",
    "(4) For each phase you are also given exit_queued: vehicles already stopped on the exit "
    "lanes that phase discharges into. A phase whose exits are blocked cannot move traffic, and "
    "feeding a blocked exit spreads the queue back into the network (gridlock), so discount a "
    "phase with a high exit_queued. Reply with ONLY")
assert SYSTEM_DS != SYSTEM_DELAY_AWARE

_DOWN: list[int] = []
_orig_green_waiting = MaxPressureController.green_waiting


def _green_waiting_with_downstream(self, st, gi):
    if gi == 0:
        _DOWN.clear()
    lanes = {st["out_lanes"][i] for i, ch in enumerate(st["green"][gi])
             if ch in "Gg" and st["out_lanes"][i]}
    _DOWN.append(int(sum(self.c.lane.getLastStepHaltingNumber(l) for l in lanes)))
    return _orig_green_waiting(self, st, gi)


MaxPressureController.green_waiting = _green_waiting_with_downstream


def build_user(junction_id, phase_context) -> str:
    if len(_DOWN) != len(phase_context):
        raise base.CellAbort(f"downstream capture out of sync: {len(_DOWN)} vs {len(phase_context)}")
    parts = []
    for i, ctx in enumerate(phase_context):
        cur = " (CURRENT)" if ctx.get("current") else ""
        parts.append(f"phase {i}: queued={int(ctx.get('queue', 0))}, "
                     f"wait={float(ctx.get('waiting', 0.0)):.0f}s, exit_queued={_DOWN[i]}{cur}")
    return (f"Junction {junction_id}. " + "; ".join(parts)
            + '. Which phase should get green now? Reply ONLY {"phase": <index>}.')


class DownstreamAgent(base.ClaudeCLIAgent):
    def _ask(self, user: str) -> str:
        cmd = [base.CLAUDE, "-p", "--model", base.MODEL, "--system-prompt", SYSTEM_DS,
               "--tools", "", "--no-session-persistence", "--strict-mcp-config",
               "--setting-sources", "", "--effort", "low", "--output-format", "json"]
        last = ""
        for attempt in range(base.RETRIES):
            try:
                import subprocess
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
        if phase_context is None:
            raise base.CellAbort("sota arm expects phase_context")
        user = build_user(junction_id, phase_context)
        t0 = time.time()
        text = self._ask(user)
        phase = base.SLMAgent._parse(text, num_phases)
        with open(self.reply_log, "a", encoding="utf-8") as fh:
            fh.write(json.dumps({"user": user, "reply": text, "phase": phase,
                                 "s": round(time.time() - t0, 2)}) + "\n")
        return phase


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def run_cell(key: str, cell: dict):
    os.chdir(base.REPO)
    reply_log = os.path.join(REPLIES, key.replace("|", "_") + ".jsonl")
    if os.path.exists(reply_log):
        os.remove(reply_log)
    t0 = time.time()
    try:
        r = run_arm(f"sonnetds_{key.replace('|', '_')}",
                    TimingAgent(DownstreamAgent(reply_log), forward_note=True),
                    seed=1, end=base.END, config="sota", net=base.NET, routes=base.routes_for(cell))
    except Exception as e:  # noqa: BLE001
        return key, {"arm": LABEL, "day": cell["day"], "hour": cell["hour"],
                     "error": f"{type(e).__name__}: {e}"}
    m, ds = r["metrics"], r.get("decision_stats", {}) or {}
    return key, {"arm": LABEL, "model_id": base.MODEL, "day": cell["day"], "hour": cell["hour"],
                 "frac": cell["frac"], "delay_s": round(m["mean_network_delay_s"], 2),
                 "completed": m["completed"], "departed": m["departed"],
                 "teleports": m["teleports"], "decision_stats": ds,
                 "runtime_s": round(time.time() - t0, 1)}


def main() -> int:
    os.makedirs(REPLIES, exist_ok=True)
    mp = {k.split("|", 1)[1]: c for k, c in base.SWEEP["cells"].items() if k.startswith("maxpressure|")}
    for k in CELLS:
        if not os.path.exists(base.routes_for(mp[k])):
            log(f"ABORT: missing route file for {k}")
            return 1
    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"meta": {}, "cells": {}}
    res["meta"] = {"arm": LABEL, "control": "sota:claude-sonnet-5-5 in scoot_sweep_sonnet.json",
                   "cells": CELLS, "extra_field": "exit_queued (halting on distinct exit lanes)",
                   "config": "sota", "seed": 1, "end": base.END}
    todo = [k for k in CELLS if "delay_s" not in res["cells"].get(k, {})]
    log(f"start {LABEL}: {len(todo)} cells, {WORKERS} workers")
    with ProcessPoolExecutor(max_workers=WORKERS, max_tasks_per_child=1) as ex:
        for f in as_completed([ex.submit(run_cell, k, mp[k]) for k in todo]):
            key, cell = f.result()
            res["cells"][key] = cell
            log(f"{key} " + (f"ERROR {cell['error']}" if "error" in cell else
                             f"delay={cell['delay_s']} tp={cell['teleports']} ({cell['runtime_s']}s)"))
            tmp = OUT + ".tmp"
            json.dump(res, open(tmp, "w", encoding="utf-8"), indent=2)
            os.replace(tmp, OUT)
    log(f"DONE cells={sum('delay_s' in v for v in res['cells'].values())}/{len(CELLS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
