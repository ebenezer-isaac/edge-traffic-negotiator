"""Summarise the real-demand sweep: each SLM arm vs MaxPressure in the same (day, hour) cell."""
import json
import os
import statistics as st

HERE = os.path.dirname(os.path.abspath(__file__))
cells = json.load(open(os.path.join(HERE, "results", "scoot_sweep_v2.json"), encoding="utf-8"))["cells"]
DAYS = ("2026-05-12", "2026-05-13", "2026-05-14")
ARMS = ("slm:phi-4-mini", "slm:phi4mini-gen-gpu", "slm:qwen3-0.6b-ft1", "slm:qwen3-0.6b-ft2")


def cell(arm, day, hour):
    return cells.get(f"{arm}|{day}|{hour:02d}")


mp = [c for k, c in cells.items() if k.startswith("maxpressure|") and "error" not in c]
print(f"maxpressure: n={len(mp)} mean delay {st.mean(c['delay_s'] for c in mp):.1f}s "
      f"completed/cell {st.mean(c['completed'] for c in mp):.0f} teleports {sum(c['teleports'] for c in mp)}")
print(f"{'arm':24} {'median%':>8} {'mean%':>7} {'ties':>5} {'worse':>6} {'compl/cell':>10} {'teleports':>9}")
for arm in ARMS:
    pairs = [(cell("maxpressure", d, h), cell(arm, d, h)) for d in DAYS for h in range(24)]
    pairs = [(m, s) for m, s in pairs if m and s and "error" not in m and "error" not in s]
    rel = [(s["delay_s"] - m["delay_s"]) / m["delay_s"] * 100 for m, s in pairs]
    ties = sum(1 for m, s in pairs if s["delay_s"] == m["delay_s"])
    worse = sum(1 for m, s in pairs if s["delay_s"] > m["delay_s"])
    dcomp = st.mean(s["completed"] - m["completed"] for m, s in pairs)
    print(f"{arm:24} {st.median(rel):+8.2f} {st.mean(rel):+7.2f} {ties:5d} {worse:6d} {dcomp:+10.1f} "
          f"{sum(s['teleports'] for _, s in pairs):9d}")
