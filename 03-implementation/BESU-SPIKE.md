# Besu De-Risk Spike (Wk 5-6 pull-forward)

**Goal:** prove, with hard data, that the on-chain permissioned registry +
audit log from `PROJECT-DECISION-BRIEF.md` is buildable and that its latency
profile is compatible with the brief's "ledger is **async** registry + audit
only, **never** in the control loop, ~1-2 s finality" assumption — so that the
actual Wk 5-6 work is *integrate-and-merge*, not *discover-and-debug*.

**Status: DE-RISKED.** A Solidity 0.8.24 `AgentRegistry` was compiled with
py-solc-x, deployed to a single-node Besu dev chain in Docker, and driven
end-to-end (register / revoke / isApproved / getPublicKey) over web3.py with
**real 44-byte Ed25519 DER public keys** from `src/identity.py`. A
`BesuRegistry` Python class is a verified **drop-in** for the local
`src/registry.py` — `MessageBus(BesuRegistry(...), adjacency)` constructs and
delivers/rejects signed messages unchanged. Latencies were measured
(`src/bench_ledger.py` → `results/ledger_bench.md`).

---

## 1. Artifacts produced by this spike

| File | Purpose |
|---|---|
| `edge-negotiator/contracts/AgentRegistry.sol` | Solidity 0.8.24 permissioned allowlist + audit events |
| `edge-negotiator/src/besu_registry.py` | `BesuRegistry` — drop-in for `src/registry.py`, web3.py-backed |
| `edge-negotiator/src/bench_ledger.py` | Latency benchmark (Besu vs in-memory baseline) |
| `edge-negotiator/results/ledger_bench.md` | Measured numbers (median + p95, >=20 trials) |
| `edge-negotiator/.besu-spike/` | Scratch dir (Besu config experiments) — git-ignorable |

The on-chain contract surface deliberately mirrors `src/registry.py`:

| Local `Registry` (src/registry.py) | On-chain `AgentRegistry.sol` | `BesuRegistry` Python |
|---|---|---|
| `register(jid, public_key: bytes)` | `register(string,bytes)` (onlyOwner) | `register(jid, public_key)` |
| `revoke(jid)` | `revoke(string)` (onlyOwner) | `revoke(jid)` |
| `is_approved(jid) -> bool` | `isApproved(string) -> bool` | `is_approved(jid) -> bool` |
| `public_key(jid) -> bytes\|None` | `getPublicKey(string) -> bytes` | `public_key(jid) -> bytes\|None` |
| `audit_log` (hash-chained) | `AgentRegistered` / `AgentRevoked` events | `audit_log` (rebuilt from events) |

`MessageBus` only ever calls `public_key`, `is_approved`, and iterates
`audit_log` reading `action` / `junction_id`. `BesuRegistry` reproduces all
three, so it is a true drop-in.

---

## 2. How to reproduce (verbatim)

### 2.0 Python prerequisites

The venv already has `web3==7.16.0` and `eth-account`. The spike additionally
uses **`py-solc-x==2.0.5`** with **solc `0.8.24`** installed (these are present
in `.venv` but are **not yet pinned in `requirements.txt`** — add them before
the Wk 5-6 merge):

```bash
.venv/Scripts/python -m pip install py-solc-x
.venv/Scripts/python -c "import solcx; solcx.install_solc('0.8.24')"
```

### 2.1 Start a single-node Besu (dev mode, free gas, instant-ish blocks)

> **Besu version pin:** use **`hyperledger/besu:24.12.0`**. The current
> `:latest` (26.6.0-RC1) **removed the `--miner-enabled` / `--miner-coinbase`
> CLI flags** (and rejects them as config keys too), so its dev network does
> not mine and every transaction times out. 24.12.0 still has the dev PoW
> miner. This is documented as a known blocker, not worked around silently.

```bash
docker pull hyperledger/besu:24.12.0

docker run -d --name besu-spike -p 8545:8545 hyperledger/besu:24.12.0 \
  --network=dev \
  --miner-enabled \
  --miner-coinbase=0xfe3b557e8fb62b89f4916b721be55ceb828dbd73 \
  --min-gas-price=0 \
  --rpc-http-enabled=true \
  --rpc-http-host=0.0.0.0 \
  --rpc-http-port=8545 \
  --rpc-http-cors-origins="*" \
  --host-allowlist="*" \
  --rpc-http-api=ETH,NET,WEB3,ADMIN
```

> **Windows / Git-Bash gotcha:** do **not** mount a volume with a `/...` path
> from Git-Bash — MSYS rewrites `/cfg` into `C:/Program Files/Git/cfg`. Run the
> `docker run` from **PowerShell**, or pass all config as CLI flags (as above).

> **Argument-order gotcha:** keep `--miner-enabled` / `--miner-coinbase` ahead
> of a comma-list option like `--rpc-http-api=ETH,NET,...`. picocli's list
> parser will otherwise greedily swallow the following flags as API entries and
> Besu dies with `invalid entries found [--miner-enabled, ...]`.

- **RPC URL:** `http://127.0.0.1:8545`
- **chainId:** `1337` (`0x539`)
- **gasPrice:** `0`
- **Prefunded dev account** (well-known Besu dev key, safe to hardcode for a
  throwaway dev chain — *never* a real key):
  - address `0xfe3b557e8fb62b89f4916b721be55ceb828dbd73`
  - private key `0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63`

Readiness check (block number should climb ~1/sec):

```bash
curl -s -X POST --data '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}' \
  -H "Content-Type: application/json" http://127.0.0.1:8545
```

### 2.2 Deploy + exercise the contract

```bash
cd edge-negotiator
.venv/Scripts/python - <<'PY'
import sys; sys.path.insert(0, "src")
from identity import JunctionIdentity
from besu_registry import BesuRegistry
RPC="http://127.0.0.1:8545"
ADDR="0xfe3b557e8fb62b89f4916b721be55ceb828dbd73"
KEY="0x8f2a55949038a9610f50fb23b5883af3b4ecb3c3bb792cbcefbd1542c692be63"
reg = BesuRegistry.deploy(RPC, ADDR, KEY)         # compiles + deploys
a = JunctionIdentity("A0")
reg.register("A0", a.public_key)                  # real 44-byte Ed25519 DER
assert reg.is_approved("A0") and reg.public_key("A0") == a.public_key
reg.revoke("A0"); assert not reg.is_approved("A0")
print("contract at", reg.contract_address)
print("audit_log", reg.audit_log)
PY
```

> **solc EVM-version pin (critical):** `besu_registry.compile_contract()`
> compiles with `evm_version="paris"`. solc >=0.8.20 defaults to `shanghai`,
> which emits the **PUSH0 (0x5f)** opcode; the Besu dev genesis activates a fork
> that predates PUSH0, so shanghai bytecode reverts on deploy with
> `INVALID_OPERATION`. `paris` produces PUSH0-free bytecode that deploys cleanly.

### 2.3 Run the benchmark

```bash
cd edge-negotiator
.venv/Scripts/python src/bench_ledger.py --trials 20 --batch 10
# writes results/ledger_bench.md
```

### 2.4 Tear down

```bash
docker rm -f besu-spike
```

---

## 3. Headline measured result

See `edge-negotiator/results/ledger_bench.md` for the full table. Measured on
Besu 24.12.0 single-node dev (block period 1.0 s), 20 trials/op:

| op | local median | besu median | besu p95 |
|---|---|---|---|
| register (write/commit) | 0.0154 ms | **1444 ms** | 3863 ms |
| revoke (write/commit) | 0.0101 ms | **1842 ms** | 5389 ms |
| isApproved (read) | 0.0002 ms | **46 ms** | 67 ms |
| getPublicKey (read) | 0.0002 ms | **32 ms** | 48 ms |
| batch of 10 registers | 0.148 ms | **20560 ms** | 27784 ms |

- **Reads** (`isApproved`, `getPublicKey`) are local `eth_call`s — ~30-50 ms,
  vs sub-microsecond for the in-memory map.
- **Writes** (`register`, `revoke`) are transactions: median **~1.4-1.8 s**
  commit-to-finality, bounded by the 1.0 s block period plus submission/receipt
  overhead (p95 up to ~5 s under the dev miner's intermittent world-state pauses).
- The brief's **"1-2 s finality, async-only" assumption HOLDS**: write commit
  medians (1.44 s / 1.84 s) sit inside the stated 1-2 s band on single-node dev,
  and a production QBFT network (2 s default block period) stays in the same
  envelope. That is fine for an **async audit-write path** and would be
  **catastrophic on the fast control path** — a ~1.4 s ledger write vs a 15 µs
  local membership check (~94,000x).

---

## 4. Integration plan for Wk 5-6

1. **Swap the backend, not the callers.** Construct `BesuRegistry.deploy(...)`
   (or `.attach(...)` to a pre-deployed address) and hand it to
   `MessageBus(registry, adjacency)` exactly where the local `Registry()` is
   used today. No `MessageBus` / controller changes — verified in this spike.
2. **Keep the local `Registry` as a cache + the fast path.** Per the brief, the
   fast path must not consult the chain per message. Use the local registry (or
   an in-process membership cache) for per-message verification, and treat the
   on-chain `BesuRegistry` as the **source of truth synced asynchronously**:
   apply `AgentRegistered` / `AgentRevoked` events to refresh the cache.
3. **Async audit-log writes via batching/anchoring.** Do **not** write one
   transaction per control decision. Buffer audit events on the fast path and
   flush them off-loop — periodic batched transactions, or anchor a Merkle root
   of each batch on-chain (cheap, tamper-evident, O(1) on-chain per batch).
   `bench_ledger.py`'s `batch_register_N` row shows per-tx cost scales linearly,
   confirming un-batched per-event writes do not scale to control cadence.
4. **Production hardening = QBFT multi-validator.** Replace the single-node dev
   chain with a **QBFT** network (≥4 validators for BFT, 2 s block period) using
   a real genesis (allocate the city-authority admin account, set a recent EVM
   fork so the PUSH0/`paris` pin can be dropped). Permissioning: on-chain or
   node permissioning so only authorised junction hosts can join.
5. **Keys & governance.** The admin (`onlyOwner`) key is the single
   city-authority key (brief decision). For production, move it behind a
   hardware/HSM or a multisig (brief's documented optional hardening) and never
   ship the dev key.

---

## 5. Honest limitations

- **Single-node dev != QBFT BFT.** This spike used Besu `--network=dev` with a
  PoW dev miner: it proves the *contract, the web3 glue, and the latency
  envelope*, but gives **no Byzantine-fault-tolerance guarantee**. Real BFT
  finality and the validator-round-trip latency component come only with a
  multi-validator QBFT network — that is the genuine Wk 5-6 production step.
- **Free gas / no fee market.** `gasPrice=0` removes fee-market queueing that a
  loaded permissioned chain could still exhibit; the measured write latency is
  therefore a lower bound.
- **Localhost RPC.** No agent-host↔node network latency is included; a
  distributed deployment adds it.
- **`:latest` is broken for this use.** Besu 26.6.0-RC1 removed the dev miner
  CLI flags; the spike is pinned to 24.12.0. Before production, re-validate
  mining/consensus config against whatever Besu LTS is current, since the CLI
  surface is clearly still moving.
- **Dev miner can stall briefly.** Under rapid back-to-back sends the dev PoW
  miner occasionally needs more than one cycle to seal; `BesuRegistry._send`
  uses a pending-nonce + generous receipt timeout to stay robust. QBFT's fixed
  block period removes this jitter.

---

## 6. Single biggest integration risk for Wk 5-6

**Coupling the audit-log write path to consensus latency.** If audit events are
written one-transaction-per-decision, the ~1-2 s commit latency leaks into the
system's effective throughput and (if anyone naively `await`s the receipt on the
control path) into control latency itself. **Mitigation is mandatory and
designed-in:** the ledger stays strictly async, audit events are batched/anchored
off-loop, and per-message membership checks hit a locally-cached copy of the
allowlist refreshed from on-chain events — never a synchronous `eth_call` per
message. The drop-in `BesuRegistry` makes the swap trivial; disciplined async
batching is what makes it *safe*.
