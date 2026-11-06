## Control Flow Integrity and Execution Protections

### Data Execution Prevention (DEP)

- Windows/Linux:
  - Marks certain memory regions as non-executable.
  - Prevents execution of code from data pages, mitigating buffer overflow attacks.

#### Bypass Techniques

- **Return-oriented Programming (ROP)**: Using existing code fragments to create attack chains without injecting code.
- **ret2libc**: Jump directly to code in libc.
- **ret2data**: Place shellcode in the data section.
- **ret2strcpy**: Place shellcode on the stack and use strcpy to move it somewhere executable.
- **ret2gets**: Read from stdin to gain control.
- **VirtualProtect/VirtualAlloc**: Call these functions to change memory permissions.
- **JIT Spraying**: Leverage Just-In-Time compilation to get executable memory.

#### Practitioner

- use `!vprot rip` or `!vpro rsp` to check for protections inside WinDbg
- `.scriptload G:\Projects\narly.js; !nmod` also helps you to see which modules have DEP protection
- `Data Execution Prevention` settings inside `Windows Exploit Guard` can be used to force DEP protection on an executable
- pivot with `VirtualProtect` / `NtProtectVirtualMemory` (or pre‑ACG RWX section) from a ROP/JOP chain.
- Modern Windows 10/11 enforce **CET (Shadow Stack)** and **XFG (Cross‑Function Guard)**, which break classic ROP; successful chains must first disable CET (for example with `SetProcessMitigationPolicy`) or switch to JOP/SCS gadgets.
- an example would be `pop rcx; retn; pop rcx; retn; mov [rcx], rax; pop rbp; retn;`
- we can use `IAT` to identify and call `WriteProcessMemory` which can be used to circumvent DEP protection through `NtProtectVirtualMemory` API
- [Ropper 2.0](https://github.com/sashs/Ropper) **or Rizin‑ropper** — both support CET/XFG‑aware gadget filtering.

### Control Flow Integrity (CFI)

- Windows:
  - Ensures kernel execution follows legitimate paths.
  - Thwarts control-flow hijacking attacks like function pointer overwrites.

#### Bypass Techniques

- **Similar Function Prototypes**: For XFG (Extreme Flow Guard), functions with similar prototypes may be exploitable.
- **Data-Only Attacks**: Manipulating program state without violating CFI constraints.
- **Implementation Weaknesses**: Exploiting gaps in the implementation of CFI.
- **JIT Compilation**: Just-in-time compiled code may bypass CFI checks.

#### Practitioner

- Windows build: enable CFG/XFG via `/guard:cf /guard:xfg` and `/Qspectre` where applicable; inspect PE `LoadConfig` for CFG/XFG metadata.
- Linux build: Clang `-fsanitize=cfi` (user space) or `CONFIG_CFI_CLANG=y` (kernel), with LTO; verify symbols contain CFI jump tables.

### kCFI

- Linux
  - Clang-based forward-edge Control-Flow Integrity that verifies indirect function calls at runtime in the kernel.
  - Enabled by default in Android GKI kernels and ChromeOS since early 2024; available upstream via `CONFIG_CFI_CLANG`.
  - Complements FineIBT and hardware CET by protecting software-only control-flow edges.
  - **BHI Hardening (Linux 6.9/6.10):** FineIBT now incorporates indirect‑branch serialization to mitigate Branch History Injection.

### Control Flow Guard (CFG)

- Windows:
  - Ensures indirect calls go only to valid, predefined locations.
  - Helps prevent control-flow hijacking attacks.

#### Bypass Techniques

- **JIT Code Execution**: Using Just-In-Time compiled code which may not be properly protected.
- **Import Address Table (IAT) Manipulation**: Inserting entries in IAT since these aren't checked.
- **Data-only Attacks**: Modifying program data to influence control flow without redirecting execution.
- **Type Confusion**: Exploiting type confusion to bypass CFG checks.

#### Practitioner

- Check process mitigation: `Get-ProcessMitigation -Name process.exe` (PowerShell) → CFG/strictCFG/XFG states.
- PE inspection: `dumpbin /loadconfig` shows GuardCFFunctionTable and flags.

### Stack Canaries

- Linux/Windows:
  - Inserts random values before return addresses on the stack.
  - Detects stack buffer overflows before they overwrite return addresses.

#### Bypass Techniques

- **Leaking Canary Values**: Using format string or other information disclosure vulnerabilities.
- **Overwriting Non-return Variables**: Attacking function pointers or other control flow variables not protected by canaries.
- **Brute Force**: On systems with low entropy canaries or predictable generation.
- **Exception Handler Attacks**: Targeting exception registration records which may not be protected.
- **Unprotected Functions**: Exploiting functions not protected by canaries (often due to performance considerations).

### Stack Clash Protection

- Linux/GCC:
  - Prevents stack and heap collisions by probing stack pages during large allocations.
  - Mitigates privilege escalation attacks that rely on stack/heap layout manipulation.
  - Enabled with `-fstack-clash-protection` compiler flag.

#### Bypass Techniques

- **Precise Heap Layout**: Carefully crafting heap allocations to avoid clash detection.
- **Small Allocations**: Using allocations smaller than the probe size to avoid triggering protection.
- **Alternative Memory Regions**: Targeting other memory regions not protected by stack clash detection.
- **Implementation Gaps**: Exploiting edge cases in the probing logic.

### Hardware‑Enforced Stack Protection

- Windows:
  - Utilizes Intel CET (specifically the Shadow Stack feature, referred to as Kernel Mode Hardware-enforced Stack Protection or KCET) and AMD Shadow Stack features.
  - Requires Hypervisor-Enforced Code Integrity (HVCI) / Virtualization-Based Security (VBS) to be enabled.
  - Provides a hardware-backed shadow stack to protect return addresses against ROP/JOP attacks.
  - Applies to kernel-mode stacks, including those associated with user-mode threads executing in kernel mode (e.g., during system calls).
  - Hardware-Enforced Stack Protection is enabled by default on compatible hardware with Windows 11, version 24H2, when VBS/HVCI is active. The `IMAGE_GUARD_SHADOW_STACK` PE flag indicates compatibility and is increasingly adopted for key binaries, with Windows components widely enabling it.

#### Bypass Techniques

- **Increased Difficulty with HVCI:** When combined with Hypervisor-Enforced Code Integrity (HVCI), bypassing hardware-enforced shadow stacks becomes significantly more challenging. HVCI leverages virtualization (Hyper-V) to protect the shadow stack's integrity via the Secure Kernel (VTL1). The Secure Kernel manages the shadow stack pointer (`VMX_GUEST_SSP` in the VMCS for VTL0) through hypercalls, preventing even kernel-mode code (VTL0) from directly tampering with it.
- **Return Address Protection:** The hardware compares the return address on the main stack with the one stored on the protected shadow stack before executing a `RET` instruction. Mismatches typically cause a fault (system crash for KCET), mitigating standard ROP/JOP attacks that rely on overwriting the return address on the main stack.
- **Secure Kernel Validation:** The Secure Kernel is involved in validating and restoring shadow stack context (e.g., during exception handling via functions like `nt!KeKernelShadowStackRestoreContext` and secure system calls like `securekernel!SkmmNtKernelShadowStackAssist`), adding another layer of integrity checking.
- **Potential (Difficult) Vectors:** Bypasses would likely require exploiting vulnerabilities in the hypervisor (Hyper-V) or the Secure Kernel itself, finding flaws in the hardware CET implementation, or developing sophisticated data-only attacks that achieve control without corrupting the stack's return addresses. These are considerably harder than bypassing software-based or unprotected hardware stack protections.
- **Limited Scope:** Like other CFI mechanisms, attacks targeting non-control data or logic bugs may still be possible if they don't violate the protected control flow.

### Pointer Authentication (ARM64)

- Linux/iOS:
  - Uses cryptographic signatures to protect pointers.
  - Mitigates attacks like Return-Oriented Programming (ROP).

#### Bypass Techniques

- **Unprotected Assembly Code**: Assembly code often lacks PAC protection.
- **Raw Function Pointers**: Recovery handlers and other mechanisms that use raw pointers.
- **Signing Gadgets**: Using existing code that signs pointers.
- **Switch Case Branches**: Unprotected indirect branches in switch case implementations.
- **Authentication Failure Handling**: Exploiting cases where authentication failures don't trigger exceptions.
- **Thread State Manipulation**: Incorrect handling of thread state during context switches.

### Intel Control‑flow Enforcement Technology (CET)

- Hardware feature providing protections against control-flow hijacking.
- Includes Shadow Stack and Indirect Branch Tracking.
- Enabled by default starting with Windows 11 build 26100 (Win11 24H2+). Any stack pivot or `ret` without a valid shadow‑stack token raises `STATUS_STACK_BUFFER_OVERRUN` (0xC0000409).
- **Detect CET:** Read the `IMAGE_DLLCHARACTERISTICS_GUARD_CF` flag in the PE header or `PEB→LdrDataTableEntry.GuardFlags`.
  - Windows: `Get-ProcessMitigation -System` shows `UserShadowStack` and `UserCetEnabled`.
  - Linux: check `cet_ss` in `/proc/cpuinfo` and `prctl(PR_SET_SHADOW_STACK_STATUS, ...)`.
- **Bypass tips for CET in shellcode:**
  1. Align the shellcode entry to a valid call target and emit `ENDBR64`/`SETSSP` before the first `ret`.
  2. Use ROP‑less staging (queued APC, `NtContinue`, or `NtTestAlert`) so the kernel performs the first return.

### Intel Indirect Branch Tracking (IBT)

- Linux/Windows:
  - Part of Intel CET that enforces legitimate indirect branch targets.
  - Requires `ENDBR32` or `ENDBR64` instructions at valid indirect call/jump destinations.
  - Prevents JOP (Jump-Oriented Programming) attacks by validating branch targets.
  - Available on Tiger Lake+ CPUs, enabled via `CET_IBT` bit in MSR.

#### Bypass Techniques

- **ENDBR Gadgets**: Finding existing code sequences that start with valid `ENDBR32/64` instructions.
- **ENDBR Spraying**: Injecting or finding multiple `ENDBR` instructions to create gadget chains.
- **Unprotected Modules**: Targeting libraries or code not compiled with IBT support.
- **Legacy Code Paths**: Exploiting code paths that bypass IBT checks (e.g., signal handlers, exception contexts).
- **Hardware Quirks**: Exploiting CPU-specific implementation differences or errata.

#### Practitioner

- Check IBT status: `cat /proc/cpuinfo | grep cet_ibt` (Linux) or inspect `cr4.cet` bit
- Compile with IBT: `-fcf-protection=branch` (GCC) or `-mcet` flag
- Binary analysis: Look for `ENDBR64` (0xF3 0x0F 0x1E 0xFA) or `ENDBR32` (0xF3 0x0F 0x1E 0xFB) instructions

### Shadow Call Stack (SCS)

- Linux:
  - Compiler-based CFI mechanism using a shadow stack to protect return addresses.
  - Helps prevent ROP attacks.
  - Ensures only signed and verified code can execute in kernel mode.
  - Blocks RWX pages and unsigned kernel callbacks when **Memory Integrity** is ON (default on 2024‑hardware).
  - Common allocation pattern for executable memory: `PAGE_READWRITE` → write payload → `NtProtectVirtualMemory` → `PAGE_EXECUTE_READ`.
  - WoW64 heaven‑gate patches to `WOW64CFG` are rejected by HVCI; favour direct 64‑bit syscalls (e.g., via `wow64log`).

#### Bypass Techniques

- **Data‑only Attacks** (no return‑address writes).
- **Hypervisor/Kernel Bugs** that corrupt GCS state.

### Guarded Control Stack (GCS)

- Linux/ARM64:
  - Hardware user‑space shadow stack on Armv9‑A CPUs, merged in Linux 6.13 and on by default in modern Android.
  - Complements KCET/CET on x86.

#### PAN‑GCS Dual Enforcement (Android 16, Armv9 Realms)

- From Android 16, GCS (shadow stack) plus Privileged Access Never (PAN) are **mandatory** for all Play‑targetSdk 34+ apps running on Armv9 Realms hardware, providing dual hardware + software enforcement.

#### Bypass Techniques

- **Data‑only Attacks** (no return‑address writes).
- **Hypervisor/Kernel Bugs** that corrupt GCS state.

### FineIBT

- Linux:
  - Enhanced CFI mechanism for indirect branch targets.
  - Provides finer-grained control flow protection than basic CFI.
  - The initial implementation was vulnerable to Branch History Injection (BHI). Hardened FineIBT with serialising `INT3` fences landed upstream in Linux 6.14

### Arbitrary Code Guard (ACG)

- Windows:
  - Prevents processes from allocating or modifying memory to be executable.
  - Mitigates attacks relying on dynamic code generation or modification.

#### Practitioner

- Check ACG: `Get-ProcessMitigation -Name process.exe | Select-Object -ExpandProperty DynamicCode`.
- WDAC policy can enforce ACG: audit with `Get-CIPolicy` and `CodeIntegrity` logs.

### Code Integrity Guard (CIG)

- Windows:
  - Restricts loading of DLLs to only those signed by Microsoft or WHQL.
  - Prevents loading of potentially malicious or untrusted libraries.

#### Practitioner

- PowerShell: `Get-ProcessMitigation -Name process.exe | Select-Object -ExpandProperty BinarySignature`.
- Event Logs: `Microsoft-Windows-CodeIntegrity/Operational` for blocked DLL loads.

### Kernel Control-Flow Guard (kCFG)

- Windows:
  - Kernel-specific implementation and enforcement of Control Flow Guard.
  - Protects against control-flow hijacking within the kernel itself.

### eXtended Flow Guard (XFG)

- Windows:
  - Debuted with Windows 11 23H2. Adds strict function‑prototype hashing to CFG, blocking many type‑confusion escapes.

#### Bypass Techniques

- **Prototype Collisions** (extremely rare).
- **Modules Without XFG** (legacy or JIT code).

### Export Address Filtering (EAF) / Import Address Filtering (IAF)

- Windows:
  - Protects module export and import tables from tampering.
  - Prevents attacks that redirect function calls by modifying these tables.

### Structured Exception Handling Overwrite Protection (SEHOP)

- Windows:
  - Protects the integrity of exception handler chains on the stack.
  - Prevents exploits that overwrite exception handlers to gain control flow.

#### Bypass Techniques

- **Modules Without SafeSEH**: A single module without protection breaks the chain.
- **ROP Chains**: Building ROP chains that don't rely on exception handlers.
- **Alternative Attack Vectors**: Targeting other vulnerable components not protected by SEHOP.
- **Unprotected Exception Handlers**: Finding handlers that are still vulnerable.

### Exploit Address Table Filtering (EAF & EAF+)

- Windows:
  - Blocks access to Export Address Tables of critical DLLs like kernel32.dll and ntdll.dll.
  - EAF+ allows specifying modules not permitted to access the EAT, particularly targeting UAF bugs.
  - Uses hardware breakpoints to filter access attempts.

#### Bypass Techniques

- **Alternative Discovery Methods**: Using different techniques to locate functions.
- **Unprotected Modules**: Targeting modules not covered by EAF protection.

### Import Address Filtering (IAF)

- Windows:
  - Ensures all functions listed in a DLL's IAT exist within the image's load address range.
  - Prevents IAT overwrite attacks.

### Virtual Table Guard

- Windows:
  - Ensures virtual function table pointers point to valid guard pages.
  - Terminates execution if invalid vptrs are detected.
  - Protects against C++ virtual function table overwrites.

### MemGC

- Windows:
  - Replacement for MemProtect technology.
  - Specifically targets mitigation of use-after-free exploitation.

### Kernel Text Read-only Region (KTRR)

- iOS:
  - Prevents modification of the iOS kernel at runtime.
  - Implements hardware-enforced read-only memory for kernel code.

#### KTRR‑v2 & FastPAC (iOS 18, A18/A19)

- Hardware‑enforced cache‑colouring prevents pointer‑authentication re‑spray, complementing traditional KTRR for stricter kernel integrity.

### Intel Memory Protection Extensions (MPX)

> [!NOTE]
> Support was removed from Linux 5.6 (April 2020) and GCC 9.1; no mainstream OS or compiler ships MPX today.

