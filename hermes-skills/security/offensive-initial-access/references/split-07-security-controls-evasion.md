## Security Controls Evasion

### Perimeter Defense Evasion

#### Secure Web Gateway

- sensitive on
  - Domain characteristics
  - URL-fetched contents (HTML, body, javascript)
  - MIME types (where file type is allowed or not)
- can be evaded via
  - high reputation servers (cloud instances)
  - HTML smuggling

#### Secure DNS

- sensitive on
  - Domain categorisation, maturity, `whois` examination
  - Presence on real-time blocking lists, threat intelligence feeds, virustotal-alike databases
  - SSL/TLS certificate contents
- can be evaded via
  - high reputation domains (Domain fronting CDN like azure edge CDN, Cloud-based resources like AWS lambda or azure blob storage, personal cloud drives)
  - use [Talos Intelligence](https://talosintelligence.com/reputation_center/) to check reputation
  - AWS is dumber than Azure, use it

### Endpoint Defense Evasion

#### Antivirus

- sensitive on
  - static signatures
  - heuristic signatures
  - behavioural signatures
  - trigger events `on-demand -> on-write -> on-access -> on-execute -> real-time`
  - proactive protection of them is weaker due to low false-positive, low impact and high stability requirements
    - before-exec: mainly cloud-reputation based examination
    - before-exec: machine learning evaluation focusing on hand-picked characteristics
    - on-exec: simulating entry point and first N instructions
    - on-exec: memory scanner sweeping process virtual memory allocations for presence of signatured threats
  - steps
    - static analysis
    - heuristic analysis
    - cloud reputation analysis + automated sandboxing / detonation
    - ML analysis
    - emulation
    - behavioural analysis
- can be evaded via
  - static analysis by writing custom malware
  - heuristic analysis by smartly blending-in with our payload
  - cloud reputation by backdooring legitimate binaries, devising malware in containers (PDF, Office docs), sticking to DLLs
  - automated sandboxing by environmental keying (only execute if something)
  - ML analysis by trial and error, hard to combat
  - emulation by time-delaying, environmental keying
  - behavioural analysis by
    - avoiding suspicious WinAPI calls
    - acting low-and-slow instead of all-at-once
    - unhooking/direct syscalls may work

#### EDR Evasion Techniques

For detailed information on EDR evasion techniques, including:

- Malware Virtualization
- API Unhooking
- Early Cascade Injection
- Killing Bit techniques
- Call Stack Obfuscation
- Sleep Obfuscation
- Telemetry obfuscation
- Persistence strategies
- Event correlation evasion

See the [EDR Evasion documentation](exploit/edr.md).

### Windows Defender Bypass Techniques

For detailed information on Windows Defender bypass techniques, including ASR bypasses and custom detection rules evasion, see the [EDR Evasion documentation](exploit/edr.md).

