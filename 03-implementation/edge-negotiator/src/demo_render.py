"""Render the demo video from a demo_capture.py capture plus the crash-law suite.

Segments (all frames 1280x720, 15 fps, captions burned in, no audio):
  0 title card
  1 live closed-loop run: network, vehicles, signals, signed decision feed
  2 audit chain: verify, tamper a record, forge a signature
  3 crash-law suite: seven scenarios, one evidence pack
  4 results card

Usage:
    python src/demo_render.py --capture results/demo_capture__<tag>.json.gz --out demo.mp4
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import shutil
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from audit_log import AuditLog  # noqa: E402
from identity import JunctionIdentity  # noqa: E402

FPS = 15
W, H = 1280, 720
BG = "#10151C"; PANEL = "#171E27"; INK = "#E8ECF1"; MUTED = "#8B97A5"; LINE = "#2A3441"
ROAD = "#3A4656"; TEAL = "#4FC3A1"; AMBER = "#E3A73B"; RED = "#E06C6C"; BLUE = "#6FA8DC"
MONO = "DejaVu Sans Mono"; SANS = "DejaVu Sans"


class Frames:
    def __init__(self, d):
        self.d = d; self.n = 0; os.makedirs(d, exist_ok=True)
    def path(self):
        return os.path.join(self.d, f"f{self.n:05d}.png")
    def save(self, fig, hold=1):
        p = self.path(); fig.savefig(p, dpi=100, facecolor=BG); self.n += 1
        for _ in range(hold - 1):
            shutil.copyfile(p, self.path()); self.n += 1


def new_fig():
    fig = plt.figure(figsize=(W / 100, H / 100), dpi=100, facecolor=BG)
    return fig


def text_card(fr, lines, hold_s, footer=None, n_frames=None):
    """lines: list of (text, size, color, weight, family, y)."""
    fig = new_fig()
    for t, size, color, weight, fam, y in lines:
        fig.text(0.5, y, t, ha="center", va="center", fontsize=size, color=color,
                 weight=weight, family=fam, wrap=True)
    if footer:
        fig.text(0.5, 0.06, footer, ha="center", fontsize=11, color=MUTED, family=MONO)
    fr.save(fig, hold=n_frames or int(hold_s * FPS)); plt.close(fig)


def typed_lines(fr, title, lines, per_line_s=0.5, hold_s=2.5, subtitle=None, n_frames=None):
    """Terminal-style reveal: lines appear one by one; each is (text, color).

    With ``n_frames`` the reveal is spread over the first 65% of the budget and the
    completed screen holds for the rest, so the segment matches a narration clip.
    """
    n = len(lines)
    if n_frames:
        reveal = max(n, int(n_frames * 0.65)); per = max(1, reveal // n)
        holds = [per] * n; holds[-1] = max(1, n_frames - per * (n - 1))
    else:
        holds = [int(per_line_s * FPS)] * n; holds[-1] = int(hold_s * FPS)
    for k in range(1, n + 1):
        fig = new_fig()
        fig.text(0.05, 0.93, title, fontsize=17, color=INK, weight="bold", family=SANS)
        if subtitle:
            fig.text(0.05, 0.885, subtitle, fontsize=11.5, color=MUTED, family=SANS)
        y = 0.83
        for t, c in lines[:k]:
            fig.text(0.05, y, t, fontsize=12.5, color=c, family=MONO, va="top")
            y -= 0.048
        fr.save(fig, hold=holds[k - 1]); plt.close(fig)


# --------------------------------------------------------------------------- #
# Segment 1: the live run
# --------------------------------------------------------------------------- #
def sim_segment(fr, cap, every=2, caption_plan=None, n_frames=None):
    geo = cap["geometry"]; frames = cap["frames"]; decs = cap["decisions"]
    segs = [[tuple(p) for p in lane] for edge in geo["edges"] for lane in edge if len(lane) >= 2]
    xs = [p[0] for s in segs for p in s]; ys = [p[1] for s in segs for p in s]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pad = 0.03 * max(x1 - x0, y1 - y0)
    tls_nodes = geo["tls_nodes"]
    total = len(frames); n_dec = len(decs)
    dec_ptr = 0
    slm = floor = sub = 0
    fig = new_fig()
    ax = fig.add_axes([0.02, 0.10, 0.56, 0.82]); ax.set_facecolor(BG)
    ax.set_xlim(x0 - pad, x1 + pad); ax.set_ylim(y0 - pad, y1 + pad); ax.set_aspect("equal"); ax.axis("off")
    ax.add_collection(LineCollection(segs, colors=ROAD, linewidths=1.6))
    veh_sc = ax.scatter([], [], s=16, c=[], cmap="YlGnBu_r", vmin=0, vmax=14, zorder=3, linewidths=0)
    node_sc = ax.scatter([tls_nodes[t][0] for t in tls_nodes], [tls_nodes[t][1] for t in tls_nodes],
                         s=140, facecolors="none", edgecolors=MUTED, linewidths=2, zorder=4)
    node_names = list(tls_nodes.keys())
    title = fig.text(0.02, 0.955, "", fontsize=15, color=INK, weight="bold", family=SANS)
    subt = fig.text(0.02, 0.925, "", fontsize=10.5, color=MUTED, family=SANS)
    panel = fig.add_axes([0.60, 0.10, 0.38, 0.82]); panel.set_facecolor(PANEL); panel.set_xticks([]); panel.set_yticks([])
    for sp in panel.spines.values(): sp.set_edgecolor(LINE)
    ptexts = []
    caption = fig.text(0.02, 0.045, "", fontsize=12, color=INK, family=SANS)
    legend_y = 0.075
    for k, (c, lbl) in enumerate([(TEAL, "SLM-authored"), (MUTED, "shield / MaxPressure"), (AMBER, "anti-starvation floor")]):
        fig.text(0.62 + k * 0.12, legend_y, "● " + lbl, fontsize=9.5, color=c, family=SANS)
    last_by = {t: MUTED for t in node_names}
    cum_arrived = [0] * total
    run = 0
    for i, fr_ in enumerate(frames):
        run += int(fr_.get("arrived") or 0); cum_arrived[i] = run
    if n_frames:
        idxs = [min(total - 1, round(k * (total - 1) / max(1, n_frames - 1))) for k in range(n_frames)]
    else:
        idxs = list(range(0, total, every))
    for i in idxs:
        f = frames[i]
        veh = f["veh"]
        if veh:
            veh_sc.set_offsets([[v[0], v[1]] for v in veh]); veh_sc.set_array([v[2] for v in veh])
        else:
            veh_sc.set_offsets([[0, 0]]); veh_sc.set_array([0])
        while dec_ptr < n_dec and decs[dec_ptr]["step"] <= f["step"]:
            d = decs[dec_ptr]; by = d["served_by"]
            if by == "slm": slm += 1; last_by[d["tls"]] = TEAL
            elif by == "anti_starvation": sub += 1; last_by[d["tls"]] = AMBER
            else: floor += 1; last_by[d["tls"]] = MUTED
            dec_ptr += 1
        node_sc.set_edgecolors([last_by[t] for t in node_names])
        title.set_text("Live run: fine-tuned Qwen3-0.6B (int4, Foundry Local, RTX 2060) on the calibrated Bloomsbury grid")
        subt.set_text(f"seed {cap['seed']} · 9 signalised junctions · 686 vehicles · shield: MaxPressure mask + substitution + anti-starvation · decision every 10 s")
        for t in ptexts: t.remove()
        ptexts.clear()
        tot = max(1, slm + floor + sub)
        rows = [
            (f"sim time  {f['step']:>5d} s   running {len(veh):>3d}   completed {cum_arrived[i]:>3d}   teleports {f['teleports']}", INK),
            ("", INK),
            (f"decisions logged   {slm + floor + sub:>4d}", INK),
            (f"  SLM-authored      {slm:>4d}   ({slm / tot:.2f})", TEAL),
            (f"  shield/MaxPressure{floor:>4d}   ({floor / tot:.2f})", MUTED),
            (f"  anti-starvation   {sub:>4d}   ({sub / tot:.2f})", AMBER),
            ("", INK),
            (f"signed chain length {f['chain_len']:>4d}", INK),
            (f"head hash  {(f['chain_head'] or '')[:24]}…", BLUE),
            ("", INK),
            ("last decisions   t    junction   SLM→served  by      latency", MUTED),
        ]
        recent = decs[max(0, dec_ptr - 7):dec_ptr]
        for d in reversed(recent):
            by = d["served_by"] or "?"
            col = TEAL if by == "slm" else (AMBER if by == "anti_starvation" else MUTED)
            lat = f"{d['latency_s']:.2f}s" if d.get("latency_s") is not None else "   -  "
            sp = "-" if d["slm_phase"] is None else str(d["slm_phase"])
            rows.append((f"  seq {d['seq']:>4d}  {d['step']:>4d}  {str(d['tls'])[:9]:<9}  {sp:>2}→{str(d['served']):<2}      {by[:5]:<5}  {lat}", col))
        y = 0.90
        for t, c in rows:
            ptexts.append(fig.text(0.615, y, t, fontsize=10.2, color=c, family=MONO, va="top"))
            y -= 0.036
        if caption_plan:
            cur = ""
            for start, txt in caption_plan:
                if f["step"] >= start: cur = txt
            caption.set_text(cur)
        fr.save(fig)
    plt.close(fig)


# --------------------------------------------------------------------------- #
# Segment 2: audit chain verify + tamper + forge
# --------------------------------------------------------------------------- #
def audit_segment(fr, cap, jsonl_path, pubkeys_path, n_frames=None):
    text = open(jsonl_path, encoding="utf-8").read()
    pub = {k: bytes.fromhex(v) for k, v in json.load(open(pubkeys_path)).items()}
    log = AuditLog.from_jsonl(text)
    n = len(log); ok_chain = log.verify_chain(); ok_sig = log.verify_signatures(pub)
    root = log.merkle_root(0, n)
    # tamper: flip the executed phase of one decision, reload without verify
    lines = text.splitlines(); idx = min(120, n - 1)
    e = json.loads(lines[idx]); orig = e["event"].get("executed"); e["event"]["executed"] = (orig or 0) + 1
    lines_t = list(lines); lines_t[idx] = json.dumps(e, sort_keys=True, separators=(",", ":"))
    tampered = AuditLog.from_jsonl("\n".join(lines_t), verify=False)
    t_chain = tampered.verify_chain()
    # forge: re-sign one entry's hash with an attacker key, chain stays intact
    attacker = JunctionIdentity(e["issuer"] or "J")
    e2 = json.loads(lines[idx]); e2["signature"] = attacker.sign(e2["hash"].encode()).hex()
    lines_f = list(lines); lines_f[idx] = json.dumps(e2, sort_keys=True, separators=(",", ":"))
    forged = AuditLog.from_jsonl("\n".join(lines_f), verify=False)
    f_chain = forged.verify_chain(); f_sig = forged.verify_signatures(pub)
    by = cap["decision_stats"]
    seg = [
        (f"$ load results/{os.path.basename(jsonl_path)}", MUTED),
        (f"entries: {n}   decision records: {n}   issuers: {len(pub)} junction Ed25519 keys", INK),
        (f"verify_chain()        -> {ok_chain}", TEAL if ok_chain else RED),
        (f"verify_signatures()   -> {ok_sig}", TEAL if ok_sig else RED),
        (f"merkle_root(0, {n})   -> {root[:40]}…", BLUE),
        ("", INK),
        (f"$ tamper: entry seq {idx}, executed phase {orig} -> {(orig or 0) + 1}, hashes left untouched", MUTED),
        (f"verify_chain()        -> {t_chain}   (hash of seq {idx} no longer matches its body)", RED if not t_chain else TEAL),
        ("", INK),
        (f"$ forge: re-sign entry seq {idx} with a key that is not junction {str(e['issuer'])[:18]}'s", MUTED),
        (f"verify_chain()        -> {f_chain}   (the body was not changed, so the chain holds)", TEAL if f_chain else RED),
        (f"verify_signatures()   -> {f_sig}   (signature does not verify under the registered key)", RED if not f_sig else TEAL),
        ("", INK),
        ("Every served phase in the run above is one of these records: who proposed, what the shield", INK),
        ("allowed, what was served and by whom. Nothing in the record can be edited or re-attributed unseen.", INK),
    ]
    typed_lines(fr, "Audit chain: verify, tamper, forge", seg, per_line_s=0.55, hold_s=4.0,
                subtitle="Hash-chained, per-junction Ed25519 signed decision records written during the run you just watched",
                n_frames=n_frames)
    return {"n": n, "chain": ok_chain, "sig": ok_sig, "tamper": t_chain, "forge_chain": f_chain, "forge_sig": f_sig}


# --------------------------------------------------------------------------- #
# Segment 3: crash-law suite
# --------------------------------------------------------------------------- #
def crash_segment(fr, crash_json, n_table=None, n_pack=None):
    d = json.load(open(crash_json, encoding="utf-8"))
    sc = d["scenarios"]
    rows = [("scenario                        chain  sigs   forgery-caught  rule inferred  proven", MUTED)]
    for s in sc:
        rows.append((f"{s['name']:<32}{str(s['verify_chain']):<7}{str(s['verify_signatures']):<7}"
                     f"{str(s['tamper_caught']):<16}{str(s['expected_rule_inferred']):<15}{str(s['proven'])}",
                     TEAL if s["proven"] else RED))
    rows.append(("", INK))
    rows.append((f"{d['n_scenarios']} scenarios, all proven: {d['all_proven']}", TEAL if d["all_proven"] else RED))
    typed_lines(fr, "Crash reconstruction: seven scenarios against the UK-law knowledge base", rows,
                per_line_s=0.5, hold_s=3.0,
                subtitle="Per scenario: signed incident record, chain and signature verification, rule inferred from verified facts, forged signature caught",
                n_frames=n_table)
    # one evidence pack
    s = next(x for x in sc if x["name"] == "ambulance_crosses_red_exempt")
    facts = s["verified_facts"]
    law = s["governing_law"]
    if isinstance(law, str):
        import ast
        try: law = ast.literal_eval(law)
        except Exception: law = []
    pack = [
        ("EVIDENCE PACK  scenario: ambulance_crosses_red_exempt", INK),
        (f"verified facts  signal={facts.get('signal_state')}  crossing={facts.get('crossing_class')}  "
         f"key_valid={facts.get('key_valid')}  authority={facts.get('authority_class')}  corroborated={facts.get('corroborated')}", INK),
        (f"chain verified={s['verify_chain']}  signatures verified={s['verify_signatures']}  forged signature caught={s['tamper_caught']}", TEAL),
        ("", INK),
        ("governing rules cited (fault_weight is the knowledge base's, not a finding of fault):", MUTED),
    ]
    for r in law[:3]:
        pack.append((f"  {r.get('rule_id'):<26} {r.get('statute_ref'):<38} {r.get('fault_weight')}", BLUE))
        why = str(r.get("why", ""))
        if len(why) > 92:
            why = why[:92].rsplit(" ", 1)[0] + " …"
        pack.append((f"      why: {why}", INK))
    pack.append(("", INK))
    pack.append(("Output is a cited evidence pack for a human adjudicator, never a verdict.", AMBER))
    typed_lines(fr, "Evidence pack: what the reconstruction hands to an adjudicator", pack, per_line_s=0.55, hold_s=4.5,
                n_frames=n_pack)


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True)
    ap.add_argument("--crash", default=os.path.join(_HERE, "..", "results", "experiment_crash_law.json"))
    ap.add_argument("--out", default=os.path.join(_HERE, "..", "..", "..", "demo-edge-negotiator.mp4"))
    ap.add_argument("--frames", default=os.path.join(_HERE, "..", "results", "_demo_frames"))
    ap.add_argument("--every", type=int, default=2)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    args = ap.parse_args()

    with gzip.open(args.capture, "rt", encoding="utf-8") as fh:
        cap = json.load(fh)
    if os.path.isdir(args.frames): shutil.rmtree(args.frames)
    fr = Frames(args.frames)
    m = cap["metrics"]; ds = cap["decision_stats"]; au = cap["audit"]
    dec_total = ds.get("decisions") or (len(cap["decisions"]))
    sb = ds.get("served_by", {}) if isinstance(ds.get("served_by"), dict) else {}
    auth_share = (sb.get("slm", 0) / dec_total) if dec_total else 0.0
    acc = (ds.get("slm_proposal_served", 0) / ds["slm_valid_proposals"]) if ds.get("slm_valid_proposals") else 0.0
    div = (ds.get("slm_diverged_and_served", 0) / ds["slm_proposal_served"]) if ds.get("slm_proposal_served") else 0.0

    # 0 title
    text_card(fr, [
        ("The Edge Negotiator", 34, INK, "bold", SANS, 0.62),
        ("On-device small-language-model traffic control with a provable accident audit", 16, MUTED, "normal", SANS, 0.53),
        ("Demo: one live closed-loop run, then the audit layer that records it", 13, INK, "normal", SANS, 0.42),
        ("Candidate WKSR2 · COMP0234 · SEIoT MSc 2026", 12, MUTED, "normal", MONO, 0.34),
    ], hold_s=4.5, footer="SUMO 1.20 · Microsoft Foundry Local · NVIDIA RTX 2060 6 GB · everything shown is computed live in this run")

    # 1 sim
    plan = [
        (0, "Every 10 s the SLM proposes a phase from the junction's queues; the MaxPressure shield masks, substitutes or lets it through."),
        (200, "Teal rings: the last served phase at that junction was the SLM's own. Grey: the shield's. Amber: the anti-starvation floor."),
        (450, "Each decision is signed by the junction's Ed25519 key and hash-chained; the head hash on the right changes with every record."),
        (750, "Latency per decision is measured on the 6 GB card; the median in the study is 1.75 s against a 10 s interval."),
        (1000, "Run ends at 1,200 s. Completed vehicles and mean delay are computed from SUMO's tripinfo, never from the controller."),
    ]
    sim_segment(fr, cap, every=args.every, caption_plan=plan)

    # 1b run summary
    text_card(fr, [
        ("This run, seed %d" % cap["seed"], 22, INK, "bold", SANS, 0.72),
        (f"loaded {m['loaded']}   completed {m['completed']} ({100 * m['completed'] / max(1, m['loaded']):.1f}%)   teleports {m['teleports']}   undeparted {m['undeparted']}", 14, INK, "normal", MONO, 0.60),
        (f"mean network delay {m['mean_network_delay_s']:.1f} s", 14, INK, "normal", MONO, 0.54),
        (f"decisions {dec_total}   SLM-authored {sb.get('slm', 0)} ({auth_share:.2f})   shield {sb.get('shield', 0)}   anti-starvation {sb.get('anti_starvation', 0)}   acceptance {acc:.2f}   divergence {div:.2f}", 12.5, MUTED, "normal", MONO, 0.46),
        (f"audit: {au['entries']} entries, verify_chain={au['verify_chain']}, verify_signatures={au['verify_signatures']}, inclusion proof {au['inclusion_proof_valid']}", 13, TEAL, "normal", MONO, 0.40),
        ("One seed is a demonstration, not a result. The report's numbers are thirty paired seeds per cell.", 12.5, AMBER, "normal", SANS, 0.28),
    ], hold_s=6.0)

    # 2 audit
    jsonl = args.capture.replace(".json.gz", ".audit.jsonl"); pk = args.capture.replace(".json.gz", ".pubkeys.json")
    audit_segment(fr, cap, jsonl, pk)

    # 3 crash law
    crash_segment(fr, args.crash)

    # 4 results card (values from the submitted report, harness-verified)
    text_card(fr, [
        ("What the study found (n = 30 seeds per cell)", 22, INK, "bold", SANS, 0.80),
        ("Fine-tuning moves authorship, not delay: SLM-authored share 0.39–0.62 → 0.56–0.77 on every map", 13.5, INK, "normal", SANS, 0.68),
        ("Where the network can clear, the distilled 0.6B student cuts delay 18.3% against its stock twin, 30 of 30 seeds", 13.5, TEAL, "normal", SANS, 0.61),
        ("The 3.8B student lands within ±0.38% of the 0.6B: scale saturates at 0.6B", 13.5, INK, "normal", SANS, 0.54),
        ("Seven crash scenarios reconstructed end-to-end with forgeries caught; the output is a cited evidence pack", 13.5, INK, "normal", SANS, 0.47),
        ("Limits stated in the report: single-network headline, Euston did not reproduce it, no unmasked arm, trust battery at three seeds", 12.5, AMBER, "normal", SANS, 0.36),
        ("Candidate WKSR2 · COMP0234 · 2026", 11.5, MUTED, "normal", MONO, 0.22),
    ], hold_s=8.0)

    # stitch
    out = os.path.abspath(args.out)
    cmd = [args.ffmpeg, "-y", "-framerate", str(FPS), "-i", os.path.join(args.frames, "f%05d.png"),
           "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart", out]
    print(" ".join(cmd), flush=True)
    subprocess.run(cmd, check=True)
    print(f"frames {fr.n}  duration {fr.n / FPS:.1f}s  -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
