## Side-Channel Attack Mitigations

### Speculative Execution Mitigations

- Linux/Windows:
  - Addresses vulnerabilities like Spectre and Meltdown.
  - Includes microcode updates and patches to prevent speculative execution attacks.

### Recent Spectre Mitigations

- **IBPB (Indirect Branch Prediction Barrier)**:
  - Intel/AMD feature that flushes indirect branch predictors.
  - Prevents cross-privilege domain speculation leakage.
  - Controlled via `MSR_IA32_PRED_CMD`.

- **IBRS (Indirect Branch Restricted Speculation)**:
  - Restricts speculation of indirect branches when in higher privilege levels.
  - Mitigates Spectre v2 by preventing user-space speculation attacks on kernel.
  - Performance overhead led to adoption of retpolines as primary mitigation.

- **STIBP (Single Thread Indirect Branch Predictors)**:
  - Prevents sibling threads from controlling each other's indirect branch prediction.
  - Mitigates cross-hyperthread Spectre attacks.
  - Particularly important for SMT (Simultaneous Multi-Threading) environments.

- **SSBD (Speculative Store Bypass Disable)**:
  - Prevents speculative execution of loads that bypass older stores.
  - Mitigates Spectre v4 (Speculative Store Bypass).
  - Can be controlled per-process via `prctl()` on Linux.

#### Bypass Techniques

- **Microarchitectural Timing**: Using cache timing, TLB timing, or other side channels.
- **Cross-Process Leakage**: Exploiting shared microarchitectural state between processes.
- **Hardware Implementation Gaps**: CPU-specific vulnerabilities in mitigation implementations.
- **Performance Optimization Exploitation**: Targeting cases where mitigations are disabled for performance.

#### Practitioner

- Check mitigations: `cat /proc/cpuinfo | grep -E "(ibpb|ibrs|stibp|ssbd)"`
- Runtime controls: `/sys/devices/system/cpu/vulnerabilities/` directory
- Per-process SSBD: `prctl(PR_SET_SPECULATION_CTRL, PR_SPEC_STORE_BYPASS, ...)`
- Performance impact: Use `perf` to measure mitigation overhead

### Kernel Memory Sanitizer (KMSAN)

- Linux:
  - Detects use of uninitialized memory in the kernel.
  - Helps find and fix initialization bugs.

### Linux Kernel Runtime Guard (LKRG)

- Linux (Module):
  - Loadable kernel module performing runtime integrity checks on critical kernel structures.
  - Aims to detect and prevent various exploits in real-time.

### Spectre-BHB Mitigations

- Linux:
  - Addresses Branch History Injection vulnerabilities on ARM.
  - Prevents certain speculative execution attacks.

