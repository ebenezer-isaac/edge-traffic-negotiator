# Failure Forensics: Audit-Trail Analysis of Catastrophic Closed-Loop Seeds (H1×H2 Fusion)

**Date:** 2026-08-21 · **Data:** `results/frontier_raw/` (270 cells: qwen3-0.6b-ft1, qwen3-0.6b-ft0, phi4mini-gen-gpu × euston_peakhour, bloomsbury_grid, oldstreet_junction × 30 seeds, all `sota` config) · **Companion data file:** `results/failure_forensics.json`

## Methodology

Every closed-loop cell records aggregate decision-composition statistics (`decision_stats`: who served each decision — SLM, shield, or anti-starvation — plus divergence counts) and a hash-chain verification flag (`audit_verify_chain`) over the signed decision log. We flag every cell with `delay_rel_pct ≥ +20%` (controller ≥20% worse than its seed-matched MaxPressure baseline) as catastrophic, then use the recorded decision composition — compared against the same arm's topology-level norms, the same seed's other arms, and the seed's baseline — to attribute each failure to the model, the scaffold, or the demand realisation. **Caveat:** `audit_records` is `null` in every cell of this campaign (per-decision entries were not persisted to the result JSONs), so the *timing* of divergence (early ramp vs sustained) cannot be characterised; all forensics below use the aggregate `decision_stats`, the network-level metrics, and the chain-verification result, exactly as recorded.

## 1. Catastrophic cells (14 / 270 = 5.2%)

All in euston_peakhour (8) and oldstreet_junction (6); **zero** in bloomsbury_grid. `base rank` = the seed's baseline delay rank within the topology (1 = easiest of 34–36 seeds).

| Model | Topology | Seed | rel % | baseline s | SLM s | base rank | authored | anti-starv (arm mean) | div-served (arm mean) | teleports (base) | chain |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| qwen3-0.6b-ft0 | euston_peakhour | 13 | **+110.3** | 186.1 | 391.4 | 4/34 | 0.673 | 121 (114) | 119 (86) | 51 (13) | ✓ |
| qwen3-0.6b-ft1 | oldstreet_junction | 20 | +68.6 | 138.3 | 233.2 | 10/36 | 0.870 | 117 (100) | 30 (14) | 13 (0) | ✓ |
| phi4mini-gen-gpu | oldstreet_junction | 20 | +68.5 | 138.3 | 233.1 | 10/36 | 0.867 | 119 (101) | 28 (16) | 14 (0) | ✓ |
| qwen3-0.6b-ft0 | euston_peakhour | 10 | +66.5 | 241.7 | 402.2 | 18/34 | 0.670 | 121 (114) | 114 (86) | 58 (22) | ✓ |
| qwen3-0.6b-ft1 | euston_peakhour | 9 | +50.9 | 193.0 | 291.3 | 5/34 | 0.695 | 114 (107) | 25 (23) | 47 (13) | ✓ |
| phi4mini-gen-gpu | euston_peakhour | 9 | +50.7 | 193.0 | 290.9 | 5/34 | 0.692 | 116 (108) | 24 (25) | 47 (13) | ✓ |
| qwen3-0.6b-ft1 | euston_peakhour | 17 | +26.5 | 221.2 | 279.8 | 16/34 | 0.687 | 116 (107) | 21 (23) | 42 (22) | ✓ |
| phi4mini-gen-gpu | euston_peakhour | 17 | +26.5 | 221.2 | 279.8 | 16/34 | 0.691 | 115 (108) | 21 (25) | 42 (22) | ✓ |
| qwen3-0.6b-ft1 | euston_peakhour | 4 | +25.1 | 198.8 | 248.7 | 8/34 | 0.693 | 107 (107) | 14 (23) | 28 (10) | ✓ |
| phi4mini-gen-gpu | euston_peakhour | 4 | +25.0 | 198.8 | 248.6 | 8/34 | 0.696 | 106 (108) | 13 (25) | 28 (10) | ✓ |
| phi4mini-gen-gpu | oldstreet_junction | 4 | +22.6 | 140.5 | 172.3 | 14/36 | 0.763 | 114 (101) | 26 (16) | 9 (0) | ✓ |
| qwen3-0.6b-ft0 | euston_peakhour | 19 | +21.8 | 172.3 | 209.9 | 1/34 | 0.677 | 114 (114) | 84 (86) | 21 (9) | ✓ |
| qwen3-0.6b-ft0 | oldstreet_junction | 10 | +20.4 | 142.4 | 171.5 | 20/36 | 0.519 | 174 (168) | 71 (64) | 7 (0) | ✓ |
| qwen3-0.6b-ft0 | oldstreet_junction | 8 | +20.2 | 135.7 | 163.1 | 7/36 | 0.521 | 181 (168) | 82 (64) | 7 (0) | ✓ |

Near-misses (+10..+20%): 9 cells, dominated by euston s19/s21 (all three arms elevated on both) — listed in the JSON.

## 2. Per-cell forensic capsules

**qwen3-0.6b-ft0 / euston_peakhour / s13 (+110.3%) — the worst cell; model-attributed.** The SLM authored 214/335 served decisions (63.9%); the anti-starvation guard served the other 121 — only mildly above the arm's topology mean of 114.5, i.e. the scaffold behaved normally. What is abnormal is divergence: 119 SLM proposals that *disagreed with the shield* were served (arm norm 86.2), out of 318 valid proposals of which only 95 agreed with the shield — an override rate of 0.556. Absolute collapse is real, not a denominator artifact: SLM delay 391.4 s vs the arm's topology median of 196.4 s (2.0×), on a baseline-easy seed (rank 4/34, baseline 186.1 s = 0.78× topology median). Network damage: 210 completed vs 454 under baseline, 341 undeparted vs 135, 51 teleports vs 13. Comparators on the same seed: ft1 +1.1%, phi4mini +5.5% — both fine. `audit_verify_chain = True`.

**qwen3-0.6b-ft0 / euston_peakhour / s10 (+66.5%) — model-attributed.** Same signature: 114 diverged-and-served (norm 86), override 0.535, teleports 58 vs baseline 22, completed 206 vs 360. Baseline is unremarkable (rank 18/34, 1.02× median). ft1 +3.8%, phi4mini +3.8% on the same seed. Chain ✓.

**qwen3-0.6b-ft0 / euston_peakhour / s19 (+21.8%) — mixed (seed-hard for all arms).** ft0's composition is exactly at its own norms (anti-starv 114 vs 114, div-served 84 vs 86, override 0.472 vs 0.465) — nothing anomalous in the decision stream. But ft1 (+18.3%) and phi4mini (+18.7%) also degrade here, and this is the *easiest* baseline seed of the topology (rank 1/34, 172.3 s = 0.72× median): the MaxPressure baseline got lucky on this realisation, inflating everyone's rel%. Chain ✓.

**qwen3-0.6b-ft0 / oldstreet_junction / s8 (+20.2%) and s10 (+20.4%) — model-leaning, weak-margin.** ft0 on Old Street authors barely half its decisions (authored 0.52 both cells; arm mean 0.536) with anti-starvation serving 181/174 decisions (norm 168) and 82/71 diverged-and-served (norm 64). Mild anomaly on every axis plus 7 teleports (baseline 0). Comparators clean: ft1 −1.1%/−1.4%, phi4mini −0.9%/−2.4%. Chain ✓ both.

**qwen3-0.6b-ft1 + phi4mini-gen-gpu / oldstreet_junction / s20 (+68.6% / +68.5%) — shared pair failure; model(policy)-attributed.** The two arms are near-clones on this seed: authored 0.870 vs 0.867, anti-starv 117 vs 119, diverged-and-served 30 vs 28 (double the arm norms of 14.5/16.1), teleports 13/14 on a topology whose baseline and normal cells teleport ~0–1, completed 326/336 vs baseline 421. The SLM authored 208/325 and 209/328 decisions with only ~9% shield fallback pressure — the models owned the collapse; the scaffold's anti-starvation absorbed the queues it created. ft0 on the same seed: +0.9%. Chain ✓ both.

**qwen3-0.6b-ft1 + phi4mini-gen-gpu / euston_peakhour / s9 (+50.9% / +50.7%) — shared pair failure.** Again near-identical: authored 0.695/0.692, anti-starv 114/116, teleports 47/47 (baseline 13), completed 302/302 vs 443. Divergence is *at* the arm norm (25/24 vs 23/25) — this pair fails not by overriding the shield but by the served mixture (agreeing SLM + anti-starvation) being wrong for this realisation. ft0: −3.7%. Chain ✓ both.

**qwen3-0.6b-ft1 + phi4mini-gen-gpu / euston_peakhour / s17 (+26.5% both) and s4 (+25.1% / +25.0%) — shared pair failures, low-anomaly.** Decision composition sits essentially at arm norms (s4: anti-starv 107 vs mean 107, div-served 14 vs 23 — *less* divergent than usual); baselines are easy seeds (ranks 8 and 16). Elevated teleports (28 vs 10; 42 vs 22) and depressed completions mark real congestion, but the decision stream looks statistically normal — the failure is a policy×realisation mismatch, not a scaffold malfunction or a divergence burst. Chain ✓ all four.

**phi4mini-gen-gpu / oldstreet_junction / s4 (+22.6%) — the one true singleton.** Authored 0.763 vs arm mean 0.883 (depressed — shield disagreement pushed more decisions to anti-starvation: 114 vs 101), div-served 26 vs 16, teleports 9 vs 0 baseline. ft1 −2.6%, ft0 −5.4% on the same seed. The only catastrophic cell that breaks the ft1≈phi4mini pairing. Chain ✓.

## 3. Shared vs arm-specific: the verdict

The 14 cells collapse onto **10 (topology, seed) pairs**: 4 pairs with exactly two catastrophic arms — and it is *always the same two arms* (qwen3-0.6b-ft1 + phi4mini-gen-gpu, with per-seed rel% agreeing to within 0.1–0.2 points) — and 6 single-arm pairs, of which 5 are qwen3-0.6b-ft0 alone and 1 is phi4mini alone. No seed is catastrophic for all three arms (euston s19 comes closest: +21.8/+18.3/+18.7).

The data therefore supports a **two-regime, controller-property explanation, not a demand-hardness explanation**:

1. **It is not the seed's demand being objectively hard.** Catastrophic seeds are *baseline-easy or median* realisations — ranks 1, 4, 5, 7, 8, 10, 14, 16, 18, 20 of ~35; none in the top-baseline-delay tail. The MaxPressure baseline never blows up on these seeds; only controllers do. (Low baselines do inflate rel% somewhat, but the absolute SLM delays are also 1.2–2.0× the arm's own topology median, so the collapses are real.)
2. **ft1 and phi4mini-gen-gpu fail as a pair** because their served decision streams are nearly identical (high shield agreement ~0.85–0.90, near-identical served_by splits, teleports matching to ±1) — the fine-tune converged onto essentially the same effective policy as generalist phi-4-mini under this scaffold. Their failures are a *shared-policy × seed* interaction: same policy, same seeds, same collapse.
3. **ft0's failures are strictly its own** (5/6 singleton cells), driven by a visibly different mechanism: override rate ~0.47–0.65 and diverged-and-served counts 3–5× the ft1/phi4mini level. Where ft0 collapses, the other two arms are within ±5% of baseline, and vice versa.

## 4. What the audit trail adds (H1×H2 fusion)

The H2 audit layer was built to prove what the controller did after an *accident*; the same signed record is what turns a performance collapse from an anecdote into an attributable event. Worked example — the worst cell, **qwen3-0.6b-ft0 / euston_peakhour / seed 13 (+110.3%)**: the tamper-evident decision log verifies end-to-end (`audit_verify_chain = True`), so the following served-decision ledger is provably the one the controller actually executed: 335 decisions, `served_by = {slm: 214, shield: 0, anti_starvation: 121}`; 318 valid SLM proposals of which only 95 agreed with the shield and **119 divergent proposals were served** (override rate 0.556). That record rules out the two exculpatory hypotheses in one read: the shield never had to replace a malformed proposal (`shield_fallbacks_none = 0`, shield-served = 0), and the anti-starvation guard fired at its normal rate (121 vs an arm-topology mean of 114.5) — so the collapse was not the scaffold thrashing, it was the model's own served, shield-divergent decisions, and the model cannot disown them because each one is in the verified chain. Conversely, the same ledger *clears* the model in cells like euston s19, where every composition statistic sits at its norms and the comparator arms degrade too. Without the audit layer these 14 cells would all read as "SLM slow on some seeds"; with it, each failure carries a signed decision-composition fingerprint that separates model fault, scaffold fault, and unlucky realisation — which is precisely the fusion of the H1 (performance) and H2 (accountability) hypotheses. Limitation, stated plainly: per-decision `audit_records` were not persisted in this campaign's result files (only aggregate `decision_stats` plus the chain-verification flag), so within-run *timing* of the divergence burst (demand ramp vs sustained) is not recoverable from these JSONs.
