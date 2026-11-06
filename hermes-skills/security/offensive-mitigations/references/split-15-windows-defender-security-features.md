## Windows Defender Security Features

### Windows Defender Application Control (WDAC)

- Windows:
  - Controls which drivers and applications are allowed to run.
  - Uses code integrity policies to prevent unauthorized code execution.

#### Practitioner

- Enumerate policies: `Get-CIPolicy -Effective` and `Get-ComputerInfo | Select WindowsProductName, WindowsVersion`.
- Validate blocklists: ensure `DriverSiPolicy.p7b` is current; check with `gpresult /r` or MEM policies.

### Exploit Protection

- Windows:
  - System-wide mitigation settings against common exploit techniques.
  - Includes heap spray allocation prevention, mandatory ASLR, etc.

#### Practitioner

- Export/import settings via `Export-ProcessMitigation` / `Set-ProcessMitigation`.
- Audit per‑process: `Get-ProcessMitigation` for DEP/ASLR/SEHOP/CFG/XFG.

### Attack Surface Reduction (ASR) Rules

- Windows:
  - Part of Windows Defender Exploit Guard, providing configurable rules.
  - Blocks specific behaviors often associated with malware or exploits (e.g., Office macro execution, script obfuscation).

#### Practitioner

- Query ASR state: `Get-MpPreference | Select -ExpandProperty AttackSurfaceReductionRules_Ids, AttackSurfaceReductionRules_Actions`.
- Enable common rules in audit first; deploy in enforced after tuning.

### Smart Screen

- Windows:
  - Analyzes files and websites for suspicious characteristics.
  - Warns or blocks potentially malicious content.

### Controlled Folder Access

- Windows:
  - Protects files and folders from unauthorized changes.
  - Helps prevent ransomware from encrypting or deleting data.

