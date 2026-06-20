"""Generate platooned arterial demand for the corridor substrate.

Demand shape (the headroom regime):
  * HEAVY directional through-flow on the arterial (W->E and E->W). The upstream
    signal meters this steady stream into PLATOONS automatically, so we never
    hand-craft bursts. This is the flow a green wave can help.
  * LIGHT north-south cross demand at each junction, so the signal faces a real
    trade-off and cannot just hold the arterial green.

Stochastic, seed-dependent arrivals via ``period="exp(rate)"`` (SUMO draws
Poisson inter-arrival times from its seeded RNG), so different ``--seed`` values
at run time give genuinely different vehicle streams -> meaningful paired-seed
statistics. ``scale`` multiplies every rate so we can tune to the
saturated-but-flowing band found in characterisation.
"""
from __future__ import annotations

import argparse
import os

HERE = os.path.dirname(os.path.abspath(__file__))
N_JUNCTIONS = 4

# Base arrival rates (veh/s) at scale=1.0. Arterial dominates; cross is light.
ARTERIAL_RATE = 0.18   # per direction, ~650 veh/h each way
CROSS_RATE = 0.035     # per cross approach, ~125 veh/h each


def _arterial_route_eastbound() -> str:
    edges = ["WJ0"] + [f"J{i}J{i+1}" for i in range(N_JUNCTIONS - 1)] + [
        f"J{N_JUNCTIONS-1}E"]
    return " ".join(edges)


def _arterial_route_westbound() -> str:
    edges = [f"EJ{N_JUNCTIONS-1}"] + [
        f"J{i}J{i-1}" for i in range(N_JUNCTIONS - 1, 0, -1)] + ["J0W"]
    return " ".join(edges)


def write_routes(path: str, scale: float = 1.0) -> None:
    if not (isinstance(scale, (int, float)) and scale > 0):
        raise ValueError(f"scale must be a positive number, got {scale!r}")
    art = ARTERIAL_RATE * scale
    cross = CROSS_RATE * scale
    lines = ['<?xml version="1.0" encoding="UTF-8"?>', "<routes>"]
    lines.append('  <vType id="car" accel="2.6" decel="4.5" length="5.0" '
                 'minGap="2.5" maxSpeed="13.89" sigma="0.5"/>')
    # Arterial through routes (the platooned flows).
    lines.append(f'  <route id="eb" edges="{_arterial_route_eastbound()}"/>')
    lines.append(f'  <route id="wb" edges="{_arterial_route_westbound()}"/>')
    lines.append(
        f'  <flow id="art_eb" type="car" route="eb" begin="0" end="3600" '
        f'period="exp({art:.4f})" departLane="best" departSpeed="max"/>')
    lines.append(
        f'  <flow id="art_wb" type="car" route="wb" begin="0" end="3600" '
        f'period="exp({art:.4f})" departLane="best" departSpeed="max"/>')
    # Cross routes per junction (light): N_i -> S_i and S_i -> N_i straight over.
    for i in range(N_JUNCTIONS):
        lines.append(
            f'  <route id="ns{i}" edges="N{i}J{i} J{i}S{i}"/>')
        lines.append(
            f'  <route id="sn{i}" edges="S{i}J{i} J{i}N{i}"/>')
        lines.append(
            f'  <flow id="cross_ns{i}" type="car" route="ns{i}" begin="0" '
            f'end="3600" period="exp({cross:.4f})" departSpeed="max"/>')
        lines.append(
            f'  <flow id="cross_sn{i}" type="car" route="sn{i}" begin="0" '
            f'end="3600" period="exp({cross:.4f})" departSpeed="max"/>')
    lines.append("</routes>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Generate corridor demand.")
    ap.add_argument("--scale", type=float, default=1.0,
                    help="multiply all arrival rates (demand intensity).")
    ap.add_argument("--out", default=os.path.join(HERE, "corridor.rou.xml"))
    args = ap.parse_args()
    write_routes(args.out, scale=args.scale)
    print(f"[wrote] {args.out} (scale={args.scale})")
