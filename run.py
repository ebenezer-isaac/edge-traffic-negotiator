"""Run one controller on one network and print delay, throughput and the audit check.

Examples:
    python run.py                                   # MaxPressure shield only, no GPU needed
    python run.py --controller slm --model phi-4-mini     # stock SLM proposer via Foundry Local
    python run.py --controller slm --model qwen3-0.6b-ft1 --topology euston_peakhour_calibrated
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from experiment_topology import _topologies  # noqa: E402
from experiment_traffic import NullAgent, run_arm  # noqa: E402


def main() -> int:
    topologies = {t["label"]: t for t in _topologies()}
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--controller", choices=["maxpressure", "slm"], default="maxpressure")
    ap.add_argument("--model", default="phi-4-mini",
                    help="Foundry Local model alias or id (used with --controller slm)")
    ap.add_argument("--topology", choices=sorted(topologies), default="bloomsbury_calibrated")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--end", type=int, default=1200, help="simulated seconds")
    ap.add_argument("--json", help="also write the full result (metrics + audit bundle) here")
    args = ap.parse_args()

    if args.controller == "slm":
        from slm_agent import SLMAgent
        agent = SLMAgent(alias=args.model)
        if agent.choose_phase("PROBE", 2, [8, 0]) is None:
            print(f"Model '{agent.model}' did not return a valid phase. Is it loaded? "
                  f"Try: foundry model run {args.model}", file=sys.stderr)
            return 1
        print(f"SLM proposer: {agent.model}")
    else:
        agent = NullAgent()

    topo = topologies[args.topology]
    print(f"Running {args.controller} on {args.topology} (seed {args.seed}, {args.end} s)...", flush=True)
    r = run_arm(args.controller, agent, seed=args.seed, end=args.end, config="sota",
                net=topo["net"], routes=topo["routes"])

    m, a, d = r["metrics"], r["audit"], r["decision_stats"]
    print(f"\n  vehicles completed   {m['completed']} / {m['loaded']}")
    print(f"  mean delay           {m['mean_network_delay_s']:.1f} s")
    print(f"  teleports (gridlock) {m['teleports']}")
    if args.controller == "slm":
        print(f"  decisions            {json.dumps(d)}")
    print(f"  audit entries        {a['entries']}  chain ok={a['verify_chain']}  "
          f"signatures ok={a['verify_signatures']}  merkle proof ok={a['inclusion_proof_valid']}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(r, fh, indent=2, default=str)
        print(f"\n  full result -> {args.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
