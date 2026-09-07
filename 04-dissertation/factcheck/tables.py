# -*- coding: utf-8 -*-
"""Positional table audit: every cell of the main result tables is checked
against the fact the table claims to print, so a wrong number cannot hide
behind a coincidental match elsewhere in the document.

Each spec: label -> (row_map, cols). row_map turns the row-header text into
(arm, topo) keys; cols is a list, per column, of fact-id templates for the
numeric tokens found in that cell, in order. Templates use {topo} and {arm}.
Output: TABLE-AUDIT.md (PASS/FAIL per cell with expected renders).
"""
import io, os, re, json, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import extract

TOPO = {"euston peak-hour": "euston_peakhour", "euston": "euston_peakhour", "bloomsbury grid": "bloomsbury_grid",
        "bloomsbury": "bloomsbury_grid", "old street": "oldstreet_junction", "bloomsbury calibrated": "bloomsbury_calibrated",
        "bloomsbury calib.": "bloomsbury_calibrated", "euston calibrated": "euston_peakhour_calibrated",
        "euston calib.": "euston_peakhour_calibrated", "oversaturated": "bloomsbury_grid", "calibrated": "bloomsbury_calibrated",
        "(14% clears)": "bloomsbury_grid", "(87% clears)": "bloomsbury_calibrated"}
ARM = {"ft": "qwen_ft", "stock": "qwen_stock", "phi ft": "phi_ft", "qwen ft": "qwen_ft", "qwen stock": "qwen_stock",
       "fixed-time": "ftfloor", "maxpressure": "mp", "qwen3-0.6b ft": "qwen_ft", "qwen3-0.6b stock": "qwen_stock",
       "phi-4-mini ft": "phi_ft"}
NUM = re.compile(r"[+\-−]?\d+(?:\.\d+)?|(?<![\w.])\.\d+")

SPECS = {
    # label: (header-col count, column templates). None = non-numeric column.
    "tab:mpfloor": [None, "mpfloor.{topo}.mp_mean_s", "mpfloor.{topo}.ft_mean_s", "mpfloor.{topo}.rel",
                    ["mpfloor.{topo}.ci_lo", "mpfloor.{topo}.ci_hi"], "mpfloor.{topo}.p_t1"],
    "tab:closedloop-full": [None, None, "arm.{arm}.{topo}.vsFT.rel", "arm.{arm}.{topo}.vsMP.rel",
                            "arm.{arm}.{topo}.authored_share", "arm.{arm}.{topo}.floor_share",
                            "arm.{arm}.{topo}.acceptance", "arm.{arm}.{topo}.divergence"],
    "tab:robust": [None, None, ["arm.{arm}.{topo}.vsFT.rel", "arm.{arm}.{topo}.vsFT.ci_lo", "arm.{arm}.{topo}.vsFT.ci_hi"],
                   "arm.{arm}.{topo}.vsFT.p_t1", "arm.{arm}.{topo}.vsFT.p_w"],
    "tab:guards": [None, None, "{armfam}.{topo}.loaded", "{armfam}.{topo}.completion_pct", "{armfam}.{topo}.teleports", "{armfam}.{topo}.undeparted"],
    "tab:calib": [None, None, ["arm.{arm}.{topo}.vsFT.rel", "arm.{arm}.{topo}.vsFT.ci_lo", "arm.{arm}.{topo}.vsFT.ci_hi"],
                  ["arm.{arm}.{topo}.vsMP.rel", "arm.{arm}.{topo}.vsMP.ci_lo", "arm.{arm}.{topo}.vsMP.ci_hi"],
                  "arm.{arm}.{topo}.completion_pct", "arm.{arm}.{topo}.authored_share"],
    "tab:composition": [None, None, "arm.{arm}.{topo}.authored_share", "arm.{arm}.{topo}.shield_share_pct",
                        "arm.{arm}.{topo}.floor_share", "arm.{arm}.{topo}.divergence"],
    "tab:latency": [None, "lat.{arm}.uncal.p50_median_of_cells", ["lat.{arm}.uncal.p50_min", "lat.{arm}.uncal.p50_max"],
                    "lat.{arm}.uncal.p99_max", "lat.{arm}.uncal.worst_call"],
    "tab:ev": [None, "ev.{evkey}.mean", ["ev.{evkey}.ci_lo", "ev.{evkey}.ci_hi"]],
}
EV = {"ambulance time saved": "ev_benefit_s", "cost to the ambulance": "gate_cost_s",
      "mean": "attack_harm_avoided_s", "worst case": "attack_worstcase_avoided_s"}
OFFLINE_ROWS = {"qwen3-0.6b stock": "Qwen3-0.6B stock", "qwen3-0.6b generalist ft": "Qwen3-0.6B generalist ft",
                "phi-4-mini stock": "Phi-4-mini stock", "phi-4-mini generalist ft": "Phi-4-mini generalist ft",
                "phi-4-mini loto": "Phi-4-mini LOTO", "phi-4-mini sota-specialist": "Phi-4-mini sota-specialist",
                "phi-4-mini myopic-specialist": "Phi-4-mini myopic-specialist",
                "phi-4-mini prediction-specialist": "Phi-4-mini prediction-specialist",
                "phi-4-mini coordination-specialist": "Phi-4-mini coordination-specialist"}


def clean(cell):
    s = re.sub(r"\\(mathbf|textbf|emph|text)\{([^}]*)\}", r"\2", cell)
    s = s.replace("$", "").replace("\\%", "").replace("\\,s", "").replace("\\,", " ").replace("{,}", "")
    s = s.replace("--", " ").replace("\u2212", "-").replace("\\\\", "").strip()
    return s


def find_tables():
    lines = extract.expand("main.tex")
    text = "\n".join(l for _, _, l in lines)
    out = {}
    for m in re.finditer(r"\\begin\{tabular\*?\}\{[^}]*\}(.*?)\\end\{tabular\*?\}(.*?)\\label\{(tab:[^}]*)\}", text, re.S):
        body, _, label = m.group(1), m.group(2), m.group(3)
        rows = []
        for raw in body.split("\\\\"):
            raw = raw.strip()
            if not raw or "rule" in raw.split("&")[0] and "&" not in raw:
                continue
            raw = re.sub(r"\\(toprule|midrule|bottomrule)", "", raw).strip()
            if "&" in raw:
                rows.append([clean(c) for c in raw.split("&")])
        out[label] = rows
    return out


def norm(tok):
    t = tok.replace("\u2212", "-")
    if t.startswith("+"):
        t = t[1:]
    if t.startswith("."):
        t = "0" + t
    if t.startswith("-."):
        t = "-0" + t[1:]
    return t


def main():
    facts = {f["id"]: f for f in json.load(io.open(os.path.join(HERE, "facts.json"), encoding="utf-8"))["facts"]}
    tables = find_tables()
    report, npass, nfail, nskip = [], 0, 0, 0
    for label, spec in SPECS.items():
        rows = tables.get(label)
        if not rows:
            report.append(f"| {label} | - | - | SKIP | table not found |"); nskip += 1
            continue
        topo = arm = None
        for row in rows[1:]:  # skip header
            if len(row) != len(spec):
                report.append(f"| {label} | {' & '.join(row)[:60]} | - | SKIP | {len(row)} cells vs {len(spec)} spec |"); nskip += 1
                continue
            h0, h1 = row[0].lower().strip(), (row[1].lower().strip() if len(row) > 1 else "")
            if label == "tab:latency":
                arm = ARM.get(h0, arm); ctx = {"arm": arm}
            elif label == "tab:ev":
                key = next((v for k, v in EV.items() if k in h0), None); ctx = {"evkey": key}
            elif label == "tab:mpfloor":
                topo = TOPO.get(h0, topo); ctx = {"topo": topo}
            elif label == "tab:robust":
                arm = ARM.get(h0, arm) if h0 else arm; topo = TOPO.get(h1, topo); ctx = {"arm": arm, "topo": topo}
            else:
                if h0.startswith("pooled"):
                    topo = "pooled"
                else:
                    topo = TOPO.get(h0, topo)
                arm = ARM.get(h1, arm) if h1 else arm
                ctx = {"topo": topo, "arm": arm, "armfam": ("arm." + arm) if arm in ("qwen_ft", "qwen_stock", "phi_ft") else arm}
            for ci, tmpl in enumerate(spec):
                if tmpl is None:
                    continue
                toks = [norm(t) for t in NUM.findall(row[ci])]
                tmpls = tmpl if isinstance(tmpl, list) else [tmpl]
                if not toks:
                    continue
                for tok, t in zip(toks, tmpls):
                    fid = t.format(**{k: (v or "?") for k, v in ctx.items()})
                    if arm == "mp" and fid.startswith("arm.mp"):
                        fid = fid.replace("arm.mp.", "mp.")
                    if label == "tab:composition" and arm in ("ftfloor", "mp"):
                        fid = f"floor.mp.{topo}.share" if "floor_share" in t else None
                    if fid is None:
                        continue
                    f = facts.get(fid)
                    if f is None:
                        report.append(f"| {label} | {row[0][:22]} / {row[1][:14] if len(row)>1 else ''} | `{tok}` | SKIP | no fact `{fid}` |"); nskip += 1
                        continue
                    ok = tok in {norm(r) for r in f["renders"]}
                    if ok:
                        npass += 1
                    else:
                        nfail += 1
                        report.append(f"| {label} | {row[0][:22]} / {row[1][:14] if len(row)>1 else ''} | `{tok}` | **FAIL** | `{fid}` = {round(f['value'],4) if isinstance(f['value'],float) else f['value']} (renders {', '.join(f['renders'][:3])}) |")
    # offline table
    rows = tables.get("tab:offline-full", [])
    for row in rows[1:]:
        key = OFFLINE_ROWS.get(row[0].lower().strip())
        if not key or len(row) != 5:
            continue
        for fmt, cell in zip(("myopic", "sota", "prediction", "coordination"), row[1:]):
            tok = norm(cell.strip()); f = facts.get(f"offline.{key}.{fmt}.acc")
            if f is None:
                nskip += 1; report.append(f"| tab:offline-full | {row[0]} | `{tok}` | SKIP | no fact |"); continue
            if tok in {norm(r) for r in f["renders"]}:
                npass += 1
            else:
                nfail += 1; report.append(f"| tab:offline-full | {row[0]} / {fmt} | `{tok}` | **FAIL** | `offline.{key}.{fmt}.acc` = {round(f['value'],2)} |")
    head = [f"# Table audit\n", f"Cells checked: PASS **{npass}**, FAIL **{nfail}**, SKIP {nskip}\n",
            "Every numeric cell of the result tables is compared positionally with the fact it claims to print. FAIL rows show the artifact-derived value.\n",
            "| table | row | cell | result | detail |", "|---|---|---|---|---|"]
    io.open(os.path.join(HERE, "TABLE-AUDIT.md"), "w", encoding="utf-8").write("\n".join(head + report) + "\n")
    print(f"table cells: pass={npass} fail={nfail} skip={nskip}")


if __name__ == "__main__":
    main()
