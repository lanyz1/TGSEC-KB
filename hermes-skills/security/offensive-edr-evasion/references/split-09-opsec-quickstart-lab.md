## OpSec Quickstart (lab)

- Pre‑run
  - Network: block or sinkhole vendor EDR/XDR endpoints; disable cloud sample submission; tag lab hosts.
  - Mitigations snapshot: `Get-ProcessMitigation -System`; `Get-CimInstance Win32_DeviceGuard` (VBS/HVCI/KDP); `Get-MpPreference` (ASR/Cloud).
  - Events baseline: enable and tail `Microsoft-Windows-CodeIntegrity/Operational`, `Security (4688/4689)`, `Microsoft-Windows-Sense/Operational`, Sysmon (if present).
- Injection hygiene
  - Favor `MEM_IMAGE` mappings (ghosting/herpaderping/overwriting) over `MEM_PRIVATE` RWX to avoid 24H2 hotpatch loader checks.
  - Satisfy XFG/CET: jump via import thunks; ensure IBT `ENDBR64` at indirect targets; maintain plausible stacks for syscalls (replicate `ntdll` frames).
  - Avoid noisy APIs: split `alloc/write/exec` over time; prefer APC+`NtContinue` pivots; keep thread contexts consistent.
- Telemetry minimization
  - Jitter long‑lived channels; prefer named‑pipe/HTTP3 over noisy HTTP1; throttle upload intervals.
  - Use COM/runspace over PowerShell console to reduce script‑block logs; avoid AMSI‑flagged prologues.
- Cleanup
  - Remove services, tasks, drivers; restore SDDL; revert registry policy flips (WDAC/CI/Defender) and re‑enable protections.
  - Purge user caches (Recent Files, Jump Lists) and ETW providers enabled during tests.

### Memory Regions

- Monitors suspicious memory allocation patterns
- Flags RWX (read-write-execute) regions
- Tracks regions that change from RW to RX

### Callstack Analysis

- Examines the call stack of suspicious functions
- Verifies legitimate origin of critical operations
- Detects unusual function call chains

### Hook Implementation

EDRs can't directly hook kernel memory due to PatchGuard, so they:

1. Inject their DLL into newly spawned processes
2. Position before malware can block/unmap it
3. Adjust `_PEB`, hook process's module `IAT`/Imports, and loaded libraries `EAT`/Exports
4. Implement trampolines, hooks, and detours

### ETW Monitoring

- EDR maintains ring-buffer with per-process activities produced by ETW Ti:
  - Processes, command lines, parent-child relationships
  - File/Registry/Process open/write operations
  - Created threads, their call stacks, starting addresses
  - Native functions called
  - Created .NET AppDomains, loaded .NET assemblies, static class names, methods

#### Event Correlation

- High fidelity alert (such as LSASS open) triggers correlation of collected activities
- High memory/resources cost limits preservation of events to a time window
- ML/AI may compute risk scores and isolate TTP (Tactics, Techniques, and Procedures)

#### Shellcode Loaders

Shellcode loaders typically follow this pattern:

```c
char *shellcode = "\xAA\xBB...";
char *dest = VirtualAlloc(NULL, 0x1234, 0x3000, PAGE_READWRITE);
memcpy(dest, shellcode, 0x1234)
VirtualProtect(dest, 0x1234, PAGE_EXECUTE_READ, &result)
(*(void(*)())(dest))();  // jump to dest: execute shellcode
```

