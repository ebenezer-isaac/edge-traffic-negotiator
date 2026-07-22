> **SUPERSEDED HISTORICAL DE-RISK RECORD (pre-2026-05-31 pivot).** Dated lab-notebook measurements kept for the audit trail; the substrate here (Lambeth A23/A3) was DROPPED and the ledger/Besu framing DEMOTED. Current thesis: specs/001-edge-negotiator/MASTER-SPEC.md (Euston A501; self-referential coupling; CT-style accountability credited to prior art; Phi-4-mini). Numbers/terms below are historical, not current claims.

# Authenticated Coordination on the REAL Lambeth Corridor — Generalisation Evidence

**Goal (dissertation, "The Edge Negotiator"):** prove the authenticated
cross-junction *integrity layer* (Ed25519 identity + permissioned registry +
signed message bus + vehicle-conservation reconciliation) — built and validated
on the 2×2 toy grid (Milestone-2) — **generalises to the real Lambeth A23/A3
spine corridor** (`sumo/lambeth/lambeth_spine.net.xml`, 9 TLS). The headline
claim under test: *"it works on the real net."*

**Verified on this machine:** SUMO 1.26.0, venv `.venv`, TraCI. Every number
below was produced by an executed run via
`sumo/lambeth/run_corridor_coord.py`, not asserted.

The `src/` integrity modules were **NOT edited** (`coordinated_controller.py`,
`identity.py`, `registry.py`, `message_bus.py`, `conservation.py`). The runner
imports them verbatim. It uses the deterministic **`StubAgent`** (no Foundry
Local) so the result is reproducible and CI-able. Tripinfo is written under a
unique dir (`results/tripinfo_corridor/`) to avoid collision with other sims.

---

## TL;DR (the three asked-for answers)

1. **Does it run end-to-end on the real corridor?** **YES.** The full stack runs
   the unmodified `CoordinatedController` logic over the 9 real TLS at the clean
   operating point (`scale 1.0`), with **zero exceptions**, real signed traffic,
   real conservation detections, and a valid registry hash-chain.

2. **Message / detection counts** (chain adjacency, `scale 1.0`, `seed 7`,
   `end 1200`, 6 SLM junctions; numbers grow ∝ run length):

   | metric | value |
   |---|---:|
   | SLM decisions | 266 |
   | signed messages published (non-empty `toward`) | 82 |
   | **verified** neighbour messages delivered | **243** |
   | **rejected** messages (total) | **35 268** |
   | &nbsp;&nbsp;• `not_neighbour` | 28 601 |
   | &nbsp;&nbsp;• `replay` | 6 667 |
   | conservation **detections** (per-edge verdicts) | 167 |
   | &nbsp;&nbsp;• `ok` / `under_reported` / `inflated` | 120 / 38 / 9 |
   | **flagged** detections | 47 |
   | `coord_adjusted_decisions` (Channel-B causal proof) | 3 |
   | decisions that saw any verified incoming | 18 |
   | registry hash-chain valid | **True** |

3. **Biggest transfer gap (the most valuable finding): the grid edge-naming
   convention is FALSE on the real net, so the unmodified controller silently
   no-ops its coordination unless given an explicit edge map.** Details in §2.

---

## 1. Real corridor topology, derived from the net with sumolib

`run_corridor_coord.py` reads `lambeth_spine.net.xml` with `sumolib` and derives
two things the integrity layer needs: the **TLS-to-TLS adjacency** and the
**explicit directed in-edge map** `(src_tls, dst_tls) -> edge_id`.

### 1a. Strict brief definition ("a single edge connects two TLS") is near-empty

Defining neighbours as *"a single edge directly connects a node of one TLS to a
node of the other"* yields **exactly ONE neighbour pair** on this net:

```
GS_227716  <->  cluster_10273328593_..._#4more
  in-edges:  GS_227716 -> #4more  = 325568663#0
             #4more     -> GS_227716 = -634042794#2
```

All other 7 TLS have **no** direct single-edge connection to any TLS, because the
real corridor interleaves non-signalised OSM nodes (and OSM-split edge segments
`…#1`, `…#2`) between consecutive signals. This is `--adjacency single`.

### 1b. Corridor-logical adjacency ("chain through non-TLS interior nodes")

Defining neighbours as *"a directed path of only non-signalised interior nodes
connects two TLS with no intervening signal"* recovers the real arterial graph
(`--adjacency chain`, the default). 7 of 9 TLS gain at least one neighbour; the
in-edge is the last hop entering the downstream signal:

| from TLS | to TLS | in-edge entering dst |
|---|---|---|
| GS_7173810958 | cluster_102714594_…#7more | -222587544#1 |
| cluster_102714594_…#7more | cluster_1032792732_…#11more | -677008394#1 |
| cluster_1032792732_…#11more | cluster_102714594_…#7more | 243976865 |
| cluster_2592978101_…#2more | GS_227722 | 253362217#0 |
| GS_227722 | cluster_2592978101_…#2more | -253362216#1 |
| GS_227722 | cluster_10273328593_…#4more | 321450388 |
| cluster_10273328593_…#4more | GS_227716 | -634042794#2 |
| cluster_10273328593_…#4more | GS_227722 | -613141473#1 |
| GS_227716 | cluster_10273328593_…#4more | 325568663#0 |
| GS_8413292286 | GS_8412978817 | -905990664 |

Two TLS (`GS_8412978817`, and one branch) remain leaf/边 nodes; that is real
topology, reported honestly, not a bug.

---

## 2. THE TRANSFER GAP — grid edge-naming does not survive on the real net

This is the central finding and the thing to fix before any "real-net SLM" work.

The grid `CoordinatedController` recovers the directed edge between two junctions
**by STRING CONVENTION**: an edge id is the concatenation of two junction ids
(`"A0A1" -> ("A0","A1")`). Three methods depend on it:

* `_toward_counts` → `_split_edge(out_edge)` to find the downstream neighbour,
* `_incoming_per_phase` → `in_edge = f"{nb}{tl}"`,
* `_observed_inflows` → `edge = f"{nb}{recipient}"`.

**On the real net this convention is FALSE.** Verified directly:

* TLS ids are OSM cluster strings, e.g.
  `cluster_1032792732_1032792753_1032792770_1032792773_#11more`.
* Inter-junction edge ids are OSM way ids, e.g. `-634042794#2`, `325568663#0`,
  `243976865` — **0 of them** equal `f"{fromTLS}{toTLS}"`.
* `_split_edge("325568663#0", tls_ids)` returns **`None`** for *every* real
  inter-junction edge.
* `f"{nb}{tl}"` never names a real edge → `_incoming_per_phase` and
  `_observed_inflows` look up edges that do not exist.

**Consequence if the grid controller were run UNMODIFIED on the real net:** it
would still "run" (no crash) but its coordination would be a **silent no-op** —
`_toward_counts` returns `{}` for every phase, so it would publish empty `toward`
payloads, deliver **0 verified messages**, raise **0 claims**, produce **0
conservation detections**. The integrity layer would look alive while doing
nothing. *This is exactly the silent-failure mode the brief warned about, and it
is real.*

**What DOES transfer:** `_edge_of_lane` (lane→edge via rsplit, e.g.
`"325568663#0_0" → "325568663#0"`) is naming-agnostic and works unchanged. The
crypto/registry/bus trust checks and the conservation maths are fully
topology-independent and transfer verbatim.

**Fix applied (authorised by the brief):** supply the adjacency/edge map
**explicitly** instead of relying on name parsing. `run_corridor_coord.py`
defines `CorridorCoordinatedController`, a thin subclass that overrides **only**
those three name-parsing methods to consult the sumolib-derived
`in_edge_map` / `out_edge_to_neighbour` maps. Everything else is inherited
unchanged. With this, `published_nonempty = 82` and `verified = 243` (chain) —
proof the pathway is now live on the real net. This subclass is the concrete
integration change Wk9-10 must fold back into `src/` (e.g. inject an edge map
into `CoordinatedController` rather than parse ids).

---

## 3. End-to-end run evidence (Milestone-2-style, on the REAL net)

`StubAgent`, `coord_weight = 1.0`, `scale 1.0`, `seed 7`, `end 1200`, 6 SLM
junctions. Same demand seed for both adjacency modes, so traffic metrics are
identical — coordination did **not** move travel time here (expected; see §4).

| metric | chain adjacency | single adjacency |
|---|---:|---:|
| ran end-to-end (exit 0) | ✅ | ✅ |
| sim_steps | 1200 | 1200 |
| teleports | 1 | 1 |
| trips completed | 1089 | 1089 |
| avg travel time (s) | 114.76 | 114.76 |
| avg waiting time (s) | 16.56 | 16.56 |
| SLM decisions | 266 | 266 |
| published (non-empty `toward`) | 82 | 82 |
| **verified messages** | **243** | **101** |
| rejected (total) | 35 268 | 35 410 |
| &nbsp;• not_neighbour | 28 601 | 33 707 |
| &nbsp;• replay | 6 667 | 1 703 |
| conservation detections | 167 | 44 |
| &nbsp;• ok / under_reported / inflated | 120 / 38 / 9 | 26 / 9 / 9 |
| flagged detections | 47 | 18 |
| coord_adjusted_decisions | 3 | 3 |
| decisions_with_incoming | 18 | 18 |
| registry chain valid | True | True |

Reading the evidence:

* **Signed messaging works on the real net.** Junctions sign per-phase `toward`
  payloads with their Ed25519 keys; neighbours verify against the registered
  public key over canonical bytes. 243 (chain) / 101 (single) messages passed
  *all four* trust checks (neighbour ∧ approved ∧ signature ∧ non-replay).

* **The bus is doing its job.** Rejections are dominated by `not_neighbour`,
  which is correct: every published message is offered to every recipient's
  inbox, and the topology check drops non-adjacent senders. The chain graph
  (more neighbours) → more `verified` and fewer `not_neighbour` than single, as
  expected. `replay` rejections show the per-`(recipient,sender,t)` replay guard
  firing as the controller re-reads the growing buffer each decision.

* **Conservation reconciliation works on the real net.** 167 (chain) per-edge
  verdicts, of which 47 flagged: 38 `under_reported` (observed inflow exceeded
  the upstream's claimed release — platoons already arrived) and 9 `inflated`
  (claim > observation beyond tolerance). These are **uncoordinated
  spoof/fault-class** flags exactly as on the grid; the same evadable-by-
  coordinated-attacker caveat (`Xiao2026`) applies.

* **Coordination is causal, not cosmetic.** `coord_adjusted_decisions = 3`: on 3
  decisions the Channel-B incoming-release term changed the deterministic phase
  choice vs plain MaxPressure. It is small because real cross-pressure is small
  here (single arterial axis), matching the controllability report's "modest
  headroom" finding — not because the pathway is dead (it published 82 signed
  messages and delivered 243).

* **Registry hash-chain stays valid** end-to-end (`verify_chain() == True`).

### Full 3600 s run
A full `scale 1.0`, `end 3600` chain run was also launched. It runs correctly but
is **slow** — see the performance finding in §4. The integrity behaviour is fully
characterised by the 1200 s runs above; the 3600 s counts scale roughly linearly.

---

## 4. Honest caveats / secondary findings

1. **Performance gap (real, worth flagging): `MessageBus.inbox()` is O(n²).**
   `inbox()` scans the **entire** `_published` list on every call, and every SLM
   junction calls it every decision. Over a 3600 s run the buffer grows to tens
   of thousands of messages, so the back half of the run slows to a crawl (the
   28 601 `not_neighbour` rejections in 1200 s are the same scan re-rejecting old
   messages). On the 4-junction grid this is invisible; on a 9-TLS corridor over
   an hour it dominates wall-clock. **Wk9-10 should add per-tick / per-recipient
   indexing or buffer pruning** before scaling to more junctions or longer runs.
   (Not a correctness bug — counts are right — purely scaling.)

2. **Coordination does not change travel time on this corridor.** Identical
   traffic metrics across modes. This is the *expected* honest result: the
   controllability report already showed MaxPressure ≈ fixed-time here (single
   arterial axis, limited cross-pressure, 2 of 6 controllable junctions are
   simple 2-phase). The corridor result is a **realism / integrity-generalisation**
   story, not a throughput-win story.

3. **Adjacency definition is a modelling choice, documented both ways.** The
   strict brief definition ("single edge") is near-empty on real OSM topology
   (§1a); the corridor-logical "chain" definition (§1b) is what gives a
   meaningful neighbour graph. Both are runnable (`--adjacency single|chain`).
   Wk9-10 should pick and justify one (recommend `chain`, it reflects how
   platoons actually propagate between signals).

4. **`queue_forecast == release` placeholder** carries over unchanged from the
   grid (no roll-forward model yet); conservation consumes only `release`, never
   the forecast, exactly as on the grid.

---

## 5. Reproduce

```
.venv/Scripts/python sumo/lambeth/run_corridor_coord.py                       # chain, scale 1.0, full
.venv/Scripts/python sumo/lambeth/run_corridor_coord.py --adjacency single    # strict 1-pair graph
.venv/Scripts/python sumo/lambeth/run_corridor_coord.py --seed 7 --end 1200   # fast integrity check
```

**Bottom line.** The authenticated-coordination integrity layer **generalises to
the real Lambeth corridor**: it signs, verifies, reconciles, and keeps a valid
audit chain on the real 9-TLS net with real demand — *once it is handed an
explicit edge map*. The single biggest grid→corridor transfer gap is that the
grid's `src+dst` edge-id parsing is FALSE on real OSM edge ids and would make the
coordination silently no-op; fixing it needs an explicit `(src,dst)->edge` map
(supplied here by subclass, to be folded into `src/` for Wk9-10). The secondary
gap is the O(n²) message bus, which must be indexed before scaling up.
