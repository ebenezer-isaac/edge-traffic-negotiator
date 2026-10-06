"""Generate the arterial-corridor headroom substrate for the coordination study.

Why this network exists
------------------------
MaxPressure is throughput-optimal but MYOPIC: it reacts to queues that have
already formed and never coordinates signal OFFSETS. Its one structural blind
spot is a platoon travelling down an arterial: by the time the platoon's queue
forms at the next junction it has already stopped. A predictive controller that
knows a platoon is *en route* can pre-position green (a green wave), which
MaxPressure cannot. To demonstrate that, we need a network where green-wave
progression is the dominant available gain:

  * a single straight EAST-WEST arterial of 4 signalised crossroads (J0..J3),
    evenly spaced D metres apart, so the free-flow travel time between adjacent
    junctions is a known constant tt = D / v_free (the prediction horizon);
  * light NORTH-SOUTH cross streets at each junction (N_i / S_i) so the signal
    has a real trade-off (it cannot just hold the arterial green forever);
  * a heavy directional through-flow on the arterial so the upstream signal
    METERS the steady demand into platoons automatically (no hand-built bursts).

Spacing D=250 m at v=13.89 m/s (50 km/h) => tt ~= 18 s, comparable to one
green+yellow, so a missed offset costs a full stop. That is the headroom a
predictive controller can recover and a reactive one cannot.

This script ONLY writes plain node/edge files and calls netconvert; it adds no
controller logic. Routes are generated separately (gen_routes.py) so demand and
seed vary without rebuilding the net.
"""
from __future__ import annotations

import os
import subprocess

from sumolib import checkBinary

HERE = os.path.dirname(os.path.abspath(__file__))

N_JUNCTIONS = 4
SPACING = 250.0          # metres between adjacent arterial junctions
ARTERIAL_SPEED = 13.89   # m/s (~50 km/h)
CROSS_SPEED = 13.89      # m/s; keep equal so the only asymmetry is demand
CROSS_OFFSET = 200.0     # metres N/S the cross stubs sit from the arterial
END_STUB = 300.0         # metres the arterial entry/exit stubs extend
ARTERIAL_LANES = 1
CROSS_LANES = 1


def _arterial_x(i: int) -> float:
    return i * SPACING


def write_nodes(path: str) -> None:
    """Arterial J0..J3 (traffic_light) + W/E entry stubs + N_i/S_i cross stubs."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<nodes>"]
    # Arterial entry/exit stubs (priority, not signalised).
    lines.append(f'  <node id="W" x="{-END_STUB:.1f}" y="0.0" type="priority"/>')
    lines.append(
        f'  <node id="E" x="{_arterial_x(N_JUNCTIONS - 1) + END_STUB:.1f}" '
        f'y="0.0" type="priority"/>')
    for i in range(N_JUNCTIONS):
        x = _arterial_x(i)
        lines.append(
            f'  <node id="J{i}" x="{x:.1f}" y="0.0" type="traffic_light"/>')
        lines.append(
            f'  <node id="N{i}" x="{x:.1f}" y="{CROSS_OFFSET:.1f}" type="priority"/>')
        lines.append(
            f'  <node id="S{i}" x="{x:.1f}" y="{-CROSS_OFFSET:.1f}" type="priority"/>')
    lines.append("</nodes>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def _edge(eid: str, frm: str, to: str, lanes: int, speed: float) -> str:
    return (f'  <edge id="{eid}" from="{frm}" to="{to}" '
            f'numLanes="{lanes}" speed="{speed:.2f}"/>')


def write_edges(path: str) -> None:
    """Bidirectional arterial chain W..E plus a bidirectional cross street per J."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<edges>"]
    a, sp = ARTERIAL_LANES, ARTERIAL_SPEED
    # Arterial eastbound + westbound between consecutive nodes (incl. stubs).
    chain = ["W"] + [f"J{i}" for i in range(N_JUNCTIONS)] + ["E"]
    for u, v in zip(chain, chain[1:]):
        lines.append(_edge(f"{u}{v}", u, v, a, sp))   # eastbound
        lines.append(_edge(f"{v}{u}", v, u, a, sp))   # westbound
    # Cross streets at each junction (N_i <-> J_i <-> S_i), bidirectional.
    c, cs = CROSS_LANES, CROSS_SPEED
    for i in range(N_JUNCTIONS):
        for stub in (f"N{i}", f"S{i}"):
            lines.append(_edge(f"{stub}J{i}", stub, f"J{i}", c, cs))
            lines.append(_edge(f"J{i}{stub}", f"J{i}", stub, c, cs))
    lines.append("</edges>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def build(out_net: str | None = None) -> str:
    """Write node/edge files and run netconvert; return the .net.xml path."""
    nod = os.path.join(HERE, "corridor.nod.xml")
    edg = os.path.join(HERE, "corridor.edg.xml")
    net = out_net or os.path.join(HERE, "corridor.net.xml")
    write_nodes(nod)
    write_edges(edg)
    netconvert = checkBinary("netconvert")
    cmd = [
        netconvert,
        "--node-files", nod,
        "--edge-files", edg,
        "--output-file", net,
        # Signalise the arterial crossroads; generate fixed-time programs we can
        # later read/override. tls.guess-signals off: types are set explicitly.
        "--tls.guess-signals", "false",
        "--tls.default-type", "static",
        # Reasonable phase durations so the FIXED-TIME baseline is a fair Webster
        # stand-in (not a pathological program).
        "--tls.green.time", "31",
        "--tls.yellow.time", "3",
        "--no-turnarounds", "true",
        "--default.speed", str(ARTERIAL_SPEED),
        "--no-internal-links", "false",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return net


if __name__ == "__main__":
    net = build()
    print(f"[built] {net}")
