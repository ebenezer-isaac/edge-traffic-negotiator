#!/usr/bin/env python3
"""Resolve <!-- TODO: registry tag --> markers in sec-2-8.md sequentially.

NOTE (post thesis-cutover): sec-2-8.md was rewritten from the equity-audit framing
to the legal-accountability framing and now carries inline [tag] citations with no
TODO markers, so this script is inert (it will report 0 markers). The equity/
pedestrian-harm tags (nchrp-969-2021, dangerous-by-design-2024, tfl-ksi-2023) were
dropped with the equity axis and are no longer part of the sequence below.
"""
from pathlib import Path

SECTION = Path(__file__).parent / "sec-2-8.md"

# Sequence of tag replacements in textual order (accountability framing):
TAGS = [
    "ofqual-2020",
    "syri-court-hague-2020",
    "amazon-recruit-2018",
    "chicago-ssl-oig-2020",
    "nyc-ads-task-force-2019",
    "equality-act-2010-psed",
    "eu-ai-act-2024",
    "uk-atrs",
    "bridges-v-swp-2020",
    "schufa-cjeu-2023",
]

MARKER = ".<!-- TODO: registry tag -->"

text = SECTION.read_text(encoding="utf-8")
todo_count = text.count(MARKER)
if todo_count != len(TAGS):
    print(f"WARN: found {todo_count} markers, expected {len(TAGS)}")

for tag in TAGS:
    if MARKER not in text:
        print(f"  no more markers, stopping (tag {tag} unused)")
        break
    text = text.replace(MARKER, f" [{tag}].", 1)
    print(f"  replaced -> {tag}")

remaining = text.count("<!-- TODO")
print(f"remaining TODO markers: {remaining}")

SECTION.write_text(text, encoding="utf-8")
print("saved")
