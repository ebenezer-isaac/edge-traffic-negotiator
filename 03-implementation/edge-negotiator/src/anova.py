"""Two-way ANOVA with replication + an F-test p-value, in pure Python.

The full-scale phase adds >=2 seeds per (model, scenario) cell so the model x scenario
INTERACTION becomes inferentially testable (Alin & Kurt 2006: at n=1 it is not). This module
gives the balanced two-way ANOVA (model, scenario, interaction) and an F-distribution upper
tail via the regularised incomplete beta function -- no scipy dependency (protects the
reproducible Foundry environment), implemented from Numerical Recipes and unit-tested against
known values.

  F upper tail:  P(F_{d1,d2} > F) = I_x(d2/2, d1/2),  x = d2 / (d2 + d1*F)
"""
from __future__ import annotations

import math

_FPMIN = 1e-300
_EPS = 3e-16


def _betacf(a: float, b: float, x: float) -> float:
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < _FPMIN:
        d = _FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, 300):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < _FPMIN:
            d = _FPMIN
        c = 1.0 + aa / c
        if abs(c) < _FPMIN:
            c = _FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < _EPS:
            break
    return h


def betai(a: float, b: float, x: float) -> float:
    """Regularised incomplete beta I_x(a, b)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def f_sf(f: float, d1: int, d2: int) -> float:
    """Upper-tail p-value P(F_{d1,d2} > f)."""
    if f <= 0.0:
        return 1.0
    x = d2 / (d2 + d1 * f)
    return betai(d2 / 2.0, d1 / 2.0, x)


def _mean(xs):
    return sum(xs) / len(xs)


def two_way(cells: dict, factor_a: list, factor_b: list) -> dict:
    """Balanced two-way ANOVA with replication.

    ``cells``: {(a_level, b_level): [replicate values]}. Every cell must have the SAME number
    of replicates n >= 2. ``factor_a`` (e.g. models), ``factor_b`` (e.g. scenarios) are the
    level lists. Returns SS/df/MS/F/p and partial eta-squared for A, B, and the A:B interaction.
    """
    a, b = len(factor_a), len(factor_b)
    ns = {len(cells[(i, j)]) for i in factor_a for j in factor_b}
    if len(ns) != 1:
        raise ValueError(f"unbalanced design: replicate counts {ns} (need equal n per cell)")
    n = ns.pop()
    if n < 2:
        raise ValueError("interaction needs n >= 2 replicates per cell")
    all_vals = [v for i in factor_a for j in factor_b for v in cells[(i, j)]]
    grand = _mean(all_vals)
    cell_mean = {(i, j): _mean(cells[(i, j)]) for i in factor_a for j in factor_b}
    a_mean = {i: _mean([v for j in factor_b for v in cells[(i, j)]]) for i in factor_a}
    b_mean = {j: _mean([v for i in factor_a for v in cells[(i, j)]]) for j in factor_b}

    ss_a = b * n * sum((a_mean[i] - grand) ** 2 for i in factor_a)
    ss_b = a * n * sum((b_mean[j] - grand) ** 2 for j in factor_b)
    ss_ab = n * sum((cell_mean[(i, j)] - a_mean[i] - b_mean[j] + grand) ** 2
                    for i in factor_a for j in factor_b)
    ss_within = sum((v - cell_mean[(i, j)]) ** 2
                    for i in factor_a for j in factor_b for v in cells[(i, j)])
    ss_total = sum((v - grand) ** 2 for v in all_vals)

    df_a, df_b = a - 1, b - 1
    df_ab = (a - 1) * (b - 1)
    df_within = a * b * (n - 1)

    def term(ss, df):
        ms = ss / df if df else 0.0
        ms_w = ss_within / df_within if df_within else 0.0
        f = ms / ms_w if ms_w > 0 else None
        p = f_sf(f, df, df_within) if f is not None else None
        # partial eta-squared = SS_effect / (SS_effect + SS_error)
        peta = ss / (ss + ss_within) if (ss + ss_within) > 0 else None
        return {"SS": round(ss, 4), "df": df, "MS": round(ms, 4),
                "F": round(f, 4) if f is not None else None,
                "p": round(p, 5) if p is not None else None,
                "partial_eta_sq": round(peta, 4) if peta is not None else None}

    return {
        "n_per_cell": n, "levels_a": factor_a, "levels_b": factor_b,
        "grand_mean": round(grand, 4),
        "model": term(ss_a, df_a),
        "scenario": term(ss_b, df_b),
        "interaction": term(ss_ab, df_ab),
        "within": {"SS": round(ss_within, 4), "df": df_within,
                   "MS": round(ss_within / df_within, 4) if df_within else None},
        "ss_total": round(ss_total, 4),
    }
