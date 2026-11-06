## Fuzzing

Fuzzing is a technique where you feed the application malformed inputs and monitor for crashes or unintended behaviors. See the dedicated [Fuzzing](/exploit/fuzzing.md) document for more detailed techniques.

### Fuzzing Overview

#### What is Fuzzing?

- Target software parses controllable input
- We create and/or mutate input and feed it into program
- Find crashes

#### What a Fuzzer Does

- Generic but platform/architecture specific
- Handles Input Generation/Mutation/Saving (called Corpus)
- Instrumenting Target (running, resetting, getting feedback)
- Reporting Crashes

#### What a Harness Does

- Target Specific
- Handles Feeding the input into the target

#### Fuzzer vs Harness Relationship

- Find Top Level Callable Functions
- Use Harness to Call that Function and Feed Input to it
- Fuzzer Generates and Sends the Input to Harness and Collects Coverage and Detects Crashes

### Crash Detection Techniques

- Paged Heap (heap overflows, UAF)
  - Guard pages between allocations
- Address Sanitizer (overflows + more)
  - Shadow memory (by inserting red zones in-between stack objects)
- Memory Sanitizer (uninitialized variable read)
  - Memory Leak, Used to Break ASLR
- Cluster crashes with token‑based Capstone‑hashing or `gdb‑script dedup.py` before manual analysis.

### Fuzzing Tools

#### Modern Fuzzing Frameworks

- **AFL++ 4.21+** – Unified cross-platform fuzzer with Windows support, CMPLOG, QEMU-mode
- **LibAFL 0.13+** – Rust-native, highly customizable, supports in-process and fork-server modes
- **Honggfuzz** – Persistent-mode Windows support, hardware-based feedback
- **Nyx** – Full-VM snapshot fuzzing with KVM acceleration
- **ICICLE** – Fast Windows kernel fuzzing framework
- **Syzkaller** – Kernel fuzzer with LLM-guided seed selection (2025)

#### Instrumentation & Coverage

- **DynamoRIO** – Used by AFL++, faster than Intel Pin (Note: Intel Pin is now sustain-only)
- **Frida Stalker** – Cross-platform dynamic instrumentation
- **Intel PT** – Hardware-accelerated coverage collection
- **Emerald** – Generates `drcov` data for coverage visualization

#### Specialized Fuzzers

- **ChatAFL / LLM-driller** – LLM-guided corpus expansion (+30% coverage on complex targets)
- **Reads-From Fuzzer (RFF)** – Concurrency fuzzer for race/TOCTOU bugs
- **LibFuzzer** – In-process, coverage-guided fuzzer for source-available targets
- **Radamsa** → **Replaced by LibAFL mutators** (more coverage-aware)

#### Symbolic Execution Engines

- **Triton** – Dynamic binary analysis framework
- **Angr** – Binary analysis platform with symbolic execution
- **Manticore** – Dynamic symbolic execution tool
- **S2E** – Selective symbolic execution platform

### Continuous-Integration Fuzzing

- **ClusterFuzzLite** – GitHub Actions/CI runner that feeds corpora to AFL++, libFuzzer or honggfuzz and files issues automatically.

### Snapshot Fuzzing

#### VMM Snapshot Fuzzing

- **QEMU Snapshots:** Fast restoration for stateful targets
- **KVM Acceleration:** Dirty page tracking for efficient resets
- **Persistent Mode:** Memory-only reset without full VM restore

### Fuzzing Types

#### Dumb Fuzzing

- Just sending random data to the target

#### Smart Fuzzing

- _Mutation Based_: Test cases are obtained by applying mutations to valid, known good samples (e.g., [Radamsa](https://gitlab.com/akihe/radamsa))
- _Generation(Grammar) Based_: Test cases are obtained by modeling files or protocol specifications based on models, templates, RFCs, or documentation (e.g., [Peach Fuzzer](https://peachtech.gitlab.io/peach-fuzzer-community/))
- _Model Based_: Test cases are obtained by modeling the target protocol/file format (when you want to test the target's ability to accept and process invalid sequences of data)
- _Differential Fuzzing_: Comparing outputs of different implementations with the same input

#### Evolutionary Fuzzing

- Test cases and inputs are generated based on the response from the program
- `AFL` is an example
- Or Google ClusterFuzz

#### Concurrency Fuzzing

- Systematically permutes thread scheduling to uncover data‑race, atomicity, and TOCTOU vulnerabilities that traditional coverage‑guided fuzzers miss

#### LLM‑Guided Fuzzing

- **ChatAFL** – integrates an LLM to propose protocol‑aware mutations; boosts state coverage on network daemons by ~40 %.
- **SyzAgent / SyzLLM (2025‑02)** – schedules kernel `syz` programs suggested by an LLM fine‑tuned on the Syzkaller corpus.
- **NumSeed** – leverages natural‑language descriptions of inputs to seed generation for binary‑only targets.

### Combined Method

The most effective approach often combines multiple techniques:

- Reverse engineer first to identify interesting parts
- Fuzz those parts to find crashes
- Investigate crashes to find exploitable vulnerabilities
- For shellcode development, see [Shellcode](/exploit/shellcode.md)

