## Day 5: Drivers, Filesystems, and Boot Vulnerabilities

- **Goal**: Understand vulnerabilities in kernel drivers, filesystem implementations, and boot security mechanisms.
- **Activities**:
  - _Reading_:
    - [The Linux Kernel Module Programming Guide](https://sysprog21.github.io/lkmpg/#character-device-drivers)
    - [Linux Driver Verification Project](http://linuxtesting.org/ldv)
    - [Windows Driver Security Checklist](https://learn.microsoft.com/en-us/windows-hardware/drivers/driversecurity/)
  - _Online Resources_:
    - [UEFI Secure Boot](https://uefi.org/specs/UEFI/2.10/32_Secure_Boot_and_Driver_Signing.html)
    - [Dirty Pipe Explanation](https://dirtypipe.cm4all.com/)
  - _Concepts_:
    - Driver IOCTL attack surfaces
    - Filesystem logic flaws and permission bypasses
    - BYOVD (Bring Your Own Vulnerable Driver) technique
    - Secure Boot bypass vulnerabilities
    - Pipe and splice operation security

### IOCTL/Syscall Handler Vulnerabilities

**What It Is**: Faulty user↔kernel marshalling and validation in system calls or device control paths (e.g., Windows `DeviceIoControl`, Linux `ioctl`).

**Case Study - CVE-2023-21768 (Windows AFD.sys Buffer Size Confusion)**:

- **The Bug**: The Windows Ancillary Function Driver (AFD.sys), which handles socket operations, had a buffer size confusion vulnerability in its IOCTL handler. When processing `IOCTL_AFD_SELECT` requests, the driver failed to properly validate the relationship between user-provided buffer size and the actual structure size.
- **The Attack**: An attacker could call `DeviceIoControl()` with a specially crafted input buffer where the declared size didn't match the actual data size. The driver would allocate a buffer based on one size value but copy data based on another, leading to an out-of-bounds write in kernel pool memory.
- **The Impact**: Local privilege escalation from standard user to SYSTEM. The OOB write primitive was used to corrupt adjacent kernel objects in the pool, hijacking control flow. Exploited in the wild before patching.
- **The Fix**: Microsoft KB5022845 added strict validation ensuring user-provided length matched expected structure size, used `ProbeForRead()` to validate user pointers, and implemented additional bounds checking before memory operations.
- **Why It Matters**: IOCTL/syscall handlers are common attack vectors due to size/bounds confusion, trusting user pointers without probing, double-fetch issues, and incomplete pointer chasing. These lead to LPE via UAF/OOB/arbitrary write and sandbox escapes.

### Driver and Peripheral Interface Vulnerabilities

**What They Are**: Validation failures and memory corruption in device drivers handling USB, HID, audio/video, network interfaces, and legacy hardware. Drivers represent a massive attack surface due to complex state machines, insufficient input validation, and third-party code quality issues.

**Case Study - CVE-2024-53150 (Linux ALSA USB-Audio OOB Read)**:

- **The Bug**: The Advanced Linux Sound Architecture (ALSA) USB audio driver failed to properly validate the bLength field of USB device descriptors when traversing clock descriptors. When parsing malformed audio streaming interface descriptors with shorter-than-expected bLength values, the driver could read beyond allocated buffer boundaries.
- **The Attack**: An attacker with physical access or USB emulation capabilities (e.g., BadUSB, malicious USB device, or compromised USB hub) could craft a USB audio device with bogus descriptors containing shortened bLength fields. When the device enumerated, the kernel driver would traverse these descriptors without proper bounds checking, leading to out-of-bounds reads.
- **The Impact**: Local information disclosure and potential privilege escalation from user to root. The out-of-bounds read primitive could leak sensitive kernel memory contents, including addresses to defeat KASLR. Added to CISA's Known Exploited Vulnerabilities catalog in April 2025.
- **The Fix**: Linux kernel 6.12.2 (December 2024) added comprehensive descriptor validation, checking bLength against sizeof() for clock source and clock multiplier descriptors, and validating array bounds for clock selector descriptors before traversal.
- **Why It Matters**: Driver vulnerabilities dominate Windows exploits (20+ vulnerabilities in drivers like RasMan since 2022) and are increasingly targeted in Linux. USB/HID/audio/video drivers are particularly vulnerable due to complex parsing requirements and are exploitable via physical access or emulated devices.

**Bring Your Own Vulnerable Driver (BYOVD)**:

**What It Is**: A technique where attackers abuse legitimate but vulnerable signed drivers to gain kernel-level access on Windows systems. While not a vulnerability per se, BYOVD is widely used in exploit chains.

**Case Study Context - Lazarus Group Driver Abuse**:

- **The Technique**: Attackers drop a legitimate but vulnerable signed driver (e.g., old versions of ASUS, Gigabyte, or MSI drivers) that Windows will load due to valid signature.
- **The Attack**: Once loaded, the vulnerable driver provides arbitrary kernel read/write primitives through its IOCTL interface. Attackers use this to disable security features (PatchGuard, AV/EDR), load unsigned drivers, or escalate privileges.
- **The Evolution**: Microsoft's response included Driver Blocklist expansion and Vulnerable Driver Blocklist. Advanced groups like Lazarus shifted from BYOVD to direct zero-day kernel exploits after 2023 due to increased detection.
- **Defense**: Enable Vulnerable Driver Blocklist (HVCI/Memory Integrity), monitor for unusual driver loads, implement application control policies.

**Win32k.sys Graphics/Window Manager Issues**:

**Case Study - CVE-2025-24983 (Win32k Use-After-Free EoP)**:

- **The Bug**: A use-after-free in the Windows Win32k kernel subsystem allowed an authorized local attacker to elevate privileges. Classified under CWE‑416, it was added to CISA’s KEV in March 2025.
- **The Attack**: By manipulating window/GUI objects via Win32k APIs, a local attacker could trigger the UAF and corrupt kernel memory to achieve SYSTEM.
- **The Impact**: Local privilege escalation to SYSTEM.
- **The Fix**: Microsoft updated Win32k to harden object lifetime handling and mitigate the UAF condition.
- **Why It Matters**: Win32k remains a frequent target due to complex GUI state and broad exposure to unprivileged code.

### Filesystem and Mounting Vulnerabilities

**What They Are**: Logic flaws in filesystem handling, mounting operations, and file metadata processing. Increasingly exploited for privilege escalation in multi-user and container environments.

**Case Study - CVE-2023-0386 (OverlayFS Privilege Escalation)**:

- **The Bug**: The Linux OverlayFS implementation failed to properly validate file capabilities when copying files from lower to upper layers. The vulnerability allowed bypassing user namespace UID/GID mapping for setuid/setgid binaries.
- **The Attack**: An attacker in an unprivileged container could create a specially crafted OverlayFS mount structure where setuid binaries from the lower layer retained elevated privileges when copied to the upper layer, despite being in a user namespace.
- **The Impact**: Container escape and privilege escalation from unprivileged user to root on the host system. Affected Kubernetes clusters, Docker environments, and systems using OverlayFS for container storage.
- **The Fix**: Linux kernel 6.2+ added proper capability validation during file copy operations, ensuring user namespace mappings are respected and setuid/setgid bits are stripped appropriately.
- **Why It Matters**: Filesystem logic flaws are common in Linux (OverlayFS, FUSE, NFS) and provide reliable privilege escalation paths in containerized environments. Improper ownership inheritance and permission checks are recurring patterns.

**Pipe/Stream Splicing Issues**:

**Case Study - CVE-2022-0847 (Dirty Pipe)**:

- **The Bug**: The Linux kernel's pipe implementation failed to properly initialize the `PIPE_BUF_FLAG_CAN_MERGE` flag when splicing pages from page cache into pipes. This allowed overwriting data in read-only files by splicing modified pages back.
- **The Attack**: An attacker could open a read-only file (e.g., `/etc/passwd`), use `splice()` to create a pipe containing pages from that file, modify the pipe buffer, then splice it back to overwrite the original file contents.
- **The Impact**: Local privilege escalation from any user to root by overwriting `/etc/passwd` or other privileged files. Extremely reliable exploitation requiring minimal permissions. Affected Linux kernels 5.8+ through 5.16.11.
- **The Fix**: Linux kernel 5.16.11+ properly initializes pipe buffer flags and prevents splicing back to read-only files.
- **Why It Matters**: Pipe and splice operations are complex kernel mechanisms with subtle state management requirements. Dirty Pipe demonstrated how initialization bugs can lead to powerful arbitrary file write primitives.

**Malicious File/Mount Handling**:

**Case Study - CVE-2025-24071 (Windows File Explorer Credential Leak)**:

- **The Bug**: Windows File Explorer improperly handled `.library-ms` files, which are XML-based library definition files. When parsing malicious `.library-ms` files with crafted UNC paths, Explorer would automatically attempt authentication to remote SMB shares.
- **The Attack**: An attacker could create a `.library-ms` file pointing to `\\attacker-server\share`. When a user browsed a folder containing this file (even without opening it), Explorer would send NTLMv2 authentication credentials to the attacker's server.
- **The Impact**: Credential harvesting via automatic NTLM authentication. Attacker captures NTLMv2 hashes for offline cracking or relay attacks. Similar issues exist with NTFS features allowing chained RCE (CVE-2025-24993).
- **The Fix**: Windows patches restrict automatic network authentication during file parsing and add warnings for UNC paths in library files.
- **Why It Matters**: File format parsers in GUI components often have network access capabilities. Credential leaks through automatic authentication are valuable for lateral movement in enterprise environments.

### Boot and Security Feature Bypass Vulnerabilities

**What They Are**: Vulnerabilities that bypass boot-time security protections or kernel hardening features. Emerging prominently in 2024-2025 exploits for persistence and rootkit deployment.

**Case Study - CVE-2025-47827 (Secure Boot Bypass)**:

- **The Bug**: In IGEL OS before v11, the `igel-flash-driver` module improperly verified cryptographic signatures, allowing a crafted SquashFS root filesystem to be mounted and bypass Secure Boot protections.
- **The Attack**: With physical access or admin control, an attacker could leverage the signature verification flaw during boot to load untrusted kernel code.
- **The Impact**: Complete system compromise with kernel-level persistence. Enables evil-maid attacks, bypasses BitLocker, Windows Defender, and EDR solutions. Rootkit survives OS reinstallation if firmware is not reflashed.
- **The Fix**: Vendor guidance for IGEL OS v10 is limited due to end-of-support; mitigation guidance focuses on revocation/DBX updates and upgrading to supported versions enforcing strict signature validation.
- **Why It Matters**: Secure Boot bypasses enable persistent compromise below the OS level. Physical access scenarios (stolen laptops, interdiction) and supply chain attacks leverage these vulnerabilities for long-term persistence.

**Kernel Hardening Evasion**:

**Case Study - CVE-2025-53136 (Windows Kernel Pointer Leak)**:

- **The Bug**: Multiple Windows kernel functions exposed kernel memory addresses through information disclosure vulnerabilities. Specifically, NtQuerySystemInformation and related APIs leaked kernel heap and pool addresses.
- **The Attack**: An attacker could call specific system information query APIs to leak kernel addresses, defeating Kernel Address Space Layout Randomization (KASLR). These leaks are chained with other vulnerabilities (UAF, OOB write) to reliably exploit kernel bugs.
- **The Impact**: Information disclosure enabling exploitation of kernel vulnerabilities. KASLR bypass is a prerequisite for modern kernel exploitation. Often combined with vulnerabilities like CVE-2023-21768 (AFD.sys) for full privilege escalation chains.
- **The Fix**: Microsoft added restrictions to information query APIs, reducing precision of returned information or requiring elevated privileges for sensitive queries.
- **Why It Matters**: Kernel hardening features (KASLR, SMEP, SMAP, Control Flow Guard) require information leaks to bypass. Pointer leaks are critical primitives in exploit chains and are actively targeted by attackers.

### Key Takeaways

1. **Drivers are high-risk**: expansive IOCTL surfaces and complex descriptor parsing create memory corruption and arbitrary read/write.
2. **IOCTL/syscall handlers are high-value targets**: Size confusion and function pointer validation failures provide powerful LPE primitives without requiring traditional buffer overflows.
3. **Concurrency bugs enable sophisticated exploits**: Double-fetch, race conditions and locking misuse are difficult to reproduce but provide reliable exploitation when timing is controlled.
4. **Arbitrary write is the ultimate primitive**: Whether achieved through IOCTL handlers, PreviousMode corruption, or RCU misuse, arbitrary kernel write enables privilege escalation, security callback disabling, and rootkit deployment.
5. **User namespaces expand attack surface**: Many kernel vulnerabilities (netfilter, io_uring) become exploitable from unprivileged contexts when user namespaces grant capabilities like `CAP_NET_ADMIN`.
6. **Defense requires atomic operations**: TOCTOU vulnerabilities demonstrate that check-then-use patterns are inherently racy; atomic check-and-use operations, proper locking, and defensive copying are essential.
7. **Physical/adjacent vectors matter**: USB/Thunderbolt/emulated devices are attacker-controlled input.

### Discussion Questions

1. Which testing strategies most effectively surface IOCTL handler bugs in complex drivers?
2. Why are IOCTL handlers such prevalent sources of kernel vulnerabilities, and what validation patterns should be mandatory for all IOCTL implementations?
3. How can developers design IOCTL interfaces to prevent size confusion and arbitrary function call vulnerabilities while maintaining performance and flexibility?
4. What monitoring best detects Secure Boot tampering and unexpected kernel module loads?
5. Which container runtime settings most reduce OverlayFS and mount attack viability?
6. How should organizations treat removable and emulated devices to minimize driver-exposed risk?

