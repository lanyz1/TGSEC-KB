## Fundamentals

### AV vs EDR

**Antivirus (preventive approach)**:

- Static Analysis: Matching known signatures in files
- Dynamic Analysis: Limited behavioral monitoring/sandboxing
- Effective against known threats, weaker against advanced attacks

**EDR (proactive & investigative approach)**:

- Continuous endpoint monitoring
- Behavioral analysis at kernel level
- Anomaly detection and post-compromise visibility
- Prioritizes incident response and investigation

### Windows Execution Flow

Windows program execution follows a hierarchical flow:

1. **Applications** - User programs like firefox.exe
2. **DLLs** - Libraries providing Windows functionality without direct low-level access
3. **Kernel32.dll** - Core DLL for memory management, process/thread creation
4. **Ntdll.dll** - Lowest user-mode DLL that exposes the NT API interface to the kernel
5. **Kernel** - Core OS component with unrestricted hardware access

Example operation flow (creating a file):

1. Application invokes `CreateFile` function
2. CreateFile forwards to `NtCreateFile`
3. Ntdll.dll triggers `NtCreateFile` syscall
4. Kernel creates the file and returns a handle

