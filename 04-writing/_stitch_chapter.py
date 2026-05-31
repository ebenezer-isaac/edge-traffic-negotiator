#!/usr/bin/env python3
"""Stitch sec-2-1.md ... sec-2-9.md into a single Chapter 2 with numbered refs.

Citation format in section files:  [short-tag] or [tag1; tag2; tag3]
Output format:                     [N] or [N1, N2, N3]
References section is built from registry.json entries actually cited.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SECTIONS_DIR = ROOT / "sections"
REGISTRY = ROOT.parent / "06-literary-survey" / "registry.json"
OUTPUT = ROOT / "02-literature-review.md"

SECTION_FILES = [SECTIONS_DIR / f"sec-2-{i}.md" for i in range(1, 10)]


def format_reference(entry: dict, n: int) -> str:
    """Render an IEEE-style numbered reference from a registry entry."""
    title = entry.get("title") or entry.get("tag")
    year = entry.get("year")
    url = entry.get("url") or ""
    src_type = entry.get("source_type") or ""
    yr_str = f", {year}" if year else ""
    type_str = f" [{src_type}]" if src_type else ""
    url_str = f" {url}" if url else ""
    return f"[{n}] {title}{yr_str}.{type_str}{url_str}"


def load_registry() -> dict[str, dict]:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {p["tag"]: p for p in reg["papers"]}


CITE_PATTERN = re.compile(r"\[([A-Za-z0-9_;\-\.\s]+?)\]")


def collect_section_text() -> str:
    """Concatenate sections in order, stripping any per-section preamble or HTML word-count comments."""
    parts: list[str] = []
    for f in SECTION_FILES:
        if not f.exists():
            raise SystemExit(f"missing section: {f}")
        txt = f.read_text(encoding="utf-8").rstrip()
        # strip trailing HTML comment lines like <!-- §2.X word count: NNNN -->
        lines = txt.splitlines()
        while lines and lines[-1].strip().startswith("<!--") and lines[-1].strip().endswith("-->"):
            lines.pop()
        parts.append("\n".join(lines).rstrip())
    return "\n\n".join(parts)


def is_likely_citation(token: str, registry_index: dict[str, dict]) -> bool:
    """Decide whether a [...] bracket is a citation vs prose like [2020]."""
    parts = [p.strip() for p in token.split(";")]
    if not parts:
        return False
    # all parts must be recognised registry tags for this to count as a citation
    return all(p in registry_index for p in parts)


def assign_numbers(text: str, registry_index: dict[str, dict]) -> tuple[str, list[str]]:
    """Replace [tag] with [N]. Returns transformed text and ordered tag list."""
    order: list[str] = []
    seen: dict[str, int] = {}

    def repl(match: re.Match) -> str:
        token = match.group(1).strip()
        # ignore obvious non-citations
        if not is_likely_citation(token, registry_index):
            return match.group(0)
        parts = [p.strip() for p in token.split(";")]
        nums: list[int] = []
        for tag in parts:
            if tag not in seen:
                order.append(tag)
                seen[tag] = len(order)
            nums.append(seen[tag])
        return "[" + ", ".join(str(n) for n in nums) + "]"

    return CITE_PATTERN.sub(repl, text), order


def build_references_block(order: list[str], registry_index: dict[str, dict]) -> str:
    out = ["## References", ""]
    for i, tag in enumerate(order, 1):
        entry = registry_index[tag]
        out.append(format_reference(entry, i))
        out.append("")
    return "\n".join(out)


HEADER = """# Chapter 2 — Literature Review

**The Edge Negotiator: An Audit-Anchored Architecture for Decentralised Traffic Signal Control**

**Author:** 25153651
**Institution:** University College London, United Kingdom

## Abstract

This chapter establishes that no published work integrates a sub-7B small-language-model traffic signal controller, a deterministic Max-Pressure shield, a permissioned blockchain audit ledger, and an executable equity-audit protocol on a real London signalised corridor under combined UK and Indian regulatory comparative framing. The chapter traces, section by section, how each architectural decision is compelled by the literature rather than stipulated, surveying the classical adaptive baseline (Max-Pressure, SCOOT, SCATS), reinforcement-learning controllers and their adversarial brittleness, the LLM/SLM-for-TSC frontier, edge-hardware constraints on sub-7B inference, the chain-of-thought-faithfulness literature governing reasoning logs, the permissioned-blockchain audit-ledger literature, and the algorithmic-fairness audit literature spanning UK, EU, and Indian regulatory frameworks. The chapter closes on a seven-axis novelty tuple. Each axis is occupied by adjacent prior work; their conjunction is not.

**Keywords:** decentralized traffic optimisation, edge AI, blockchain auditability, small language models, algorithmic fairness audit, chain-of-thought faithfulness, permissioned consensus, equity in transport

---

"""


def main() -> None:
    registry_index = load_registry()
    raw = collect_section_text()
    transformed, order = assign_numbers(raw, registry_index)
    refs = build_references_block(order, registry_index)
    word_count = len(re.findall(r"\b\w+\b", transformed))
    body = HEADER + transformed + "\n\n---\n\n" + refs + f"\n\n<!-- chapter word count (sections only): {word_count} -->\n"
    OUTPUT.write_text(body, encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(f"  {len(order)} unique citations resolved")
    print(f"  ~{word_count} words in stitched sections (excluding header/refs)")
    print(f"  references block: {len(order)} entries")
    # report any bracket tokens that look like citations but didn't resolve (sanity check)
    leftovers = []
    for m in CITE_PATTERN.finditer(transformed):
        token = m.group(1).strip()
        # numeric-only is a resolved citation; pure year like "2020" is fine; tag-shaped tokens that survive are suspicious
        if re.match(r"^[A-Za-z][A-Za-z0-9_-]+$", token) and token not in registry_index and not token.isdigit():
            leftovers.append(token)
    if leftovers:
        print(f"  WARN: {len(set(leftovers))} unresolved tag-shaped tokens: {sorted(set(leftovers))}")


if __name__ == "__main__":
    main()
