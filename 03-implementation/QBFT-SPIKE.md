# QBFT De-Risk Spike (Wk 5-6 production-consensus pull-forward)

**Goal:** the prior spike (`BESU-SPIKE.md`) measured the on-chain `AgentRegistry`
on a **single-node Besu `--network=dev`** chain (PoW dev miner, ~1.44 s register).
That proved the contract + web3 glue + latency *envelope*, but gave **no
Byzantine-fault-tolerance guarantee** and no validator-round-trip latency. The
real Wk 5-6 production target is a **permissioned QBFT network** (multiple
validators, real BFT consensus). This spike de-risks that: stand up a real QBFT
network, deploy the *same* contract unchanged, and measure real consensus
latency against the single-node dev numbers.

**Status: DE-RISKED — full 4-validator QBFT stood up and measured.** A 4-node
Besu QBFT network (the BFT minimum that tolerates 1 faulty validator) was run in
Docker with the real QBFT consensus engine (NOT the dev PoW miner), 2 s block
period, free gas. `AgentRegistry.sol` was deployed (paris EVM) and driven
end-to-end (register / revoke / isApproved / getPublicKey + a batch) over
`src/besu_registry.py` **unchanged**. Latencies measured by `src/bench_qbft.py`
→ `edge-negotiator/results/qbft_bench.md`.

---

## 1. Artifacts produced by this spike

| File | Purpose |
|---|---|
| `edge-negotiator/.qbft-spike/qbftConfigFile.json` | QBFT genesis-generator input (4 nodes, 2 s period, free gas, London fork) |
| `edge-negotiator/.qbft-spike/networkFiles/` | Generated `genesis.json` + 4 validator key pairs (`besu operator generate-blockchain-config` output) |
| `edge-negotiator/.qbft-spike/docker-compose.yml` | 4-node QBFT network on a Docker bridge net, static-nodes peering, node1 RPC on 8545 |
| `edge-negotiator/.qbft-spike/static-nodes.json` | enode list pinning each validator to its container IP |
| `edge-negotiator/src/bench_qbft.py` | QBFT latency benchmark (reuses `besu_registry.py`); writes the report |
| `edge-negotiator/results/qbft_bench.md` | Measured QBFT numbers (median + p95, 20 trials/op) vs single-node dev |

`contracts/AgentRegistry.sol` and `src/besu_registry.py` are **reused as-is** —
no changes. The contract still compiles with `evm_version="paris"` because the
genesis here sets the **London** fork, which is still pre-PUSH0; a production
genesis would set a recent fork (Shanghai/Cancun) and drop the pin.

---

## 2. How to reproduce (verbatim)

All commands run from `edge-negotiator/`. Image pinned to
`hyperledger/besu:24.12.0` (parity with the single-node spike; QBFT uses the
consensus engine, not `--miner-enabled`, so the `:latest` miner-flag regression
from `BESU-SPIKE.md` does not strictly apply — but keep the pin).

### 2.1 Generate the QBFT genesis + validator keys

`.qbft-spike/qbftConfigFile.json` declares 4 nodes, a 2 s block period, free gas
(`zeroBaseFee`), the London fork (pre-PUSH0), and prefunds the well-known Besu
dev account. Run Besu's operator tool in a throwaway container (mount the spike
dir):

```bash
docker run --rm -v "${PWD}/.qbft-spike:/data" hyperledger/besu:24.12.0 \
  operator generate-blockchain-config \
  --config-file=/data/qbftConfigFile.json \
  --to=/data/networkFiles \
  --private-key-file-name=key
```

This writes `.qbft-spike/networkFiles/genesis.json` (with all 4 validators
baked into `extraData`) and `.qbft-spike/networkFiles/keys/0x<addr>/{key,key.pub}`
for each validator. **Run from PowerShell** (`${PWD}` works there); avoid
Git-Bash, which rewrites `/data` mount paths (see `BESU-SPIKE.md`).

### 2.2 Wire up static peering

Read each validator's `key.pub` (the enode node-id) and write
`.qbft-spike/static-nodes.json` mapping node-id → container IP
(`172.28.0.11..14`). The committed `static-nodes.json` already contains the
enodes for the generated keys; if you regenerate keys, refresh it.

### 2.3 Start the 4-validator QBFT network

```bash
docker compose -f .qbft-spike/docker-compose.yml up -d
```

Each node runs with `--genesis-file`, its own `--node-private-key-file`,
`--static-nodes-file`, `--min-gas-price=0`, and a fixed `--p2p-host` IP. Only
node1 publishes RPC on host `8545`.

Readiness (block number should climb ~1 every 2 s; peers should reach 3;
validators should be 4):

```bash
curl -s -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  -H "Content-Type: application/json" http://127.0.0.1:8545
curl -s -X POST --data '{"jsonrpc":"2.0","method":"net_peerCount","params":[],"id":1}' \
  -H "Content-Type: application/json" http://127.0.0.1:8545
curl -s -X POST --data '{"jsonrpc":"2.0","method":"qbft_getValidatorsByBlockNumber","params":["latest"],"id":1}' \
  -H "Content-Type: application/json" http://127.0.0.1:8545
```

Observed node1 log lines confirm **real QBFT consensus**, not a dev miner:
`QbftRound | Importing proposed block ... round=ConsensusRoundIdentifier{...}`
and round-robin `Produced/Imported empty block #N` every ~2 s.

### 2.4 Deploy + benchmark

```bash
.venv/Scripts/python src/bench_qbft.py --trials 20 --batch 10
# writes results/qbft_bench.md
```

This deploys `AgentRegistry.sol` (paris) via `BesuRegistry.deploy(...)` and times
register / revoke / isApproved / getPublicKey + a batch of 10.

> **PoA / web3.py gotcha (new vs the dev spike):** QBFT is a PoA-style engine;
> its block header `extraData` is >32 bytes, so web3.py's default block
> formatter raises `ExtraDataLengthError` on **any** `eth_getBlock*`. Writes and
> `eth_call` reads are unaffected (they never fetch a block), so
> `besu_registry.py` works unchanged. Only block-timestamp reads need the PoA
> middleware — `bench_qbft.py` injects `ExtraDataToPOAMiddleware` into a
> *throwaway* Web3 for its block-period measurement, leaving the shared
> `besu_registry.py` provider untouched.

### 2.5 Tear down

```bash
docker compose -f .qbft-spike/docker-compose.yml down -v
# or: docker rm -f qbft-node1 qbft-node2 qbft-node3 qbft-node4
```

---

## 3. Headline measured result

Besu 24.12.0, **4-validator QBFT**, measured block period **2.0 s**, free gas,
20 trials/op. Full table in `edge-negotiator/results/qbft_bench.md`.

| op | dev median | dev p95 | **QBFT median** | **QBFT p95** | QBFT/dev (median) |
|---|---|---|---|---|---|
| register (write/commit) | 1444 ms | 3863 ms | **2142 ms** | 2545 ms | 1.48x |
| revoke (write/commit) | 1842 ms | 5389 ms | **2169 ms** | 2299 ms | 1.18x |
| isApproved (read) | 46 ms | 67 ms | **16 ms** | 18 ms | 0.34x |
| getPublicKey (read) | 32 ms | 48 ms | **15 ms** | 16 ms | 0.47x |
| batch of 10 registers | 20560 ms | 27784 ms | **22080 ms** | 22138 ms | 1.07x |

*dev = single-node Besu `--network=dev` PoW, 1.0 s block period (from
`results/ledger_bench.md`). QBFT = this spike.*

**Key observations:**

- **Writes are block-period-dominated, NOT validator-count-dominated.** QBFT
  register/revoke medians (~2.14-2.17 s) ≈ **one 2 s block period +
  submission/receipt overhead**. The single-node dev chain had a 1 s period and
  ~1.4-1.8 s medians; QBFT has a 2 s period and ~2.15 s medians. The latency
  scaled with the *block period*, not with going from 1 to 4 validators — the
  QBFT 3-phase round-trip among 4 LAN containers is well under one block period.
- **QBFT's distribution is TIGHTER and more predictable.** Dev-PoW p95 spiked to
  3.9-5.4 s (intermittent world-state pauses); QBFT p95 is ~2.3-2.55 s — barely
  above its median. QBFT gives **deterministic, immediate finality** at block
  commit (no probabilistic re-org tail), so the worst case is bounded by the
  block period, not by miner jitter.
- **Reads are cheap and, here, faster than dev** (~15-16 ms vs 32-46 ms): they
  are local `eth_call`s against node1's warm state and never enter a consensus
  round, so consensus topology does not affect read cost.

---

## 4. Does the brief's async-registry assumption still hold under real BFT?

**YES — and more cleanly than on the single-node dev chain.**

- The brief's design (`PROJECT-DECISION-BRIEF.md` §2/§3) is: the ledger is an
  **async registry + audit log only, ~1-2 s finality, NEVER in the real-time
  control loop**. Under real 4-validator QBFT, write commit medians
  (register 2.14 s, revoke 2.17 s) land in the 1-2-s-class envelope, driven by
  the deterministic 2 s block period. With a 1 s block period they would drop to
  ~1.x s, squarely in band.
- **BFT makes the async design SAFER, not riskier.** Deterministic finality
  removes the PoW re-org tail, so the latency a writer experiences is tight and
  bounded by the block period. There is no scenario where a "committed" audit
  write silently reverts.
- The fast-path verdict is unchanged and reinforced: a **~2.14 s
  BFT-committed write** vs a **~15 µs in-memory membership check** is ~5 orders
  of magnitude — **catastrophic on the control path, completely fine off-loop.**
  The ledger must stay the asynchronously-synced source of truth; per-message
  verification hits a local membership cache refreshed from
  `AgentRegistered`/`AgentRevoked` events, never a consensus round.
- **Batching is still mandatory.** `batch_register_10` ≈ 22 s (10 sequential
  commits). One transaction per control decision would couple control throughput
  to consensus latency. Audit events must be buffered on the fast path and
  flushed off-loop (periodic batched tx, or anchor a Merkle root per batch).

---

## 5. Production topology recommendation

- **Validator count: 4 minimum (f=1), size as 3f+1.** 4 validators tolerate 1
  faulty/offline node — the BFT minimum, validated here. For a city authority
  wanting to survive 2 simultaneous failures, use 7 (f=2). A permissioned
  traffic authority rarely needs more than ~7-10; QBFT message complexity grows
  with validator count, and there is no decentralisation incentive to over-size.
- **Block period: 2 s default.** Confirmed to keep write finality in the
  1-2-s-class band while being gentle on validators. The block period is the
  single biggest write/finality tuning knob (halve it ⇒ roughly halve commit
  latency). The fast control loop is unaffected at any period because it never
  blocks on a write.
- **Gas-free permissioning.** Keep `zeroBaseFee` + `--min-gas-price=0` (no fee
  market on a closed authority chain). Add **node + account permissioning**
  (on-chain permissioning contracts, or `static-nodes` + permissioning config)
  so only authorised junction hosts can peer, and only the city-authority admin
  key can mutate the allowlist — already enforced by `AgentRegistry.onlyOwner`.
- **EVM fork.** Production genesis should set a recent fork (Shanghai/Cancun),
  letting the `evm_version=paris` PUSH0 work-around be dropped.
- **Admin key custody.** Move the `onlyOwner` city-authority key behind an HSM or
  multisig (brief's optional hardening). Never ship the well-known dev key used
  here.

---

## 6. Honest limitations

- **All 4 validators on one host** (Docker bridge net) ⇒ inter-validator latency
  is loopback-class, not WAN. A geographically distributed validator set adds
  real RTT per QBFT round. But since commit latency is **block-period-dominated**,
  modest WAN RTT (tens of ms) stays well under a 2 s period and would not change
  the headline finding. (A multi-host follow-up would quantify the WAN term.)
- **Localhost RPC** from the benchmark to node1: no agent-host → node network
  latency included; a distributed agent deployment adds it.
- **Free gas** excludes fee-market queueing (none on this closed chain by design).
- **Dev column is transcribed**, not co-measured in this run (the dev chain is
  torn down); it is the previously-measured single-node result from
  `results/ledger_bench.md`, shown for side-by-side context.

---

## 7. Biggest remaining risk for Wk 5-6

**Distributed-validator WAN latency + audit-write batching discipline.** The
consensus mechanics are now de-risked (real QBFT, 4 validators, deterministic
~2 s finality, contract + web3 glue unchanged). Two things remain to validate in
the real deployment: (1) the WAN RTT between geographically separated validators
(this spike was single-host), which adds to but is dominated by the block
period; and (2) the discipline that audit events are **always** batched/anchored
off-loop and per-message checks **always** hit the local cache — the same
mitigation the dev spike flagged, now confirmed necessary under BFT because a
single committed write costs a full ~2 s block.
