# -*- coding: utf-8 -*-
"""Match every numeric claim in the report to a computed fact and write a
back-traceable report. Deterministic: string match on rendered values.

Outputs (in this directory):
  claims.json          every numeric token in the body with file:line + context
  facts.json           every computed fact with value, renders, provenance
  FACTCHECK-REPORT.md  human-readable: coverage, unsourced tokens, expected-but-absent
  factcheck.json       machine-readable backtrace per claim
"""
import io, os, re, json, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import extract, facts as F

LOW_INFO_MAX = 12          # bare small integers (list counts, "three of eight") are reported separately
KEY_FAMILIES = [           # facts whose primary render we expect to find in the text
    r"^mpfloor\.\w+\.(rel|ci_lo|ci_hi|mp_mean_s|ft_mean_s)$",
    r"^arm\.\w+\.\w+\.vs(FT|MP)\.rel$",
    r"^arm\.\w+\.\w+\.(authored_share|acceptance|divergence|completion_pct|teleports|undeparted|loaded)$",
    r"^h2h\.qwen_ft_vs_stock\.\w+\.(rel|wins|ci_lo|ci_hi)$",
    r"^offline\.(Qwen3-0\.6B (stock|generalist ft)|Phi-4-mini (stock|generalist ft|LOTO|\w+-specialist))\.\w+\.acc$",
    r"^ev\.\w+\.(mean|ci_lo|ci_hi)$",
    r"^(ftfloor|mp)\.\w+\.(completion_pct|teleports|undeparted|completed_mean)$",
    r"^dataset\.",
    r"^retention\.\w+ \w+\.acc$",
    r"^forensics\.(n_cells|n_catastrophic|pct_catastrophic)$",
    r"^lat\.\w+\.(uncal|all)\.(p50_median_of_cells|p50_pooled|p50_min|p50_max|p99_max|worst_call)$",
    r"^teacher\.audit\.(agree_pct_overall|agree_min|agree_max|n_total)$",
    r"^battery\.(cloud|local)\.(min|max)$",
    r"^provenance\.\w+\.(gap_points_vsMP|n_shared)$",
    r"^calib\.horizon\.(1200|3600)\.teleports$",
]
ALLOW = json.load(io.open(os.path.join(HERE, "allowlist.json"), encoding="utf-8"))["entries"]


def allowlisted(c):
    for e in ALLOW:
        if norm(e["token"]) == norm(c["token"]) and re.search(e["context"], c["context"]):
            return e["reason"]
    return None


def norm(tok):
    t = tok.replace("{,}", "").replace(",", "").replace("\u2212", "-")
    if t.startswith("+"):
        t = t[1:]
    if t.startswith("."):
        t = "0" + t
    return t


def main():
    claims = extract.main()
    facts = F.build()
    json.dump({"artifact_sha256_12": F._sha, "facts": facts}, io.open(os.path.join(HERE, "facts.json"), "w", encoding="utf-8"), indent=0)
    index = collections.defaultdict(list)
    for f in facts:
        for r in f["renders"]:
            index[norm(r)].append(f["id"])
            if norm(r).startswith("0."):
                index[norm(r)[1:]].append(f["id"])
    fact_by_id = {f["id"]: f for f in facts}

    verified, unsourced, lowinfo, allowed = [], [], [], []
    hit_ids = set()
    for c in claims:
        key = norm(c["token"])
        ids = index.get(key, [])
        reason = allowlisted(c)
        if ids:
            verified.append({**c, "facts": ids[:8], "n_facts": len(ids)})
            hit_ids.update(ids)
        elif reason:
            allowed.append({**c, "reason": reason})
        elif c["value"] is not None and float(c["value"]).is_integer() and abs(c["value"]) <= LOW_INFO_MAX and "." not in c["token"]:
            lowinfo.append(c)
        else:
            unsourced.append(c)

    absent = []
    for f in facts:
        if any(re.match(p, f["id"]) for p in KEY_FAMILIES) and f["id"] not in hit_ids:
            absent.append(f)

    total = len(claims)
    subst = total - len(lowinfo)
    lines = []
    lines.append("# Fact-check report (deterministic, artifact-backed)\n")
    lines.append(f"Claims (numeric tokens in body): **{total}**; substantive (excluding bare integers ≤{LOW_INFO_MAX}): **{subst}**\n")
    lines.append(f"- VERIFIED (token equals a rendering of a computed fact): **{len(verified)}** ({len(verified)/max(subst,1)*100:.1f}% of substantive)")
    lines.append(f"- ALLOWLISTED (literature figure, hardware id, statute, seed, LaTeX constant; reason recorded): **{len(allowed)}**")
    lines.append(f"- UNSOURCED substantive tokens: **{len(unsourced)}**")
    lines.append(f"- Bare small integers not matched (list counts, ordinal words): {len(lowinfo)}")
    lines.append(f"- Facts computed: {len(facts)}; artifacts hashed: {len(F._sha)}\n")
    lines.append("A VERIFIED token can still be attached to the wrong quantity in prose; the backtrace lists every fact that renders to the token so a reader can judge. An UNSOURCED token is either structural (years, section counts, hyperparameters) or a number the harness cannot yet derive from an artifact; each must be resolved by adding a fact or an allowlist entry, never by trusting the prose.\n")

    lines.append("## Unsourced substantive tokens\n")
    lines.append("| token | file:line | context |\n|---|---|---|")
    for c in unsourced:
        ctx = c["context"].replace("|", "\\|").replace("\n", " ")
        lines.append(f"| `{c['token']}` | {c['file']}:{c['line']} | {ctx} |")

    lines.append("\n## Key facts whose primary rendering appears nowhere in the body (candidate mismatches)\n")
    lines.append("| fact | value | renders | method |\n|---|---|---|---|")
    for f in absent:
        lines.append(f"| `{f['id']}` | {f['value'] if not isinstance(f['value'], float) else round(f['value'], 4)} | {', '.join(f['renders'][:4])} | {f['prov']['method'].replace('|', '/')} |")

    lines.append("\n## Backtrace of verified claims\n")
    lines.append("| token | file:line | matched fact ids (value; method; artifacts) |\n|---|---|---|")
    for v in verified:
        descs = []
        for fid in v["facts"][:3]:
            f = fact_by_id[fid]
            arts = ", ".join(f["prov"]["artifacts"][:2]) + (" +%d" % (len(f["prov"]["artifacts"]) - 2) if len(f["prov"]["artifacts"]) > 2 else "")
            val = f["value"] if not isinstance(f["value"], float) else round(f["value"], 4)
            descs.append(f"`{fid}` = {val}; {f['prov']['method'].replace('|', '/')}; [{arts}]")
        more = f" (+{v['n_facts'] - 3} more)" if v["n_facts"] > 3 else ""
        lines.append(f"| `{v['token']}` | {v['file']}:{v['line']} | " + "<br>".join(descs) + more + " |")

    io.open(os.path.join(HERE, "FACTCHECK-REPORT.md"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
    lines.append("\n## Allowlisted tokens (not experimental results)\n")
    lines.append("| token | file:line | reason |\n|---|---|---|")
    for c in allowed:
        lines.append(f"| `{c['token']}` | {c['file']}:{c['line']} | {c['reason']} |")
    json.dump({"summary": {"claims": total, "substantive": subst, "verified": len(verified), "allowlisted": len(allowed), "unsourced": len(unsourced), "lowinfo": len(lowinfo), "facts": len(facts)},
               "artifact_sha256_12": F._sha, "verified": verified, "allowlisted": allowed, "unsourced": unsourced, "lowinfo": lowinfo,
               "absent_key_facts": [{"id": f["id"], "value": f["value"], "renders": f["renders"]} for f in absent]},
              io.open(os.path.join(HERE, "factcheck.json"), "w", encoding="utf-8"), indent=0)
    print(f"claims={total} substantive={subst} verified={len(verified)} unsourced={len(unsourced)} lowinfo={len(lowinfo)} facts={len(facts)} absent_key={len(absent)}")


if __name__ == "__main__":
    main()
