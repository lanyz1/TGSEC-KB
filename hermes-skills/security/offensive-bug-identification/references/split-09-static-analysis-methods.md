## Static Analysis Methods

Static analysis examines code without execution to identify potential vulnerabilities.

### Manual Code Review

- Installing the target application and examining its structure
- Enumerating the ways to feed input to it
- Examine the file formats and network protocols that the application uses
- Locating logical vulnerabilities or memory corruptions
- For Windows-specific techniques, see [Windows Kernel](/exploit/windows-kernel.md)
- For Linux-specific techniques, see [Linux](/exploit/linux.md)

### Patch Diffing

Patch diffing compares vulnerable and patched versions of binaries to identify security changes.

#### What is Patch Diffing

Patch diffing is a technique to identify changes across versions of binaries related to security patches. It compares a vulnerable version of a binary with a patched one to highlight the changes, helping to discover new, missing, and interesting functionality across versions.

##### Benefits

- **Single Source of Truth**: Without a CVE blog post or sample POC, a patch diff can be the only source of information to determine changes and deduce the original issue.
- **Vulnerability Discovery**: While understanding the original issue, you may discover additional vulnerabilities in the troubled code area.
- **Skill Development**: Patch diffing provides focused practice in reverse engineering and helps build mental models for various vulnerability classes.

##### Challenges

- **Asymmetry**: Small source code changes can drastically affect compiled binaries.
- **Finding Security-Related Changes**: Security patches often include other changes like new features, bug fixes, and performance improvements.
- **Minimizing Noise**:
  - Diff the correct binaries to avoid analyzing unrelated updates
  - Reduce the time delta between compared versions
  - Use binary symbols when available to add precision to comparisons

#### Tools

- IDA Pro with plugins like DarunGrim and Diaphora
- BinDiff Works with analysis output from IDA or Ghidra
- [Ghidriff](https://github.com/clearbluejar/ghidriff): Ghidra binary diffing engine
- Radare2 (radiff2)
- Ghidra Version Tracking Tool
- Ghidra 11 built-in Partial Match Correlator

#### Patch Diffing Workflow

The process of patch diffing typically follows these steps:

1. **Preparation**
   - Create a diffing session
   - Load binary versions (vulnerable and patched)
   - Ensure binaries pass preconditions
   - Run auto-analysis on both binaries

2. **Evaluation**
   - Run correlators to find similarities
   - Generate associations between binaries
   - Evaluate matches between functions
   - Accept matching functions
   - Analyze differences until sufficient understanding is reached

3. **Function Analysis**
   - **Identify new functions**: Functions in the patched binary with no match in the original
   - **Identify deleted functions**: Functions in the original binary with no match in the patched version
   - **Identify changed functions**: Functions that exist in both versions but have been modified
   - Focus on functions with security relevance (often indicated by their names or based on CVE descriptions)

4. **Interpreting Results**
   - New functions often indicate added security checks or validation
   - Changed functions may show modified logic for handling edge cases
   - Correlate changes with public CVE information when available
   - Remember that patches are not necessarily atomic - multiple issues may be fixed in one update

When using Ghidra's Version Tracking:

- Use "Show Only Unmatched Functions" filter to identify new or deleted functions
- Look for functions with a similarity score below 1.0 to find modified functions
- Examine the modified functions to understand what security checks were added

Starting with Ghidra 11 (December 2024) a built-in _Partial Match Correlator_ covers most PatchDiffCorrelator use-cases; install the plugin only if you need bulk-mnemonics scoring.

#### Case Study: 7‑Zip Symlink Path Traversal

- Target: 7‑Zip 24.09 (vulnerable) → 25.00 (fixed)
- File of interest: `CPP/7zip/UI/Common/ArchiveExtractCallback.cpp`
- High‑signal edits: absolute‑path detection and link‑path validation for WSL/Linux symlinks converted on Windows.

##### Minimal security‑relevant diff (simplified):

```cpp
-bool IsSafePath(const UString &path)
+static bool IsSafePath(const UString &path, bool isWSL)
{
  CLinkLevelsInfo levelsInfo;
-  levelsInfo.Parse(path);
+  levelsInfo.Parse(path, isWSL);
  return !levelsInfo.IsAbsolute
      && levelsInfo.LowLevel >= 0
      && levelsInfo.FinalLevel > 0;
}

+bool IsSafePath(const UString &path);
+bool IsSafePath(const UString &path)
+{
+  return IsSafePath(path, false); // isWSL
+}

-void CLinkLevelsInfo::Parse(const UString &path)
+void CLinkLevelsInfo::Parse(const UString &path, bool isWSL)
{
-  IsAbsolute = NName::IsAbsolutePath(path);
+  IsAbsolute = isWSL ? IS_PATH_SEPAR(path[0]) : NName::IsAbsolutePath(path);
  LowLevel = 0;
  FinalLevel = 0;
}
```

##### Root cause (logic):

- Linux/WSL symlink data containing a Windows‑style path (e.g., `C:\...`) was treated as relative by the Linux absolute‑path check, setting `linkInfo.isRelative = true`.
- `SetFromLinkPath` prefixed the symlink’s zip‑internal directory when building `relatPath`, letting `IsSafePath(relatPath)` pass despite an absolute Windows target.
- A subsequent “dangerous link” guard checked `_item.IsDir`; non‑directory symlinks skipped the validation.
- Result: symlink creation to arbitrary absolute Windows paths; extracted files written into the link target.

##### Practical triage checklist:

- Search this file for: `IsSafePath`, `CLinkLevelsInfo::Parse`, `SetFromLinkPath`, `CloseReparseAndFile`, `FillLinkData`, `CLinkInfo::Parse`, `_ntOptions.SymLinks_AllowDangerous`.
- Verify absolute‑path detection across OS semantics (Linux vs Windows) and that relative/absolute status cannot be desynced by mixed‑style paths.
- Ensure “dangerous link” checks run for both files and directories; avoid `_item.IsDir` short‑circuiting validation for file symlinks.
- Confirm `IsSafePath` evaluates the final target path after concatenations; normalize before validation.

##### Quick repro (Windows, developer mode or elevated):

- Create zip structure:
  - `data/link` → symlink to `C:\Users\<USER>\Desktop`
  - `data/link\calc.exe` → payload file
- If `link` is extracted first, subsequent writes follow the symlink into the absolute target directory.

#### Apple Patch Diffing

- Identify a CVE of interest
- Download corresponding IPSW and update and N-1
  - use [ipsw.me](https://ipsw.me/) to download those files
  - convert the downloaded `.ipsw` to `.zip`
- Determine changes for update
  - you can use [IPSW tool](https://github.com/blacktop/ipsw) to download and diff
- Map binaries to CVE
- Extract the related file(s)
- Diff the binaries
  - In Ghidra set Decompiler Parameter ID to true
  - Leverage [IDAObjectTypes](https://github.com/PoomSmart/IDAObjcTypes)
- Root cause the vulnerability

```bash
# Downloading the correct IPSWs
ipsw download --device Macmini9,1 -V -b 23A344
ipsw download --device Macmini9,1 -V -b 23B74

# Comparing two different IPSWs
ipsw diff UniversalMac_14.0_23A344.ipsw UniversalMac_14.1_23B74.ipsw

# What is inside the DSC
ipsw extract -d IPSW

# Extracting files
ipsw extract -f -p file

# Extracting specific architecture file
ipsw macho lipo Contacts
```

#### Windows 11 Patch Diffing

This checklist mirrors the Apple IPSW workflow but uses Microsoft tooling and build numbers.

1. Identify the target update
   - Open **Settings → Windows Update → Update history** or consult the Windows Release Health dashboard to note the **KB** and **OS build** numbers (e.g., _KB5037778 → build 22631.3525_).
   - Record the previous build you want to diff against (e.g., _22631.3447_).

2. Collect the binaries

```bash
winbindex download tcpip.sys 10.0.22631.3447 10.0.22631.3525

mkdir pre,post
wget -Uri https://www.catalog.update.microsoft.com/Download.aspx?q=KB5037778 -OutFile kb.msu
expand -F:* .\kb.msu .\post
# repeat for the older KB into .\pre
# Download both *UUP* bundles, then run
uup_download_windows.cmd --extract
# and copy changed PE files to *pre* / *post*
```

3. Fetch matching symbols

```powershell
# Requires Debugging Tools for Windows
foreach ($ver in '3447','3525') {
    symchk /r .\$ver /s SRV*https://msdl.microsoft.com/download/symbols
}
```

4. Load in the disassembler
   - Open _tcpip.sys_ from both **pre** and **post** folders in **IDA 8+** or **Ghidra 11**; ensure PDB symbols resolve.
   - Save the IDA databases (e.g., `tcpip_3447.i64`, `tcpip_3525.i64`).

5. Run the diff
   - **BinDiff 7**: _Tools → BinDiff → Diff Database…_ and select the two IDBs to generate a `.BinDiff` report.
   - **Ghidriff** (headless):
     ```bash
     ghidriff diff pre/tcpip.sys post/tcpip.sys -o tcpip.diff
     ```

6. Triage the results
   - Sort by _Similarity %_ ascending; investigate anything below **95 %**.
   - Focus on functions with names like `Validate`, `Parse`, `Copy`, `Check`, or protocol‑specific handlers (`IppReceiveEsp`, `Ipv6pFragmentReassemble`, etc.).
   - Determine whether changes add bounds checks, size validations, or privilege checks.

7. Validate in a lab VM
   - Snapshot two Windows 11 VMs (build **3447** and **3525**).
   - Attach WinDbg (kernel mode) using `bcdedit /dbgsettings net hostip:<IP> port:<PORT>`.
   - Reproduce the issue against the **pre‑patch** VM; confirm no crash or breakpoint triggers in the **post‑patch** VM.

8. Automate monthly
   - Schedule a PowerShell script that, every Patch Tuesday (second Tuesday), downloads the latest Cumulative Update, extracts changed PE files, retrieves symbols, and launches a headless **Diaphora** diff.
   - Email the generated HTML report to quickly spot new attack surface.

> [!TIP]
> For large modules like **ntoskrnl.exe**, diff only the `.text` section to save RAM:  
> bindiff --primary ntoskrnl_pre.i64 --secondary ntoskrnl_post.i64 --section .text

#### Linux Kernel Patch Diffing

Patch‑diffing Linux kernels is often faster at the source level, but for binary‑only targets (vendor kernels, modules) function‑level diffing is still practical.

1. Identify target builds
   - Note distro and kernel build (e.g., Ubuntu `6.8.0-47-generic`, RHEL `5.14.0-503`).
   - Capture both pre and post versions (package changelogs or CVE bulletins help).

2. Fetch kernel images and debug info
   - Ubuntu/Debian:
     ```bash
     # Discover versions
     apt list -a linux-image-generic | cat
     # Download image + modules dirs (repeat for both versions)
     apt-get download linux-image-unsigned-<ver>-generic linux-modules-<ver>-generic
     # Debug symbols via debuginfod (preferred to ddebs)
     export DEBUGINFOD_URLS="https://debuginfod.ubuntu.com https://debuginfod.debian.net"
     ```
   - Fedora/RHEL/CentOS:
     ```bash
     dnf download kernel-core-<ver> kernel-debuginfo-<ver>
     rpm2cpio kernel-core-<ver>.rpm | cpio -idmv
     rpm2cpio kernel-debuginfo-<ver>.rpm | cpio -idmv
     ```

3. Extract `vmlinux`

   ```bash
   # If only vmlinuz is present, use the upstream helper
   /usr/src/linux-headers-<ver>/scripts/extract-vmlinux /boot/vmlinuz-<ver> > vmlinux-<ver>
   # Or take vmlinux directly from debuginfo package tree
   ```

4. Identify changed modules quickly

   ```bash
   # Compare module trees (pre vs post)
   rsync -rcn --delete /lib/modules/<pre>/ /lib/modules/<post>/ | grep -E "\.ko$" | sed 's/^/chg: /'
   ```

5. Function‑level binary diff
   - Open `vmlinux-<pre>` and `vmlinux-<post>` in Ghidra 11/IDA 8 and run Diaphora/BinDiff/Ghidriff.
   - For hot subsystems (e.g., `io_uring`, `net/ipv6`, `fs/overlayfs`), diff only the relevant `.ko` pairs to reduce noise.

6. Source‑level triage (when sources are available)

   ```bash
   # Ubuntu example: unpack both source trees, then
   git diff --no-index -- function.c.orig function.c.patched | less
   # Or use diffoscope for enriched reports
   ```

7. Symbolization and crash mapping (cheat‑sheet)

   ```bash
   # Decode kernel oops backtraces to lines
   ./scripts/decode_stacktrace.sh vmlinux /lib/modules/<ver>/build < dmesg.log
   # Map PC to file:line quickly
   addr2line -e vmlinux-<ver> 0xffffffff81234567
   ```

> [!TIP]
> For modern distros built with Clang: KCFI and fine‑grained CFI thunks create many small stub changes; filter by real function body deltas to focus on security‑relevant logic.

> [!NOTE]
> Syzkaller routinely bisects kernel bugs; consult syzbot reports for reproducers and fix commits, then confirm your diff isolates the same region before deeper RE.

#### Kernel network parser identification heuristics (SMB2-inspired, broadly applicable)

##### Cross-field invariants (length/offset/next)

- Always validate `(offset + length) <= remaining_buffer` and `<= total_buffer` using a widened type (e.g., `u64`) before arithmetic; reject on overflow with `check_add_overflow()`/`array_size()` helpers.
- For chained entries with a `next` field, assert: `next >= sizeof(entry_header)`, `next <= remaining_buffer`, and that pointer advancement actually makes progress. For entries carrying sub-lengths (e.g., `name_len`, `value_len`), assert `header + name_len + value_len <= next`.
- Do not cast to a struct until the full header is present and aligned; gate recasts with a prior `buf_len` check.

##### Fixed-size buffers vs variable-length payloads

- Ban unbounded copies/crypto/decompression into fixed-size arrays. Require `len <= sizeof(array)` (or clamp with `min_t()` and bail) when writing into in-struct arrays.
- Crypto transforms are just writes with extra steps: if using ARC4/AES helpers that copy `len` bytes into a fixed buffer (e.g., session keys), bound `len` against a named maximum constant and prefer allocating a buffer sized from validated `len`.

##### Type/width hazards

- Normalize parser math to a wide unsigned type before comparisons; avoid truncating `u32/u64` fields into `u16` for size checks. Favor `size_t/u64` for `offset+len` arithmetic, then compare to `buf_len` of the same width.

##### Loop structure around `next`

- Pattern to flag: `e = (struct entry *)((char *)e + next);` without a preceding block that revalidates `buf_len` and the entry’s internal sub-lengths.
- Ensure a break condition on exhaustion and reject zero/negative progress values to avoid infinite loops or pointer stagnation.

##### Allocation-size correlation

- When parser-controlled `len` influences a subsequent write into an object from a fixed SLUB cache (e.g., `kmalloc-512`), ensure the write length is bounded by the destination object field, not just the incoming length.

##### Patch-diff signals to prioritize

- Newly added guards like `if (len > CONST) return -EINVAL;`, `if (buf_len < sizeof(struct foo)) return -EINVAL;`, or conversions to `min_t(size_t, len, sizeof(...))`.
- Insertions of `check_add_overflow(offset, len, &sum)` or `array_size(n, sz)` helpers in hot parse paths.

##### Static query seeds (Semgrep/CodeQL), to tune per codebase

- Unbounded copies into struct fields:
  ```yaml
  rules:
    - id: c-fixed-array-unbounded-copy
      languages: [c, cpp]
      patterns:
        - pattern: memcpy($DST, $SRC, $LEN)
        - pattern-inside: |
            struct $S { ... char $BUF[$N]; ... };
            ...
            $DST = &...->$BUF
        - pattern-not: memcpy($DST, $SRC, MIN($LEN, sizeof(*$DST)))
      message: Unbounded copy into fixed-size struct field
      severity: WARNING
  ```
- Dangerous `next`-driven pointer arithmetic without bounds checks:
  ```yaml
  - id: c-parser-next-missing-bounds
    languages: [c, cpp]
    pattern: |
      $E = (struct $T *)((char *)$E + $NEXT);
    message: Parser advances by user-controlled 'next' without prior buf_len/sizeof checks
    severity: WARNING
  ```
- Crypto/decompression writes to fixed arrays (seed with function names in your tree, e.g., `*_crypt`, `*_decrypt`, `decompress_*`).

##### Dynamic confirmation (cheap)

- Grammar fuzz small invariants: send `next < header`, `next > remaining`, `name_len + value_len > next`, and `len > MAX_CONST` variants; expect `-EINVAL`/reject. If not, investigate.
- Use TUN/TAP + KCOV to drive packet/SMB request paths; enable KASAN/KMSAN to surface overflows/leaks early.

##### Reference (motivating example)

- Lessons distilled from a 2025 ksmbd remote chain writeup combining a fixed-buffer overflow in NTLM auth with an EA `next` validation issue — see Will’s Root: Eternal‑Tux: KSMBD 0‑Click RCE (`https://www.willsroot.io/2025/09/ksmbd-0-click.html`).

#### Case Study: EvilESP Vulnerability (CVE-2022-34718)

This case study demonstrates real-world patch diffing to identify a Windows TCP/IP RCE vulnerability.

##### Vulnerability Overview

- CVE-2022-34718: Critical RCE in `tcpip.sys` discovered in September 2022
- An unauthenticated attacker could send specially crafted IPv6 packets to Windows nodes with IPsec enabled
- Affects the handling of ESP (Encapsulating Security Payload) packets in IPv6 fragmentation

##### Patch Diffing Process

1. **Binary Acquisition**
   - Used Winbindex to obtain sequential versions of `tcpip.sys` (pre-patch and post-patch)
   - Loaded both files in Ghidra with PDB symbols

2. **Diff Analysis**
   - Used BinDiff to compare the binaries
   - Identified only two functions with less than 100% similarity: `IppReceiveEsp` and `Ipv6pReassembleDatagram`

3. **Code Analysis**
   - **Ipv6pReassembleDatagram**: Added bounds check comparing `nextheader_offset` against the header buffer length
   - **IppReceiveEsp**: Added validation for the Next Header field of ESP packets

4. **Root Cause Identification**
   - Found an out-of-bounds 1-byte write vulnerability
   - ESP Next Header field is located after the encrypted payload data
   - A malicious packet could cause `nextheader_offset` to exceed the allocated buffer size

_(Update: Server 2022 build 20349.2300, May 2024, hardened this code path; the original PoC needs a 2-byte pad tweak to reproduce the crash.)_

##### Exploitation

- Required setting up IPsec security association on the victim
- Created fragmented IPv6 packets encapsulated in ESP
- Controlled the offset of the out-of-bounds write through payload and padding size
- Value written is controllable via the Next Header field
- Limited to writing to addresses that are 4n-1 aligned (where n is an integer)
- Initially achieved DoS with potential for RCE through further exploitation

##### Lessons Learned

- Binary patch diffing effectively identified the vulnerability location and nature
- Understanding protocol specifications (ESP and IPv6 fragmentation) was critical
- Simple buffer checks are still overlooked in complex networking code
- Even limited primitives (single byte overwrite at constrained offsets) can be dangerous
- For modern exploitation techniques, see [Modern Samples](/exploit/modern-samples.md)
- For mitigation bypass techniques, see [Modern Mitigations](/exploit/modern-mitigations.md)

When applying patch diffing to networking protocols:

1. Understand the protocol specifications thoroughly
2. Look for missing bounds checks in data processing
3. Pay attention to buffer size calculations
4. Check for proper validation of protocol field values and locations
5. Consider evasion techniques for exploit deployment - see [EDR](/exploit/edr.md)
6. Specs: ESP (RFC 4303) and IPv6 (RFC 8200) are essential references when reasoning about header placement and bounds

#### Semi-Automatic Patch Diffing

- Use [WinbIndex](https://winbindex.m417z.com/) to download the changed binary and then use [BinDiff](https://www.zynamics.com/bindiff.html) or [Ghidriff](https://github.com/clearbluejar/ghidriff) to actually see the diff itself
- You can also use [Diaphora](https://github.com/joxeankoret/diaphora) instead of BinDiff

#### Manual Patch Diffing

- Microsoft releases patches on the second Tuesday of each month
- For Windows you can go to [update catalog](https://www.catalog.update.microsoft.com/Search.aspx) and search for the product version (for example `2022-10 x64 "Windows 10" 22H2`)
- Try to look for smaller updates

```shell
mkdir 2022-09
mv *.msu 2022-09
cd 2022-09
mkdir extract
mkdir patch
expand -F:* .\*.msu .\extract
expand -F:* .\extract\<largest>.cab .\patch
expand -F:* .\patch\<largest>.cab .\patch
expand -F:* .\patch\Cab_* .\patch\
```

You can use [Patch Extract](https://gist.github.com/abzcoding/f6191c3aa9ca6d019f360b429d6b510f) instead

```shell
gci -Recurse c:\windows\WinSxS\ -Filter ntdll.dll
# copy the biggest file somewhere
.\delta_patch.py -i .\NTDLL\ntdll.dll -o ntdll.2020-10.dll .\NTDLL\r\ntdll.dll .\2020-10\x64\ntdll_<stuff>\f\ntdll.dll
.\delta_patch.py -i .\NTDLL\ntdll.dll -o ntdll.2020-11.dll .\NTDLL\r\ntdll.dll .\2020-11\x64\ntdll_<stuff>\f\ntdll.dll
```

Open unpatched version in IDA as the primary and the second, after that use BinDiff add-on to find the differences between them
then right click on a different matched function and see the visual diff in bin diff
also you can uncheck proximity browsing to see the entire function
look at red blocks and then yellow blocks

With patch clean script you can only see the actual changed files

### Static Analysis Tools

#### IDA Pro and Rust Tools for Vulnerability Research

- [rhabdomancer](https://github.com/0xdea/rhabdomancer): IDA Pro headless plugin that locates calls to potentially insecure API functions in binary files
  - Helps auditors backtrace from candidate points to find pathways allowing access from untrusted input
  - Generates JSON/SARIF reports containing vulnerable function calls and their details
  - Written in Rust using IDA Pro 9 idalib and Binarly's idalib Rust bindings

- [haruspex](https://github.com/0xdea/haruspex): IDA Pro headless plugin that extracts pseudo-code generated by IDA Pro's decompiler
  - Exports pseudo-code in a format suitable for IDEs or static analysis tools like Semgrep/weggli
  - Creates individual files for each function with their pseudo-code
  - Can be used as a library by third-party crates

- [augur](https://github.com/0xdea/augur): IDA Pro headless plugin that extracts strings and related pseudo-code from binary files
  - Stores pseudo-code of functions that reference strings in an organized directory tree
  - Helps trace how strings are used within the application
  - Complements other reverse engineering tools

#### Modern Static Analysis Tools

- **Semgrep Pro** – Cloud-augmented SAST with custom rule sharing, LLM-assisted rule writing
- **CodeQL** – GitHub's semantic code analysis, excellent for variant analysis
- **Weggli** – Fast semantic search for C/C++ (better than grep for code patterns)
- **Joern** – Code property graph analysis for vulnerability discovery
- **Ghidra 11.2+** – Built-in ML-powered function signature recognition
- **Binary Ninja 4.0** – Cloud collaboration, improved HLIL decompilation
- **Cutter** – Rizin GUI with built-in decompiler integration

#### Deprecated Tools (Avoid)

- **Intel Pin** → Use DynamoRIO or Frida (Pin is sustain-only mode)
- **WinAFL** → Use AFL++ 4.x (integrated Windows support)
- **Old BinDiff** → Use BinDiff 8 or Ghidriff

For more details about these tools: [Streamlining vulnerability research with IDA Pro and Rust](https://security.humanativaspa.it/streamlining-vulnerability-research-with-ida-pro-and-rust/)

