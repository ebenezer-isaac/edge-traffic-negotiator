import json, os
"""No-model control for the coordination and prediction configs: the same controllers with a
NullAgent, so the deterministic reference decides every phase. --all runs all 72 hours."""
import sys
import run_scoot_sweep_claude as base
from experiment_traffic import NullAgent, TimingAgent, run_arm
CELLS = ["2026-05-12|17", "2026-05-12|18", "2026-05-14|08", "2026-05-13|11", "2026-05-13|21", "2026-05-12|22"]
mp = {k.split("|", 1)[1]: c for k, c in base.SWEEP["cells"].items() if k.startswith("maxpressure|")}
out = {}
ALL = "--all" in sys.argv
for cfg in ("coordination", "prediction"):
    for k in (sorted(mp) if ALL else CELLS):
        r = run_arm(f"{"nullfull" if ALL else "nullctl"}{cfg}_{k.replace('|','_')}", TimingAgent(NullAgent(), forward_note=True), seed=1,
                    end=base.END, config=cfg, net=base.NET, routes=base.routes_for(mp[k]))
        m = r["metrics"]; out[f"{cfg}|{k}"] = {"delay_s": round(m["mean_network_delay_s"], 2), "teleports": m["teleports"]}
        print(cfg, k, out[f"{cfg}|{k}"], flush=True)
name = "scoot_config_null_full72.json" if ALL else "scoot_config_null_control.json"
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", name), "w"), indent=2)
