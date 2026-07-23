"""Watch the controller run Euston Road A501 LIVE in the SUMO GUI.

A viewer/demo (NOT a graded experiment): it drives the SAME battery-verified
controller the experiments use, but launches ``sumo-gui`` so you can watch the
lights being driven in real time, then prints the mean network delay against the
MaxPressure baseline.

    # watch the SLM (the winning run: smallest model, myopic) beat MaxPressure:
    python src/run_euston_gui.py --arm slm --model qwen2.5-0.5b --end 1200
    # watch the plain MaxPressure baseline (no Foundry needed):
    python src/run_euston_gui.py --arm maxpressure --end 1200

``--delay`` sets the GUI animation speed (ms per step). The SLM arm needs Foundry
Local up; the maxpressure arm does not. This reuses experiment_traffic's controller
wiring verbatim, so what you watch is exactly what the experiments measured.
"""
from __future__ import annotations

import argparse
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from experiment_traffic import (  # noqa: E402
    DECISION_INTERVAL_S, NET, ROUTES, _SUMO_EUSTON, NullAgent, TimingAgent,
    build_controller, metrics_from_tripinfo,
)

# MaxPressure baseline delay on this corridor at the saturating horizon (from
# results/experiment_sweep.json) -- printed for context so the beat is visible.
BASELINE_DELAY_S = 314.55

# alias -> Foundry model id (from `foundry cache list`), same catalog as the sweep.
_MODEL_IDS = {
    "qwen2.5-0.5b": "qwen2.5-0.5b-instruct-generic-gpu:4",
    "qwen2.5-1.5b": "qwen2.5-1.5b-instruct-generic-gpu:4",
    "qwen3-0.6b": "qwen3-0.6b-generic-gpu:2",
    "qwen3-1.7b": "qwen3-1.7b-generic-gpu:2",
    "phi-4-mini": "Phi-4-mini-instruct-generic-gpu:5",
}


def _slm_agent(alias: str):
    """Build a real SLMAgent for the given alias and probe it (SKIP-with-reason if
    Foundry is down / the model won't answer). Returns (TimingAgent, None) or
    (None, reason)."""
    from slm_agent import SLMAgent, discover_endpoint
    model_id = _MODEL_IDS.get(alias, alias)
    base, _ = discover_endpoint()
    agent = SLMAgent(base_url=base, model=model_id)
    try:
        agent.client.models.list()
        if agent.choose_phase("PROBE", 2, [8, 0]) is None:
            return None, f"model {model_id} did not answer a well-formed decision"
    except Exception as exc:  # noqa: BLE001
        return None, f"Foundry not reachable for {model_id} ({type(exc).__name__})"
    return TimingAgent(agent), None  # myopic (note not forwarded)


def run(arm: str, model: str, end: int, seed: int, delay_ms: int, gate: int = 2) -> int:
    import traci
    from sumolib import checkBinary

    if arm == "maxpressure":
        agent, label = NullAgent(), "MaxPressure baseline"
    else:
        agent, reason = _slm_agent(model)
        if agent is None:
            print(f"SLM arm unavailable: {reason}\n"
                  "Start Foundry (`foundry service start`) or use --arm maxpressure.")
            return 2
        label = f"SLM {model} (myopic)"

    binary = checkBinary("sumo-gui")
    tripinfo = os.path.join(_SUMO_EUSTON, f"tripinfo_gui_{arm}.xml")
    # --start auto-plays; --delay animates at a watchable speed; --quit-on-end keeps
    # the window open after the run so you can inspect the final state.
    traci.start([binary, "-n", NET, "-r", ROUTES,
                 "--tripinfo-output", tripinfo,
                 "--tripinfo-output.write-unfinished", "true",
                 "--tripinfo-output.write-undeparted", "true",
                 "--begin", "0", "--end", str(end),
                 "--time-to-teleport", "300", "--seed", str(seed),
                 "--start", "--delay", str(delay_ms),
                 "--quit-on-end", "false", "--no-warnings", "true"])
    teleports = step = 0
    tls = list(traci.trafficlight.getIDList())
    ctrl = build_controller(traci, tls, agent, config="myopic", gate=gate)
    print(f"Watching: {label}  |  corridor Euston A501 ({len(tls)} junctions)  |  "
          f"horizon {end}s")
    try:
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            teleports += traci.simulation.getStartingTeleportNumber()
            step += 1
    finally:
        try:
            traci.close()
        except Exception:
            pass

    m = metrics_from_tripinfo(tripinfo, teleports, step)
    delay = m["mean_network_delay_s"]
    print("=" * 64)
    print(f"  {label}")
    print(f"  mean network delay = {delay:.2f} s   (MaxPressure baseline = {BASELINE_DELAY_S:.2f} s)")
    if arm != "maxpressure" and isinstance(delay, (int, float)):
        d = delay - BASELINE_DELAY_S
        verdict = ("BEATS" if d < -0.02 * BASELINE_DELAY_S else
                   "matches" if abs(d) <= 0.02 * BASELINE_DELAY_S else "loses")
        print(f"  vs baseline: {d:+.1f} s  ->  {verdict}")
    print(f"  completed={m['completed']}  departed={m['departed']}  teleports={m['teleports']}")
    if isinstance(agent, TimingAgent):
        from slm_latency import summarize_latency
        lat = summarize_latency(agent.latencies_s, warmup=1)
        print(f"  SLM choose_phase P50/P99 = {lat.get('p50')}/{lat.get('p99')} s "
              f"({agent.calls} calls)")
    print("=" * 64)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="Watch the controller run Euston in the SUMO GUI.")
    ap.add_argument("--arm", choices=["slm", "maxpressure"], default="slm")
    ap.add_argument("--model", default="qwen2.5-0.5b",
                    help="SLM alias (default qwen2.5-0.5b, the winning run)")
    ap.add_argument("--end", type=int, default=600, help="sim horizon s (1200 = full saturating)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--delay", type=int, default=40, help="GUI ms per step (higher = slower)")
    return ap


if __name__ == "__main__":
    a = _build_parser().parse_args()
    raise SystemExit(run(a.arm, a.model, a.end, a.seed, a.delay))
