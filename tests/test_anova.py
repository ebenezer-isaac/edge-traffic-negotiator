"""Tests for the pure-Python two-way ANOVA + F-test (src/anova.py).

Verifies the incomplete-beta / F-distribution against known values and the ANOVA against a
hand-computable balanced design, so the inferential interaction test can be trusted without
scipy."""
import os
import sys

_SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import anova  # noqa: E402


def test_betai_symmetry_and_midpoint():
    # I_0.5(a, a) = 0.5 for any a (symmetry of the Beta distribution)
    assert abs(anova.betai(5, 5, 0.5) - 0.5) < 1e-9
    assert abs(anova.betai(2, 2, 0.5) - 0.5) < 1e-9
    assert anova.betai(3, 4, 0.0) == 0.0
    assert anova.betai(3, 4, 1.0) == 1.0


def test_f_sf_known_values():
    # F=1 with equal df -> upper tail = 0.5 (median of a central F is not 1 in general,
    # but P(F>1) = I_{d2/(d2+d1)}(d2/2,d1/2) = I_0.5(5,5) = 0.5 when d1=d2)
    assert abs(anova.f_sf(1.0, 10, 10) - 0.5) < 1e-6
    # large F -> tiny p; F=0 -> p=1
    assert anova.f_sf(0.0, 3, 12) == 1.0
    assert anova.f_sf(100.0, 3, 12) < 1e-3
    # monotone decreasing in F
    assert anova.f_sf(2.0, 4, 20) > anova.f_sf(5.0, 4, 20)


def test_two_way_no_interaction_is_additive():
    # perfectly additive cells (a_i + b_j), n=2 with tiny symmetric noise -> interaction ~0,
    # so its SS is negligible and p is large.
    cells = {
        ("m1", "s1"): [10.0, 10.0], ("m1", "s2"): [20.0, 20.0],
        ("m2", "s1"): [14.0, 14.0], ("m2", "s2"): [24.0, 24.0],
    }
    r = anova.two_way(cells, ["m1", "m2"], ["s1", "s2"])
    assert r["interaction"]["SS"] < 1e-9          # additive -> no interaction
    # main effects are real (model +4, scenario +10)
    assert r["model"]["SS"] > 0 and r["scenario"]["SS"] > 0


def test_two_way_detects_crossover_interaction():
    # a disordinal (crossover) interaction: m1 wins s1, m2 wins s2, tight within-cell spread.
    cells = {
        ("m1", "s1"): [-25.0, -24.0], ("m1", "s2"): [+60.0, +61.0],
        ("m2", "s1"): [-15.0, -16.0], ("m2", "s2"): [+40.0, +39.0],
    }
    r = anova.two_way(cells, ["m1", "m2"], ["s1", "s2"])
    assert r["interaction"]["F"] is not None
    assert r["interaction"]["SS"] > 0
    # with tight within-cell variance the interaction should be highly significant
    assert r["interaction"]["p"] < 0.05


def test_unbalanced_and_n1_rejected():
    import pytest
    with pytest.raises(ValueError):
        anova.two_way({("m", "s1"): [1.0, 2.0], ("m", "s2"): [1.0]}, ["m"], ["s1", "s2"])
    with pytest.raises(ValueError):
        anova.two_way({("m", "s"): [1.0]}, ["m"], ["s"])   # n=1 -> no interaction test
