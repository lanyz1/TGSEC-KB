## Virtualization-Based Security Enhancements

### Virtualization-Based Security (VBS)

- Windows:
  - Creates an isolated, secure memory region using hardware virtualization.
  - Protects sensitive system components and data from malware and exploits.

#### Bypass Techniques

- **Hypervisor Vulnerabilities:** Exploiting bugs in the underlying hypervisor (Hyper-V) to escape the VBS container.
- **Misconfiguration:** Weaknesses in VBS configuration or deployment.
- **Physical Access:** Hardware-level attacks (e.g., DMA attacks if not mitigated by Kernel DMA Protection).
- **Compromised Signed Components:** Exploiting vulnerabilities in trusted components running within VBS.

#### Practitioner

- Confirm VBS/HVCI: `Core isolation` settings or PowerShell `Get-CimInstance -ClassName Win32_DeviceGuard` (look for `VirtualizationBasedSecurityStatus` and `SecurityServicesConfigured`).

### AMD Secure Encrypted Virtualization – Secure Nested Paging (SEV‑SNP)

- Linux guest support since 6.11; provides full memory encryption + integrity with an SVSM.
- Shipping today in major cloud "confidential VM" SKUs.

### Intel Trust Domain Extensions (TDX)

- Guest driver landed in 6.11; host enablement queued for 6.16.
- Protects guest memory against a compromised hypervisor.

#### Practitioner

- Cloud: verify TDX/SEV‑SNP instance type (`Azure DCasv5/ECasv5`, `GCP C3`, `AWS C7g` variants); attest via platform‑specific tools (e.g., `az confcom attestation`).

### Arm Confidential Compute Architecture (CCA) Realms

- Realm VM support merged in 6.13 for Arm v9 CPUs, giving encrypted, isolated guest environments.

### Hypervisor-Enforced Code Integrity (HVCI)

- Windows:
  - Uses VBS to enforce code integrity checks on kernel-mode drivers and binaries.
  - Ensures only signed and verified code can execute in kernel mode.

#### Bypass Techniques

- **Signed Malicious Drivers:** Obtaining signing certificates (stolen or illicitly acquired) to sign malicious code.
- **Exploiting Allowed Drivers:** Finding vulnerabilities in legitimate, signed drivers already running on the system ("Bring Your Own Vulnerable Driver" - BYOVD).
- **Hypervisor Vulnerabilities:** Exploiting the underlying hypervisor (see VBS bypasses).
- **Configuration Issues:** Weaknesses in Code Integrity policies.

### Mode Based Execution Control (MBEC)

- Windows:
  - Ensures driver code can only be executed in kernel mode.
  - Available in hardware and software (emulated) forms.
  - Prevents user-mode execution of kernel code.

### Kernel Mode Code Integrity (KMCI)

- Windows:
  - Ensures kernel pages can only become executable with proper signing.
  - Enforces driver signing enforcement and vulnerable driver blocklists.
  - Implements software SMEP (Supervisor Mode Execution Prevention).
  - `DriverSiPolicy.p7b` now refreshes **weekly** via Windows Update and MEM Configuration Manager, accelerating the BYOVD blocklist cadence.

### User Mode Code Integrity (UMCI)

- Windows:
  - Ensures user mode pages can only become executable with proper signing.
  - CI validates the signaturees of EXE and DLL before allowing them to load.
  - Enforces protected processes and protected process light signature requirements
  - Enforces `/INTEGRITYCHECK` for `FIPS 140-2` modules
  - Exposed to consumers as _Smart App Control_ and businesses as _App Control for Business_.
  - Part of the Device Guard technology stack.

### Windows Defender System Guard

- Windows:
  - Monitors system integrity during boot and runtime.
  - Protects against rootkits and bootkits by verifying system integrity.

### Windows Defender Application Guard

- Windows:
  - Runs untrusted content in isolated containers.
  - Protects the host from potentially malicious websites and documents.

### Credential Guard

- Windows:
  - Uses VBS to isolate and protect credentials.
  - Prevents attacks like Pass-the-Hash or Pass-the-Ticket.

### Device Guard

- Windows:
  - Combines WDAC and virtualization-based security to lock down devices.
  - Ensures only trusted applications can run.

