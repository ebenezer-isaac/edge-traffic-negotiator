"""Full-frontier model sweep: EVERY servable Foundry model (smallest -> 6GB, GPU) as the
single-junction SLM controller, across every topology and seed, capturing EVERY data point
to disk for later review/analysis. No latency gate -- reasoning models run too; we record what
happens (latency cost vs any reasoning gain) instead of skipping them.

Per cell (model x topology x seed) we persist results/frontier_raw/<model>__<map>__s<seed>.json
with: baseline + SLM mean_network_delay, delay_rel_pct, the FULL metrics dict, the FULL
decision_stats (override / agreement / authored / served counts), the FULL per-decision latency
list (every choose_phase wall-clock, not just percentiles), the latency summary, wall-clock, and
the audit verification (chain ok + record count). Resumable: a cell whose raw file exists is
skipped, so the sweep survives restarts and Foundry evictions.

Aggregation (experiment_frontier.py --aggregate) rolls the raw cells into results/
experiment_frontier.json: per (model, topology) mean/std of delay_rel + override_rate + latency
percentiles, plus a balanced two-way ANOVA (model x topology) via src/anova.py when the design
supports it. Reuses run_arm / TimingAgent / summarize_latency / _topologies unchanged.

DEMAND HONESTY: demand is still DfT daily-resolution (MASTER-SPEC §8); these are cross-seed
descriptive/interaction results, not absolute significance vs live time-resolved London demand.
That is a data fact, not a scope choice.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import traceback

_SRC = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(_SRC), "results")
RAW = os.path.join(RESULTS, "frontier_raw")

from anova import two_way  # noqa: E402
from experiment_topology import _tls_count, _topologies  # noqa: E402
from experiment_traffic import NullAgent, TimingAgent, run_arm  # noqa: E402
from slm_agent import SLMAgent, discover_endpoint  # noqa: E402
from slm_latency import summarize_latency  # noqa: E402

# Every chat/tools-capable Foundry model with a GPU file size <= 6 GB (fits the 6 GB RTX 2060),
# smallest -> largest. Full Foundry model IDs (the OpenAI-compatible endpoint wants the ID).
# qwen3.5 VISION variants are omitted: they fail to load in this Foundry runtime (genai_config
# vision parse error) -- recorded as an infra gate elsewhere, not silently dropped.
CATALOG = {
    "qwen3-0.6b": "qwen3-0.6b-generic-gpu:2",
    "qwen2.5-coder-0.5b": "qwen2.5-coder-0.5b-instruct-generic-gpu:4",
    "qwen2.5-0.5b": "qwen2.5-0.5b-instruct-generic-gpu:4",
    "qwen2.5-coder-1.5b": "qwen2.5-coder-1.5b-instruct-generic-gpu:4",
    "qwen3.5-2b-text": "qwen3.5-2b-text-generic-gpu:3",
    "qwen3-1.7b": "qwen3-1.7b-generic-gpu:2",
    "qwen2.5-1.5b": "qwen2.5-1.5b-instruct-generic-gpu:4",
    "phi-3.5-mini": "Phi-3.5-mini-instruct-generic-gpu:2",
    "smollm3-3b": "smollm3-3b-generic-gpu:1",
    "qwen3-4b": "qwen3-4b-generic-gpu:2",
    "phi-4-mini-reasoning": "Phi-4-mini-reasoning-generic-gpu:3",
    "ministral-3-3b": "ministral-3-3b-instruct-2512-generic-gpu:1",
    "phi-4-mini": "Phi-4-mini-instruct-generic-gpu:5",
    "mistral-7b-v0.2": "mistralai-Mistral-7B-Instruct-v0-2-generic-gpu:2",
    "qwen2.5-coder-7b": "qwen2.5-coder-7b-instruct-generic-gpu:4",
    "qwen2.5-7b": "qwen2.5-7b-instruct-generic-gpu:4",
    "qwen3.5-4b-text": "qwen3.5-4b-generic-gpu:2",  # attempt; may be VL-broken -> honest skip
    "olmo-3-7b": "olmo-3-7b-instruct-generic-gpu:1",
    "deepseek-r1-7b": "deepseek-r1-distill-qwen-7b-generic-gpu:4",
    "qwen3-8b": "qwen3-8b-generic-gpu:2",  # 6.00 GB, borderline; may OOM -> honest capture
}

DEFAULT_SEEDS = (42, 7, 123)
DEFAULT_END = 1200
DEFAULT_GATE = 2
# Prompting / information configs. "sota" = the delay-aware myopic mode (waiting-time priority +
# switching hysteresis). coordination/prediction add the signed neighbour layer.
DEFAULT_CONFIGS = ("myopic", "sota", "coordination", "prediction")


def _raw_path(model, label, config, seed):
    safe = model.replace("/", "_")
    return os.path.join(RAW, f"{safe}__{label}__{config}__s{seed}.json")


def _baseline_path(label, seed):
    return os.path.join(RAW, f"BASELINE__{label}__s{seed}.json")


def _warm_probe(agent, tries=6, sleep_s=8.0):
    """Warm a possibly-cold model. NO latency skip: retry across cold-load. Returns (ok, detail).

    Makes a RAW chat call so the TRUE error surfaces (SLMAgent.choose_phase swallows exceptions
    to None, which previously masked HTTP 400 = model-not-downloaded as 'malformed decision').
    Fails FAST on a 400 (not on disk / not loadable in this runtime -- retrying wastes time);
    retries on transient/connection/5xx (genuine cold-load)."""
    last = "no attempt"
    for i in range(tries):
        try:
            r = agent.client.chat.completions.create(
                model=agent.model, temperature=0, max_tokens=48,
                messages=[{"role": "system", "content": 'Reply ONLY JSON {"phase": <index>}.'},
                          {"role": "user", "content": 'phase 0=8, phase 1=0. Reply {"phase": <index>}.'}])
            content = (r.choices[0].message.content or "")
            if agent.choose_phase("PROBE", 2, [8, 0]) is not None:
                return True, f"probe ok attempt {i + 1}"
            last = f"unparseable output: {content[:90]!r}"
        except Exception as exc:  # noqa: BLE001
            code = getattr(exc, "status_code", None) or getattr(getattr(exc, "response", None), "status_code", None)
            last = f"{type(exc).__name__}({code}): {str(exc)[:110]}"
            if code == 400 or " 400" in str(exc) or "400 -" in str(exc):
                return False, f"HTTP 400 (model not downloaded/loadable in this runtime): {last}"
        time.sleep(sleep_s)
    return False, f"probe failed after {tries} tries: {last}"


def _is_conn_error(detail: str) -> bool:
    return "Connection" in (detail or "") or "APIConnection" in (detail or "")


def _ensure_foundry():
    """Revive a crashed/hung Foundry Local service and return the (possibly new) endpoint.

    This hardware's Foundry service dies under sustained inference; on a connection failure we
    restart it and re-discover the port so a crash mid-sweep self-heals instead of recording a
    wall of false 'blocked' cells."""
    import subprocess
    # Only `start` -- it returns fast whether the service is down or already up. `restart` hangs
    # on this runtime (spawns detached children that wedge subprocess pipes), so never call it here.
    try:
        subprocess.run(["foundry", "service", "start"], timeout=40, capture_output=True)
    except Exception:  # noqa: BLE001
        pass
    time.sleep(8)
    try:
        base, _ = discover_endpoint()
        return base
    except Exception:  # noqa: BLE001
        return None


def _baseline(label, net, routes, seed, end, gate):
    p = _baseline_path(label, seed)
    if os.path.exists(p):
        with open(p, encoding="utf-8") as fh:
            return json.load(fh)["mean_network_delay_s"]
    b = run_arm(f"fr_{label}_mp_s{seed}", NullAgent(), seed=seed, end=end, gate=gate,
                config="myopic", net=net, routes=routes)
    d = b["metrics"]["mean_network_delay_s"]
    os.makedirs(RAW, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump({"topology": label, "seed": seed, "mean_network_delay_s": d,
                   "metrics": b["metrics"], "decision_stats": b.get("decision_stats")}, fh, indent=2)
    return d


def _run_cell(model, model_id, label, net, routes, config, seed, end, gate, base_delay):
    """Run one (model, config, topology, seed) cell and persist EVERY data point. Never raises:
    any failure is captured into the raw file so the sweep continues and stays analysable."""
    p = _raw_path(model, label, config, seed)
    rec = {"model": model, "model_id": model_id, "topology": label, "seed": seed,
           "config": config, "end": end, "gate": gate, "baseline_delay_s": base_delay}
    t0 = time.perf_counter()
    try:
        base, _ = discover_endpoint()
        agent = SLMAgent(base_url=base, model=model_id)
        ok, detail = _warm_probe(agent)
        # Self-heal: if Foundry is unreachable, revive it and retry once with the fresh port.
        if not ok and _is_conn_error(detail):
            new_base = _ensure_foundry()
            if new_base:
                agent = SLMAgent(base_url=new_base, model=model_id)
                ok, detail = _warm_probe(agent)
        rec["probe"] = detail
        if not ok:
            # A persistent CONNECTION failure is Foundry-down, NOT a model verdict: DEFER
            # (write no file) so a later pass re-attempts it. Only a real 400/unparseable/OOM
            # is recorded as a blocked cell.
            if _is_conn_error(detail):
                rec.update({"status": "deferred", "reason": detail})
                return rec
            rec.update({"status": "blocked", "reason": detail})
            with open(p, "w", encoding="utf-8") as fh:
                json.dump(rec, fh, indent=2)
            return rec
        # forward_note lets the neighbour coordination note through (coord/pred). myopic/sota
        # are own-junction: sota's delay-aware phase_context is forwarded regardless.
        timing = TimingAgent(agent, forward_note=(config != "myopic"))
        slm = run_arm(f"fr_{label}_{model}_{config}_s{seed}", timing, seed=seed, end=end, gate=gate,
                      config=config, net=net, routes=routes)
        d = slm["metrics"]["mean_network_delay_s"]
        ds = slm.get("decision_stats", {}) or {}
        served = ds.get("slm_proposal_served", 0) or 0
        diverged = ds.get("slm_diverged_and_served", 0) or 0
        agreed = ds.get("slm_agreed_with_shield", 0) or 0
        valid = ds.get("slm_valid_proposals", 0) or 0
        audit = slm.get("audit", {}) or {}
        rec.update({
            "status": "measured",
            "slm_delay_s": d,
            "delay_rel_pct": round((d - base_delay) / base_delay * 100.0, 4) if base_delay else None,
            "override_rate": round(diverged / served, 4) if served else 0.0,
            "agreement_rate": round(agreed / served, 4) if served else 0.0,
            "authored_share": round(served / valid, 4) if valid else 0.0,
            "metrics": slm["metrics"],
            "decision_stats": ds,
            "coordination": slm.get("coordination"),   # neighbour-exchange stats (coord/pred)
            "latencies_s": list(getattr(timing, "latencies_s", [])),   # EVERY per-decision call
            "latency_summary": summarize_latency(getattr(timing, "latencies_s", []), warmup=1),
            "audit_verify_chain": audit.get("verify_chain"),
            "audit_records": audit.get("n_records") or audit.get("count"),
            "wall_clock_s": round(time.perf_counter() - t0, 2),
        })
    except Exception as exc:  # noqa: BLE001
        rec.update({"status": "error", "reason": f"{type(exc).__name__}: {exc}",
                    "traceback": traceback.format_exc()[-1500:],
                    "wall_clock_s": round(time.perf_counter() - t0, 2)})
    os.makedirs(RAW, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2)
    return rec


def sweep(models, configs=DEFAULT_CONFIGS, seeds=DEFAULT_SEEDS, end=DEFAULT_END, gate=DEFAULT_GATE,
          topologies=None):
    os.makedirs(RAW, exist_ok=True)
    tops = [t for t in _topologies() if os.path.exists(t["net"]) and os.path.exists(t["routes"])
            and (topologies is None or t["label"] in topologies)]
    total = len(models) * len(configs) * len(tops) * len(seeds)
    print(f"frontier sweep: {len(models)} models x {len(configs)} configs x {len(tops)} topologies "
          f"x {len(seeds)} seeds = {total} cells", flush=True)
    done = 0
    deferred = 0
    for top in tops:
        label, net, routes = top["label"], top["net"], top["routes"]
        for s in seeds:
            base_delay = _baseline(label, net, routes, s, end, gate)
            print(f"  [{label} s{s}] baseline delay={base_delay:.1f}s", flush=True)
            for cfg in configs:
                for m in models:
                    done += 1
                    mid = CATALOG.get(m, m)
                    p = _raw_path(m, label, cfg, s)
                    if os.path.exists(p):
                        print(f"    [{done}/{total}] {m:20s} {cfg:12s} SKIP", flush=True)
                        continue
                    rec = _run_cell(m, mid, label, net, routes, cfg, s, end, gate, base_delay)
                    st = rec.get("status")
                    if st == "deferred":
                        deferred += 1
                    extra = (f"delay={rec.get('slm_delay_s',0):.1f}s rel={rec.get('delay_rel_pct')}% "
                             f"ovr={rec.get('override_rate')} p99={rec.get('latency_summary',{}).get('p99')}"
                             if st == "measured" else rec.get("reason", "")[:60])
                    print(f"    [{done}/{total}] {m:20s} {cfg:12s} {st:9s} {extra}", flush=True)
    print(f"sweep pass complete (deferred={deferred})", flush=True)
    return deferred


def _agg(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    m = sum(xs) / len(xs)
    sd = (sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5 if len(xs) > 1 else 0.0
    return {"mean": round(m, 2), "std": round(sd, 2), "min": round(min(xs), 2),
            "max": round(max(xs), 2), "n": len(xs), "values": [round(x, 2) for x in xs]}


def _interaction(anova_cells, models, tops):
    """Balanced two-way ANOVA over the largest fully-replicated (model x topology) sub-grid."""
    a_models = [m for m in models if all((m, t) in anova_cells for t in tops)]
    common = [t for t in tops if all((m, t) in anova_cells for m in a_models)]
    a_models = [m for m in a_models if all((m, t) in anova_cells for t in common)]
    if len(a_models) >= 2 and len(common) >= 2:
        ns = {len(anova_cells[(m, t)]) for m in a_models for t in common}
        if len(ns) == 1 and ns.pop() >= 2:
            try:
                return (two_way({(m, t): anova_cells[(m, t)] for m in a_models for t in common},
                                a_models, common), a_models, common)
            except Exception as exc:  # noqa: BLE001
                return ({"error": str(exc)}, a_models, common)
    return (None, a_models, common)


def aggregate(seeds=DEFAULT_SEEDS, end=DEFAULT_END, gate=DEFAULT_GATE):
    """Roll raw cells into experiment_frontier.json, grouped by config (partial ok). Each config
    gets its own model x topology matrix + interaction ANOVA."""
    tops = [t["label"] for t in _topologies()]
    by = {}      # (config, model, label) -> accumulators
    configs, models = set(), set()
    for fn in sorted(os.listdir(RAW)) if os.path.isdir(RAW) else []:
        if fn.startswith("BASELINE__") or not fn.endswith(".json"):
            continue
        with open(os.path.join(RAW, fn), encoding="utf-8") as fh:
            r = json.load(fh)
        cfg = r.get("config", "myopic")
        key = (cfg, r["model"], r["topology"])
        configs.add(cfg); models.add(r["model"])
        d = by.setdefault(key, {"rel": [], "ovr": [], "lat_p99": [], "lat_p50": [],
                                "wall": [], "status": []})
        d["status"].append(r.get("status"))
        if r.get("status") == "measured":
            d["rel"].append(r.get("delay_rel_pct"))
            d["ovr"].append(r.get("override_rate"))
            d["lat_p99"].append((r.get("latency_summary") or {}).get("p99"))
            d["lat_p50"].append((r.get("latency_summary") or {}).get("p50"))
            d["wall"].append(r.get("wall_clock_s"))

    live_models = sorted(models)
    by_config = {}
    for cfg in sorted(configs):
        anova_cells = {}
        rows = []
        for m in live_models:
            row = {"model": m, "topologies": {}}
            for label in tops:
                d = by.get((cfg, m, label))
                if not d:
                    continue
                cell = {"n_measured": sum(1 for s in d["status"] if s == "measured"),
                        "n_attempts": len(d["status"]), "statuses": d["status"],
                        "delay_rel_pct": _agg(d["rel"]), "override_rate": _agg(d["ovr"]),
                        "latency_p99_s": _agg(d["lat_p99"]), "latency_p50_s": _agg(d["lat_p50"])}
                row["topologies"][label] = cell
                if cell["delay_rel_pct"] and cell["delay_rel_pct"]["n"] >= 2:
                    anova_cells[(m, label)] = cell["delay_rel_pct"]["values"]
            if row["topologies"]:
                rows.append(row)
        anova, a_models, a_tops = _interaction(anova_cells, live_models, tops)
        by_config[cfg] = {"cells": rows, "interaction_anova": anova,
                          "anova_scope": {"models": a_models, "topologies": a_tops}}

    out = {"experiment": "H1_frontier_sweep", "configs": sorted(configs), "seeds": list(seeds),
           "end": end, "gate": gate, "models": live_models, "by_config": by_config,
           "demand_note": ("DfT daily-resolution demand (MASTER-SPEC §8): cross-seed descriptive / "
                           "interaction results, NOT absolute significance vs live TfL demand."),
           "raw_dir": "results/frontier_raw/"}
    jp = os.path.join(RESULTS, "experiment_frontier.json")
    with open(jp, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"aggregated {len(live_models)} models x {len(configs)} configs -> {jp}", flush=True)
    for cfg, blk in by_config.items():
        a = blk["interaction_anova"]
        if a and "interaction" in a:
            i = a["interaction"]
            print(f"  [{cfg}] interaction F={i['F']} p={i['p']} eta2={i['partial_eta_sq']}", flush=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Full-frontier Foundry model sweep (<=6GB GPU).")
    ap.add_argument("--models", nargs="*", default=None,
                    help="model aliases (default: entire <=6GB CATALOG, smallest first)")
    ap.add_argument("--configs", nargs="*", default=list(DEFAULT_CONFIGS),
                    help="prompting configs (myopic sota coordination prediction)")
    ap.add_argument("--topologies", nargs="*", default=None,
                    help="restrict to these topology labels (default: all)")
    ap.add_argument("--seeds", nargs="*", type=int, default=list(DEFAULT_SEEDS))
    ap.add_argument("--end", type=int, default=DEFAULT_END)
    ap.add_argument("--gate", type=int, default=DEFAULT_GATE)
    ap.add_argument("--aggregate", action="store_true", help="only roll up existing raw cells")
    ap.add_argument("--max-passes", type=int, default=12,
                    help="re-run passes until no cells are deferred (Foundry-down self-heal)")
    ns = ap.parse_args()
    if ns.aggregate:
        aggregate(seeds=tuple(ns.seeds), end=ns.end, gate=ns.gate)
    else:
        ms = ns.models if ns.models else list(CATALOG.keys())
        for pass_i in range(1, ns.max_passes + 1):
            _ensure_foundry()  # make sure the service is up before each pass
            print(f"===== PASS {pass_i}/{ns.max_passes} =====", flush=True)
            deferred = sweep(ms, configs=tuple(ns.configs), seeds=tuple(ns.seeds),
                             end=ns.end, gate=ns.gate, topologies=ns.topologies)
            aggregate(seeds=tuple(ns.seeds), end=ns.end, gate=ns.gate)
            if not deferred:
                print(f"all cells resolved after pass {pass_i}", flush=True)
                break
            print(f"pass {pass_i}: {deferred} cells deferred (Foundry-down); retrying", flush=True)
