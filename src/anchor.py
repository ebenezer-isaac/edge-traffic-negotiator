"""Salted-root completeness anchoring + a >=2-witness cross-audit (MASTER-SPEC
§6.7/§7.7; gate D-anchor).

The audit log's Merkle root commits a batch's COMPLETENESS. Publishing it to
external witnesses gives non-equivocation (a signer cannot show one investigator a
different history than another). But an UNSALTED root over pseudonymous signer
records would immutably commit those fingerprints to a public log (§7.7). So we
publish a SALTED root:

    leaf_i = sha256(salt_i || entry_hash_i)     # salt_i is fresh 32-byte randomness
    root   = merkle(leaf_0 .. leaf_n)           # same _hash_pair fold as audit_log

The salt vector is kept OFF-CHAIN and is ERASABLE (§7.7): the published root reveals
nothing about the entries, yet an investigator holding the salt can still prove a
specific decision was in the anchored batch (salted inclusion proof). Erase the salt
and the commitment becomes unlinkable -- forward privacy for the pseudonymous fpr.

NON-EQUIVOCATION via >=2 witnesses. Each witness is an independent store of
``label -> root``. A CrossAuditor reads the root back from every witness; if two
witnesses return DIFFERENT roots for the same label the signer has EQUIVOCATED
(shown a split view) and the auditor FLAGS it -- the teeth of the mechanism. A
single witness, or witnesses that all agree, cannot by itself prove non-equivocation
across the whole ecosystem; that is the honest limit (§4.2).
"""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass

from audit_log import _hash_pair


def _salted_leaf(salt_hex: str, entry_hash_hex: str) -> str:
    """A salted leaf: sha256(salt || entry_hash). Salt hides the entry hash (and
    thus the pseudonymous fpr it commits) on the published root."""
    return hashlib.sha256((salt_hex + entry_hash_hex).encode("utf-8")).hexdigest()


def _merkle(leaves: list) -> str:
    """Fold leaf hex digests into a root with the audit_log Bitcoin-style promotion
    (identical to AuditLog.merkle_root so the constructions match)."""
    if not leaves:
        raise ValueError("merkle root requires a non-empty leaf set")
    level = list(leaves)
    while len(level) > 1:
        if len(level) % 2 == 1:
            level = [*level, level[-1]]
        level = [_hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
    return level[0]


@dataclass(frozen=True)
class SaltedAnchor:
    """A salted completeness commitment over a batch of entry hashes."""
    salted_root: str
    salts: tuple            # OFF-CHAIN, erasable; never published with the root
    entry_hashes: tuple     # the batch's raw entry hashes (held by the log owner)
    n: int

    @classmethod
    def from_hashes(cls, entry_hashes, *, salts=None) -> "SaltedAnchor":
        hs = tuple(entry_hashes)
        if not hs:
            raise ValueError("SaltedAnchor requires a non-empty batch")
        if salts is None:
            salts = tuple(os.urandom(32).hex() for _ in hs)
        else:
            salts = tuple(salts)
            if len(salts) != len(hs):
                raise ValueError("salts length must match entry_hashes length")
        leaves = [_salted_leaf(s, h) for s, h in zip(salts, hs)]
        return cls(salted_root=_merkle(leaves), salts=salts, entry_hashes=hs, n=len(hs))

    @classmethod
    def from_audit(cls, audit, start: int = 0, end: int | None = None,
                   *, salts=None) -> "SaltedAnchor":
        entries = audit.entries()
        end = len(entries) if end is None else end
        hs = [entries[i]["hash"] for i in range(start, end)]
        return cls.from_hashes(hs, salts=salts)

    def salted_inclusion_proof(self, index: int) -> dict:
        """Prove entry ``index`` is in the anchored batch: its salt + a Merkle branch
        over the SALTED leaves. The verifier recomputes the salted leaf and folds the
        branch to the published root -- without the salt the proof cannot be forged
        and the root reveals nothing."""
        if index < 0 or index >= self.n:
            raise IndexError(f"index {index} out of range [0,{self.n})")
        leaves = [_salted_leaf(s, h) for s, h in zip(self.salts, self.entry_hashes)]
        branch: list[dict] = []
        level = list(leaves)
        pos = index
        while len(level) > 1:
            if len(level) % 2 == 1:
                level = [*level, level[-1]]
            sib = pos ^ 1
            branch.append({"hash": level[sib],
                           "position": "right" if sib > pos else "left"})
            level = [_hash_pair(level[i], level[i + 1]) for i in range(0, len(level), 2)]
            pos //= 2
        return {"index": index, "salt": self.salts[index],
                "entry_hash": self.entry_hashes[index], "branch": branch}


def verify_salted_inclusion(proof: dict, root: str) -> bool:
    """Recompute the salted leaf + fold the branch; True iff it reaches ``root``."""
    try:
        node = _salted_leaf(proof["salt"], proof["entry_hash"])
        for step in proof["branch"]:
            sib = step["hash"]
            node = (_hash_pair(sib, node) if step["position"] == "left"
                    else _hash_pair(node, sib))
        return node == root
    except (KeyError, TypeError):
        return False


# --------------------------------------------------------------------------- #
# Witnesses + the cross-auditor.
# --------------------------------------------------------------------------- #
class LocalLedgerWitness:
    """An INDEPENDENT file-backed witness: a distinct process/store that records
    ``label -> root``. Two instances over two different files are genuinely
    independent histories, so a cross-audit over them is a real non-equivocation
    check (not a shared-object illusion). Append-only: a second, different root for
    an existing label is REJECTED (a witness does not silently overwrite history)."""

    def __init__(self, name: str, path: str):
        self.name = name
        self.path = path
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({}, fh)

    def _load(self) -> dict:
        with open(self.path, encoding="utf-8") as fh:
            return json.load(fh)

    def submit(self, label: str, root: str) -> dict:
        store = self._load()
        if label in store and store[label] != root:
            raise ValueError(
                f"witness {self.name}: label {label!r} already anchored to a "
                f"different root (append-only; refusing to overwrite)")
        store = {**store, label: root}
        with open(self.path, "w", encoding="utf-8") as fh:
            json.dump(store, fh)
        return {"witness": self.name, "label": label, "root": root, "accepted": True}

    def fetch(self, label: str):
        return self._load().get(label)


class CrossAuditor:
    """Reads a label's root back from >=2 witnesses and detects equivocation.

    Returns a report: the roots each witness holds, whether they AGREE (all present
    and equal), and an ``equivocation`` flag set when two witnesses disagree (a
    split view -- the signer showed different histories). Fewer than 2 witnesses
    present -> ``quorum_met`` False (non-equivocation cannot be asserted)."""

    def __init__(self, name: str):
        self.name = name

    def audit(self, witnesses, label: str) -> dict:
        seen = {}
        for w in witnesses:
            try:
                seen[w.name] = w.fetch(label)
            except Exception as exc:  # noqa: BLE001
                seen[w.name] = f"ERROR:{type(exc).__name__}"
        present = {k: v for k, v in seen.items()
                   if isinstance(v, str) and not v.startswith("ERROR:")}
        distinct = set(present.values())
        quorum_met = len(present) >= 2
        equivocation = len(distinct) > 1
        return {
            "cross_auditor": self.name,
            "label": label,
            "witness_roots": seen,
            "witnesses_present": len(present),
            "quorum_met": quorum_met,
            "roots_agree": (len(distinct) == 1) if present else False,
            "equivocation_detected": equivocation,
            "consistent": bool(quorum_met and not equivocation),
        }


def per_signer_counts(audit) -> dict:
    """Reconciled per-signer entry counts over the log (the D-anchor NON-BLOCKING
    process check): how many entries each issuer signed. Names a KEY/issuer id,
    never a person."""
    counts: dict = {}
    for e in audit.entries():
        issuer = e.get("issuer")
        key = issuer if issuer else "<unsigned>"
        counts[key] = counts.get(key, 0) + 1
    return counts


def try_besu_witness(rpc_url: str = "http://127.0.0.1:8545"):
    """ATTEMPT a live Besu ledger witness. Returns (witness_info, None) if a node is
    reachable, else (None, reason) -- SKIP-with-record, never raises. Bringing up the
    node is out of band (`docker compose -f .qbft-spike/docker-compose.yml up`)."""
    try:
        from web3 import Web3
    except Exception as exc:  # noqa: BLE001
        return None, f"web3 not importable ({type(exc).__name__})"
    try:
        w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 4}))
        if not w3.is_connected():
            return None, (f"Besu RPC {rpc_url} not reachable (node not running). "
                          "Start it: docker compose -f .qbft-spike/docker-compose.yml up -d")
        return {"rpc_url": rpc_url, "chain_id": w3.eth.chain_id,
                "block": w3.eth.block_number}, None
    except Exception as exc:  # noqa: BLE001
        return None, f"Besu connect failed: {type(exc).__name__}: {str(exc)[:120]}"


def try_rekor_reachable(url: str = "https://rekor.sigstore.dev/api/v1/log"):
    """READ-ONLY reachability of the public Rekor transparency log. We do NOT WRITE
    to the production public log (that would permanently publish test data / pollute
    a shared public good); the write is a deliberate, documented WITHHOLD. Returns
    (info, None) if reachable else (None, reason). Never raises."""
    import urllib.request
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            data = json.loads(resp.read())
        return {"url": url, "tree_size": data.get("treeSize"),
                "root_hash": str(data.get("rootHash"))[:16],
                "write": "WITHHELD (would permanently publish to the public log)"}, None
    except Exception as exc:  # noqa: BLE001
        return None, f"Rekor unreachable: {type(exc).__name__}: {str(exc)[:120]}"
