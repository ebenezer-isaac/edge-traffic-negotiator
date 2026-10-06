"""Capture one live closed-loop cell for the demo video.

Reproduces run_arm's loop (experiment_traffic.run_arm) step for step, with one
addition: after every ctrl.step() it records vehicle positions, signal states
and the new signed decision records, so the run can be rendered headlessly.
The controller, shield, audit chain and SUMO invocation are the harness's own.

Usage (project venv, Foundry Local running with the model loaded):
    python src/demo_capture.py --model qwen3-0.6b-ft1 --seed 1 --end 1200
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from audit_log import AuditLog  # noqa: E402
from experiment_traffic import (  # noqa: E402
    TimingAgent, build_controller, mirror_new_events, metrics_from_tripinfo,
    decision_stats, audit_bundle, _SUMO_EUSTON,
)
from experiment_topology import _topologies  # noqa: E402
from identity import JunctionIdentity  # noqa: E402
from slm_agent import SLMAgent, discover_endpoint  # noqa: E402

RESULTS = os.path.normpath(os.path.join(_HERE, "..", "results"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3-0.6b-ft1")
    ap.add_argument("--topology", default="bloomsbury_calibrated")
    ap.add_argument("--config", default="sota")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--end", type=int, default=1200)
    ap.add_argument("--out", default=None)
    ap.add_argument("--gui", action="store_true", help="run sumo-gui instead of sumo (for screenshots)")
    ap.add_argument("--delay", type=int, default=50, help="sumo-gui ms per step")
    args = ap.parse_args()

    import traci
    from sumolib import checkBinary

    topo = next(t for t in _topologies() if t["label"] == args.topology)
    net, routes = topo["net"], topo["routes"]
    base, _ = discover_endpoint()
    agent = TimingAgent(SLMAgent(base_url=base, model=args.model),
                        forward_note=(args.config != "myopic"))
    # warm probe: one real call so a missing model fails before SUMO starts
    probe = agent.inner.choose_phase("PROBE", 2, [8, 0])
    print(f"endpoint {base} model {args.model} probe -> {probe}", flush=True)

    tag = f"{args.model}__{args.topology}__{args.config}__s{args.seed}"
    out = args.out or os.path.join(RESULTS, f"demo_capture__{tag}.json.gz")
    tripinfo = os.path.join(_SUMO_EUSTON, f"tripinfo_demo_{tag}.xml")
    cmd = [checkBinary("sumo-gui" if args.gui else "sumo"), "-n", net, "-r", routes,
           "--tripinfo-output", tripinfo,
           "--tripinfo-output.write-unfinished", "true",
           "--tripinfo-output.write-undeparted", "true",
           "--begin", "0", "--end", str(args.end),
           "--time-to-teleport", "300",
           "--seed", str(args.seed),
           "--no-step-log", "true", "--no-warnings", "true"]
    if args.gui:
        cmd += ["--start", "--delay", str(args.delay), "--quit-on-end", "false"]
    traci.start(cmd)

    frames = []
    decisions = []
    audit = AuditLog()
    teleports = 0
    step = 0
    logged = 0
    t_wall0 = time.perf_counter()
    try:
        tls = list(traci.trafficlight.getIDList())
        identities = {tl: JunctionIdentity(tl) for tl in tls}
        # signal-head geometry via TraCI (TLS ids may be joined programs, not node ids)
        tls_lanes = {}
        nodes = {}
        for tl in tls:
            heads = []
            for ln in dict.fromkeys(traci.trafficlight.getControlledLanes(tl)):
                shp = traci.lane.getShape(ln)
                if len(shp) >= 2:
                    heads.append([[round(shp[-2][0], 1), round(shp[-2][1], 1)],
                                  [round(shp[-1][0], 1), round(shp[-1][1], 1)]])
            tls_lanes[tl] = heads
            if heads:
                nodes[tl] = [round(sum(h[1][0] for h in heads) / len(heads), 1),
                             round(sum(h[1][1] for h in heads) / len(heads), 1)]
        ctrl = build_controller(traci, tls, agent, config=args.config, gate=2)
        while traci.simulation.getMinExpectedNumber() > 0 and step < args.end:
            traci.simulationStep()
            n_lat_before = len(agent.latencies_s)
            ctrl.step()
            new_events = ctrl.events[logged:]
            logged = mirror_new_events(audit, identities, ctrl.events, logged)
            teleports += traci.simulation.getStartingTeleportNumber()
            # pair each new event with its audit entry (same order, appended just now)
            entries = audit.entries()
            base_idx = len(entries) - len(new_events)
            new_lat = agent.latencies_s[n_lat_before:]
            for k, ev in enumerate(new_events):
                ent = entries[base_idx + k]
                decisions.append({
                    "step": step, "tls": ev.get("tls"),
                    "halting": [int(h) for h in (ev.get("halting") or [])],
                    "slm_phase": ev.get("slm_phase"), "shield_phase": ev.get("shield_phase"),
                    "used": ev.get("used"), "served": ev.get("served"),
                    "served_by": ev.get("served_by"), "overridden": bool(ev.get("overridden")),
                    "seq": ent["seq"], "hash": ent["hash"], "prev_hash": ent["prev_hash"],
                    "latency_s": (new_lat[k] if k < len(new_lat) else None),
                })
            vids = traci.vehicle.getIDList()
            veh = []
            for v in vids:
                x, y = traci.vehicle.getPosition(v)
                veh.append([round(x, 1), round(y, 1), round(traci.vehicle.getSpeed(v), 1)])
            frames.append({
                "step": step,
                "veh": veh,
                "tls": {tl: traci.trafficlight.getRedYellowGreenState(tl) for tl in tls},
                "arrived": traci.simulation.getArrivedNumber(),
                "teleports": teleports,
                "chain_len": len(entries),
                "chain_head": entries[-1]["hash"] if entries else None,
            })
            step += 1
            if step % 100 == 0:
                print(f"step {step}/{args.end} vehicles {len(vids)} decisions {len(decisions)} "
                      f"wall {time.perf_counter() - t_wall0:.0f}s", flush=True)
    finally:
        try:
            traci.close()
        except Exception:
            pass

    public_keys = {jid: ident.public_key for jid, ident in identities.items()}
    bundle = audit_bundle(audit, public_keys)
    metrics = metrics_from_tripinfo(tripinfo, teleports, step)
    stats = decision_stats(ctrl.events)
    # geometry for the renderer (best effort; the run data is written regardless)
    edges = []
    try:
        import sumolib
        snet = sumolib.net.readNet(net)
        edges = [[list(map(lambda p: [round(p[0], 1), round(p[1], 1)], lane.getShape()))
                  for lane in e.getLanes()] for e in snet.getEdges()]
    except Exception as exc:  # noqa: BLE001
        print(f"geometry warning: {exc}", flush=True)
    payload = {
        "model": args.model, "topology": args.topology, "config": args.config,
        "seed": args.seed, "end": args.end, "net": net, "routes": routes,
        "wall_s": time.perf_counter() - t_wall0,
        "metrics": metrics, "decision_stats": stats, "audit": bundle,
        "latency_s": list(agent.latencies_s),
        "geometry": {"edges": edges, "tls_nodes": nodes, "tls_lanes": tls_lanes},
        "decisions": decisions, "frames": frames,
    }
    with gzip.open(out, "wt", encoding="utf-8") as fh:
        json.dump(payload, fh)
    with open(out.replace(".json.gz", ".audit.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(audit.to_jsonl())
    with open(out.replace(".json.gz", ".pubkeys.json"), "w", encoding="utf-8") as fh:
        json.dump({k: v.hex() for k, v in public_keys.items()}, fh)
    print(json.dumps({"metrics": metrics, "decision_stats": stats, "audit": bundle,
                      "wall_s": payload["wall_s"], "out": out}, indent=1), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
