## Overview

_created by AnotherOne from @Pwn3rzs Telegram channel_.

This document is Week 2 of a multi‑week exploit development course, focusing on discovering vulnerabilities through fuzzing techniques and analyzing the crashes to determine exploitability.

Last week we studied vulnerability classes through real-world examples. This week we'll learn to find these vulnerabilities ourselves using fuzzing - the automated technique that has discovered thousands of critical security bugs in production software.

Fuzzing can feel a bit front‑loaded: you may spend time wiring harnesses and running campaigns without immediately finding exciting new bugs, especially on hardened or well‑tested targets. That’s normal, and it's one reason the next week on patch diffing often feels more directly "practical" — many companies already run large fuzzing setups and need people who can understand and exploit the bugs those systems uncover. Still, working through this week is important: it teaches you how fuzzers actually discover real vulnerabilities, so when you later triage crashes or study patches, you'll have a solid intuition for how those bugs were found and how to reproduce them.

### Prerequisites

Before starting this week, ensure you have:

- A Linux virtual machine (Ubuntu 24.04 recommended) with at least 8GB RAM and 8 cpu cores
- Basic understanding of C/C++ programming
- Familiarity with command-line tools and debugging (GDB basics)
- Understanding of memory corruption vulnerabilities (from Week 1)

