// SPDX-License-Identifier: MIT
pragma solidity 0.8.24;

/// @title AgentRegistry — permissioned allowlist of approved junction agents.
/// @notice On-chain analogue of the local `src/registry.py` Registry. It records
///         *which junction agents are currently approved* and stores each one's
///         canonical DER-encoded Ed25519 public key. The emitted
///         `AgentRegistered` / `AgentRevoked` events ARE the tamper-evident,
///         non-repudiable on-chain audit log (provenance + history); the
///         contract state is just the current membership view.
///
/// @dev Trust model (PROJECT-DECISION-BRIEF.md §6): this vouches for *membership*,
///      not for the honesty of an approved agent. A single city-authority admin
///      key governs the allowlist (`onlyOwner`); multisig is documented as an
///      optional production hardening, not implemented here.
///
///      The ledger is ASYNC registry + audit only and is NEVER in the real-time
///      control loop (brief §2 / §3). Public keys are treated as opaque bytes —
///      the contract never parses or validates the key material beyond a
///      non-empty check; canonical encoding (44-byte Ed25519 DER) is enforced
///      off-chain by src/identity.py.
contract AgentRegistry {
    /// @notice The single city-authority admin key permitted to mutate the allowlist.
    address public immutable owner;

    /// @dev Per-junction record. `exists` distinguishes "never registered" from
    ///      "registered then revoked" (mirrors the local registry's `_known` set),
    ///      so callers can tell `unknown_sender` apart from `revoked`.
    struct Agent {
        bytes publicKey; // canonical DER Ed25519 public key (opaque to the contract)
        bool approved;   // currently approved (true) vs revoked (false)
        bool exists;     // ever registered at all
    }

    /// @dev junctionId (string) -> agent record.
    mapping(string => Agent) private _agents;

    /// @notice Emitted on every (re-)registration. This is an audit-log entry:
    ///         the junctionId and full public key are carried in the event so the
    ///         off-chain reader can reconstruct the complete history from logs.
    event AgentRegistered(string indexed junctionIdHash, string junctionId, bytes publicKey);

    /// @notice Emitted on every revocation. Audit-log entry for the revoke action.
    event AgentRevoked(string indexed junctionIdHash, string junctionId);

    /// @dev Reverts any state-changing call not made by the admin key.
    modifier onlyOwner() {
        require(msg.sender == owner, "AgentRegistry: caller is not the owner");
        _;
    }

    /// @param admin The city-authority admin key (the deployer if address(0) is passed).
    constructor(address admin) {
        owner = admin == address(0) ? msg.sender : admin;
    }

    /// @notice Approve `junctionId` with `publicKey` (DER bytes); append an event.
    /// @dev Re-registration after revocation is permitted and may carry a new key,
    ///      matching the local Registry semantics. Empty inputs are rejected.
    function register(string calldata junctionId, bytes calldata publicKey) external onlyOwner {
        require(bytes(junctionId).length > 0, "AgentRegistry: empty junctionId");
        require(publicKey.length > 0, "AgentRegistry: empty publicKey");

        _agents[junctionId] = Agent({publicKey: publicKey, approved: true, exists: true});

        emit AgentRegistered(junctionId, junctionId, publicKey);
    }

    /// @notice Revoke `junctionId`; append an event.
    /// @dev Reverts if the junction was never registered (mirrors the local
    ///      Registry's KeyError). Revoking an already-revoked-but-known junction
    ///      is allowed and still records an event for the audit trail.
    function revoke(string calldata junctionId) external onlyOwner {
        require(bytes(junctionId).length > 0, "AgentRegistry: empty junctionId");
        require(_agents[junctionId].exists, "AgentRegistry: unknown junctionId");

        _agents[junctionId].approved = false;

        emit AgentRevoked(junctionId, junctionId);
    }

    /// @notice True iff `junctionId` is registered AND not currently revoked.
    function isApproved(string calldata junctionId) external view returns (bool) {
        return _agents[junctionId].approved;
    }

    /// @notice Current approved DER public key for `junctionId`.
    /// @dev Returns empty bytes if the junction is not currently approved (either
    ///      never registered or revoked), so callers can treat empty == None.
    function getPublicKey(string calldata junctionId) external view returns (bytes memory) {
        Agent storage a = _agents[junctionId];
        if (!a.approved) {
            return "";
        }
        return a.publicKey;
    }
}
