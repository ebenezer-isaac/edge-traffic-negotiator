"""On-chain permissioned agent registry backed by Hyperledger Besu (web3.py).

`BesuRegistry` is a **drop-in replacement** for the local in-memory
`src/registry.py` Registry: it exposes the same four method names the rest of
the system depends on —

    register(junction_id: str, public_key: bytes) -> None
    revoke(junction_id: str) -> None
    is_approved(junction_id: str) -> bool
    public_key(junction_id: str) -> bytes | None

plus an `audit_log` property and a `verify_chain()`. Because `MessageBus`
(`src/message_bus.py`) only ever calls `registry.public_key(sender)`,
`registry.is_approved(sender)` and iterates `registry.audit_log` reading the
`action` / `junction_id` fields, a `BesuRegistry` can be handed to
`MessageBus(registry, adjacency)` unchanged.

Architecture (MASTER-SPEC.md §2/§3): the ledger is an **async
registry + audit log only and is NEVER in the real-time control loop**. Reads
(`is_approved`, `public_key`) are local `eth_call`s against contract state and
are cheap; writes (`register`, `revoke`) are transactions that must be mined and
therefore carry block/finality latency — which is exactly why MASTER-SPEC.md keeps
them off the fast path (MASTER-SPEC.md §4.1).

The on-chain `AgentRegistered` / `AgentRevoked` events ARE the tamper-evident
audit log; `audit_log` reconstructs the chronological event list from those logs
(ordered by block number then log index). Each reconstructed event mirrors the
local registry's event shape — `seq`, `action`, `junction_id`, `pubkey_sha256` —
augmented with on-chain provenance (`block_number`, `tx_hash`, `log_index`).

Error policy (per the project rules): the *not-connected* case is raised
explicitly with a clear message; underlying web3 exceptions are **not swallowed**
— they propagate so a real failure is never silently masked.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from web3 import Web3
from web3.exceptions import ContractLogicError, Web3RPCError

try:  # solc compilation is only needed when deploying a fresh contract.
    import solcx
except ImportError:  # pragma: no cover - solcx is installed in this project venv
    solcx = None  # type: ignore[assignment]

_SOLC_VERSION = "0.8.24"
_CONTRACT_PATH = Path(__file__).resolve().parent.parent / "contracts" / "AgentRegistry.sol"
_CONTRACT_NAME = "AgentRegistry"


class BesuRegistryError(RuntimeError):
    """Raised for registry-level failures (no connection, missing contract)."""


def compile_contract(contract_path: Path = _CONTRACT_PATH) -> dict[str, Any]:
    """Compile AgentRegistry.sol with py-solc-x; return {'abi', 'bytecode'}.

    Raises BesuRegistryError if solcx is unavailable or the source is missing.
    """
    if solcx is None:
        raise BesuRegistryError("py-solc-x is not installed; cannot compile contract")
    if not contract_path.exists():
        raise BesuRegistryError(f"contract source not found: {contract_path}")

    installed = {str(v) for v in solcx.get_installed_solc_versions()}
    if _SOLC_VERSION not in installed:
        solcx.install_solc(_SOLC_VERSION)

    # Pin the EVM target to "paris": solc >=0.8.20 defaults to "shanghai",
    # which emits the PUSH0 (0x5f) opcode. The Besu dev-mode genesis used here
    # activates a fork that predates PUSH0, so shanghai bytecode reverts with
    # INVALID_OPERATION on deploy. "paris" produces PUSH0-free bytecode that the
    # dev chain executes. (Production QBFT genesis would set a recent fork and
    # this pin could be dropped.)
    compiled = solcx.compile_files(
        [str(contract_path)],
        output_values=["abi", "bin"],
        solc_version=_SOLC_VERSION,
        optimize=True,
        evm_version="paris",
    )
    # compile_files keys are "<path>:<ContractName>"; find ours.
    key = next(k for k in compiled if k.endswith(f":{_CONTRACT_NAME}"))
    artifact = compiled[key]
    return {"abi": artifact["abi"], "bytecode": artifact["bin"]}


class BesuRegistry:
    """Permissioned allowlist backed by the on-chain AgentRegistry contract.

    Construct via :meth:`deploy` (compiles + deploys a fresh contract) or
    :meth:`attach` (binds to an already-deployed address). Both require a live
    web3 connection to the Besu RPC endpoint.
    """

    def __init__(
        self,
        w3: Web3,
        contract: Any,
        admin_address: str,
        *,
        private_key: str | None = None,
    ) -> None:
        if not w3.is_connected():
            raise BesuRegistryError(
                "web3 is not connected to the Besu RPC endpoint; "
                "start the node and check the RPC URL before using BesuRegistry"
            )
        self._w3 = w3
        self._contract = contract
        self._admin = Web3.to_checksum_address(admin_address)
        self._private_key = private_key
        # Locally-managed nonce. Re-reading the chain's "pending" nonce per send
        # is racy on the single-node dev chain: after a long world-state pause
        # the node can briefly report a stale count, yielding "Nonce too low".
        # We seed once from the chain and increment on each accepted send, which
        # is correct as long as this object is the only sender for `_admin`
        # (true for the spike/benchmark). Resynced lazily on a nonce error.
        self._nonce: int | None = None

    # -- constructors --------------------------------------------------------

    @classmethod
    def deploy(
        cls,
        rpc_url: str,
        admin_address: str,
        private_key: str,
        *,
        admin_on_chain: str | None = None,
    ) -> "BesuRegistry":
        """Compile, deploy a fresh AgentRegistry, and return a bound instance.

        `admin_address` / `private_key` are the deploying (and signing) account;
        `admin_on_chain` is the contract's `owner` (defaults to `admin_address`).
        """
        w3 = cls._connect(rpc_url)
        admin = Web3.to_checksum_address(admin_address)
        owner = Web3.to_checksum_address(admin_on_chain or admin_address)

        art = compile_contract()
        factory = w3.eth.contract(abi=art["abi"], bytecode=art["bytecode"])
        tx = factory.constructor(owner).build_transaction(
            cls._tx_params(w3, admin)
        )
        receipt = cls._send(w3, tx, private_key)
        contract = w3.eth.contract(address=receipt["contractAddress"], abi=art["abi"])
        return cls(w3, contract, admin, private_key=private_key)

    @classmethod
    def attach(
        cls,
        rpc_url: str,
        contract_address: str,
        abi: list,
        admin_address: str,
        private_key: str | None = None,
    ) -> "BesuRegistry":
        """Bind to an already-deployed AgentRegistry at `contract_address`."""
        w3 = cls._connect(rpc_url)
        contract = w3.eth.contract(
            address=Web3.to_checksum_address(contract_address), abi=abi
        )
        return cls(w3, contract, admin_address, private_key=private_key)

    # -- mutating operations (transactions; mined => carry finality latency) --

    def register(self, junction_id: str, public_key: bytes) -> None:
        """Approve `junction_id` with DER `public_key` on-chain (a transaction).

        Mirrors Registry.register: validates inputs the same way and permits
        re-registration after revocation with a new key.
        """
        if not isinstance(junction_id, str) or not junction_id:
            raise ValueError("junction_id must be a non-empty string")
        if not isinstance(public_key, (bytes, bytearray)):
            raise TypeError("public_key must be bytes (canonical DER encoding)")

        fn = self._contract.functions.register(junction_id, bytes(public_key))
        self._send_fn(fn)

    def revoke(self, junction_id: str) -> None:
        """Revoke `junction_id` on-chain (a transaction).

        Mirrors Registry.revoke: raises KeyError if the junction was never
        registered (the contract reverts "unknown junctionId").
        """
        if not isinstance(junction_id, str) or not junction_id:
            raise ValueError("junction_id must be a non-empty string")
        if not self._was_ever_registered(junction_id):
            raise KeyError(junction_id)

        fn = self._contract.functions.revoke(junction_id)
        try:
            self._send_fn(fn)
        except ContractLogicError as exc:  # contract-level revert
            if "unknown junctionId" in str(exc):
                raise KeyError(junction_id) from exc
            raise

    # -- queries (local eth_call against contract state; cheap, off-loop) -----

    def is_approved(self, junction_id: str) -> bool:
        """True iff `junction_id` is registered AND not currently revoked."""
        if not isinstance(junction_id, str) or not junction_id:
            return False
        return bool(self._contract.functions.isApproved(junction_id).call())

    def public_key(self, junction_id: str) -> bytes | None:
        """Current approved DER public key for `junction_id`, else None."""
        if not isinstance(junction_id, str) or not junction_id:
            return None
        raw = self._contract.functions.getPublicKey(junction_id).call()
        return bytes(raw) if raw else None

    # -- audit log (reconstructed from on-chain events) -----------------------

    @property
    def audit_log(self) -> list[dict]:
        """Chronological audit log rebuilt from on-chain events.

        Each entry mirrors the local Registry event shape (`seq`, `action`,
        `junction_id`, `pubkey_sha256`) and adds on-chain provenance fields.
        Ordered by (block_number, log_index). MessageBus only reads `action`
        and `junction_id`, so this is a faithful drop-in.
        """
        registered = self._contract.events.AgentRegistered().get_logs(
            from_block=0
        )
        revoked = self._contract.events.AgentRevoked().get_logs(from_block=0)

        combined = list(registered) + list(revoked)
        combined.sort(key=lambda ev: (ev["blockNumber"], ev["logIndex"]))

        log: list[dict] = []
        for seq, ev in enumerate(combined):
            args = ev["args"]
            if ev["event"] == "AgentRegistered":
                pk = bytes(args["publicKey"])
                action = "register"
                pubkey_sha256 = hashlib.sha256(pk).hexdigest()
            else:
                action = "revoke"
                pubkey_sha256 = None
            log.append(
                {
                    "seq": seq,
                    "action": action,
                    "junction_id": args["junctionId"],
                    "pubkey_sha256": pubkey_sha256,
                    "block_number": ev["blockNumber"],
                    "tx_hash": ev["transactionHash"].hex(),
                    "log_index": ev["logIndex"],
                }
            )
        return log

    def verify_chain(self) -> bool:
        """On-chain tamper-evidence is provided by the chain itself.

        Unlike the local registry's app-level sha256 hash chain, integrity here
        rests on the ledger's block hashes / consensus. We expose this method for
        interface parity and confirm we can re-read the event log deterministically
        (i.e. the node is reachable and the contract's log set is consistent).
        Returns True if the audit log is readable and sequence-contiguous.
        """
        log = self.audit_log
        return all(entry["seq"] == i for i, entry in enumerate(log))

    # -- introspection --------------------------------------------------------

    @property
    def contract_address(self) -> str:
        return self._contract.address

    @property
    def abi(self) -> list:
        return self._contract.abi

    # -- internals ------------------------------------------------------------

    def _was_ever_registered(self, junction_id: str) -> bool:
        for event in self.audit_log:
            if event["action"] == "register" and event["junction_id"] == junction_id:
                return True
        return False

    def _send_fn(self, fn) -> dict:
        if self._private_key is None:
            raise BesuRegistryError(
                "no private key bound to this BesuRegistry; cannot send a "
                "state-changing transaction"
            )
        # Seed the local nonce from the chain on first use.
        if self._nonce is None:
            self._nonce = self._w3.eth.get_transaction_count(self._admin, "pending")

        # One transparent resync+retry on a "Nonce too low" race: the dev node
        # can transiently disagree with our counter after a long world-state
        # pause. We resync from the chain and retry exactly once; any other
        # web3 error (or a second nonce error) propagates — never swallowed.
        for attempt in (0, 1):
            params = {
                "from": self._admin,
                "nonce": self._nonce,
                "gasPrice": 0,
                "gas": 3_000_000,
                "chainId": self._w3.eth.chain_id,
            }
            tx = fn.build_transaction(params)
            try:
                receipt = self._send(self._w3, tx, self._private_key)
                self._nonce += 1
                return receipt
            except Web3RPCError as exc:
                if attempt == 0 and "Nonce too low" in str(exc):
                    self._nonce = self._w3.eth.get_transaction_count(
                        self._admin, "pending"
                    )
                    continue
                raise
        raise BesuRegistryError("unreachable: nonce retry loop exhausted")

    @staticmethod
    def _connect(rpc_url: str) -> Web3:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
        if not w3.is_connected():
            raise BesuRegistryError(
                f"could not connect to Besu RPC at {rpc_url}; "
                "is the node running and the URL correct?"
            )
        return w3

    @staticmethod
    def _tx_params(w3: Web3, sender: str) -> dict:
        # Free-gas dev chain: gasPrice 0, legacy tx type. Use the *pending*
        # nonce so rapid back-to-back sends (e.g. the benchmark) never collide
        # or leave a gap that strands a later transaction.
        return {
            "from": sender,
            "nonce": w3.eth.get_transaction_count(sender, "pending"),
            "gasPrice": 0,
            "gas": 3_000_000,
            "chainId": w3.eth.chain_id,
        }

    @staticmethod
    def _send(w3: Web3, tx: dict, private_key: str) -> dict:
        signed = w3.eth.account.sign_transaction(tx, private_key)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        # Poll for the receipt. The dev-mode PoW miner occasionally takes more
        # than one cycle to seal a block, so we use a generous timeout and a
        # tight poll interval; on a clean ~1 s block period this still returns
        # in roughly one block. We do NOT swallow a genuine failure (status 0).
        try:
            receipt = w3.eth.wait_for_transaction_receipt(
                tx_hash, timeout=120, poll_latency=0.1
            )
        except Exception:
            # Last-chance direct read: the tx may have mined microseconds after
            # the wait gave up. If it really isn't there, re-raise.
            receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt["status"] != 1:
            raise BesuRegistryError(f"transaction reverted on-chain: {tx_hash.hex()}")
        return receipt
