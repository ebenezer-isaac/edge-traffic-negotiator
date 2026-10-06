"""Fine-tuning dataset builder (MASTER-SPEC §14.3 step 3): sample junction decision states
at scale (pure-CPU SUMO, no SLM/GPU), emit Claude-labeling batches in the byte-identical LIVE
controller prompt, ingest labels through a deterministic verifier, and render train/held-out
JSONL for QLoRA.

PINNED DESIGN DECISIONS (§14.4 provenance):
  * SOTA/DELAY-AWARE FORMAT ONLY. States are sampled under config="sota" and rendered with
    slm_agent.build_delay_aware_user + SYSTEM_DELAY_AWARE — the config that delivered the
    powered wins and fewer catastrophic failures. A single canonical format avoids conflicting
    labels for identical myopic prompts (same halting vector, different waiting).
  * Teacher = Claude (in-session subagents; model identity recorded per batch). The verifier
    is a SANITY filter, not a rule-match: (a) phase index in range; (b) never serve a phase
    with zero queued AND zero waiting while another phase has demand. Filtering labels to
    match the greedy reference would just distill the greedy rule and void the teacher.
  * Dedupe BEFORE splitting: key = (topology, junction, queues, waiting bucketed to 10s,
    current-phase index). Held-out split is deterministic (sha256 of key, ~1 in 12), frozen
    at build time, and never labeled/trained across the boundary.
  * Train targets emit exactly {"phase": N} (unquoted int — SLMAgent._parse's primary regex).
  * The trailing " /no_think" think-suffix is part of the SERVED system prompt for qwen3
    aliases, so it is included verbatim in every rendered training/labeling system prompt.

Pipeline:
  --step sample : run every available topology x --seeds with a SamplingAgent -> states pool
  --step emit   : dedupe + split + write labeling batches (results/ft_dataset/batch_*.json)
  --step build  : ingest label files (labels_*.json), verify, render train.jsonl/holdout.jsonl
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os

_SRC = os.path.dirname(os.path.abspath(__file__))
RESULTS = os.path.join(os.path.dirname(_SRC), "results")
FTDIR = os.path.join(RESULTS, "ft_dataset")

from claude_decision_battery import SamplingAgent  # noqa: E402
from experiment_topology import _topologies  # noqa: E402
from experiment_traffic import run_arm  # noqa: E402
from slm_agent import SYSTEM_DELAY_AWARE, build_delay_aware_user  # noqa: E402

THINK_SUFFIX = " /no_think"  # served suffix for qwen3-family aliases (slm_agent.think_suffix)
SYSTEM_LIVE = SYSTEM_DELAY_AWARE + THINK_SUFFIX
HOLDOUT_MOD = 12  # ~8.3% of unique states -> held-out, deterministic by state key


def _state_key(topology: str, s: dict) -> str:
    """Dedupe/split key: waiting bucketed to 10s so near-identical states collapse."""
    pc = s["phase_context"] or []
    parts = [topology, str(s["junction"])]
    parts += [f"q{int(p['queue'])}w{int(float(p['waiting']) // 10)}" for p in pc]
    cur = next((i for i, p in enumerate(pc) if p.get("current")), -1)
    parts.append(f"c{cur}")
    return "|".join(parts)


def sample(seeds, end=1200, gate=2, config="sota"):
    """Resumable: one shard file per (config, topology, seed); existing shards are skipped,
    so a killed run loses at most the in-flight cell. config="prediction" captures the
    myopic halting vector + the anticipated-arrivals neighbor_note (kept only when the
    note is non-empty — the informative states)."""
    shard_dir = os.path.join(FTDIR, "shards" if config == "sota" else f"shards_{config}")
    os.makedirs(shard_dir, exist_ok=True)
    tops = [t for t in _topologies() if os.path.exists(t["net"]) and os.path.exists(t["routes"])]
    for t in tops:
        for seed in seeds:
            sp = os.path.join(shard_dir, f"shard__{t['label']}__s{seed}.json")
            if os.path.exists(sp):
                print(f"  {t['label']} s{seed}: SKIP (shard exists)", flush=True)
                continue
            agent = SamplingAgent()
            run_arm(f"ftsample_{config}_{t['label']}_s{seed}", agent, seed=seed, end=end,
                    gate=gate, config=config, net=t["net"], routes=t["routes"])
            if config == "sota":
                kept = [{"topology": t["label"], "seed": seed, **s} for s in agent.samples
                        if s["phase_context"] and sum(s["halting_per_phase"]) > 0]
            else:
                kept = [{"topology": t["label"], "seed": seed, **s} for s in agent.samples
                        if s.get("neighbor_note") and sum(s["halting_per_phase"]) > 0]
            with open(sp, "w", encoding="utf-8") as fh:
                json.dump({"n": len(kept), "end": end, "gate": gate, "config": config,
                           "states": kept}, fh)
            print(f"  {t['label']} s{seed}: {len(agent.samples)} decisions, "
                  f"{len(kept)} kept", flush=True)
    print("sampling complete", flush=True)


def _load_pool(shard_dir="shards"):
    pool = []
    for sp in sorted(glob.glob(os.path.join(FTDIR, shard_dir, "shard__*.json"))):
        with open(sp, encoding="utf-8") as fh:
            pool.extend(json.load(fh)["states"])
    return pool


def emit_pred(batch_size=150, config="prediction"):
    """Note-format labeling batches (prediction OR coordination): myopic halting vector +
    the neighbor_note, rendered with the LIVE build_myopic_user. Separate id-space and
    files per config (states_unique_{pred|coord}.json / batch{p|c}_*.json /
    labels{p|c}_*.json) so the frozen sota split is untouched."""
    from slm_agent import SYSTEM as SYSTEM_MYOPIC, build_myopic_user
    tag = "p" if config == "prediction" else "c"
    suffix = "pred" if config == "prediction" else "coord"
    pool = _load_pool(f"shards_{config}")
    seen, uniq = set(), []
    for s in pool:
        k = "|".join([s["topology"], str(s["junction"]),
                      ",".join(map(str, s["halting_per_phase"])), s["neighbor_note"]])
        if k in seen:
            continue
        seen.add(k)
        h = int(hashlib.sha256(k.encode()).hexdigest(), 16)
        uniq.append({"id": len(uniq), "key": k,
                     "split": "holdout" if h % HOLDOUT_MOD == 0 else "train", **s})
    n_hold = sum(1 for s in uniq if s["split"] == "holdout")
    with open(os.path.join(FTDIR, f"states_unique_{suffix}.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"n": len(uniq), "n_holdout": n_hold, "holdout_mod": HOLDOUT_MOD,
                   "states": uniq}, fh)
    for old in glob.glob(os.path.join(FTDIR, f"batch{tag}_*.json")):
        os.remove(old)
    tasks = [{"id": s["id"],
              "prompt": build_myopic_user(s["junction"], s["halting_per_phase"],
                                          s["neighbor_note"]),
              "num_phases": s["num_phases"]} for s in uniq]
    n_batches = 0
    for i in range(0, len(tasks), batch_size):
        bp = os.path.join(FTDIR, f"batch{tag}_{i // batch_size:03d}.json")
        with open(bp, "w", encoding="utf-8") as fh:
            json.dump({"system": SYSTEM_MYOPIC + THINK_SUFFIX,
                       "n": len(tasks[i:i + batch_size]),
                       "tasks": tasks[i:i + batch_size]}, fh, indent=1)
        n_batches += 1
    print(f"{len(pool)} raw {suffix} -> {len(uniq)} unique ({n_hold} holdout) -> "
          f"{n_batches} batch{tag} files of <= {batch_size} -> {FTDIR}", flush=True)


def emit(batch_size=150):
    pool = _load_pool()
    seen, uniq = set(), []
    for s in pool:
        k = _state_key(s["topology"], s)
        if k in seen:
            continue
        seen.add(k)
        h = int(hashlib.sha256(k.encode()).hexdigest(), 16)
        uniq.append({"id": len(uniq), "key": k, "split": "holdout" if h % HOLDOUT_MOD == 0
                     else "train", **s})
    n_hold = sum(1 for s in uniq if s["split"] == "holdout")
    with open(os.path.join(FTDIR, "states_unique.json"), "w", encoding="utf-8") as fh:
        json.dump({"n": len(uniq), "n_holdout": n_hold, "holdout_mod": HOLDOUT_MOD,
                   "states": uniq}, fh)
    for old in glob.glob(os.path.join(FTDIR, "batch_*.json")):
        os.remove(old)
    tasks = [{"id": s["id"], "prompt": build_delay_aware_user(s["junction"], s["phase_context"]),
              "num_phases": s["num_phases"]} for s in uniq]
    n_batches = 0
    for i in range(0, len(tasks), batch_size):
        bp = os.path.join(FTDIR, f"batch_{i // batch_size:03d}.json")
        with open(bp, "w", encoding="utf-8") as fh:
            json.dump({"system": SYSTEM_LIVE, "n": len(tasks[i:i + batch_size]),
                       "tasks": tasks[i:i + batch_size]}, fh, indent=1)
        n_batches += 1
    print(f"{len(pool)} raw -> {len(uniq)} unique ({n_hold} holdout) -> "
          f"{n_batches} labeling batches of <= {batch_size} -> {FTDIR}", flush=True)


def _verify(state, phase) -> str | None:
    """Sanity verifier (NOT a rule-match). Returns a rejection reason or None if accepted."""
    pc = state["phase_context"]
    if not isinstance(phase, int) or not (0 <= phase < state["num_phases"]):
        return "out_of_range"
    if phase >= len(pc):
        return "out_of_range"
    chosen = pc[phase]
    others_have_demand = any((p["queue"] > 0 or p["waiting"] > 0)
                             for i, p in enumerate(pc) if i != phase)
    if chosen["queue"] == 0 and chosen["waiting"] == 0 and others_have_demand:
        return "served_empty_phase"
    return None


def _verify_halting(state, phase):
    """Sanity verifier over the halting vector (for formats without phase_context waits)."""
    h = state["halting_per_phase"]
    if not isinstance(phase, int) or not (0 <= phase < state["num_phases"]) or phase >= len(h):
        return "out_of_range"
    if h[phase] == 0 and any(x > 0 for i, x in enumerate(h) if i != phase):
        # a note about incoming platoons can justify serving a currently-empty approach,
        # so this is only a rejection when there is no note to justify it
        if not state.get("neighbor_note"):
            return "served_empty_phase"
    return None


def _ingest(pattern):
    labels, provenance = {}, {}
    for lf in sorted(glob.glob(os.path.join(FTDIR, pattern))):
        with open(lf, encoding="utf-8") as fh:
            d = json.load(fh)
        for sid, phase in d["choices"].items():
            labels[int(sid)] = phase
            provenance[int(sid)] = d.get("model", "unknown")
    return labels, provenance


def build(derive_myopic=True):
    """Render train/holdout JSONL across ALL formats (full-factorial directive 2026-08-07):
    sota rows (delay-aware prompt), prediction rows (myopic prompt + neighbor note, from
    labelsp_*), and optionally PRIVILEGED myopic rows (myopic prompt, teacher label reused
    from the sota-labeled state — the teacher saw waiting times the myopic prompt hides;
    flagged privileged:true in provenance)."""
    from slm_agent import SYSTEM as SYSTEM_MYOPIC, build_myopic_user
    stats = {"accepted": 0, "rejected": {}, "by_format": {}}
    rows = {"train": [], "holdout": []}

    def add(split, fmt, sid, topology, teacher, system, user, phase, privileged=False):
        stats["accepted"] += 1
        stats["by_format"][fmt] = stats["by_format"].get(fmt, 0) + 1
        rows[split].append({
            "id": f"{fmt}:{sid}", "topology": topology, "teacher": teacher, "format": fmt,
            "privileged": privileged,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": user},
                         {"role": "assistant", "content": json.dumps({"phase": phase})}]})

    def reject(reason):
        stats["rejected"][reason] = stats["rejected"].get(reason, 0) + 1

    # sota + derived-privileged-myopic
    with open(os.path.join(FTDIR, "states_unique.json"), encoding="utf-8") as fh:
        uniq = {s["id"]: s for s in json.load(fh)["states"]}
    labels, prov = _ingest("labels_[0-9]*.json")
    for sid, phase in sorted(labels.items()):
        s = uniq.get(sid)
        if s is None:
            reject("unknown_id")
            continue
        reason = _verify(s, phase)
        if reason:
            reject(reason)
            continue
        add(s["split"], "sota", sid, s["topology"], prov[sid], SYSTEM_LIVE,
            build_delay_aware_user(s["junction"], s["phase_context"]), phase)
        if derive_myopic and _verify_halting(s, phase) is None:
            add(s["split"], "myopic", sid, s["topology"], prov[sid],
                SYSTEM_MYOPIC + THINK_SUFFIX,
                build_myopic_user(s["junction"], s["halting_per_phase"]), phase,
                privileged=True)

    # note-based formats: prediction + coordination
    for fmt, suffix, tag in (("prediction", "pred", "p"), ("coordination", "coord", "c")):
        fmt_path = os.path.join(FTDIR, f"states_unique_{suffix}.json")
        if not os.path.exists(fmt_path):
            continue
        with open(fmt_path, encoding="utf-8") as fh:
            uniq_n = {s["id"]: s for s in json.load(fh)["states"]}
        labels_n, prov_n = _ingest(f"labels{tag}_*.json")
        for sid, phase in sorted(labels_n.items()):
            s = uniq_n.get(sid)
            if s is None:
                reject(f"unknown_id_{suffix}")
                continue
            reason = _verify_halting(s, phase)
            if reason:
                reject(reason)
                continue
            add(s["split"], fmt, sid, s["topology"], prov_n[sid],
                SYSTEM_MYOPIC + THINK_SUFFIX,
                build_myopic_user(s["junction"], s["halting_per_phase"],
                                  s["neighbor_note"]), phase)

    for split, items in rows.items():
        p = os.path.join(FTDIR, f"{split}.jsonl")
        with open(p, "w", encoding="utf-8") as fh:
            for r in items:
                fh.write(json.dumps(r) + "\n")
        print(f"  {split}: {len(items)} examples -> {p}", flush=True)
    with open(os.path.join(FTDIR, "build_stats.json"), "w", encoding="utf-8") as fh:
        json.dump(stats, fh, indent=2)
    print(f"build stats: {stats}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Fine-tuning dataset builder (§14.3 step 3).")
    ap.add_argument("--step", choices=["sample", "emit", "emit-pred", "build"], required=True)
    ap.add_argument("--seeds", nargs="*", type=int,
                    default=[42, 7, 123, 11, 29, 57, 91, 3])
    ap.add_argument("--end", type=int, default=1200)
    ap.add_argument("--batch-size", type=int, default=150)
    ap.add_argument("--config", default="sota",
                    choices=["sota", "prediction", "coordination"])
    ap.add_argument("--no-derive-myopic", action="store_true")
    ns = ap.parse_args()
    if ns.step == "sample":
        sample(ns.seeds, end=ns.end, config=ns.config)
    elif ns.step == "emit":
        emit(batch_size=ns.batch_size)
    elif ns.step == "emit-pred":
        emit_pred(batch_size=ns.batch_size, config=ns.config if ns.config != "sota"
                  else "prediction")
    else:
        build(derive_myopic=not ns.no_derive_myopic)
