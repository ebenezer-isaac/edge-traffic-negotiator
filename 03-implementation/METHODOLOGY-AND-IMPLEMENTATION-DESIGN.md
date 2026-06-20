# The Edge Negotiator — Methodology & Implementation Design (Build Plan)

**Status:** prescriptive build plan, 2026-06-20. Locks down the methodology and the
concrete code/scenario changes for the emergency-handling SLM controller, the
exploit-then-defend headline, and the edge-case handling. Derived from a full read of
`src/` and the canonical `PROJECT-PROPOSAL.md` + `FORMAL-SPECIFICATION.md`.

This document is authoritative for *how to build it*. Where it conflicts with the
as-built code, this is the target. Two as-built bugs it deliberately fixes:

- **B1 — inert coordination** (`coordinated_controller.py:711`): `used = proposal if proposal is not None else coord_choice`,
  so the coordination/emergency term is only consulted on SLM fallback. A reliable agent
  never falls back, so the term is computed, counted, then discarded. The triggered-regime
  decision below makes the escalated output **causal**. (This is a prerequisite for the
  fair-victim experiment in §4: the benign "tie" claim only holds once coordination is causal.)
- **B2 — silent edge no-op on OSM**: grid `f"{src}{dst}"` parsing returns None for
  every real edge. Fixed by the existing `edge_map` injection path; emergency scenarios
  MUST pass an explicit `edge_map`.

Naming: "escalation" = a control tick where a trigger fires and the system leaves the
default MaxPressure regime. "Triggered regime" = the per-junction decision path taken on
an escalated tick.

---

## In plain terms (read this first)

This is the build plan: the concrete classes, files, and scenario changes that turn the proposal into running code, plus a register of edge cases and how each is handled. It is written for whoever implements it (including a future session). Where it disagrees with the code as it stands today, the plan is the target, not the code. Specialist terms are translated in [`GLOSSARY.md`](GLOSSARY.md).

## 0. The two regimes (the spine of the whole design)

Every SLM junction, every decision tick, is in exactly one regime:

| Regime | Entry condition | Who decides the phase | Causal? |
|---|---|---|---|
| **NORMAL** | no trigger active for this junction | MaxPressure (+ optional Channel-B coordination term, advisory) | n/a — MaxPressure is the floor |
| **TRIGGERED** | a trigger predicate fires (see §2) | SLM exception handler proposes; **safety shield validates and can override**; the *accepted* proposal is executed | YES — the emergency decision changes the executed phase, gated by the shield |

The bug B1 lives entirely in NORMAL regime, where coordination was advisory-only. We
**keep it advisory in NORMAL** (correct: MaxPressure is throughput-optimal and we never
want a weak SLM degrading normal flow) and make the SLM/emergency output **authoritative
in TRIGGERED regime, subject to the shield's veto**. This is the clean resolution of the
"Channel-B override" open question: the override is scoped to the triggered regime, not blanket-on.

---

## 1. Coordinated SLM Emergency Controller

### 1.1 New class: `EmergencyController(CoordinatedController)`

**File: NEW `src/emergency_controller.py`.** Subclasses `CoordinatedController` so all
signing/verification/conservation/coordination plumbing is inherited unchanged. It adds:

- a **trigger evaluator** (§2) producing a per-junction `Trigger | None` each tick,
- the **triggered-regime decision path** that makes the SLM/emergency output causal,
- the **shield validation** of the SLM proposal (the safety guarantee),
- richer event logging (trigger reason, proposal, shield verdict, applied phase).

We subclass rather than edit `coordinated_controller.py` so the offline attack harness,
the 30-seed StubAgent matrix, and all 166+ existing tests stay byte-identical. The
emergency behaviour only activates when an `EmergencyController` is instantiated with a
non-empty trigger config.

### 1.2 Per-tick decision flow (prescriptive)

For each SLM junction `tl`, inside `decide(tl, st)`:

```
1.  mp_choice = MaxPressure argmax over phases            # always computed first (the shield's base)
2.  if tl not in slm OR sum(halting) < gate:              # event-gate (unchanged)
        return mp_choice                                  # NORMAL, quiet: shield only

3.  publish signed `toward` message; read verified inbox  # inherited from CoordinatedController
    run conservation reconciliation -> self.detections    # inherited (windowed detector)
    compute coord_choice (Channel-B advisory ref)          # inherited

4.  trig = self._evaluate_trigger(tl, st, detections_this_tick, ctx)   # §2

5.  if trig is None:                                       # NORMAL regime
        # coordination stays ADVISORY (B1 stays fixed: no silent override of MaxPressure)
        proposal = agent.choose_phase(... neighbor_note ...)   # optional; advisory note only
        used = proposal if proposal is not None else coord_choice
        return self._shield_validate(tl, st, used, mp_choice, trig=None)

6.  else:                                                  # TRIGGERED regime — SLM is AUTHORITATIVE
        emergency_note = self._build_emergency_prompt(tl, st, trig, incoming_per_phase)
        proposal = agent.choose_phase(tl, n, halting, neighbor_note=emergency_note)
        candidate = proposal if proposal is not None else self._rule_fallback(tl, st, trig)
        applied  = self._shield_validate(tl, st, candidate, mp_choice, trig=trig)
        self._log_escalation(tl, trig, proposal, candidate, applied, mp_choice)
        return applied
```

The crucial difference vs B1: in step 6 the SLM proposal (or its rule fallback) is the
**candidate that gets executed**, not a value discarded in favour of MaxPressure. The
shield can still veto it (1.3), but a *valid, shield-approved* emergency proposal
**changes the executed phase**. This is verified by a new metric
`escalation_changed_decisions` (count of escalated ticks where `applied != mp_choice`),
the emergency analogue of `coord_adjusted_decisions`.

### 1.3 The shield: `_shield_validate(tl, st, candidate, mp_choice, trig)`

The safety guarantee. MaxPressure is the shield. The shield ACCEPTS the candidate unless
it is unsafe or clearly worse than MaxPressure by the regime's own objective:

```
def _shield_validate(tl, st, candidate, mp_choice, trig):
    # (V1) Validity: candidate must be a real green-phase index.
    if candidate is None or not (0 <= candidate < len(st["green"])):
        return mp_choice                                  # invalid -> shield wins (FR-1)

    # (V2) Hard safety invariants (always, both regimes):
    #   - never shorten an active green below min_green (handled by step() timing)
    #   - never skip the clearing yellow (handled by step(): green->yellow->green)
    #   These are STRUCTURAL: decide() only chooses a target phase; step() owns the
    #   min-green/yellow transition, so an SLM cannot create an unsafe transition.

    # (V_starve) Anti-starvation (deterministic, independent of the SLM): if any approach has
    #   been skipped > max_skip decisions, the shield FORCES the most-starved approach next
    #   cycle. The only thing that may defer it is an ADMISSIBLE (corroborated) EV preemption,
    #   and then by at most one min_green+yellow. Tracked via per-approach last-served tick.
    starved = self._most_starved_approach(tl, st)         # None unless one exceeds max_skip
    if starved is not None and not self._admissible_ev(trig):
        return self._phase_serving(tl, starved)

    # (V3) Regime-specific acceptance:
    if trig is None:                                      # NORMAL
        return candidate                                  # advisory coordination already folded in
    if trig.kind == "emergency_vehicle":
        # Preemption is admitted ONLY for a CORROBORATED EV (see _admissible_ev / 2.1):
        #   local sensing (this junction's own vClass detector), OR an advance claim that is
        #   auth-valid AND independently corroborated by an upstream junction's own sighting.
        # An uncorroborated (phantom / spoofed) claim is NOT enforced -> MaxPressure stands.
        if not self._admissible_ev(trig):
            return mp_choice                              # spoofed/uncorroborated -> no preemption
        return self._phase_serving(tl, trig.approach_edge)  # corroborated EV -> enforce
    # (V4) Conservation gate: a candidate leaning on a claim flagged as a persistent anomaly
    #   is recomputed with that claim zeroed (done in decide() before the shield); then:
    # (V5) Pressure floor (all non-EV triggers: incident / conservation_anomaly /
    #   sensor_outage / abnormal_demand): accept the SLM candidate UNLESS its served
    #   pressure is far worse than MaxPressure's (would STARVE).
    if self._pressure(st, candidate) < self._pressure(st, mp_choice) - self.shield_margin:
        return mp_choice                                  # candidate starves traffic -> veto
    return candidate

def _admissible_ev(trig) -> bool:
    if trig is None or trig.kind != "emergency_vehicle":
        return False
    if trig.source == "local_sensing":
        return True                                       # own detector saw the EV -> trust
    if trig.source == "advance_claim":
        return trig.auth_valid and trig.corroborated      # signed + upstream-sensed (2.1)
    return False
```

`shield_margin` is a calibrated `[K]` parameter (no guessed default ships; sweep {0,2,4,8,16},
report the 0 baseline and the selected value — see FORMAL-SPECIFICATION.md §1.1): 0 = shield
vetoes any candidate worse than MaxPressure (most conservative, "never regress"); larger =
gives the SLM more latitude on incident/demand triggers. A **corroborated** emergency preemption is
not subject to the pressure margin: clearing the EV is the objective and the shield enforces
it deterministically even if the SLM proposed otherwise, so a broken SLM cannot block a real
ambulance. An **uncorroborated** emergency claim is never enforced (it falls back to
MaxPressure), so a spoofed emergency cannot commandeer the signal. This is the safety
property: **the deterministic layer guarantees preemption for a real, corroborated EV and
refuses it for a phantom one; the SLM only adds nuance on the ambiguous middle** (which
non-EV phase to favour around a real EV, how to weigh multiple simultaneous EVs, EV-plus-
incident routing) where no clean deterministic rule decides.

### 1.4 Why this is safe AND causal

- **Safe:** invalid/None proposals fall to MaxPressure (FR-1). min-green/yellow are owned
  by `step()`, untouchable by the SLM. In incident/demand regimes a starving candidate is
  vetoed. EV preemption is deterministically enforced, not delegated.
- **Causal:** in TRIGGERED regime a valid shield-approved proposal is the executed phase.
  `coord_weight=0` + no triggers reduces *exactly* to MaxPressure (FR-8 ablation preserved,
  inherited from `CoordinatedController`'s short-circuit).

### 1.5 Files

- NEW `src/emergency_controller.py` (~250 lines): `Trigger` dataclass, `EmergencyController`.
- CHANGE `src/coordinated_controller.py`: extract `_phase_serving(tl, in_edge)` and
  `_pressure` reuse helpers as protected methods if not already (they exist: `_pressure`,
  `_incoming_per_phase`). Add nothing else; keep its `decide` intact.
- NEW `src/run_emergency.py`: runner wiring (mirrors `run_coordinated.py`), builds
  identities/registry/bus + `edge_map`, instantiates `EmergencyController`, drives SUMO.

---

## 2. Trigger Logic

A trigger is a frozen dataclass:

```python
@dataclass(frozen=True)
class Trigger:
    kind: str          # "emergency_vehicle" | "incident" | "sensor_outage" | "abnormal_demand" | "conservation_anomaly"
    junction: str
    approach_edge: str | None   # the in-edge the event is on (for preemption / phase targeting)
    severity: float             # normalised 0..1 for prompt + prioritisation
    evidence: dict              # raw numbers for the audit log
```

`_evaluate_trigger` returns the **highest-priority** active trigger for the junction
(priority order: `emergency_vehicle > incident > conservation_anomaly > sensor_outage >
abnormal_demand`). Multiple simultaneous triggers are recorded in `evidence["also"]` but
only the top one drives the regime; the prompt mentions all (see §7 multi-emergency).

### 2.1 Emergency vehicle (preemption)

- **Signal:** an EV is on or approaching an in-lane of `tl`. Read via TraCI:
  `traci.vehicle.getVehicleClass(vid) == "emergency"` over
  `edge.getLastStepVehicleIDs(in_edge)` for each in-edge, OR (cheaper, preferred) the
  vehicle carries `device.bluelight` and we detect it via
  `traci.vehicle.getParameter(vid, "device.bluelight.<...>")` presence. Simplest robust
  check: maintain a per-tick set of EV ids via vClass scan over watched in-edges.
- **Threshold:** fire when an EV is within `ev_horizon` metres of the stop line OR already
  halted on an in-approach. `ev_horizon = v_free·(min_green + yellow + processing)` (the
  canonical formula in FORMAL-SPECIFICATION.md §1.3; ≈195 m at 13.9 m/s), so the green can
  be pre-positioned before arrival — long enough to hold the clearing phase, run the change
  interval, and absorb the SLM round-trip.
- **Over-trigger guard:** debounce — once preemption fires for an EV id it stays latched
  for that junction until the EV clears the junction (id leaves all in/out edges), so the
  signal does not flap if the EV momentarily drops off a detector.
- **Under-trigger guard:** scan ALL in-edges (cross street included), not just the arterial,
  so a cross-street ambulance is not missed.
- **Two trigger sources, different trust (`trig.source`):** (i) `local_sensing` — this
  junction's own vClass scan of its in-edges, trustworthy (its own detector), admits
  preemption directly. (ii) `advance_claim` — a signed `ev_claim` from the EV's registered
  key or an upstream neighbour, used to pre-position green BEFORE the EV physically arrives
  (green-wave preemption). An advance claim is spoofable, so it is admitted only if
  **corroborated**.
- **Corroboration (the anti-spoof basis; answers "how would an upstream junction know?"):**
  a real EV physically traverses the corridor, so an upstream junction it has already passed
  *independently sensed* it (that junction's OWN vClass detector, shared as signed
  telemetry). An advance claim for EV `e` arriving at `tl` is `corroborated` iff some upstream
  junction `U` on `e`'s route logged a `vClass=emergency` sighting on the edge toward `tl`
  within `[now - route_traveltime - tol, now]`. A phantom claim that NO junction has sensed
  anywhere is uncorroborated, and the shield refuses preemption (1.3, V3). The knowledge never
  comes "from the claiming junction"; it comes from each junction's own physical sensing of
  the EV as it passes. **Limit:** an EV entering mid-corridor with no instrumented upstream
  junction gets only on-arrival (local) preemption, not advance; a colluding upstream junction
  faking a sighting is the >=2-key collusion case, explicitly out of scope.

### 2.2 Incident / roadblock

- **Signal:** a stopped/blocked condition on an approach not explained by the normal red.
  Detect via the existing windowed metadata `_edge_meta[edge] = (occupancy, mean_speed,
  free_speed)`: an incident edge has **high occupancy AND near-zero speed sustained across
  windows while that approach has GREEN** (a jam that green is not draining = blockage, not
  ordinary queueing). Reuse `FlowConservationDetector._is_spillback` logic but condition on
  "green and still not moving".
- **Threshold:** `occupancy >= incident_occ (0.7)` AND `mean_speed <= 0.1*free_speed` for
  `>= incident_persist (3)` consecutive windows *while the serving phase is green*.
- **Over-trigger guard:** the "while green and persistent" condition distinguishes a real
  blockage from a normal red-phase queue. Spillback from a downstream jam (occupancy high
  but the edge IS draining when green) does NOT fire — that is honest congestion (§7).
- **Under-trigger guard:** if a lane-area detector (E2) is configured on the approach, also
  fire on `jamLengthInVehicles` exceeding a fraction of edge length; gives earlier
  detection than occupancy alone.

### 2.3 Sensor outage (drop detection on an approach)

- **Signal:** a registered, approved neighbour that *should* report (adjacency + recent
  history of claims) goes silent while its in-edge shows observed inflow. This is exactly
  the as-built `reconcile_silent_neighbours=True` path producing a `missing_claim`
  Detection (`coordinated_controller.py:742`). The emergency controller turns a sustained
  `missing_claim` into a `sensor_outage` trigger.
- **Threshold:** `missing_claim` from the same neighbour for `>= outage_persist (3)`
  consecutive decision rounds.
- **Handling:** the SLM is told "neighbour X report is DOWN; rely on local queues for that
  approach"; the shield falls back to local-observation MaxPressure for that approach
  (graceful "missing report = no update", NFR-5). Conservation keeps flagging it for the
  audit log.
- **Over-trigger guard:** only fires when there IS observed inflow on the silent
  neighbour's edge (a genuinely idle approach that sends nothing is not an outage).

### 2.4 Abnormal demand

- **Signal:** total halting at the junction exceeds its historical band. Maintain a
  per-junction EWMA of total halting; fire when `total_halting > mean + k*std`
  (`k = abnormal_k`, default 3) sustained for `abnormal_persist (2)` windows.
- **Threshold:** EWMA with span ≈ 20 decisions; `k=3` ≈ one-sided 3σ.
- **Over/under guard:** the EWMA self-calibrates per junction, so a chronically busy
  junction does not constantly trip; warm-up of `warmup_windows (3)` before it can fire.

### 2.5 Conservation anomaly (the integrity↔control unification)

- **Signal:** a flagged `Detection` (`inflated` / `under_reported`) from the windowed
  detector this round — i.e. a neighbour's claim is physically implausible. Per
  `FORMAL-SPECIFICATION.md` §4/§8: the same detector that catches spoof/fault is the escalation
  trigger.
- **Handling:** escalate to the SLM but DISCOUNT the flagged neighbour's `incoming_per_phase`
  contribution to zero (do not coordinate on a claim we just judged implausible), and log
  the rejection. The shield's normal pressure-margin guard applies. This makes the defence
  in §4 *act*, not just *log*.

### 2.6 Anti-flap / global rate limit

A single `escalation_cooldown` (default 1 decision) prevents re-escalating the same
junction on the very next tick for the same latched cause unless severity rose. Foundry
serialises SLM calls (measured ~0.5 s/call, p95 0.553 s → ~18 serial decisions per 10 s
window; see results/slm_bench.md); §7 SLM-latency edge case bounds the number
of concurrent escalations.

---

## 3. SUMO Scenario Specs

All emergency scenarios run on the **corridor substrate** (`sumo/corridor/`, J0..J3
arterial + N/S cross streets) because it has green-wave headroom and clean, known edge
ids (`{from}{to}`, e.g. `WJ0`, `J0J1`, `N0J0`). The corridor's `edge_map` is derived once
via `net_topology.edge_map_from_net(net, mode="chain")` and passed to the controller
(fixes B2). Each scenario ships as a route file + an optional additional file; NO net
rebuild needed.

Directory: **NEW `sumo/corridor/scenarios/`** with one `<name>.rou.xml` (+ `<name>.add.xml`
where needed) and a `<name>.sumocfg` per scenario, plus an attacked twin
`<name>_attacked.*`. A scenario manifest `scenarios/manifest.json` lists
`{name, sumocfg, edge_map_mode, trigger_expected, attacked_variant, ground_truth}` so the
harness (§5) iterates them.

### 3.1 Emergency vehicle

**Honest:**
- Add `<vType id="ev" vClass="emergency" guiShape="emergency">` with
  `<param key="has.bluelight.device" value="true"/>`. Bluelight device makes SUMO let it
  run reds in its own right; our controller's *preemption* is what we measure (we can also
  disable bluelight reds to force the controller to clear it, configurable).
- One EV trip routed across all four junctions on the arterial:
  `WJ0 J0J1 J1J2 J2J3 J3E`, departing mid-run (t≈300) into established background demand
  (`gen_routes.py` baseline).
- Expected: each junction in turn fires `emergency_vehicle`, shield enforces the arterial
  green phase as the EV approaches; KPI = AETT/AEWT for the EV vs a no-preemption run.

**Attacked — fake preemption request:** a compromised neighbour signs a `toward` message
with an `ev_claim` field (NEW optional payload field) asserting an EV inbound on an
approach where there is **no EV**. Naive baseline (§4) preempts on the claim, starving the
real traffic. Defence: preemption fires ONLY on **locally observed** EV vClass (the signed
neighbour message can *advise* "EV coming from my direction" to pre-position, but the
shield's enforced preemption requires local confirmation within `ev_horizon`). The phantom
claim is logged as a `conservation_anomaly` (no EV observed on the claimed edge → the
vehicle-conservation check sees a claim with no matching observation).

### 3.2 Accident / roadblock

**Honest:**
- A `<stop>` on a mid-arterial edge (e.g. a vehicle with
  `<stop edge="J1J2" duration="600" parkingArea-or-lane.../>`) that blocks a lane on `J1J2`
  from t≈300. On a 1-lane arterial this is a full blockage; for a multilane variant, close
  one lane via `<rerouter>` with `<closingLaneReroute>`.
- Expected: `J1` (upstream of the block) and `J2` (downstream) fire `incident`; the SLM is
  asked to favour cross-street / alternate phases to avoid feeding the blocked link;
  shield's pressure-margin guard lets a sensible reallocation through but vetoes starvation.
- KPI = incident recovery time (windows from block onset to network delay returning to
  within X% of pre-incident baseline).

**Attacked — phantom accident report:** a compromised neighbour signs a message claiming a
blockage on `J1J2` (e.g. `incident_claim` field) when the edge is flowing. Naive baseline
reroutes/holds for a non-existent incident, wasting capacity. Defence: incident triggers
fire on **locally observed** occupancy+speed, not on the claim; the phantom claim
contradicts local observation (edge is flowing) → flagged + ignored. Logged.

### 3.3 Sensor outage

**Honest:**
- Model an approach detector going dark: the neighbour junction simply **stops publishing**
  its `toward` claim from t≈300 (runner drops its messages), while real traffic continues
  to arrive on that edge. With `reconcile_silent_neighbours=True` + sustained
  `missing_claim`, `sensor_outage` fires.
- Expected: controller degrades that approach to local-observation MaxPressure; no stall
  (NFR-5). KPI = non-priority delay unchanged vs full-sensor baseline (graceful
  degradation), `missing_claim` recall/latency.

**Attacked — spoofed sensor / neighbour message:** the silent neighbour is *replaced* by a
spoofer that over-claims `release` (count-inflation) to mask the outage or to manipulate
coordination. This is the existing `spoof` attack (`attacks.spoof_release`) lifted onto the
live corridor. Defence: windowed conservation detector flags `inflated`; the
`conservation_anomaly` trigger zeroes that neighbour's coordination contribution. Logged.

### 3.4 Scenario build files (concrete)

- NEW `sumo/corridor/scenarios/ev.rou.xml`, `ev.sumocfg` (+ `ev_attacked` twin via an
  injected fake `ev_claim` at the message layer, not a new route file — the attack is on
  the wire, so the twin shares `ev.rou.xml` and differs only in the runner's injector).
- NEW `sumo/corridor/scenarios/incident.rou.xml` (background + the stopping blocker),
  `incident.add.xml` (rerouter for the multilane variant), `incident.sumocfg`.
- NEW `sumo/corridor/scenarios/outage.rou.xml`, `outage.sumocfg` (outage realised in the
  runner by dropping a neighbour's publishes; spoof twin by swapping in `MaliciousPublisher`).
- Reuse `sumo/corridor/gen_routes.py` for the background demand (already parameterised by
  seed/demand); add a `--scenario` flag that appends the EV/blocker trips.

---

## 4. Exploit-then-Defend (the headline)

### 4.1 The fair victim baseline (addressing the reviewer concern)

The reviewer's concern is real: *breaking an unauthenticated system is trivial and a
strawman.* We make the victim baseline a controller **representative of the trust-everything
cooperative class that CoLLMLight exemplifies** (CoLLMLight itself shares neighbour state via
a spatiotemporal graph rather than signed messages; we model the same trust assumption over
an explicit message channel, which is the surface that class implicitly trusts) — otherwise
competent:

- **NEW mode `cooperative_naive`** in the runner: identical control logic to
  `coordinated` (same SLM, same Channel-B coordination term made **causal** in the
  triggered regime, same green-wave benefit) — it is a *good* coordinated controller. The
  ONLY difference: it consumes neighbour `release` / `ev_claim` / `incident_claim`
  **without the integrity layer** — no signature verification, no registry membership
  check, no conservation plausibility check. It trusts every well-formed message.
- This is fair because: (a) it gets the *same* coordination performance benefit as the
  defended system on honest scenarios (we show this with a no-attack run: the two modes are
  statistically indistinguishable on AETT/throughput when nobody lies — note this benign tie
  depends on coordination being *causal*, i.e. on the B1 fix being in place); (b) it reflects
  the trust assumption of the actual literature (CoLLMLight consumes neighbour state with no
  authentication or plausibility check), not a deliberately broken one; (c) the attack is a
  *single compromised neighbour*, the weakest realistic adversary, not a flood.

So the comparison is: **two equally-good coordinated controllers that differ only in
whether they authenticate + plausibility-check inputs.** Under no attack: tie. Under one
compromised neighbour: the naive one breaks, the defended one does not. That isolates the
contribution to the integrity layer, which is the defensible claim.

### 4.2 The exploit (quantifiable bad outcome)

Single compromised, *registered-then-spoofing* neighbour on the corridor. Three concrete
breakages, each with a measured KPI:

1. **Phantom preemption (§3.1 attacked):** spoofer claims an EV inbound. Naive preempts the
   arterial green repeatedly, **starving the cross streets** → cross-street (non-priority)
   delay spikes; measured as `non_priority_delay` increase and a `false_preemption_rate` > 0.
2. **Phantom incident (§3.2 attacked):** spoofer claims `J1J2` blocked. Naive holds/reroutes
   → arterial throughput drops, `mean_network_delay` rises.
3. **Count-inflation coordination poisoning (§3.3 attacked):** spoofer inflates `release` →
   naive's Channel-B term over-weights a phase with no real demand → `coord_changed`
   decisions go the *wrong* way → measurable delay regression.

Each is a **paired** comparison (naive-under-attack vs naive-no-attack, same seeds) so the
degradation is the within-controller effect of the spoof, isolated from baseline noise.

### 4.3 The defence (detect / reject, measured)

The defended system (`emergency` mode with full integrity):

- **Signing + registry:** the spoofer, if it forges another junction's identity, is rejected
  at `bad_signature` (KPI-4, 100% per de-risk §2). If it is a genuine compromised member
  with a valid key, signing alone does NOT catch it — and we say so honestly.
- **Conservation plausibility:** the genuine-member spoof is caught by the windowed
  conservation detector: `ev_claim`/`incident_claim`/inflated `release` have **no matching
  local observation** → flagged (`inflated` / `missing_observation`), the
  `conservation_anomaly` trigger zeroes the malicious contribution, preemption requires
  local EV confirmation (§3.1). Result: defended KPIs ≈ no-attack KPIs.
- **Honest residual (first principles):** a *coordinated* attacker that inflates a claim AND
  supplies a colluding observation in lockstep keeps the mass-balance residual inside the
  band, so it evades conservation by construction — a named limit, contained by `revoke()` +
  audit, not detection. Stated, not hidden.

### 4.4 Output of the headline experiment

A single table: rows = {no-attack, phantom-preemption, phantom-incident, count-inflation};
columns = naive KPIs vs defended KPIs (AETT/AEWT, non-priority delay, throughput,
false-preemption rate, detection P/R/latency). The story: **identical under honest
operation; naive collapses under a single lie; defended absorbs it.**

### 4.5 Files

- NEW `src/run_exploit_defend.py` wires the `cooperative_naive` mode. The victim itself is a
  `CoordinatedController` subclass `NaiveCooperativeController` (defined alongside
  `coordinated_controller.py`) that **bypasses** the bus's trust pipeline — reads
  `bus._published` directly without verification — and ignores conservation flags. This is the
  ONLY place trust is bypassed, clearly isolated and documented as the victim. (File manifest
  in §8 lists this under `run_coordinated.py`/`run_exploit_defend.py` consistently.)
- NEW `src/attacks_live.py`: extend `attacks.py` with `ev_claim` / `incident_claim`
  injectors that ride the existing `MaliciousPublisher` (compose, do not edit
  `message_bus.py`).
- Extend payload schema (validated at the boundary in `coordinated_controller.decide`'s
  inbox loop) with optional `ev_claim: bool`, `incident_edge: str` — strict validation,
  reject malformed, never trust.

---

## 5. Baselines & Metrics Wiring

### 5.1 Baseline ladder (the controller family)

Wire as new `mode` strings recognised by the runners and `evaluation.TRAFFIC_MODES`:

| Mode | Description | Exists? |
|---|---|---|
| `fixed` | SUMO fixed-time (Webster stand-in) | yes |
| `maxpressure` | classical MaxPressure / shield | yes |
| `maxpressure_preempt` | MaxPressure + deterministic EV preemption rule (no SLM, no coordination) — **the fair non-AI emergency baseline** | NEW |
| `cooperative_naive` | trust-everything coordinated SLM (the victim, §4.1) | NEW |
| `coordinated` | authenticated coordinated SLM, no emergency triggers | yes |
| `emergency` | the full system: authenticated coordination + SLM emergency handler + shield | NEW |

`maxpressure_preempt` is important: it shows how much of the emergency benefit is just the
deterministic preemption rule (the reliable floor) vs the SLM nuance (the ceiling bet),
mirroring the floor/ceiling framing in `PROJECT-PROPOSAL.md` §8.

### 5.2 KPI set and where each is computed

Reuse `metrics.py` (population-safe tripinfo) + `stats.py` (BCa/permutation/Holm) +
`evaluation.py` (matrix). Add emergency-specific KPIs as pure functions of tripinfo +
event logs:

| KPI | Source | New code |
|---|---|---|
| ATT / AWT / throughput / queue / completion / mean_network_delay | `metrics.py` (existing) | none |
| matched-set travel-time | `metrics.matched_diff` (existing) | none |
| **AETT / AEWT** (emergency vehicle travel/wait time) | tripinfo filtered to EV vType id | NEW `metrics.priority_class_times(run, vtype="ev")` — AETT = **horizon-penalised mean** over *departed* EVs (a stranded EV that never clears contributes `T_end − T_dep`, per FORMAL-SPECIFICATION.md §6, so non-completion is penalised not dropped); AEWT = mean `waitingTime` over EVs |
| **non-priority delay** | tripinfo excluding EV ids | NEW `metrics.non_priority_delay(run, priority_ids)` |
| **incident recovery time** | per-step network-delay trace (NEW lightweight per-tick log) vs pre-incident baseline | NEW `metrics.recovery_time(trace, onset_t, tol)` |
| detection precision/recall/latency | `run_attacks` / `evaluation.run_detection` (existing) | none for offline; live variant logs flags per scenario |
| **false-preemption rate** | escalation log: escalated `emergency_vehicle` ticks where NO EV was locally observed / total preemption ticks | NEW `metrics.false_preemption_rate(escalation_events)` |

New metric functions live in **NEW `src/emergency_metrics.py`** (keep `metrics.py` under
the file-size limit and unchanged for the frozen offline harness). They are pure functions
of a `RunRecord` + the controller's `escalation_events` list.

### 5.3 Harness wiring

- CHANGE `evaluation.py`: extend `TRAFFIC_MODES` to include the new modes;
  `run_traffic_cells` already dispatches by `mode` via `run_one`. Add the emergency KPIs to
  a new `emergency_tables` section (parallel to `traffic_tables`) built from per-cell
  escalation logs the runner returns alongside tripinfo.
- CHANGE `run_metrics_sweep.run_one`: accept the new modes and a `scenario` arg; for
  emergency/exploit modes, return the `escalation_events` and per-tick delay trace in the
  row dict (JSON-able) so `evaluation.py` can compute the emergency KPIs.
- The exploit-then-defend table (§4.4) is a NEW `src/run_exploit_defend.py` that calls the
  harness for `{cooperative_naive, emergency} × {no-attack, 3 attacks} × 30 seeds`, paired,
  and emits `results/exploit_defend.{md,json}`.
- Stats: all comparisons paired on seed via `stats.summarize_sweep` (unchanged). The
  emergency KPIs go through the same BCa+permutation+Holm stack.

### 5.4 Files

- NEW `src/emergency_metrics.py`, `src/run_emergency.py`, `src/run_exploit_defend.py`,
  `src/attacks_live.py`, `src/emergency_controller.py`.
- CHANGE `src/evaluation.py` (modes + emergency tables), `src/run_metrics_sweep.py`
  (`run_one` mode dispatch + scenario + escalation log return).
- UNCHANGED (frozen): `metrics.py`, `stats.py`, `conservation.py`, `flow_conservation.py`,
  `flow_accounting.py`, `message_bus.py`, `identity.py`, `registry.py`, `attacks.py`,
  `run_attacks.py`.

---

## 6. Experience-RAG Ceiling (Qdrant)

Strictly optional, controller-mediated, buffered. Keep it OFF by default so the headline
never depends on it.

### 6.1 Design

- **Controller-mediated retrieval:** the controller, not the SLM, owns the Qdrant client.
  On a TRIGGERED tick, before calling the SLM, the controller builds a state key
  `(phase_count, halting_bucket_vector, trigger_kind, incoming_per_phase_bucket)`, queries
  Qdrant for the `k` (default 3) nearest past states, and appends the retrieved
  `good_action -> outcome` summaries to the emergency prompt as additional context. The SLM
  still emits only `{"phase": N}`; retrieval only enriches the prompt (no tool-calling, no
  agentic loop). The shield still validates the result — retrieval can never bypass safety.
- **Corpus generation (state→good-action→outcome):** run the deterministic ladder
  (`maxpressure`, `maxpressure_preempt`) across many seeds/scenarios offline; for each
  decision, record `(state_key, action_taken, realised_short_horizon_delta_delay)`. Label an
  action "good" if its realised delay delta beats the per-state median. Store the good ones
  as Qdrant points: vector = normalised state features, payload = `{action, outcome_delta,
  scenario, trigger_kind}`. This is *experience without training* — in-context retrieval, the
  only learned-like route under the no-training / edge-budget constraint (PROJECT-PROPOSAL.md §3).
- **Embedding:** a fixed, deterministic feature vector (no learned embedder) — the
  normalised `(halting_per_phase, incoming_per_phase, trigger_kind one-hot, occupancy)` —
  so retrieval is reproducible and needs no GPU.

### 6.2 KPI and honesty

Reported as a ceiling ablation: `emergency` vs `emergency+rag` on the same 30 seeds. If RAG
helps (Holm-significant lower delay), report it; if neutral/null, report the null. Either
way the safety + integrity claims are unaffected.

### 6.3 Files

- NEW `src/experience_rag.py`: `ExperienceStore` (Qdrant client wrapper + deterministic
  feature vector + corpus builder + `retrieve(state_key) -> list[str]`). In-memory fallback
  (`qdrant_client.QdrantClient(":memory:")`) so it is CI-able without a server.
- NEW `src/build_experience_corpus.py`: offline corpus generator from ladder runs.
- CHANGE `src/emergency_controller.py`: optional `experience_store` ctor arg; when present,
  enrich the emergency prompt. Default None = no RAG (the ceiling stays optional).

### 6.4 Retrieval-poisoning guard (forward-ref to §7)

The corpus is built **only** from the trusted deterministic ladder offline — never from
live, possibly-attacked runs — so an attacker cannot inject poisoned experiences at
runtime. See edge case E13.

---

## 7. Edge-Case Register (≥15, each with handling)

| # | Edge case | Handling |
|---|---|---|
| E1 | **SLM parse failure / nondeterminism** | `SLMAgent.choose_phase` returns None on any parse/validity failure (existing). In TRIGGERED regime, None → `_rule_fallback` (deterministic preemption for EV, MaxPressure otherwise), then shield. Temperature=0 already; nondeterminism is bounded by the shield. Never crashes (FR-1). |
| E2 | **SLM latency under load / Foundry serialization** | Foundry serialises calls; one endpoint serves ~18–20 decisions / 10 s (de-risk §7). Cap concurrent escalations: a global `max_escalations_per_tick` (default = #SLM junctions, but if Foundry round-trip would exceed the decision interval, the controller processes escalations in priority order and the un-served junctions take the deterministic `_rule_fallback` this tick). Latency never stalls control: the SLM call has a hard timeout (`SLMAgent` already wraps in try/except → None → shield). |
| E3 | **Multi-simultaneous emergencies** | `_evaluate_trigger` returns the top-priority trigger per junction; each junction is independent. EV preemption is enforced per junction deterministically, so two EVs on different corridors both get cleared. Two EVs converging on ONE junction from conflicting approaches: shield picks the higher-severity (closer/halted) EV's phase; the other is served on the next min-green cycle (it cannot serve both greens simultaneously — physical constraint, logged). |
| E4 | **Conflicting neighbour reports** | Two neighbours' claims about the same edge that disagree: conservation reconciles each against *local* observation independently; the implausible one(s) flag. The check proves consistency vs observation, not which neighbour is "right" — but since each claim is checked against the controller's OWN observation, a contradicting claim simply fails its own reconciliation. Logged; coordination contribution from any flagged claim is zeroed (§2.5). |
| E5 | **False alarm on honest congestion / spillback** | The incident trigger requires "high occupancy AND near-zero speed WHILE GREEN, persistent". Honest spillback (edge full but draining when green) does NOT meet "not draining while green". The windowed detector's spillback classifier (`_is_spillback`) already excludes jams from conservation flags. So honest congestion neither flags conservation nor fires an incident. |
| E6 | **Emergency during a spoof** | A real EV is locally observed (vClass) while a spoofer sends a phantom `incident_claim` on the EV's path. Priority order: `emergency_vehicle > incident`, and EV preemption requires *local* confirmation (present), while the phantom incident lacks local confirmation (absent) → ignored + flagged. The EV is cleared; the spoof is logged. The two mechanisms do not interfere. |
| E7 | **Zero-emergency seeds** | Many seeds will have no EV/incident. The system stays in NORMAL regime the whole run = exactly `coordinated` mode. The 30-seed matrix includes zero-emergency seeds; emergency KPIs are reported only over seeds where the event was injected (the EV/incident is injected deterministically per scenario, so "zero-emergency" is the honest-no-attack control, not an accident). |
| E8 | **Gridlock** | On the oversaturated grid, MaxPressure (shield) is the floor; the SLM cannot make it worse (pressure-margin veto). EV preemption may be physically impossible if the EV's exit is jammed — the shield still greens the EV approach (best effort) and logs `preemption_ineffective`. We report incident recovery as "did not recover within horizon" honestly rather than masking it. Corridor substrate (not the gridlocked grid) is the primary emergency venue precisely to avoid confounding. |
| E9 | **Min-green / yellow timing vs preemption** | `step()` owns transitions: a preemption target only takes effect after the current green's `min_green` and a clearing `yellow` (safety invariant V2). So preemption cannot create a sub-min-green or skip-yellow transition. Trade-off: worst-case preemption latency = `min_green + yellow`. We optionally lower `min_green` for the EV-approach phase via a per-trigger `ev_min_green` (still ≥ a safe floor, e.g. 5 s) to tighten preemption response, configurable and bounded. |
| E10 | **Replay** | Bus replay guard keys on `(recipient, sender, t)` (existing). A replayed spoof message is dropped (`replay`) before it reaches conservation. Live scenarios increment the decision tick per publish, so a replayed `ev_claim` from a prior tick never re-triggers preemption. |
| E11 | **Revoked agent mid-emergency** | If the city authority `revoke()`s a neighbour during a run, its subsequent messages reject at `revoked` (existing). Mid-emergency: the revoked neighbour's `ev_claim` is dropped, so it cannot trigger preemption — but a *locally observed* real EV still triggers (independent of messages). Registry read is from the locally-cached allowlist (NFR-2), so revoke takes effect without a ledger round-trip on the control loop. |
| E12 | **Retrieval poisoning (if RAG on)** | Corpus built ONLY offline from the trusted deterministic ladder (§6.4); never from live/attacked runs. So no runtime injection path. Retrieved experiences are advisory prompt context; the shield still validates the SLM's resulting phase, so even a poisoned retrieval cannot produce an unsafe action. |
| E13 | **Spoofed payload field bomb / malformed `ev_claim`** | Inbox loop validates every field at the boundary (existing pattern: reject non-int `release`, clamp hostile `queue_forecast`). New fields `ev_claim`/`incident_edge` are strictly type-checked; malformed → message ignored (not crashed). Max payload depth/size enforced by canonical-JSON signing (oversized payload changes the signed bytes → still must verify, but we also cap field count). |
| E14 | **EV detector flap / EV momentarily off-edge** | Preemption latches per EV id until the EV clears the junction (§2.1 debounce), so a one-tick detector dropout does not drop preemption mid-clearance. |
| E15 | **Two triggers, one neighbour both honest-flag and attack** | A neighbour can be both genuinely faulty (under-reporting) AND the target of our suspicion. Conservation reports the *reason* (`under_reported` vs `inflated`) distinctly; the trigger uses only the flag, not an attribution of intent. The audit log records reason + counts for post-hoc human review (the system never claims to know intent — PROJECT-PROPOSAL.md §11 honesty boundary). |
| E16 | **Coordination causally inert regression (B1) creeps back** | Regression guard: a CI assertion that in TRIGGERED regime with a StubAgent whose proposal differs from MaxPressure, `escalation_changed_decisions > 0` (the executed phase actually changed). If this hits zero with differing proposals, the inert-coordination bug has returned. Mirrors the `coord_adjusted_decisions` proof. |
| E17 | **Edge-id parse silent no-op (B2) on the corridor** | The corridor uses `{from}{to}` ids that DO parse, but emergency scenarios MUST pass the explicit `edge_map` from `edge_map_from_net` anyway (so the same code path works if we move to a real OSM emergency net). A startup assertion: if `edge_map` is None on a non-grid net, refuse to run (fail loud, not silent no-op). |
| E18 | **Shield veto thrash (SLM and shield disagree every tick)** | If the SLM proposes a starving phase and the shield vetoes repeatedly, the executed behaviour is just MaxPressure (safe) — but we log `shield_veto_rate`; a high rate means the SLM is unhelpful for that trigger and we report that honestly (it does not harm safety). |

---

## 8. File-change summary (the build manifest)

**NEW files:**
- `src/emergency_controller.py` — `Trigger`, `EmergencyController` (regimes + shield).
- `src/emergency_metrics.py` — AETT/AEWT, non-priority delay, recovery time, false-preemption rate.
- `src/run_emergency.py` — emergency-mode runner (mirrors `run_coordinated.py`, passes `edge_map`).
- `src/run_exploit_defend.py` — the headline experiment driver + report.
- `src/attacks_live.py` — `ev_claim`/`incident_claim` injectors (compose on `MaliciousPublisher`).
- `src/experience_rag.py`, `src/build_experience_corpus.py` — optional Qdrant ceiling.
- `sumo/corridor/scenarios/{ev,incident,outage}{,_attacked}.{rou.xml,add.xml,sumocfg}` + `manifest.json`.
- `tests/test_emergency_controller.py`, `tests/test_emergency_metrics.py`,
  `tests/test_exploit_defend.py`, `tests/test_attacks_live.py`, `tests/test_experience_rag.py`.

**CHANGED files:**
- `src/coordinated_controller.py` — extract `_phase_serving` helper if needed; extend inbox
  field validation for optional `ev_claim`/`incident_edge`. No change to existing `decide` semantics.
- `src/evaluation.py` — add new modes to `TRAFFIC_MODES`; add `emergency_tables` section.
- `src/run_metrics_sweep.py` — `run_one` dispatches new modes + `scenario` arg; returns escalation log.
- `src/run_coordinated.py` — add `NaiveCooperativeController` victim mode (clearly isolated trust-bypass).
- `sumo/corridor/gen_routes.py` — `--scenario` flag appending EV/blocker trips.

**FROZEN (must not change — protects 166+ tests + offline harness contract):**
`metrics.py`, `stats.py`, `conservation.py`, `flow_conservation.py`, `flow_accounting.py`,
`message_bus.py`, `identity.py`, `registry.py`, `attacks.py`, `run_attacks.py`,
`net_topology.py`, `controllers.py` (MaxPressure shield untouched).

---

## 9. Build order (TDD, per git-workflow)

1. `emergency_controller.py` + tests: regimes, shield validation, B1 regression guard (E16),
   EV preemption enforcement, against an in-memory TraCI stub (reuse `run_attacks` fake-conn pattern).
2. SUMO scenarios + `gen_routes --scenario` + `run_emergency.py`: confirm triggers fire on the corridor.
3. `attacks_live.py` + `NaiveCooperativeController` + `run_exploit_defend.py`: the headline,
   no-attack tie first (fairness), then the three breakages + defence.
4. `emergency_metrics.py` + `evaluation.py` wiring: emergency KPIs through BCa/permutation/Holm.
5. 30-seed powered run on the corridor (+ zero-emergency control seeds).
6. (Buffered) `experience_rag.py` ceiling ablation.

Each step: RED → GREEN → edge-case tests (the E-register) → verify coverage ≥ 80%.
