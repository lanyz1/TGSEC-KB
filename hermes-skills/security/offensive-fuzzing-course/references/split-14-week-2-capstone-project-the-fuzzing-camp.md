## Week 2 Capstone Project: The Fuzzing Campaign

- **Goal**: Apply the week's techniques to discover and analyze a vulnerability in a real-world open source target or a complex challenge binary.
- **Activities**:
  - **Select a Target**:
    - Choose a C/C++ library that parses complex data (e.g., JSON, XML, Images, Archives, Network Packets).
    - Suggestions: `json-c`, `libarchive`, `libpng`, `tinyxml2`, `mbedtls`, or a known vulnerable version of a project (e.g., `libwebp` 1.0.0).
  - **Harness Development**:
    - Write a `LLVMFuzzerTestOneInput` harness or an AFL++ persistent mode harness.
    - Ensure the harness compiles with ASAN and UBSAN.
  - **Campaign Execution**:
    - Gather a valid seed corpus (from the internet or by generating samples).
    - Minimize the corpus using `afl-cmin` or `afl-tmin` (or libFuzzer's merge mode).
    - Run the fuzzer for at least 4 hours (or until a crash is found).
  - **Triage and Analysis**:
    - Deduplicate crashes.
    - Use GDB and ASAN reports to identify the root cause (e.g., Heap Overflow, UAF).
    - Determine exploitability (Control of instruction pointer? Arbitrary write?).
  - **Report**:
    - Document the target, harness code, campaign commands, and crash analysis.

### Deliverables

- A `fuzzing_report.md` containing:
  - **Target Details**: Project name, version, and function targeted.
  - **Harness Code**: The C/C++ harness you wrote.
  - **Campaign Stats**: Fuzzer used, duration, executions/sec, and coverage achieved.
  - **Crash Analysis**: ASAN output, GDB investigation, and root cause explanation.
  - **PoC**: A minimal input file that triggers the crash.

### Looking Ahead to Week 3

Next week, you'll learn patch diffing - analyzing security updates to understand what was fixed and discovering variant vulnerabilities. You'll see how fuzzing discoveries lead to patches, and how analyzing those patches can reveal additional bugs.

<!-- Written by AnotherOne from @Pwn3rzs Telegram channel -->

