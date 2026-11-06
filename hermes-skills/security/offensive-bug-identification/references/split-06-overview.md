## Overview

Bug identification is the process of discovering potential vulnerabilities in software through various techniques including static analysis, dynamic analysis, and fuzzing. This document outlines methodologies and tools for effective vulnerability research.

For practical exploit development, see [Exploit Development](/exploit/development.md).

```mermaid
flowchart TD
    BugId["Bug Identification"]

    %% Main Methods
    Static["Static Analysis"]
    Dynamic["Dynamic Analysis"]
    Fuzzing["Fuzzing"]
    AI["AI-Assisted"]

    %% Static Analysis Methods
    CodeReview["Manual Code Review"]
    RevEng["Reverse Engineering"]
    PatchDiff["Patch Diffing"]
    StaticTools["Static Analysis Tools"]
    SBOM["Supply Chain Analysis"]

    %% Dynamic Analysis Methods
    DebugTrace["Debugging/Tracing"]
    DBI["Dynamic Binary Instrumentation"]
    Taint["Taint Analysis"]
    SymExec["Symbolic Execution"]
    Snapshot["Snapshot Analysis"]

    %% Fuzzing Methods
    DumbFuzz["Dumb Fuzzing"]
    SmartFuzz["Smart Fuzzing"]
    EvoFuzz["Evolutionary Fuzzing"]
    LLMFuzz["LLM-Guided Fuzzing"]

    %% AI Methods
    LLMTriage["LLM Crash Triage"]
    MLPattern["ML Pattern Recognition"]
    AutoVariant["Automated Variant Analysis"]

    %% Connections
    BugId --> Static
    BugId --> Dynamic
    BugId --> Fuzzing
    BugId --> AI

    Static --> CodeReview
    Static --> RevEng
    Static --> PatchDiff
    Static --> StaticTools
    Static --> SBOM

    Dynamic --> DebugTrace
    Dynamic --> DBI
    Dynamic --> Taint
    Dynamic --> SymExec
    Dynamic --> Snapshot

    Fuzzing --> DumbFuzz
    Fuzzing --> SmartFuzz
    Fuzzing --> EvoFuzz
    Fuzzing --> LLMFuzz

    AI --> LLMTriage
    AI --> MLPattern
    AI --> AutoVariant

    %% Combinations
    Taint -.-> Fuzzing
    SymExec -.-> Fuzzing
    RevEng -.-> Fuzzing
    AI -.-> Fuzzing
    AI -.-> Static

    class BugId primary
```

