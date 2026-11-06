# Safe Multisig Module Attack Surface

Source: Fable 5 analysis via Claude Code WorkflowTool (July 10, 2026). The model provided 11,029 chars of Solidity-level security analysis.

## Core Vulnerability: execTransactionFromModule

Safe.sol's module execution path is the primary sanctioned bypass for multisig requirements:

```solidity
function execTransactionFromModule(
    address to, uint256 value, bytes memory data, Enum.Operation operation
) public virtual returns (bool success) {
    // ONLY check: is msg.sender an enabled module?
    require(isModuleEnabled(msg.sender), "GS104");
    // NO nonce check. NO signature check. NO threshold check.
    if (operation == Enum.Operation.DelegateCall) {
        assembly { success := delegatecall(gas(), to, add(data, 0x20), mload(data), 0, 0) }
    } else {
        assembly { success := call(gas(), to, value, add(data, 0x20), mload(data), 0, 0) }
    }
}
```

**Key**: Once any module is enabled, it can execute arbitrary transactions without any multisig approval.

## Attack Vectors

### 1. Fallback Handler + delegatecall
The fallback handler runs via `delegatecall` in the Safe's storage context. Has full read/write access to ALL Safe storage — owner list, threshold, module list. Cannot initiate new calls as "the Safe" in one transaction, but CAN corrupt storage for future exploitation.

### 2. EIP-7702 Owner Delegation
If a Safe owner EOA has EIP-7702 delegated code, Safe's `v=0` contract signature path (`EIP-1271`) becomes available. The delegate contract's `isValidSignature` implementation now controls what constitutes a valid signature from that owner. The 7702 delegation can be changed *without the Safe's knowledge* — the Safe still records the EOA address as owner, but signing semantics have changed.

### 3. ERC-7579 Session Key Modules
Session key modules are themselves enabled Safe modules with `execTransactionFromModule` access. Once installed, a session key bypasses the entire multisig signature collection:
- Module-internal auth (session key signature) replaces threshold-based approval
- Session key can be given permission boundaries (targets, selectors, value limits, time windows)
- Compromising the session key authentication = Safe compromise

### 4. Reentrancy in Module Execution
`execTransactionFromModule` historically lacked reentrancy guards in some Safe versions. If a Guard is enforcing invariants (spending limits, allowlists), reentrancy between `checkTransaction` and `checkAfterExecution` can bypass those checks.

## Summary Attack Surface Map

| Path | Signature Required | Notes |
|------|-------------------|-------|
| `execTransaction` | Yes (threshold) | Standard safe path |
| `execTransactionFromModule` | No | Module must be enabled |
| Fallback handler | No | delegatecall, full storage access |
| 7702 owner delegate | Depends on delegate | `isValidSignature` logic |
| Session key module | No (Safe sigs) | Module-internal auth only |
| Guard bypass via reentrance | Potentially bypassable | Version-dependent |

**Highest risk**: Module installation vectors. Anything that can add a module without full threshold approval is a total Safe compromise.
