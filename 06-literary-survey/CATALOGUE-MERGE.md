# Catalogue merge — Prompt-9 additions → `registry.json`

**Date:** 2026-06-04
**Action item closed:** merge the staged Prompt-9 paper catalogue (`prompt9-registry-additions.json`)
into the master `registry.json`.

## Summary

| Metric | Count |
|---|---|
| Entries in `registry.json` before merge | 228 |
| Prompt-9 additions offered | 23 |
| **Added** | **23** |
| **Skipped as duplicate** | **0** |
| Entries in `registry.json` after merge | **251** |

The merged `registry.json` parses cleanly with `python json` (UTF-8). All 228 pre-existing
entries are preserved byte-for-byte; the change is a pure append (`git diff`: 437 insertions, 0
deletions). The two top-level metadata blocks (`version`, `papers_dir`, `user_agent`,
`host_delay_sec`) are unchanged.

> **Note on registry size.** `INDEX.md` describes the registry as "147 (locked)" / "175 total".
> The actual file already held **228** entries before this merge, so those INDEX.md numbers are
> stale. This merge does not touch INDEX.md; the count there should be reconciled separately if
> desired. Post-merge the registry holds 251 entries.

## Duplicate check

Each addition was checked against every existing registry entry on four keys: `url`, `filename`,
`sha256`, `tag`, plus a normalised **arXiv ID** extracted from the PDF URL. **No collisions on any
key** — all 23 additions are genuinely new. Nothing was skipped.

## Topic / pillar breakdown of the 23 added

- `prompt9-detection` (physical-consistency / spoofing detection): **12** — `Xiao2026Residual`,
  `Ghosh2025Switching`, `Abshari2025CPSReview`, `Huisman2025Hybrid`, `Shahariar2025Trust`,
  `Huisman2024Realizations`, `Liu2022Blockchain`, `Azam2022Sybil`, `Obata2023FDIState`,
  `Amanullah2026CoopMD`, `Derhab2020FlowConserv`, `Keijzer2021Intersection`
- `prompt9-identity` (DID/VC, blockchain-PKI, SSI): **11** — `slvcdida25`, `endorse25`,
  `aiagents25`, `dcsm24`, `dpkidrone24`, `didlink24`, `didvcsurvey24`, `proofmember23`,
  `ssiiiot22`, `pkchain25_eprint`, `sovchain26`

## Schema mapping (additions → registry schema)

The registry's per-paper schema is the 14-field shape used by every existing entry:
`tag, title, year, url, source_prompt, category, relevance, status, filename, size_bytes,
sha256, http_status, downloaded_at, error`. (The registry is already heterogeneous — a handful of
existing entries also carry `source_type`, `ua_fallback`, or `verify_skipped`.)

Field-by-field mapping:

| Addition field | Registry field | Treatment |
|---|---|---|
| `tag`, `title`, `year`, `url`, `source_prompt`, `status`, `filename`, `size_bytes`, `sha256`, `error` | same | carried through verbatim |
| `category` (null in all 23) | `category` | set to **`"uncategorised"`** placeholder — registry uses this as an editorial field; null would be ambiguous and fabricating a category would invent editorial judgement |
| `relevance` (null in all 23) | `relevance` | set to **`"uncategorised"`** placeholder, same rationale |
| `http_status` (null) | `http_status` | **kept `null`** — additions note the original HTTP response was not re-verified in this pass; honest |
| `downloaded_at` (null) | `downloaded_at` | **kept `null`** — no download log retained; honest |
| `topic` | (added) `topic` | **added** to the new entries only (`detection`/`identity`); existing entries omit it — consistent with the registry's existing per-entry heterogeneity |
| `authors` | (added) `authors` | **added** to the new entries only; existing entries omit it |
| `title_source` | (added) `title_source` | **kept/added** for provenance honesty (records whether the title came from PDF metadata vs first-page text) |

### Fields added (new entries only)
`topic`, `authors`, `title_source` — three provenance/classification fields present in the staged
additions but absent from the legacy schema. Added rather than dropped because they carry real
provenance value and the registry already tolerates per-entry extra fields. No existing entry was
backfilled with these fields.

### Fields dropped
The additions file's top-level `_note` key was **not** carried into the registry (it is
documentation about the staging pass, not paper data). Its content is reflected here instead.

## Entries still needing manual verification

Honesty markers carried straight through — these are flagged, not fixed, and need a human pass:

1. **All 23 new entries** have `category: "uncategorised"` and `relevance: "uncategorised"`.
   These are deliberate placeholders. Editorial category (the registry's `a`/`b`/`c` scheme) and a
   relevance sentence must be assigned manually; they were **not** invented.
2. **All 23 new entries** have `http_status: null` and `downloaded_at: null`. The PDFs are present
   on disk (sha256 + size recorded), but the original HTTP status and download timestamp were not
   re-verified, so they remain null rather than assumed `200`.
3. **`Amanullah2026CoopMD`** — `authors: "unverified"`. The title was verified from PDF
   metadata-subject but the author list is not present in the metadata; needs manual confirmation
   (it is also an IEEE `stamp.jsp` URL, not an open PDF link).
4. **`pkchain25_eprint`** — tag year is 2025 but the IACR eprint ID is `2023/1791`; year
   discrepancy noted in `title_source`, tag retained as-is. Confirm the intended publication year.
5. **`didvcsurvey24`** — filename/arXiv year 2024 but IEEE COMST acceptance is 2025; noted in
   `title_source`. Confirm the year to cite.
6. **`sovchain26`** — `title_source` flags that only the lead author appears in PDF metadata; the
   author list (`Dawood Behbehani`) may be incomplete.
7. **`ssiiiot22`** — author first names were expanded from citation initials (noted in
   `title_source`); low-risk but unverified against the source.

`title_source` on every new entry records exactly how the title (and where noted, authors/year)
was derived, so each can be re-checked against its PDF.

## Out of scope (untouched)

- `INDEX.md` — not edited (stale counts noted above, left for a separate reconciliation).
- Anything under `03-implementation/` or `edge-negotiator/` — not touched.
- `prompt9-registry-additions.json` — left in place as the staging record.
