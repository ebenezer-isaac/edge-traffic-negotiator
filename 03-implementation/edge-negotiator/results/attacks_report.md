# Attack & Detection Report — The Edge Negotiator (Wk7-8 DE-RISK)

Hard detection data for the three threat-model scenarios (`../THREAT-MODEL-ANALYSIS.md` §4), measured against KNOWN ground-truth labels per injected message. All runs use the deterministic `StubAgent` and an in-memory TraCI stand-in — NO Foundry, NO SUMO — so every number below reproduces exactly via `python src/run_attacks.py`.

Conservation tolerance (default): **2 vehicles**. Detection latency is in control cycles. The conservation check is STATELESS, so a clearly-detectable spoof fires the SAME cycle its inflated edge appears — measured directly at **1 control cycle**. (The 'first-detect latency' in the summary table below is instead an artifact of the delta SWEEP ordering: the first malicious message in the sweep is a sub-tolerance lie that correctly never fires, so the first FLAGGED message arrives a couple of sweep steps later. The true per-message latency is 1 cycle.)

## Summary — precision / recall / F1 / latency per attack

| attack | TP | FP | FN | TN | precision | recall | F1 | first-detect latency |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| (a) spoof (insider over-claim) | 4 | 0 | 2 | 1 | 1.000 | 0.667 | 0.800 | 2 cycle(s) |
| (b) faulty sensor (under-claim) | 3 | 0 | 2 | 1 | 1.000 | 0.600 | 0.750 | 1 cycle(s) |
| (c) sybil/impersonation (auth, 4 cases) | 4 | 0 | 0 | 0 | 1.000 | 1.000 | 1.000 | 0 cycle(s) |

> The spoof and faulty sweeps deliberately INCLUDE within-tolerance / benign cases, so their FN/recall reflect the sub-tolerance evasion floor — recall is NOT 1.0 by construction. The auth row scores ONLY the four admission-control violations (recall 1.0, latency 0). The c3 collusion-lockstep evasion is reported separately (detected_by_auth=False, detected_by_conservation=False) — malicious but caught by NEITHER layer; see §C.

## (a) Spoofed report — conservation `inflated`

A registered, approved A1 signs a genuine message but inflates its claimed `release` toward A0 by `delta`; A0 observes the true `15`. Auth ADMITS (valid member/signature); conservation is the detector. Expected: `inflated` once `delta > tolerance (2)`; within-tolerance over-claims EVADE.

| delta | claim | observed | malicious | detected | reason | expected |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 15 | 15 | False | False | ok | ok |
| 1 | 16 | 15 | True | False | ok | ok |
| 2 | 17 | 15 | True | False | ok | ok |
| 3 | 18 | 15 | True | True | inflated | inflated |
| 5 | 20 | 15 | True | True | inflated | inflated |
| 10 | 25 | 15 | True | True | inflated | inflated |
| 25 | 40 | 15 | True | True | inflated | inflated |

**Measured:** precision=1.000, recall=0.667, F1=0.800, latency=2 cycle(s). Expected-vs-measured verdict: MATCH — every `delta > 2` flags `inflated`; every `delta <= 2` is `ok` (the sub-tolerance lies that evade, quantified).

## (b) Faulty sensor — conservation `under_reported` / `missing_claim`

No adversary: A1's own counter drops a fraction of its true release (`20`) so it UNDER-claims, while A0 observes the truth. `delta = claimed − observed < −tolerance` ⇒ `under_reported`; a TOTAL sender outage (drop=1.0) ⇒ `missing_claim`.

| drop fraction | claim | observed | malicious | detected | reason | expected | note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.0 | 20 | 20 | False | False | ok | ok |  |
| 0.1 | 18 | 20 | True | False | ok | ok |  |
| 0.25 | 15 | 20 | True | True | under_reported | under_reported |  |
| 0.5 | 10 | 20 | True | True | under_reported | under_reported |  |
| 0.75 | 5 | 20 | True | True | under_reported | under_reported |  |
| 1.0 | 0 | 20 | True | False | none | missing_claim | controller never reconciles an unclaimed edge -> missing_claim unreachable via live decide() |

**Measured:** precision=1.000, recall=0.600, F1=0.750, latency=1 cycle(s). Honest caveat (N3): the flag attaches to edge A1→A0 and CANNOT distinguish 'A1's sensor faulty' from 'A0 over-observed' — auth+revoke can eject a node but cannot repair a fault.

**As-built finding (drop=1.0 row):** a TOTAL sender outage publishes no claim, so the controller's `decide()` never constructs an observed-only edge for conservation — the `missing_claim` reason that `evaluate` *can* emit in isolation is UNREACHABLE through the live coordination path. The outage therefore goes undetected (a measured FN), an honest gap between the conservation primitive's capability and the controller's wiring.

## (c) Sybil / impersonation — caught by the AUTH layer (`bus.rejected`)

Each outsider/impersonation case is rejected at `MessageBus.inbox` BEFORE conservation is ever consulted (detection latency = 0 cycles, never delivered). The final row is the c3 collusion EVASION — malicious but caught by NEITHER layer (the Xiao2026 residual limit).

| case | expected verdict | measured verdict | caught |
| --- | --- | --- | --- |
| unknown_sender (outsider Sybil) | unknown_sender | unknown_sender | True |
| not_neighbour (non-adjacent injection) | not_neighbour | not_neighbour | True |
| revoked (membership withdrawn) | revoked | revoked | True |
| bad_signature (impersonation/tamper) | bad_signature | bad_signature | True |
| collusion lockstep (Xiao2026 evasion) | ok / NEITHER | ok (MISS) | False |

**Verdict:** all four admission-control violations (unknown_sender, not_neighbour, revoked, bad_signature) are rejected exactly as the threat-model predicts. The collusion case is UNDETECTED — recall = 0 on that scenario — which is the correct, honest result, not a bug.

**Incidental as-built note:** each junction also publishes its OWN report every decision; reading its inbox it drops that self-echo with reason `not_neighbour` (a node is not its own neighbour). This is benign and is NOT a false positive against any peer — peer-message precision stays 1.0 — but it means the raw `bus.rejected` log is never empty even on a fully honest run; scoring filters self-echoes out.

## Tolerance sweep — false-alarm rate vs recall (spoof detector)

A fixed mixed message set (benign jitter at delta∈{0,1,2}; lies at delta∈{3,5,8,15,30}) scored at each tolerance. Raising tolerance suppresses jitter false-alarms but lets larger lies slip under the band.

| tolerance | TP | FP | FN | TN | recall | false-alarm rate | precision | F1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 0 | 5 | 2 | 0 | 1 | 1.000 | 0.667 | 0.714 | 0.833 |
| 1 | 5 | 1 | 0 | 2 | 1.000 | 0.333 | 0.833 | 0.909 |
| 2 | 5 | 0 | 0 | 3 | 1.000 | 0.000 | 1.000 | 1.000 |
| 3 | 4 | 0 | 1 | 3 | 0.800 | 0.000 | 1.000 | 0.889 |
| 5 | 3 | 0 | 2 | 3 | 0.600 | 0.000 | 1.000 | 0.750 |
| 10 | 2 | 0 | 3 | 3 | 0.400 | 0.000 | 1.000 | 0.571 |

**Read-off:** the tolerance band is a hard floor on detectable manipulation magnitude — a smart attacker simply lies INSIDE it every cycle and is never flagged (non-claim N4). Lowering tolerance raises recall on small lies at the cost of false-alarming on honest in-transit jitter; raising it does the reverse. There is no setting that catches a sub-tolerance lie without also false-alarming on benign jitter.

## Most important honest limitation the data exposes

The detectors are SOUND but NARROW. Auth catches 100% of outsiders, impersonators, revoked members, and tampering (recall 1.0, latency 0). Conservation catches 100% of UNCOORDINATED single-sided lies/faults whose residual exceeds tolerance (recall 1.0 above the band). But TWO classes are measured at recall 0:

1. **Sub-tolerance lies** — any single-party falsification with `|claim − observed| <= 2` is `ok` every cycle; the stateless check accumulates no cross-tick evidence (N4). The tolerance sweep shows no operating point escapes this without false-alarming on jitter.
2. **Coordinated collusion** — two approved junctions inflating claim and observation in lockstep keep `delta` within tolerance, so conservation returns `ok` and auth (valid members, valid signatures) admits them. Caught by NEITHER layer — the empirically-confirmed Xiao2026 residual limit. The only available response is containment, not detection: `revoke()` + the tamper-evident hash-chained audit log give non-repudiable attribution AFTER the fact, never silent prevention.

This is why the defensible thesis claim is *'authenticated, consistency-checked coordination with spoof/fault detection against UNCOORDINATED adversaries and faults'* — never trust, truth, or collusion-resistance.
