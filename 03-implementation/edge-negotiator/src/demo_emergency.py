"""LIVE exploit-then-defend demo for The Edge Negotiator (the headline result).

Runs the 4-junction arterial corridor (J0-J1-J2-J3) with every junction on the
authenticated SLM-coordination layer + the emergency exception handler, and
stages the dissertation's headline security story end to end:

  1. A REAL ambulance (vClass=emergency) is injected eastbound and traverses the
     corridor. Each junction SENSES it locally and PREEMPTS to clear it. Local
     sensing is trusted -- you cannot spoof a physical vehicle into a junction's
     own detector.

  2. A COMPROMISED-but-approved insider (junction J1, holding a valid key) sends
     a SIGNED ev_claim for a PHANTOM ambulance to its downstream neighbour J2,
     trying to grab green and starve the cross street. J2 AUTHENTICATES the
     message (valid signature, approved member) but finds NO corroborating
     sighting and sees no vehicle locally -> PREEMPTION IS WITHHELD. The signal
     stays on MaxPressure; the cross street is not starved.

The point a non-expert can read off the terminal: signing alone does NOT stop a
compromised insider; the vehicle-conservation / corroboration gate does. The
defence is "shown, not asserted".

    python src/demo_emergency.py                 # GUI (watch it), stub agent
    python src/demo_emergency.py --no-gui        # headless (CI / quick check)

Nothing here edits the frozen bus, the route file, or the net. The ambulance and
the attack are injected live via TraCI; the corroboration logic is entirely in
emergency_controller.EmergencyController.
"""
from __future__ import annotations

import argparse
import os
import sys
import time

import traci
from sumolib import checkBinary

from conservation import ConservationChecker
from coordinated_controller import StubAgent
from emergency_controller import EmergencyController
from identity import JunctionIdentity
from message_bus import MessageBus
from registry import Registry

HERE = os.path.dirname(os.path.abspath(__file__))
CORRIDOR_CFG = os.path.normpath(
    os.path.join(HERE, "..", "sumo", "corridor", "corridor.sumocfg"))

# Arterial line adjacency J0-J1-J2-J3 (edges follow the f"{src}{dst}" convention,
# e.g. J0->J1 is edge "J0J1", so no explicit edge_map is needed).
ARTERIAL_ADJACENCY = {
    "J0": ["J1"], "J1": ["J0", "J2"], "J2": ["J1", "J3"], "J3": ["J2"],
}

EB_ROUTE = "eb"                 # WJ0 J0J1 J1J2 J2J3 J3E (defined in corridor.rou.xml)
REAL_AMB = "AMB-1"
PHANTOM = "PHANTOM-AMB"


def _inject_ambulance(veh_id: str) -> None:
    """Add a real emergency vehicle on the eastbound arterial route, live."""
    traci.vehicle.add(veh_id, routeID=EB_ROUTE, typeID="car",
                      departLane="best", departSpeed="max")
    try:
        traci.vehicle.setVehicleClass(veh_id, "emergency")
        traci.vehicle.setColor(veh_id, (220, 20, 20, 255))
    except Exception as exc:  # presentation niceties must never kill the sim
        print(f"  [warn] could not flag {veh_id} as emergency: "
              f"{type(exc).__name__}: {exc}", file=sys.stderr)


def run(gui: bool = True, delay: float = 0.15, seed: int = 42, end: int = 600,
        scale: float = 1.0, attack_t: int = 40, ambulance_t: int = 120,
        verbose: bool = True) -> dict:
    """Run the exploit-then-defend corridor demo; return a small summary dict.

    ``attack_t``: sim second at which the compromised J1 emits the phantom claim
    to J2 (while no real ambulance is anywhere near, so the WITHHOLD is clean).
    ``ambulance_t``: sim second at which the real eastbound ambulance is injected.
    """
    agent = StubAgent()
    binary = checkBinary("sumo-gui" if gui else "sumo")
    cmd = [binary, "-c", CORRIDOR_CFG, "--seed", str(seed),
           "--no-warnings", "true", "--scale", str(float(scale))]
    if gui:
        cmd += ["--start", "--quit-on-end"]

    traci.start(cmd)
    try:
        all_tls = list(traci.trafficlight.getIDList())
        pair = [j for j in ("J0", "J1", "J2", "J3") if j in all_tls]
        if len(pair) < 3:
            raise RuntimeError(
                f"demo expects J0..J3 in the corridor net, found {all_tls}")

        identities = {jid: JunctionIdentity(jid) for jid in all_tls}
        registry = Registry()
        for jid, ident in identities.items():
            registry.register(jid, ident.public_key)
        # Two signed channels sharing the registry + adjacency: one for routine
        # coordination, one for EV sightings/claims (separate tick-spaces).
        coord_bus = MessageBus(registry, ARTERIAL_ADJACENCY)
        ev_bus = MessageBus(registry, ARTERIAL_ADJACENCY)
        checker = ConservationChecker()

        ctrl = EmergencyController(
            traci, all_tls, agent,
            identities=identities, registry=registry, bus=coord_bus,
            adjacency=ARTERIAL_ADJACENCY, checker=checker,
            slm_junctions=pair, coord_weight=0.5, flow_window=30.0,
            ev_bus=ev_bus, ev_horizon=195.0, verbose=verbose)

        if verbose:
            print("=== Edge Negotiator: exploit-then-defend corridor demo ===")
            print(f"  Corridor junctions : {pair} (all SLM-coordinated, signed bus)")
            print(f"  Agent              : stub (deterministic, no Foundry)")
            print(f"  GUI                : {'sumo-gui' if gui else 'headless'}"
                  f"   seed={seed}   scale={scale}")
            print(f"  Scripted attack    : compromised J1 -> phantom EV claim to "
                  f"J2 at t={attack_t}s")
            print(f"  Real ambulance     : injected eastbound at t={ambulance_t}s")
            print("-" * 78)

        fired_attack = False
        injected_amb = False
        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            now = int(traci.simulation.getTime())
            # Scripted compromised-insider attack: a signed phantom EV claim.
            if not fired_attack and now >= attack_t:
                if "J1" in pair and "J2" in pair:
                    print(f"[t={now}s] >>> ATTACK: compromised J1 signs a PHANTOM "
                          f"emergency claim to J2 <<<")
                    ctrl.inject_phantom_claim("J1", "J2", PHANTOM, "J1J2")
                fired_attack = True
            # Real ambulance, injected once, after the attack is shown.
            if not injected_amb and now >= ambulance_t:
                print(f"[t={now}s] >>> REAL ambulance {REAL_AMB} enters eastbound <<<")
                _inject_ambulance(REAL_AMB)
                injected_amb = True
            ctrl.step()
            step += 1
            if delay > 0:
                time.sleep(delay)
    finally:
        traci.close()

    preempts = [e for e in ctrl.ev_events if e["preempt_phase"] is not None]
    withheld = [e for e in ctrl.ev_events
                if e["source"] == "advance_claim" and not e["admissible"]]
    summary = {
        "steps": step,
        "ev_decisions": len(ctrl.ev_events),
        "local_preemptions (real EV, sensed + granted)": sum(
            1 for e in preempts if e["source"] == "local_sensing"),
        "corroborated_claim_preemptions (real EV, confirmed downstream)": sum(
            1 for e in preempts if e["source"] == "advance_claim"),
        "PHANTOM_attack_withheld (the injected spoof, blocked)": sum(
            1 for e in withheld if e["ev_id"] == PHANTOM),
        "real_claims_awaiting_corroboration (correctly not yet preempted)": sum(
            1 for e in withheld if e["ev_id"] != PHANTOM),
    }
    print("-" * 78)
    print("=== demo finished ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return summary


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Exploit-then-defend corridor demo (spoofed EV vs real EV).")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--gui", dest="gui", action="store_true",
                   help="launch sumo-gui (DEFAULT)")
    g.add_argument("--no-gui", dest="gui", action="store_false",
                   help="run headless (CI / quick verification)")
    ap.set_defaults(gui=True)
    ap.add_argument("--delay", type=float, default=0.15,
                    help="real-time pause per sim step (s); 0 for tests")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--scale", type=float, default=1.0,
                    help="SUMO demand multiplier (corridor is sized for 1.0)")
    ap.add_argument("--attack-t", type=int, default=40,
                    help="sim second to fire the phantom EV claim")
    ap.add_argument("--ambulance-t", type=int, default=120,
                    help="sim second to inject the real ambulance")
    ap.add_argument("--quiet", action="store_true")
    return ap


if __name__ == "__main__":
    args = _build_parser().parse_args()
    if args.delay < 0:
        print("ERROR: --delay must be >= 0", file=sys.stderr)
        sys.exit(2)
    run(gui=args.gui, delay=args.delay, seed=args.seed, end=args.steps,
        scale=args.scale, attack_t=args.attack_t, ambulance_t=args.ambulance_t,
        verbose=not args.quiet)
