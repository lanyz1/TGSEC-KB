## Quick Reference: Tool Selection Guide

### By Target Type

| Target               | Primary Tools     | Secondary Tools     |
| -------------------- | ----------------- | ------------------- |
| **Linux Kernel**     | Syzkaller, AFL++  | KASAN, KCOV, ftrace |
| **Windows Kernel**   | ICICLE, WinAFL    | Verifier, KFUZZ     |
| **Browsers**         | LibFuzzer, Domato | ClusterFuzz, Dharma |
| **Network Services** | AFL++, Boofuzz    | Peach, Sulley       |
| **Mobile Apps**      | QARK, Frida       | MobSF, Objection    |
| **Web Apps**         | Burp Suite, FFUF  | Nuclei, Semgrep     |
| **Firmware**         | Binwalk, EMBA     | FACT, Firmwalker    |
| **Containers**       | Trivy, Falco      | Grype, Syft         |

### By Technique

| Technique               | Recommended Tools    | Notes                          |
| ----------------------- | -------------------- | ------------------------------ |
| **Coverage Fuzzing**    | AFL++ 4.21+          | Cross-platform, CMPLOG support |
| **Snapshot Fuzzing**    | Nyx, QEMU+AFL++      | Stateful target support        |
| **Concurrency Fuzzing** | RFF, ThreadSanitizer | Race condition detection       |
| **Symbolic Execution**  | Angr, Triton         | Path exploration               |
| **Taint Analysis**      | DynamoRIO, Triton    | Data flow tracking             |
| **Binary Diffing**      | BinDiff 8, Ghidriff  | Patch analysis                 |
| **Static Analysis**     | CodeQL, Semgrep      | Pattern matching               |
| **Dynamic Analysis**    | Frida, DynamoRIO     | Runtime instrumentation        |

### Tool Migration Path

| Old Tool  | New Alternative    | Migration Notes            |
| --------- | ------------------ | -------------------------- |
| Intel Pin | DynamoRIO          | Pin is sustain-only        |
| WinAFL    | AFL++ 4.x          | Integrated Windows support |
| Radamsa   | LibAFL mutators    | Better coverage awareness  |
| BinDiff 7 | BinDiff 8/Ghidriff | Improved algorithms        |
| IDA 7.x   | IDA 8.x/Ghidra 11  | Better decompilation       |

