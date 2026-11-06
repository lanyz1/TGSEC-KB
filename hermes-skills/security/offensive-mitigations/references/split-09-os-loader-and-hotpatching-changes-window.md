## OS Loader and Hotpatching Changes (Windows 11 24H2+)

- Recent Windows versions (24H2 and later) introduced changes that impact classic process injection techniques like Process Hollowing (RunPE).
- **Status:** Client Hotpatching availability and cadence depend on SKU/servicing channel. Validate GA status in current Microsoft documentation.
- Windows Server 2025 requires an Azure Arc subscription for hotpatch servicing.

### Impact on Process Hollowing (MEM_PRIVATE Payloads)

- **Root Cause 1 (Error `0xC0000141`):** Native Hotpatching support added a new function `RtlpInsertOrRemoveScpCfgFunctionTable` during process initialization (`LdrpInitializeProcess -> LdrpProcessMappedModule`). This function calls `ZwQueryVirtualMemory` with a new `MemoryImageExtensionInformation` class, which _only_ works on `MEM_IMAGE` memory regions.
  - Classic Process Hollowing stores the payload in `MEM_PRIVATE` memory (either by unmapping the original PE or allocating a new region).
  - The `ZwQueryVirtualMemory` call fails with `STATUS_INVALID_ADDRESS` for the `MEM_PRIVATE` payload region, causing process loading to terminate.
- **Root Cause 2 (Error `0xC00004AC`, Memory Integrity Enabled):** If Memory Integrity (HVCI) is enabled, another check occurs later in the loading process.
  - `LdrpQueryCurrentPatch` is called on the payload's memory region.
  - This leads to a call to `NtManageHotPatch`, which fails with `STATUS_CONFLICTING_ADDRESSES` for the `MEM_PRIVATE` payload.
  - This error also terminates the process loading.

### Solutions and Bypasses

1.  **Use Alternative Techniques (Recommended):** Employ methods that map the payload as `MEM_IMAGE`, which are unaffected by these specific checks.
    - Examples: Process Doppelganging, Process Ghosting, Process Herpaderping, Transacted Hollowing, Ghostly Hollowing, Herpaderply Hollowing, Process Overwriting.
    - These techniques generally interact more naturally with the loader and newer OS features.
2.  **Patch NTDLL (If sticking to Classic RunPE):**
    - **For `0xC0000141`:** Hook `ZwQueryVirtualMemory`.
      - Check if the OS is Win11 24H2+ (64-bit).
      - If the `MemoryInformationClass` is `MemoryImageExtensionInformation` AND the query targets the base address of the `MEM_PRIVATE` payload:
        - Return a benign error like `STATUS_NOT_SUPPORTED` instead of calling the original function.
      - Otherwise, call the original `ZwQueryVirtualMemory`.
      - [Implementation Example](https://github.com/hasherezade/libpeconv/blob/master/run%5Fpe/patch%5Fntdll.cpp#L91)
    - **For `0xC00004AC` (Memory Integrity):** Hook `NtManageHotPatch`.
      - Patch the function to immediately return a benign error like `STATUS_NOT_SUPPORTED`.
      - Apply this patch early in the process creation, for both 32-bit and 64-bit.
      - Ensure `FlushInstructionCache` is called if patching after the function might have been cached.
      - [32-bit Example](https://github.com/hasherezade/libpeconv/blob/master/run%5Fpe/patch%5Fntdll.cpp#L4)
      - [64-bit Example](https://github.com/hasherezade/libpeconv/blob/master/run%5Fpe/patch%5Fntdll.cpp#L43)

