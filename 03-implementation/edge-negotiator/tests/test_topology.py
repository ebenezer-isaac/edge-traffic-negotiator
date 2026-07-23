"""Tests for the multi-topology explanatory analysis (src/experiment_topology.py).

The live cross-topology run needs Foundry+SUMO; these pin the PURE explanatory logic
(gridlock proxy + the win-grows-with-gridlock trend) so the "why" analysis cannot
misreport its own direction."""
import os
import re
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import experiment_topology as tp  # noqa: E402


def _cell(label, tls, b_delay, b_completed, b_departed, b_teleports,
          m_delay_rel, joint):
    return {"topology": label, "structure": "x", "tls": tls,
            "baseline": {"delay_s": b_delay, "completed": b_completed,
                         "departed": b_departed, "teleports": b_teleports},
            "models": {"M": {"delay_rel": m_delay_rel, "joint_verdict": joint,
                             "delay_s": b_delay * (1 + m_delay_rel), "completed": 1,
                             "throughput_status": "slm_beats", "delay_status": "slm_beats"}}}


def test_explain_trend_supported_when_win_grows_with_gridlock():
    # High-gridlock topology (many teleports + stranded) has the BIG delay win; low-
    # gridlock has a small one -> hypothesis supported.
    cells = [
        _cell("hi_gridlock", 4, 314.0, 361, 624, 65, -0.25, "clean_win"),   # -25% win
        _cell("lo_gridlock", 9, 96.0, 290, 300, 2, -0.02, "match"),         # ~0% win
    ]
    ex = tp._explain(cells, ["M"])
    assert "supported" in ex["trend"]
    assert len(ex["observations"]) == 2
    # the high-gridlock row must carry the larger gridlock proxy
    hi = next(o for o in ex["observations"] if o["topology"] == "hi_gridlock")
    lo = next(o for o in ex["observations"] if o["topology"] == "lo_gridlock")
    assert hi["baseline_gridlock_proxy"] > lo["baseline_gridlock_proxy"]


def test_explain_trend_not_supported_when_inverted():
    # Win is BIG where gridlock is LOW -> hypothesis NOT supported (honest negative).
    cells = [
        _cell("hi_gridlock", 4, 314.0, 361, 624, 65, -0.02, "match"),
        _cell("lo_gridlock", 9, 96.0, 290, 300, 2, -0.25, "clean_win"),
    ]
    ex = tp._explain(cells, ["M"])
    assert "not supported" in ex["trend"]


def test_explain_skips_gated_and_skipped_cells():
    cells = [
        {"topology": "t1", "skipped": True, "reason": "x"},
        _cell("t2", 4, 300.0, 300, 600, 10, -0.10, "clean_win"),
    ]
    cells[1]["models"]["M2"] = {"skipped": True, "reason": "foundry down"}
    ex = tp._explain(cells, ["M", "M2"])
    # only the M cell of t2 contributes; skipped topology + gated model excluded.
    assert len(ex["observations"]) == 1
    assert ex["observations"][0]["topology"] == "t2"


def test_stranded_fraction_in_gridlock_proxy():
    # gridlock proxy = teleports + 100*stranded_fraction. Verify it rewards both.
    ex = tp._explain([_cell("t", 4, 300.0, 300, 600, 10, -0.1, "clean_win")], ["M"])
    o = ex["observations"][0]
    # stranded = (600-300)/600 = 0.5 -> proxy = 10 + 50 = 60
    assert o["baseline_stranded_frac"] == 0.5
    assert o["baseline_gridlock_proxy"] == 60.0


def test_topology_list_has_euston_and_grids():
    labels = [t["label"] for t in tp._topologies()]
    assert "euston_corridor" in labels
    assert any("grid" in l for l in labels)


def test_topology_list_has_real_london_bloomsbury():
    # Full-scale req 5: "not just a straight corridor but also multiple variations of the
    # map in london". Bloomsbury is a REAL London grid (OSM), not a synthetic one.
    tops = tp._topologies()
    labels = [t["label"] for t in tops]
    assert "bloomsbury_grid" in labels
    bloom = next(t for t in tops if t["label"] == "bloomsbury_grid")
    # its net/routes must point at the real extracted London assets, not a synthetic grid
    assert "bloomsbury" in bloom["net"].replace("\\", "/").lower()
    assert os.path.exists(bloom["net"]), "bloomsbury net must be committed"
    assert os.path.exists(bloom["routes"]), "bloomsbury demand must be committed"
    # PROVENANCE (not just filename): the net must carry a real OSM->UTM projection and a
    # geo-boundary inside the Bloomsbury WC1 bbox. A synthetic grid saved at this path would
    # have no such projParameter/origBoundary and would fail here.
    with open(bloom["net"], encoding="utf-8") as fh:
        head = fh.read(4000)
    assert "+proj=utm" in head, "real OSM net must be UTM-projected, not synthetic"
    m = re.search(r'origBoundary="([^"]+)"', head)
    assert m, "real OSM net must carry an origBoundary (lat/lon extent)"
    lon0, lat0, lon1, lat1 = (float(x) for x in m.group(1).split(","))
    # Bloomsbury WC1 is ~51.52N, -0.12W; assert the boundary sits in that real-London box.
    assert 51.51 < lat0 < 51.53 and 51.51 < lat1 < 51.53, f"lat outside Bloomsbury: {lat0},{lat1}"
    assert -0.14 < lon0 < -0.11 and -0.14 < lon1 < -0.11, f"lon outside Bloomsbury: {lon0},{lon1}"
