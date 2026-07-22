# Glossary: plain-language translations of every domain term

Audience: any technically literate reader (engineer, examiner) who is not a traffic-engineering, applied-statistics, or cryptography specialist. Each entry translates the jargon and keeps the concept precise. Grouped by area.

---

## Traffic-signal control

- **Phase (green phase).** One legal combination of green lights at a junction (e.g. "east-west goes, north-south stops"). A controller's job each cycle is to pick which phase to show next.
- **MaxPressure.** The classical signal-control rule we use as the baseline and safety net. It serves the phase with the most "pressure" = roughly (cars waiting upstream) − (cars stuck downstream). Proven to maximise throughput when stable. We implement the simplified vehicle-count form; the full theorem also weights by saturation flow and turning ratios.
- **Throughput-optimal.** A property of MaxPressure: if any signal policy can keep the network's queues from blowing up at a given demand, MaxPressure can too. It does not mean "lowest delay", just "won't lose stability unnecessarily".
- **Shield / deterministic shield.** A hard rule layer that checks (and can override) the AI's proposed phase, guaranteeing safety limits are never violated no matter what the AI says.
- **Safety floor.** The fixed set of rules the AI can never override: minimum and maximum green, protected yellow and all-red clearance, no approach skipped too long (anti-starvation), and preemption granted only for a corroborated emergency. It holds every tick, attacked or not.
- **Min green / max green.** The shortest and longest a phase is allowed to stay green. Min green stops the lights flickering; max green stops one direction hogging the junction.
- **Yellow change interval / all-red clearance.** The yellow time (so approaching cars can stop) and the brief all-directions-red (so the junction empties) between one green and the next. Both are safety intervals that cannot be shortened.
- **Lost time / start-up lost time.** Seconds per cycle where no useful traffic moves: drivers reacting at green onset (start-up) plus the change intervals. It reduces a junction's usable capacity.
- **Webster cycle.** A classic formula for the ideal total cycle length of a signal given its lost time and how saturated it is. Longer cycles waste less on lost time but make everyone wait longer.
- **Green wave / offset.** Timing neighbouring signals so a platoon hits greens in sequence and barely stops. The "offset" is the delay between one junction going green and the next, set from the travel time between them.
- **Anti-starvation.** A guarantee that no approach is skipped forever: if a direction has been passed over too many times, it is forced to get green next.
- **Preemption.** Overriding normal timing to give an emergency vehicle a green path through.
- **Spillback.** A queue so long it backs up past the previous junction, so the road is jammed rather than just busy. Detectors must not mistake this for a reporting error.

## The edge AI

- **SLM (small language model).** A language model small enough to run on local hardware. Here, **Phi-4-mini** (3.8 billion parameters).
- **Frozen / inference-only / no-training.** We use the model as shipped, never retraining or fine-tuning it. It only answers prompts.
- **Foundry Local.** Microsoft's runtime for serving models on local hardware (no cloud). It is how Phi-4-mini runs at the edge here.
- **Edge.** Computation on local roadside hardware rather than in a remote data centre. Matters for latency, cost, and not depending on a network link.
- **Guarded exception handler.** The role of the SLM: the classical controller runs the normal case; the SLM is only invoked on an unusual event (an anomaly or emergency), and its answer is still checked by the shield.
- **Trigger.** A condition that escalates from the classical controller to the SLM (e.g. a detected anomaly, an emergency vehicle, an incident, abnormal demand).
- **Ambiguous case.** A decision tick the classical rule cannot settle cleanly on its own: a neighbour claim the detector has flagged, an emergency claim with partial-but-not-full evidence, or two claims about the same road that disagree beyond tolerance. Only these escalate to the SLM; fully clear-cut and fully zero-evidence cases are handled deterministically and never escalated.
- **RAG (retrieval-augmented generation).** Letting a model look up relevant past cases and add them to its prompt. Optional here, never load-bearing.
- **Channel A / Channel B.** Two ways neighbour information reaches a junction's decision: Channel A folds it into the SLM's prompt; Channel B adjusts the classical controller's scores directly. `coord_weight` is how strongly Channel B counts neighbour traffic.

## Simulation

- **SUMO.** Eclipse SUMO, an open microscopic traffic simulator (every vehicle modelled individually). Our whole evaluation runs in it.
- **TraCI.** SUMO's live control interface: our code reads sensor data and writes signal states each simulated second through it.
- **vClass = emergency.** SUMO's vehicle-class tag marking a vehicle as an emergency vehicle (e.g. an ambulance) so we can detect it.
- **Tripinfo.** SUMO's per-trip output (when each vehicle departed, arrived, how long it waited). The honest source for delay and completion metrics.

## Security and trust

- **Ed25519 / signature.** A fast public-key signing scheme. Each junction signs its messages with a private key; neighbours verify with the public key. A valid signature proves who sent it and that it was not altered.
- **Permissioned registry.** The list of approved junction public keys, with the power to `revoke` a key. Only registered, non-revoked senders are trusted.
- **Hash-chained audit log.** A tamper-evident record: each entry includes a hash of the previous one, so any later edit is detectable. It records what happened; it does not prevent a lie, it makes the lie attributable.
- **Replay.** An attacker re-sending an old, validly-signed message to fool a receiver. Defended by remembering which messages were already delivered (within a session).
- **Dolev-Yao.** The standard model of a network attacker who can read, drop, reorder, and replay messages but cannot break the cryptography.
- **Compromised insider.** An attacker who holds a *valid* key (a junction that has been taken over). Signatures pass, so signing alone cannot stop it; this is the case our plausibility check targets.
- **Corroboration (the corroboration gate).** Before granting an emergency claim, the junction requires independent physical evidence: it sensed the vehicle itself, or another junction did. A signed-but-spoofed claim has no such evidence, so it is refused. This is what stops a fake emergency even from a valid-key insider.
- **Robust degradation.** The property that when a neighbour is compromised (a spoofed claim, an inflated or under-reported release, a replay, or silence), the system flags the deviation within a bounded window, stops that input from influencing control, and performs no meaningfully worse than plain local control (MaxPressure with no coordination), while the safety floor still holds throughout. A lie small enough to stay inside the tolerance band is undetected by construction: an acknowledged limit, not a failure of the property.
- **Advance claim vs local sensing.** *Local sensing* = the junction's own detector sees the vehicle (trusted; you cannot spoof a real vehicle into a sensor). *Advance claim* = a neighbour says one is coming (only acted on if corroborated).
- **Conservation check / mass-balance residual.** A plausibility test: vehicles entering a road minus vehicles leaving should match the change in vehicles stored on it. A neighbour claiming it released more cars than actually arrived produces a non-zero "residual" that flags the lie. (`residual = entered − exited − change-in-storage`.)
- **Adaptive band.** The tolerance around zero residual that counts as "normal" (sensors are noisy). It grows with traffic volume so a busy road is not falsely flagged.
- **CUSUM (cumulative sum).** A statistical detector that adds up small deviations over time and alarms when the running total crosses a threshold, catching a sustained small lie that any single reading would miss.
- **ARL (average run length).** CUSUM's tuning trade-off: ARL₀ = average time between false alarms when all is well (want it long); ARL₁ = average time to catch a real shift (want it short).
- **Exploit-then-defend.** A secondary validation experiment: build a competent victim that trusts its inputs, attack it, then show the robustness layer detects and absorbs the same attack. It validates that coordination stays safe under a compromised junction, not the primary contribution.
- **Fair victim / cooperative_naive.** The victim controller, made deliberately competent (not a strawman) so the comparison is fair. It is representative of the trust-everything cooperative class that CoLLMLight exemplifies.
- **Measured characterisation / free-deviation boundary.** A map of which stealthy insider deviations the gate can and cannot hold accountable, as the deviation gets smaller or more physics-consistent. Gross deviations are always caught; below some size (the phase-coupled coverage threshold) they escape. The result is *where* that boundary sits, not a yes/no claim. This is a measured characterisation (not a detection ROC) and is not the contribution's headline; the headline is the self-referential coupling below.
- **Lie-magnitude sweep.** Running the attack at many deviation sizes (as multiples of the tolerance band) to trace that boundary.
- **Self-referential coupling (the novel object).** The preemption attack controls the signal phase, which is *also* the variable that gates honest-witness coverage: executing the attack opens the very coverage desert that would otherwise conceal it. Stated as a conditional lemma under explicit hypotheses and measured once on the real corridor. This is the headline contribution; the accountability log mechanism itself is credited to prior art (Certificate Transparency), not claimed novel.
- **Certificate-Transparency-style anchor.** The accountability layer's mechanism: a signed hash-chained log whose batch commitments are anchored to a quorum of independent witnesses and read by a named cross-auditor (split-view detection). Credited to prior art (RFC 6962 and successors), cited, not claimed as a novel mechanism. It is a permissioned, quorum-anchored append-only log, not an open consensus ledger; the key registry is permissioned, not permissionless.

## Statistics and calibration

- **Paired on seed.** Each random scenario (seed) is run through every controller, and we compare within the same seed, so differences are not confounded by which scenario happened to be easier.
- **MDE (minimum detectable effect).** The smallest true difference our experiment has the power to detect. Reporting it turns a non-significant result into "any effect is smaller than X" instead of "no effect".
- **BCa bootstrap.** A resampling method for confidence intervals that corrects for skew and bias (Efron 1987). We report effect sizes with these intervals.
- **Permutation test.** A p-value computed by shuffling the labels many times to see how often chance reproduces the observed difference. We use the corrected (B+1)/(m+1) form for sampled permutations.
- **Holm-Bonferroni.** A method to control false positives when testing several metrics at once, less conservative than plain Bonferroni.
- **Cliff's delta.** A non-parametric effect size: the probability one group's value exceeds the other's, minus the reverse. Robust to non-normal data.
- **GEH.** A traffic-engineering goodness-of-fit statistic comparing modelled vs observed flows; GEH < 5 on most links is the standard "calibration acceptable" bar (UK DfT TAG).
- **EWMA (exponentially weighted moving average).** A running average that weights recent observations more, used to learn a junction's normal demand so abnormal demand stands out.
- **Effective sample size (n_eff).** When repeated measurements within a seed are correlated, the *effective* number of independent observations is less than the raw count; the Kish formula adjusts for it.

## Theory references

- **LWR (Lighthill-Whitham-Richards).** The foundational traffic-flow conservation law (1955-56): vehicles are conserved like a fluid, which is the physics our conservation check rests on.
- **Greenshields fundamental diagram.** The classic speed-density relationship; gives the occupancy at which a road is at capacity vs jammed, used to set the spillback threshold.
- **CoLLMLight / VLMLight / LA-Light.** The closest prior systems. CoLLMLight: cooperative LLM coordination, trusts shared state, fine-tuned 8B, CityFlow. VLMLight: fast-classical + slow-LLM dual branch, single-junction, large models. LA-Light: LLM calls rule/RL controllers for rare events, cloud GPT-4. None handles a compromised coordination channel; see the survey table.
