"""LIVE, CLICKABLE 2-node coordination demo for The Edge Negotiator.

Runs the authenticated cross-junction coordination loop on the 2x2 grid with
ONLY two junctions -- A0 and A1 -- acting as the SLM-coordinated pair. They are
direct neighbours (edges A0A1 / A1A0), exchange signed neighbour messages, and
coordinate their phase choices. The other two junctions (B0, B1) stay on plain
MaxPressure and do nothing fancy.

What makes it a DEMO (not a sweep):

  * --gui (default ON) launches sumo-gui so a supervisor can watch the grid.
    --no-gui runs headless for CI / quick verification.
  * CLICK-TO-INSPECT: every A0/A1 decision pushes a plain-English "decision
    story" into that traffic light's GUI parameters via
    traci.trafficlight.setParameter(...). In sumo-gui, right-click the A0 or
    A1 traffic light -> "Show Parameter" and the panel updates live with what
    MaxPressure proposed, what the AI proposed, what was executed, who decided,
    the neighbour message, the security check, and the conservation check.
  * LIVE LOG: every A0/A1 decision also prints one plain-English line to the
    terminal (and security events are logged distinctly).
  * --delay adds a small real-time pause per step so a human can follow along.
  * --agent stub (default, reliable, no Foundry) or --agent slm (real
    Phi-4-mini via Foundry Local). If --agent slm and Foundry is down we fail
    with a clear message rather than crashing cryptically.

This file ONLY orchestrates and presents. The coordination logic, signing,
verification, and conservation are entirely the existing, tested modules
(CoordinatedController / MessageBus / Registry / JunctionIdentity /
ConservationChecker). We subclass CoordinatedController purely to surface each
decision to the GUI and the terminal -- the decision itself is unchanged.

    python src/demo_2node.py                       # GUI, stub agent (default)
    python src/demo_2node.py --no-gui --delay 0    # headless, fast (testing)
    python src/demo_2node.py --agent slm           # GUI, real Phi-4-mini
"""
from __future__ import annotations

import argparse
import sys
import time

import traci
from sumolib import checkBinary

from conservation import ConservationChecker
from controllers import MaxPressureController
from coordinated_controller import CoordinatedController, StubAgent
from identity import JunctionIdentity
from message_bus import MessageBus
from registry import Registry
from run_baseline import CFG

# The two junctions that coordinate in this demo. They are direct neighbours via
# edges A0A1 / A1A0, so their signed messages have a physical edge to ride on.
DEMO_PAIR = ("A0", "A1")

# Demo-local adjacency: A0 and A1 coordinate ONLY with each other (a clean,
# explainable two-node story). B0/B1 are deliberately absent -- they run plain
# MaxPressure and never participate in the signed exchange.
DEMO_ADJACENCY = {"A0": ["A1"], "A1": ["A0"]}

# GUI parameter keys. Numeric prefixes force a stable, human-readable order in
# the sumo-gui "Show Parameter" panel (it sorts keys alphabetically).
PARAM_KEYS = (
    "1_maxpressure_proposed",
    "2_AI_agent_proposed",
    "3_EXECUTED",
    "4_who_decided",
    "5_incoming_from_neighbour",
    "6_neighbour_msg",
    "7_security_check",
    "8_conservation",
)


def _fmt_phase(phase) -> str:
    """Human label for a phase index (or a clear placeholder when absent)."""
    return f"phase {phase}" if phase is not None else "(none / declined)"


# Routine bus bookkeeping that is NOT an attack and should not alarm a viewer:
#   * not_neighbour where sender == recipient -- a junction re-reading its own
#     published message (it is not its own neighbour). Harmless self-echo.
#   * replay -- the bus correctly refusing to deliver an already-consumed
#     message a second time on a later scan. This is the replay guard WORKING,
#     not an adversary. (A genuine injected replay would still be counted, but
#     in this benign demo every replay is routine de-duplication.)
# Genuinely adversarial reasons (bad_signature, unknown_sender, revoked, or a
# not_neighbour from a DIFFERENT sender) are surfaced loudly.
_ROUTINE_REASONS = frozenset({"replay"})


def _is_routine_rejection(r: dict) -> bool:
    """True for benign bus bookkeeping (self-echo / replay de-dup), not an attack."""
    reason = r.get("reason")
    if reason in _ROUTINE_REASONS:
        return True
    if reason == "not_neighbour" and r.get("sender") == r.get("recipient"):
        return True
    return False


def _security_summary(received: list, attack_rejections: int) -> str:
    """One-line security verdict for a decision's inbox + adversarial rejects.

    Distinguishes states a non-expert can read:
      * VERIFIED OK (n)              -- n signed messages passed every check.
      * no neighbour message         -- the neighbour sent nothing this step.
      * REJECTED (k attacks blocked) -- k genuinely bad messages were dropped.
    """
    verified = sum(1 for r in received if isinstance(r, dict) and "from" in r)
    transport_err = any(isinstance(r, dict) and "error" in r for r in received)
    if transport_err:
        return "TRANSPORT ERROR (handled, message dropped)"
    base = (f"VERIFIED OK ({verified})" if verified
            else "no neighbour message this step")
    if attack_rejections:
        return f"{base}; REJECTED {attack_rejections} attack message(s)"
    return base


def _conservation_summary(detections: list) -> str:
    """One-line conservation verdict from this decision's fresh Detections."""
    if not detections:
        return "OK (no claims to reconcile this step)"
    flagged = [d for d in detections if d.get("flagged")]
    if not flagged:
        ok = detections[0]
        return (f"OK (claimed {ok['claimed']} vs observed {ok['observed']} "
                f"on {ok['src']}->{ok['dst']})")
    parts = [f"{d['src']}->{d['dst']}: {d['reason']} "
             f"(claimed {d['claimed']}, observed {d['observed']})"
             for d in flagged]
    return "FLAGGED -> " + "; ".join(parts)


class DemoController(CoordinatedController):
    """CoordinatedController that narrates A0/A1 decisions to the GUI + terminal.

    The decision logic is 100% the parent's. After the parent appends its event
    dict, we read that event, push a readable story into the traffic light's GUI
    parameters, and print one plain-English line. Nothing about the control
    choice is altered here -- this is presentation only.
    """

    def __init__(self, *args, demo_pair=DEMO_PAIR, verbose: bool = True, **kwargs):
        super().__init__(*args, **kwargs)
        self.demo_pair = tuple(demo_pair)
        self.verbose = verbose
        self._last_event_count = 0
        self._last_rejected = 0

    def decide(self, tl: str, st: dict) -> int:
        used = super().decide(tl, st)
        # Only narrate the coordinated pair, and only when the parent actually
        # appended a coordination event this call (quiet/non-SLM decisions add
        # none). Comparing the event count is robust to the event being skipped.
        if tl in self.demo_pair and len(self.events) > self._last_event_count:
            self._last_event_count = len(self.events)
            self._narrate(self.events[-1])
        return used

    def _narrate(self, ev: dict) -> None:
        tl = ev["tls"]
        t = int(self.c.simulation.getTime())
        mp = ev["shield_phase"]
        ai = ev["slm_phase"]
        used = ev["used"]
        # "who decided": the AI iff its (valid) proposal is what got executed;
        # otherwise the deterministic shield (coordination-adjusted) chose.
        who = "AI" if (ai is not None and used == ai) else "shield (MaxPressure)"
        incoming = ev.get("expected_incoming", 0)
        received = ev.get("received", []) or []
        detections = ev.get("detections", []) or []
        neighbour = self.demo_pair[1] if tl == self.demo_pair[0] else self.demo_pair[0]

        # Split the running reject log into genuine attacks vs routine
        # bookkeeping so a non-expert is not alarmed by benign self-echo/replay.
        all_rejected = self.bus.rejected
        attack_rejections = sum(1 for r in all_rejected
                                if not _is_routine_rejection(r))
        security = _security_summary(received, attack_rejections)
        conservation = _conservation_summary(detections)

        # Neighbour message in words: where it came from + the release it carried.
        if received and isinstance(received[0], dict) and "from" in received[0]:
            r0 = received[0]
            neighbour_msg = (f"from {r0['from']}: ~{r0['release']} cars released "
                             f"toward me (tick {r0['t']})")
            incoming_phrase = f"~{incoming} cars heading my way"
        else:
            neighbour_msg = "(no signed message received this step)"
            incoming_phrase = "no cars announced this step"

        # ---- (1) push the decision story into the GUI parameter panel --------
        params = {
            "1_maxpressure_proposed": _fmt_phase(mp),
            "2_AI_agent_proposed": _fmt_phase(ai),
            "3_EXECUTED": _fmt_phase(used),
            "4_who_decided": who,
            "5_incoming_from_neighbour": incoming_phrase,
            "6_neighbour_msg": neighbour_msg,
            "7_security_check": security,
            "8_conservation": conservation,
        }
        for key, value in params.items():
            # Never let a presentation write kill the sim; log and continue.
            try:
                self.c.trafficlight.setParameter(tl, key, str(value))
            except Exception as exc:  # pragma: no cover - GUI/transport edge
                print(f"  [warn] setParameter({tl}, {key}) failed: "
                      f"{type(exc).__name__}: {exc}", file=sys.stderr)

        # ---- (2) live plain-English log line ---------------------------------
        if self.verbose:
            tag = "(AI)" if who == "AI" else "(shield)"
            print(f"[t={t}s | Junction {tl}] "
                  f"MaxPressure wanted: {_fmt_phase(mp)}  |  "
                  f"AI proposed: {_fmt_phase(ai)}  |  "
                  f"EXECUTED: {_fmt_phase(used)} {tag}  |  "
                  f"heard from {neighbour}: {incoming_phrase}  |  "
                  f"message: {security}  |  "
                  f"conservation: {conservation}")

            # Security events called out distinctly so they stand out in a demo.
            # Only GENUINE attacks are logged loudly; routine self-echo / replay
            # de-duplication is normal bus bookkeeping and is left silent here.
            if len(all_rejected) > self._last_rejected:
                new = all_rejected[self._last_rejected:]
                for r in new:
                    if _is_routine_rejection(r):
                        continue
                    print(f"  [SECURITY] REJECTED attack message from "
                          f"{r['sender']} -> {r['recipient']} "
                          f"(tick {r['t']}): {r['reason']}")
            self._last_rejected = len(all_rejected)
            for d in detections:
                if d.get("flagged"):
                    print(f"  [SECURITY] CONSERVATION FLAG {d['src']}->{d['dst']}: "
                          f"{d['reason']} (claimed {d['claimed']}, "
                          f"observed {d['observed']}, delta {d['delta']})")


def _make_agent(kind: str):
    """Build the chosen agent. 'stub' is always safe; 'slm' needs Foundry Local.

    For 'slm' we construct the real SLMAgent and probe it once so a dead Foundry
    surfaces as a clear, actionable message here -- not as a cryptic failure
    1000 steps into the run.
    """
    if kind == "stub":
        return StubAgent()
    if kind == "slm":
        try:
            from slm_agent import SLMAgent
        except Exception as exc:  # import-time failure (missing openai etc.)
            print(f"ERROR: could not import the SLM agent ({type(exc).__name__}: "
                  f"{exc}).\n       Use --agent stub for the reliable demo.",
                  file=sys.stderr)
            sys.exit(2)
        try:
            agent = SLMAgent()
        except Exception as exc:
            print("ERROR: could not connect to Foundry Local (the local Phi-4-mini "
                  f"service).\n       {type(exc).__name__}: {exc}\n"
                  "       Start it with `foundry service start` and load phi-4-mini, "
                  "or run the safe demo with --agent stub.", file=sys.stderr)
            sys.exit(2)
        # Active probe. SLMAgent.choose_phase swallows ALL errors and returns
        # None (so the shield can take over silently in production), which means
        # it can NOT tell us whether Foundry is alive. So we probe the underlying
        # OpenAI client DIRECTLY here: a dead/missing Foundry raises a connection
        # error we can turn into a clear, actionable message instead of letting
        # the demo run silently with the SLM permanently falling back to MaxPressure.
        try:
            agent.client.chat.completions.create(
                model=agent.model, temperature=0, max_tokens=4,
                messages=[{"role": "user", "content": "ping"}],
            )
        except Exception as exc:
            print("ERROR: cannot reach Foundry Local (the local Phi-4-mini "
                  f"service).\n       {type(exc).__name__}: {exc}\n"
                  "       Start it with `foundry service start` and load "
                  "phi-4-mini,\n       or run the safe demo with --agent stub.",
                  file=sys.stderr)
            sys.exit(2)
        return agent
    raise ValueError(f"unknown agent kind {kind!r}")  # pragma: no cover


def run(gui: bool = True, agent_kind: str = "stub", delay: float = 0.2,
        seed: int = 42, end: int = 1000, verbose: bool = True) -> dict:
    """Run the 2-node coordinated demo and return a small summary dict.

    A0 and A1 are the SLM-coordinated pair (slm_junctions=DEMO_PAIR); B0/B1 run
    plain MaxPressure. coord_weight=1.0 so the deterministic coordination term is
    live (a neighbour's announced incoming traffic can actually move the shield's
    reference choice), making the on-screen story meaningful.
    """
    agent = _make_agent(agent_kind)

    binary = checkBinary("sumo-gui" if gui else "sumo")
    cmd = [binary, "-c", CFG, "--seed", str(seed), "--no-warnings", "true"]
    if gui:
        # Auto-start and auto-quit so the supervisor sees motion immediately and
        # the window closes cleanly at the end. --delay paces SUMO's own loop too.
        cmd += ["--start", "--quit-on-end"]

    traci.start(cmd)
    try:
        all_tls = list(traci.trafficlight.getIDList())
        pair = [j for j in DEMO_PAIR if j in all_tls]
        if len(pair) < 2:
            raise RuntimeError(
                f"demo expects junctions {DEMO_PAIR} in the net, found {all_tls}")

        # Identities + registry for the WHOLE net (so every TLS is a known peer),
        # but the signed bus only wires the A0<->A1 adjacency: that is the only
        # channel that carries coordination in this demo.
        identities = {jid: JunctionIdentity(jid) for jid in all_tls}
        registry = Registry()
        for jid, ident in identities.items():
            registry.register(jid, ident.public_key)
        bus = MessageBus(registry, DEMO_ADJACENCY)
        checker = ConservationChecker()

        ctrl = DemoController(
            traci, all_tls, agent,
            identities=identities, registry=registry, bus=bus,
            adjacency=DEMO_ADJACENCY, checker=checker,
            slm_junctions=pair,          # ONLY A0 + A1 are SLM-coordinated
            coord_weight=1.0,
            demo_pair=tuple(pair), verbose=verbose,
        )

        if verbose:
            print(f"=== Edge Negotiator 2-node demo ===")
            print(f"  Coordinated pair : {pair[0]} <-> {pair[1]} "
                  f"(signed neighbour messages, conservation check)")
            print(f"  Plain MaxPressure: "
                  f"{[j for j in all_tls if j not in pair]}")
            print(f"  Agent            : {agent_kind} (model={getattr(agent, 'model', '?')})")
            print(f"  GUI              : {'sumo-gui' if gui else 'headless'}"
                  f"   delay={delay}s/step   seed={seed}")
            print(f"  In sumo-gui: right-click the {pair[0]} or {pair[1]} traffic "
                  f"light -> 'Show Parameter' to watch the live decision story.")
            print("-" * 78)

        step = 0
        while traci.simulation.getMinExpectedNumber() > 0 and step < end:
            traci.simulationStep()
            ctrl.step()
            step += 1
            if delay > 0:
                time.sleep(delay)
    finally:
        traci.close()

    summary = {
        "agent": agent_kind,
        "model": getattr(agent, "model", "?"),
        "steps": step,
        "decisions_A0A1": len(ctrl.events),
        "verified_messages": sum(
            len(e.get("received", [])) for e in ctrl.events
            if isinstance(e.get("received"), list)
            and all("error" not in r for r in e.get("received", []))),
        "rejected_messages": len(ctrl.bus.rejected),
        "coord_changed_decisions": sum(
            1 for e in ctrl.events if e.get("coord_changed")),
        "conservation_checks": sum(
            len(e.get("detections", [])) for e in ctrl.events),
        "flagged_detections": sum(
            1 for d in ctrl.detections if d.flagged),
    }
    # The end-of-run summary always prints (it is the run's headline result);
    # only the per-decision live log is gated behind verbose.
    print("-" * 78)
    print("=== demo finished ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")
    return summary


def _build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Live, clickable 2-node (A0<->A1) coordination demo.")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--gui", dest="gui", action="store_true",
                   help="launch sumo-gui (DEFAULT for the demo)")
    g.add_argument("--no-gui", dest="gui", action="store_false",
                   help="run headless (CI / quick verification)")
    ap.set_defaults(gui=True)
    ap.add_argument("--agent", choices=["stub", "slm"], default="stub",
                    help="stub = reliable, no Foundry (default); "
                         "slm = real Phi-4-mini via Foundry Local")
    ap.add_argument("--delay", type=float, default=0.2,
                    help="real-time pause per sim step in seconds "
                         "(default 0.2 so a human can watch; use 0 for tests)")
    ap.add_argument("--seed", type=int, default=42, help="SUMO RNG seed")
    ap.add_argument("--steps", type=int, default=1000,
                    help="max simulation steps to run")
    ap.add_argument("--quiet", action="store_true",
                    help="suppress the per-decision live log")
    return ap


if __name__ == "__main__":
    args = _build_parser().parse_args()
    if args.delay < 0:
        print("ERROR: --delay must be >= 0", file=sys.stderr)
        sys.exit(2)
    run(gui=args.gui, agent_kind=args.agent, delay=args.delay,
        seed=args.seed, end=args.steps, verbose=not args.quiet)
