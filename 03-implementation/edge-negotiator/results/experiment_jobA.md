# Experiment Job-A — citation-faithful legal-reasoning note (PILOT)

- **Model:** Phi-4-mini-instruct-generic-gpu:5 (frozen, Foundry Local, temperature 0)
- **Split:** novel  ·  **n = 97**  ·  corpus = 18 law_rules  ·  retrieval k = 10
- **Gold:** POLICY-BASE-DERIVED PROXY (annotator-blind, event_type->applies_when); NOT human-graded; NOT the D5 gate
- **Determinism (temp 0):** 5/5 notes byte-identical on re-run (rate 1.0)

> PILOT / PROXY. The gold is policy-base-derived (event_type -> applies_when), annotator-blind, NOT human-graded. This is NOT the §12 D5 gate (which needs human faithfulness grading + 2-rater kappa >= 0.6). D5 is NOT claimed passed.

## Results (novel split)

| Metric | SLM Job-A note | Un-rigged template |
|---|---|---|
| Citation-correctness (mean F1) | 0.338 | 0.479 |
| Precision (mean) | 0.416 | 1.000 |
| Recall (mean) | 0.343 | 0.316 |
| Exact-set-match rate | 0.000 | 0.000 |
| **FCR (per note)** | **0.526** | 0.000 |
| FCR (per citation) | 0.544 | 0.000 |
| Fabrication rate (per note) | 0.052 | 0.000 |
| Fabricated citations (count) | 5 | 0 |
| Abstention rate | 0.278 | 0.000 |
| Parse-failure rate (counts as failure) | 0.000 | 0.000 |

## Split-dominance verdict (§3 pinned resolution)

- Pinned PRE-RUN (pilot): FCR ceiling (per note) = 0.2, MDE on citation-F1 = 0.1
- Citation-F1 delta (SLM - template) = **-0.141**  ·  clears MDE: False  ·  under FCR ceiling: False
- **Verdict: TEMPLATE_WINS** — citation-F1 gap -0.141 <= -MDE; the honestly-scored template beats the SLM note

## Caveats

- Gold is a policy-base-derived PROXY for the §3 human-graded applicable-rule labels; this is a PILOT (n=97), not the §12 D5 gate (needs human grading + 2-rater kappa>=0.6). D5 is NOT claimed passed.
- Citation-correctness is measured vs the proxy gold, not statute-text faithfulness graded by qualified humans.
- The Job-A note is internal/counsel-gated and never enters the evidence pack.
- **Adversarial-battery verdict: NEGATIVE-IS-FAIR** (independent audit, 2026-07-22). The SLM loss survived attack on 7 fronts: a stricter/fairer prompt made SLM F1 *worse* (0.391->0.319, FCR->0.857); k=10 is the SLM-favourable retrieval breadth (smaller k only handicaps it); the prompt explicitly forbids over-citation yet the SLM over-cites anyway; parse is lossless (0 parse-failures, abstentions genuine); gold is applied symmetrically; the 5 fabrications are real; the verdict is robust for any MDE <= 0.141. The loss is a genuine inability to discriminate applicable from non-applicable rules (precision 0.42, FCR 0.53, 0.0 exact-set matches), not a harness artifact.
- **Structural caveat on the baseline (documented, does not change the verdict):** the template's precision=1.000 is a structural artifact — the retrieval query and the proxy gold both key on `event_type`, so the template's top-1 rule always lands in gold. This makes the template a HARD baseline, which is CONSERVATIVE against the SLM claim; the SLM sees the identical ranked list and could copy the strategy but does not, and its absolute numbers (precision 0.42, FCR 0.53) are independently poor regardless of the baseline. The template pays with recall 0.316 and still wins.
- **Pre-registration:** the FCR ceiling (0.2) and MDE (0.1) are committed WITH this runner BEFORE any re-run, so they are git-provably pre-run, not post-hoc tuned.
- **Fair re-test pending (Lee's guidance):** this run used TF-IDF retrieval + direct note generation. A supervisor-prescribed fairer scaffold (CAG = whole 18-rule corpus in context, reason-then-classify against named rules, per Lee Stott 2026-06-25) is a stronger test of the SLM and is queued; if the negative holds under it too, it is maximally robust.
