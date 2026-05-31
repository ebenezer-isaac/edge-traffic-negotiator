# Handover prompt — Edge Negotiator dissertation, fresh-session onboarding

Paste this verbatim into a new Claude Code (or other agent) session in this repo. It is self-contained: a fresh agent reading it has everything it needs to continue without re-deriving prior decisions.

---

## Who I am and what I am doing

I am the UCL MSc Systems Engineering for IoT student writing the Edge Negotiator dissertation. The thesis is supervised by Dr Akin Delibasi (UCL — distributed systems, swarm robotics, AcoustoBots) and Lee Stott (Microsoft — Foundry Local, Phi-4, Microsoft Agent Framework).

The dissertation primary contribution is **locked**: a Quarterly Equity Audit Protocol executed on the Elephant & Castle–Brixton corridor (Lambeth/Southwark, London) in SUMO, evaluating an LLM-driven traffic signal controller (Qwen3-4B + Phi-4-mini, MaxPressure shield, structured-JSON+bounded-CoT logging anchored to Hyperledger Besu QBFT, with Trillian Tessera as comparator). The secondary contribution is a counterfactual demographic re-run probing for indirect-discrimination behaviour. The discussion chapter contains a small CoT-faithfulness probe.

Topic and architecture were locked on 2026-04-26 after a ten-candidate ranking pass. Do not re-litigate either.

## Read these before doing anything

In strict order:

1. **`00-SCOPE-LOCKIN.md`** at the repo root. This is the single source of truth. §3 is the locked topic, §4 the architectural substrate, §5 maps each Stott critique pillar to its answer, §7 lists mandatory cited-claim hedges, §9 lists explicitly out-of-scope alternatives, §11 the four reopening conditions.
2. **`C:\Users\Ebenezer\.claude\projects\e--desktop-assignments-dissertation\memory\MEMORY.md`** — index to seven memory entries. Already loaded by the runtime, but skim them for orientation.
3. **`06-literary-survey/INDEX.md`** — map of the 147-paper survey across seven completed prompts plus the in-flight Prompt 8.
4. **`STSD/coursework.pdf`** — the submitted Codes of Conduct paper. Stott's feedback (recorded in `feedback_stott_critiques.md`) was on this.

## Stott's four critiques and how the locked thesis answers each

- **S1 CoT exposure risks in safety-critical control** — answered by the discussion-chapter faithfulness probe (~60 hrs) and by adopting the prompt3 §4 design checklist (post-hoc-justification label, structured-JSON wrapper, Z3 verification, MaxPressure-recommendation logged alongside, raw inputs preserved).
- **S2 equity audit operationalisation** — primary chapter (Quarterly Equity Audit) + secondary chapter (counterfactual demographic re-run). This is the load-bearing answer.
- **S3 evidential basis for production deployments** — methodology and limitations chapters cite the prompt5 hedged framings verbatim. See `feedback_cited_claim_hygiene.md` for the seven flagged claims and their corrections.
- **S4 blockchain audit trade-offs** — architecture chapter cites prompt2 §3 comparison matrix and §4 "does this need a blockchain" position; thesis runs Besu QBFT and Tessera in parallel.

## Where in the project are we right now

Lock-in complete. Current state of work:

- **Done:** literary survey (147 papers, seven prompts), STSD coursework submitted and reviewed, ten-topic ranking pass, scope lock-in, memory entries, repo orientation files.
- **In flight:** Prompt 8 (`06-literary-survey/PROMPT8.md`). User is running this externally on a deep-research tool. Output will be a single Markdown file `06-literary-survey/india-context.md` with five Section A theme tables, a Section B UK→India adaptation matrix, Section C gap analysis, Section D download list. Minimum 28 sources.
- **Next up after Prompt 8 returns:**
  1. Verify any Theme 5 deployment claim that requires correction in the coursework or registry (Section C question 2).
  2. Confirm Bengaluru secondary-chapter feasibility from open data alone (Section C question 3). If feasible, no commitment yet — only if primary work runs ahead of schedule.
  3. Add Indian regulatory framing (DPDPA 2023, NITI Aayog Responsible AI, Articles 14/15/16, Puttaswamy) to the methodology chapter alongside the existing EU AI Act / UK ATRS / US NIST AI RMF triad.
  4. Begin methodology chapter drafting in `04-writing/`.
  5. Begin implementation of the Quarterly Equity Audit protocol in `03-implementation/` against `01-research/prompt-outputs/prompt4-equity-audit-protocol.pdf` Phase A–E (18 steps).

## Hard rules for any agent picking this up

- **Do not propose alternative dissertation topics.** The other nine candidates are listed and rejected in `00-SCOPE-LOCKIN.md` §9. Reopening conditions are §11.
- **Do not vary the architectural substrate.** No Llama, no Hyperledger Fabric, no Iroha 2, no CityFlow, no Jetson. See `feedback_architecture_lockin.md`.
- **Do not cite the seven flagged claims at face value.** Use prompt5 hedged framings verbatim. See `feedback_cited_claim_hygiene.md`.
- **Do not invent registry tags.** All citations use short-tags from `06-literary-survey/registry.json`. If a tag is needed and missing, add it to the registry first.
- **Do not run another deep-research pass beyond Prompt 8** without explicit user instruction. The 147-paper survey is locked.
- **Honour the 90-day Study Away constraint.** The student may be working remotely from India for stretches. The locked SUMO-on-laptop substrate was chosen partly because it is London-resource-independent. Do not recommend changes that anchor work to UCL.
- **Stott's S2 is the load-bearing answer.** When weighting effort across chapters, equity-audit empirical work gets the most pages. S1 / S3 / S4 are addressed but secondary.

## What I am not asking you to do

Do not start drafting the dissertation chapters yet unless I explicitly ask. Do not run code unless I explicitly ask. Do not propose research extensions or alternatives. The lock is the point.

## How to confirm you have the picture

Before taking any action, reply with a one-paragraph summary stating: (1) what the locked topic is, (2) the locked SLM and ledger choices, (3) which Stott critique is the primary answer, (4) what state Prompt 8 is in, (5) what the next concrete deliverable is. If your summary contradicts anything in `00-SCOPE-LOCKIN.md`, re-read the file before acting.
