## Detection Methods

### AV Signature Scanning

- Scans files using known signatures (YARA rules)
- Typically targets loaders and droppers
- Primarily static analysis of files on disk

### AV Emulation

- Runs suspicious programs in a simulated environment
- Triggers on behaviors without executing real code
- Used to detect obfuscated malware

### Usermode Hooks

- EDR hooks critical API calls in userspace (ntdll.dll)
- Monitors process creation, memory allocations, and network operations
- Allows for inspection before execution continues

### Kernel Telemetry

- Monitors events directly from the kernel
- Captures file, registry, process, and network operations
- Difficult to bypass as it operates at a lower level

### Memory Scanning

- Scans process memory for known signatures
- Triggers based on suspicious behavior
- Looks for shellcode, encryption, malicious strings
- **Modern Context:**
  - Attackers also scan process memory for sensitive artifacts like authentication tokens. Co‑pilot/IDE integrations, chat assistants, and browser extensions frequently cache Bearer/JWT tokens in memory.
  - Practical triage: search for `"Authorization: Bearer"`, `"eyJ"` (base64 JWT prefix), or provider‑specific headers; dump minimal pages to avoid tripping anti‑exfil rules.

