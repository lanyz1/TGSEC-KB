## EDR Visibility

### EDR Architecture & Components

EDR solutions consist of multiple components creating a complex attack surface:

**Client-Side Components:**

- **User-space Applications** - Main agent processes and UI components
- **Kernel-space Drivers** - Filter drivers, network drivers, software drivers
- **Communication Interfaces** - IOCTLs, FilterConnectionPorts, ALPC, Named Pipes

**Component Communication Methods:**

- **Kernel-to-Kernel**: Exported functions, IOCTLs
- **User-to-Kernel**: IOCTLs, FilterConnectionPorts (minifilter-specific), ALPC
- **User-to-User**: ALPC, Named Pipes, Files, Registry

**Server-Side Components:**

- Cloud services and management consoles
- On-premise servers (some vendors)
- Custom protocols for agent-to-cloud communication

### EDR Visibility Methods

EDR solutions require extended visibility into system activities:

- Filesystem monitoring via mini-filter drivers
- Process/module loading via image load kernel callbacks
- Process/.NET modules/Registry/kernel object events via ETW Ti
- Network monitoring via NDIS and network filtering drivers

### Static Analysis

- Extract information from binary
  - Known malicious strings
  - Threat actor IP or domains
  - Malware binary hashes

### Dynamic Analysis

- Execute binary in a sandbox environment and observe it
  - Network connections
  - Registry changes
  - Memory access
  - File creation/deletion
- AntiMalware Scan Interface

### Behavioral Analysis

- Observe the binary as its executing, Hook into functions/syscalls
  - User actions
  - System calls
  - Kernel callbacks
  - Commands executed in the command line
  - Which process is executing the code
  - Event Tracing for Windows

