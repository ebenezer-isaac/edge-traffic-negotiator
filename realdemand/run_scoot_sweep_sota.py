"""Real-demand Euston sweep, SLM arms re-run with the delay-aware ("sota") prompt.

The original sweep (scoot_sweep_v2.json) ran every SLM arm with run_arm's default config
("myopic", queue-only prompt). The headline 0.6B student (v1) was trained only on the sota
format, and the dissertation's closed-loop results used config="sota" with
TimingAgent(forward_note=True) (experiment_frontier.py). This re-run uses exactly that, on the
identical 72 demand files (regenerated with subsample(frac, seed=7); MaxPressure cells are
reproduced first as a determinism check). It also records decision_stats so agreement with
MaxPressure can be reported. Resumable; writes after every cell to scoot_sweep_sota.json.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback

REPO = os.environ.get("EDGE_NEGOTIATOR_DIR", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "src"))
os.chdir(REPO)

from calibrate_demand import subsample  # noqa: E402
from experiment_traffic import NullAgent, TimingAgent, run_arm  # noqa: E402
from slm_agent import SLMAgent, discover_endpoint  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SWEEP = json.load(open(os.path.join(HERE, "results", "scoot_sweep_v2.json"), encoding="utf-8"))
OUT = os.path.join(HERE, "results", "scoot_sweep_sota.json")
LOG = os.path.join(HERE, "logs", "scoot_sweep_sota.log")
NET = os.path.join(REPO, "sumo", "euston", "euston_spine.net.xml")
BASE = os.path.join(REPO, "sumo", "euston", "base_hourly.rou.xml")
END = SWEEP["meta"]["end"]
TMP = tempfile.mkdtemp(prefix="scoot_sota_")
CACHE = os.environ.get("FOUNDRY_CACHE", os.path.expanduser(r"~/.cache/foundry-local"))
V1_MD5 = "edd2a446b396ad4e3a63a10b18880ad2"  # v1 sota-only student (headline), see ft-model-provenance

# (arm label, Foundry model id). Defaults follow the Hugging Face / release naming (ft1 = v1 headline,
# ft2 = v2 generalist). The published results were produced on a machine whose local cache had the
# two names swapped (model_id fields in results/scoot_sweep_sota.json say "qwen3-0.6b-ft2" for v1);
# the md5 check below verifies content, not names. Override with QWEN_V1_ID / QWEN_V2_ID.
V1_ID = os.environ.get("QWEN_V1_ID", "qwen3-0.6b-ft1")
V2_ID = os.environ.get("QWEN_V2_ID", "qwen3-0.6b-ft2")
ARMS = [
    ("sota:qwen3-0.6b-v1", V1_ID),
    ("sota:qwen3-0.6b-v2", V2_ID),
    ("sota:phi-4-mini-ft", "phi4mini-gen-gpu"),
    ("sota:phi-4-mini-stock", "Phi-4-mini-instruct-generic-gpu:5"),
]


def log(msg: str) -> None:
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def routes_for(cell) -> str:
    p = os.path.join(TMP, f"{cell['day'][-2:]}_{cell['hour']:02d}.rou.xml")
    if not os.path.exists(p):
        subsample(BASE, p, cell["frac"], seed=7)
    return p


def foundry(*args: str) -> str:
    r = subprocess.run(["foundry", *args], capture_output=True, text=True, timeout=600)
    return (r.stdout + r.stderr).strip().splitlines()[-1] if (r.stdout + r.stderr).strip() else ""


def main() -> int:
    v1 = md5(os.path.join(CACHE, V1_ID, "model.onnx.data"))
    v2 = md5(os.path.join(CACHE, V2_ID, "model.onnx.data"))
    if v1 != V1_MD5 or v2 == V1_MD5:
        log(f"ABORT provenance: {V1_ID}={v1} {V2_ID}={v2}; expected {V1_ID} to be v1 ({V1_MD5})")
        return 1
    mp = {k.split("|", 1)[1]: c for k, c in SWEEP["cells"].items() if k.startswith("maxpressure|")}
    for key in ("2026-05-12|06", "2026-05-14|22"):
        r = run_arm(f"sotacheck_{key.replace('|', '_')}", NullAgent(), seed=1, end=END, net=NET,
                    routes=routes_for(mp[key]))
        got = round(r["metrics"]["mean_network_delay_s"], 2)
        log(f"determinism {key}: stored {mp[key]['delay_s']} reproduced {got}")
        if got != mp[key]["delay_s"]:
            log("ABORT: demand files differ from the original sweep")
            return 1

    res = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"meta": {}, "cells": {}}
    res["meta"] = {"source": "scoot_sweep_v2.json demand files", "config": "sota",
                   "forward_note": True, "end": END, "seed": 1, "arms": dict(ARMS),
                   "provenance": {"v1_md5": v1, "v2_md5": v2}}
    for label, model_id in ARMS:
        todo = [k for k in sorted(mp) if f"{label}|{k}" not in res["cells"]]
        if not todo:
            continue
        log(f"load {model_id}: {foundry('model', 'load', model_id)}")
        base, _ = discover_endpoint()
        agent = SLMAgent(base_url=base, model=model_id)
        if agent.choose_phase("PROBE", 2, [8, 0]) is None:
            log(f"SKIP {label}: {model_id} gave no valid phase on probe")
            continue
        for n, key in enumerate(todo, 1):
            cell = mp[key]
            try:
                t0 = time.time()
                r = run_arm(f"sota_{label.split(':')[1]}_{key.replace('|', '_')}",
                            TimingAgent(agent, forward_note=True), seed=1, end=END,
                            config="sota", net=NET, routes=routes_for(cell))
                m, ds = r["metrics"], r.get("decision_stats", {}) or {}
                res["cells"][f"{label}|{key}"] = {
                    "arm": label, "model_id": model_id, "day": cell["day"], "hour": cell["hour"],
                    "frac": cell["frac"], "delay_s": round(m["mean_network_delay_s"], 2),
                    "completed": m["completed"], "departed": m["departed"],
                    "teleports": m["teleports"], "decision_stats": ds,
                    "runtime_s": round(time.time() - t0, 1)}
                log(f"[{label} {n}/{len(todo)}] {key} delay={res['cells'][f'{label}|{key}']['delay_s']} "
                    f"({res['cells'][f'{label}|{key}']['runtime_s']}s)")
            except Exception as e:  # noqa: BLE001
                log(f"[{label}] {key} ERROR {e}\n{traceback.format_exc()}")
                res["cells"][f"{label}|{key}"] = {"arm": label, "day": cell["day"], "hour": cell["hour"], "error": str(e)}
            tmp = OUT + ".tmp"
            json.dump(res, open(tmp, "w", encoding="utf-8"), indent=2)
            os.replace(tmp, OUT)
        log(f"unload {model_id}: {foundry('model', 'unload', model_id)}")
    log(f"DONE cells={len(res['cells'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
