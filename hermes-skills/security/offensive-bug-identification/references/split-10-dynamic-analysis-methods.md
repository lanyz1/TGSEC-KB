## Dynamic Analysis Methods

Dynamic analysis examines code during execution to identify vulnerabilities in real-time operation.

### Hybrid Reverse Engineering (dynamic)

Reverse engineering involves analyzing an application while it runs to understand its behavior.

#### Network Protocol Analysis Example

- Identify ports used by a program
- Use WinDbg to debug it
- Set a breakpoint on `bp wsock32!recv`
- Write a python script to send data to that port
- After your breakpoint hits, continue execution using `pt` and check `rax` for result and `dd rsp L5` for input buffer
- `lm m <exe_name>` to identify its location on the disk
- Open that executable with IDA and rebase module
- Use the information printed by WinDbg `k` command to find the location you need to investigate
- Set a hardware breakpoint on your input buffer, only check functions that touches it
- Dump the callstack when your breakpoint got hit
- Try to identify the correct packet structure
- Then try to send proper malformed packets to crash it

#### Hypervisor Debugging and Analysis

- Debugging Windows Hypervisor (Hyper-V) requires specialized setup and knowledge
- Setup requirements:
  - Host: Windows 10/11 with WinDbg
  - Guest: Windows VM with Virtualization-based security (VBS) enabled
  - Configure debugging with `bcdedit /hypervisorsettings` commands

- Analyzing Hypervisor components:
  - Target `hvix64.exe` (Intel processor hypervisor core)
  - Use bindiff with `winload.efi` and older versions of `hvloader.dll` for insight
  - Leverage Hypervisor Top Level Functional Specification (TLFS) documentation

- Inspecting Secure Kernel (SK) Calls:
  - Monitor VTL calls (transitions from VTL0 to VTL1)
  - Use conditional breakpoints on `nt!VslpEnterIumSecureMode`
  - Examine secure service call numbers (SSCN)
  - Use tools like hvext to translate guest virtual addresses

- Memory access techniques:
  - Translate Guest Virtual Address (GVA) to Guest Physical Address (GPA)
  - Translate GPA to Host Physical Address (HPA) when needed
  - Understand Second Level Address Translation mechanisms

- For mitigation techniques, see [Mitigation](/exploit/mitigation.md) or [Modern Mitigations](/exploit/modern-mitigations.md)

### Binary Instrumentation

Binary instrumentation is a prerequisite for advanced dynamic analysis methods.

- [Intel Pin](https://www.intel.com/content/www/us/en/developer/articles/tool/pin-a-dynamic-binary-instrumentation-tool.html): is a dynamic binary instrumentation framework
  - It enables you to write modules that execute some program and insert code into it at execution time to track things
  - Can easily hook any function in the program and collect runtime data
  - Can be combined with Ghidra/IDA to provide more information
    > [!NOTE]
    > Intel Pin is now in sustain‑only mode — no new ISA extensions will be added. Prefer **DynamoRIO** or **Frida‑Stalker** for forward‑looking projects.
- [DynamoRIO](https://github.com/DynamoRIO/dynamorio): more powerful and faster alternative to `Intel Pin`, but harder to setup
- `Frida`: Slower, better for mobile applications

### Dynamic Taint Analysis

- Technique to determine how data flow through a given program and influence its state
- Done by marking certain bytes of memory and tracking how it flows through program execution
- Often implemented on top of dynamic binary instrumentation tools like Intel Pin
- Steps:
  - Define taint sources: data that you want to track
  - Define taint sinks: program locations that we want to check if they get influenced by data from taint sources
  - Tracking input propagation: all instructions handling taint data need to be instrumented

### Symbolic Execution

- Transform the program into a mathematical equation that can be solved
- Instructions are simulated to maintain a binary formula describing the satisfied conditions for each path
- Scan types:
  - `Static`: [S2E](https://github.com/S2E/s2e) based on source code, not reliant on architecture, very hard to reason about kernel/libraries
  - `Dynamic`: combine concrete state with symbolic state, scales better
- Engine types:
  - `Full System`: operates on the entire VM by integrating with hypervisors, very powerful but hard to use
  - `Binary`: [Triton](https://github.com/JonathanSalwan/Triton) based on Pin/Taint Analysis and [Angr](https://github.com/angr/angr) based on `VEX-IR`
  - `Source Code`: [Klee](https://github.com/klee/klee) based on LLVM
- You can augment fuzzers via symbolic execution, [driller](https://github.com/shellphish/driller) is an example

#### Challenges with Symbolic Execution

- Memory
  - Complex data structures are hard to symbolize
- Environment
  - How are library and system calls handled
  - Symbolically executing massive library functions hurt performance
- State/Path Explosion
  - Biggest issue, loops/nested conditionals exponentially increases execution state
  - Heuristics are often used to determine with paths to follow
- Constraint Solving
  - Once the formula gets large enough, it gets hard to solve and impacts performance

### eBPF‑based Dynamic Tracing

- **bpftrace** / **BCC**: attach uprobes/kprobes to collect heap, syscall, or scheduler events with minimal overhead
- Ideal for pre‑fuzz triage and live coverage measurement on kernels or containerised workloads

### Coverage Recon (quick)

```bash
# Collect light coverage then visualize
drrun -t drcov -- ./target @@
python3 drcov2lcov.py ./drcov.*.log > coverage.info
genhtml coverage.info -o cov_html
```

- Load into Lighthouse (IDA) or lcov HTML to identify cold paths reachable from attacker input
- Use results to select fuzz targets and build a minimal, representative seed corpus

