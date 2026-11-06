## Memory Safety Initiatives

### Rust in the Linux Kernel

- First‑class Rust support landed in Linux 6.1 (December 2022) and was declared production‑ready with Linux 6.6 (October 2023).
- In‑tree Rust drivers (e.g., NVMe, DRM simple‑display, Wi‑Fi) have so far exhibited zero memory‑safety bugs under continuous fuzzing, demonstrating the practical security benefit of memory‑safe languages.
- Ongoing work aims to extend Rust usage into networking, Android GKI modules, and scheduler subsystems, further shrinking the kernel's attack surface.

### Safer Windows Drivers with C++20 and Rust

- Starting in Windows 11 23H2, the Windows Driver Framework (WDF) officially supports both modern C++20 and a Rust projection (`windows‑drivers‑rs`) that wrap KMDF/WDF APIs with lifetime‑safe abstractions.
- Hardware vendors can now obtain WHQL signatures for C++20 or Rust kernels drivers, eliminating common lifetime and IRQL‑misuse bugs without sacrificing performance.

### CHERI / Morello (Experimental Capability Hardware)

- Arm's Morello evaluation platform (2022‑2025) runs a CHERI‑enabled Linux kernel that enforces pointer capabilities in user and kernel space, providing hardware‑enforced spatial and temporal memory safety.
- Although experimental, CHERI demonstrates a plausible post‑2025 path toward fundamentally safer C/C++ code with architectural support.

### memfd_secret (userland secret memory)

- Linux:
  - `memfd_secret` (Linux 5.14+) provides user‑mode pages hidden from other processes and the kernel direct mappings
  - Useful for protecting keys and ROP staging from accidental exposure; verify support via kernel config and `memfd_secret(2)`

