"""CLI launcher for the END-TO-END INTEGRATED SYSTEM (src/system.py).

One flag per backend choice. The DEFAULT (no flags) runs the fully CI-able
config — inprocess / memory / stub / grid2x2 / audit-on, no attacks — with NO
Docker, NO Foundry, NO SUMO, and prints the result bundle as JSON.

Examples
--------
    # CI-able default (no live dependency)
    python src/run_system.py

    # inject a spoof attack and save the bundle
    python src/run_system.py --attack spoof:A1:A0:99:0:2 --out results/run.json

    # live SUMO microsimulation on the grid (real tripinfo metrics)
    python src/run_system.py --sumo --network grid2x2 --end 300

    # live MQTT transport over a running eclipse-mosquitto broker
    python src/run_system.py --transport mqtt --end 300

    # live Besu registry over a running node
    python src/run_system.py --registry besu --sumo --end 300

    # real SLM (needs Foundry Local serving Phi-4-mini)
    python src/run_system.py --agent slm --sumo --end 300

Each non-default backend is opt-in and LIVE-GATED: a missing broker / node /
SUMO / Foundry surfaces a clear error rather than a silent fallback.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from system import AttackSpec, IntegratedSystem, SystemConfig  # noqa: E402


def _parse_attack(spec: str) -> AttackSpec:
    """Parse a ``kind:sender:recipient[:release[:observed[:tick[:signer]]]]`` flag.

    Examples:
      ``spoof:A1:A0:99:0:2``           — A1 over-claims 99, A0 observes 0, tick 2
      ``under_report:A1:A0:2:20:2``    — A1 under-claims 2, A0 observes 20
      ``not_neighbour:B1:A0:40:0:1``   — non-adjacent B1 injects at tick 1
      ``revoked:A1:A0:40:0:1``         — revoked A1 keeps signing
      ``bad_signature:A1:A0:40:0:1:B0``— impersonate A1, signed by B0
    """
    parts = spec.split(":")
    if len(parts) < 3:
        raise argparse.ArgumentTypeError(
            f"attack must be kind:sender:recipient[:release[:observed[:tick[:signer]]]], "
            f"got {spec!r}")
    kind, sender, recipient = parts[0], parts[1], parts[2]

    def _int(idx: int, default: int) -> int:
        if idx >= len(parts) or parts[idx] == "":
            return default
        try:
            return int(parts[idx])
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"bad int in attack {spec!r}: {exc}") from exc

    release = _int(3, 0)
    observed = _int(4, 0)
    tick = _int(5, 1)
    signer = parts[6] if len(parts) > 6 and parts[6] else None
    try:
        return AttackSpec(kind=kind, sender=sender, recipient=recipient,
                          release=release, observed=observed, tick=tick, signer=signer)
    except (ValueError, TypeError) as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def build_config(args: argparse.Namespace) -> SystemConfig:
    """Translate parsed CLI args into an immutable SystemConfig."""
    return SystemConfig(
        transport=args.transport,
        registry=args.registry,
        agent=args.agent,
        network=args.network,
        audit=not args.no_audit,
        attacks=tuple(args.attack or ()),
        seed=args.seed,
        end=args.end,
        rounds=args.rounds,
        coord_weight=args.coord_weight,
        tolerance=args.tolerance,
        gate=args.gate,
        mqtt_host=args.mqtt_host,
        mqtt_port=args.mqtt_port,
        besu_rpc=args.besu_rpc,
        use_sumo=args.sumo,
    )


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    # One flag per backend choice.
    ap.add_argument("--transport", choices=["inprocess", "mqtt"], default="inprocess")
    ap.add_argument("--registry", choices=["memory", "besu"], default="memory")
    ap.add_argument("--agent", choices=["stub", "slm"], default="stub")
    ap.add_argument("--network", choices=["grid2x2", "lambeth"], default="grid2x2")
    ap.add_argument("--no-audit", action="store_true",
                    help="disable the signed audit log (default: on)")
    ap.add_argument("--sumo", action="store_true",
                    help="drive a real SUMO microsimulation (real tripinfo metrics)")
    ap.add_argument("--attack", action="append", type=_parse_attack, default=[],
                    metavar="SPEC",
                    help="inject an attack (repeatable): "
                         "kind:sender:recipient[:release[:observed[:tick[:signer]]]]")
    # Run controls.
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--end", type=int, default=200, help="SUMO sim steps")
    ap.add_argument("--rounds", type=int, default=40, help="CI fake-conn decide() rounds")
    ap.add_argument("--coord-weight", dest="coord_weight", type=float, default=1.0)
    ap.add_argument("--tolerance", type=int, default=2)
    ap.add_argument("--gate", type=int, default=2)
    # Live-backend connection details.
    ap.add_argument("--mqtt-host", dest="mqtt_host", default="127.0.0.1")
    ap.add_argument("--mqtt-port", dest="mqtt_port", type=int, default=1883)
    ap.add_argument("--besu-rpc", dest="besu_rpc", default="http://127.0.0.1:8545")
    # Output.
    ap.add_argument("--out", default=None, help="write the JSON bundle to this path")
    ap.add_argument("--compact", action="store_true", help="single-line JSON")
    args = ap.parse_args(argv)

    try:
        config = build_config(args)
    except (ValueError, TypeError) as exc:
        ap.error(str(exc))

    result = IntegratedSystem(config).run()
    bundle = result.to_dict()
    text = json.dumps(bundle, separators=(",", ":")) if args.compact else json.dumps(
        bundle, indent=2)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(f"[written] {os.path.abspath(args.out)}")

    _print_summary(bundle)
    if not args.out:
        print(text)
    return 0


def _print_summary(bundle: dict) -> None:
    """Human-readable headline of the run before the full JSON."""
    b = bundle["backends"]
    t = bundle["traffic"]
    c = bundle["coordination"]
    a = bundle["audit"]
    print("=== Edge Negotiator — integrated run ===")
    print(f"  backends: transport={b['transport']} registry={b['registry']} "
          f"agent={b['agent']} network={b['network']} path={b['run_path']} live={b['live']}")
    print(f"  traffic:  completed={t.get('completed')} "
          f"microsimulation={t.get('microsimulation')}")
    print(f"  coord:    decisions={c.get('decisions')} "
          f"verified={c.get('verified_messages')} rejected={c.get('rejected_messages')} "
          f"detections={c.get('detections')} flagged={c.get('flagged_detections')} "
          f"coord_adjusted={c.get('coord_adjusted_decisions')}")
    if a.get("enabled"):
        print(f"  audit:    entries={a.get('entries')} verify_chain={a.get('verify_chain')} "
              f"merkle_root={str(a.get('merkle_root'))[:16]}... "
              f"inclusion_proof_valid={a.get('inclusion_proof_valid')}")
    else:
        print("  audit:    disabled")
    for o in bundle.get("attack_outcomes", ()):
        print(f"  attack:   {o['kind']} {o['sender']}->{o['recipient']} "
              f"detected={o['detected']} reason={o['reason']} "
              f"in_audit={o['captured_in_audit']}")


if __name__ == "__main__":
    raise SystemExit(main())
