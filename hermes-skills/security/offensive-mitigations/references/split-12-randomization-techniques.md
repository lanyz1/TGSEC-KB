## Randomization Techniques

### Address Space Layout Randomization (ASLR)

- Linux & Windows:
  - Randomizes memory addresses used by executables and libraries.
  - Makes it harder for attackers to predict target addresses.

#### Bypass Techniques

- **Information Leaks**: Exploiting vulnerabilities to leak addresses of loaded modules.
- **ROP with PLT/GOT**: Using the Procedure Linkage Table to leak addresses and calculate base addresses.
- **Low Entropy**: Exploiting systems with limited randomization bits.
- **Heap Spraying**: Filling memory with copies of shellcode to increase hit probability.
- **Local Privilege Escalation**: Using local exploits to bypass protection.
- **Partial Overwrite**: Overwriting only part of an address to maintain alignment.
- **Statically Linked Code**: Targeting code that doesn't use ASLR.

#### Practitioner

- you probably first need an information leak to identify the correct memory address and then use it to circumvent ASLR and DEP
- format string bugs also helps trigger an information leak, so you can use them alongside `ropchains` to bypass ASLR and DEP
- information leaks are often happen through logical errors or memory corruption bugs

### Position Independent Executables (PIE)

- Linux/Windows:
  - Compiles executables as position-independent code, enabling ASLR for the main executable.
  - Without PIE, the main executable loads at a fixed base address, providing attackers a reliable target.
  - Essential for full ASLR coverage across all memory regions.

#### Bypass Techniques

- **Information Leaks**: Same techniques as ASLR bypass - leak addresses to calculate base.
- **Partial Overwrites**: Overwriting only the lower bytes of addresses to maintain relative offsets.
- **Non-PIE Dependencies**: Targeting linked libraries that aren't position-independent.
- **GOT/PLT Attacks**: Exploiting Global Offset Table entries before they're resolved.

#### Practitioner

- Check PIE status: `file /path/to/binary` or `readelf -h /path/to/binary | grep Type`
- Compile with PIE: `-fPIE -pie` (GCC) or `-fPIC -shared` for libraries
- Detect at runtime: `/proc/PID/maps` shows randomized executable base addresses
- **checksec**: `checksec --file=/path/to/binary` shows PIE status

### ASCII Armored Address Space

- Windows:
  - Loads all shared libraries in addresses starting with `0x00`.
  - Prevents string manipulation exploits that terminate at null bytes.

#### Bypass Techniques

- **Partial Injection**: Still possible to inject one null byte.
- **Main Executable Attacks**: Main executable is not moved, so attackers can target it instead.

### Function Granular KASLR (FGKASLR)

- Linux:
  - Randomizes kernel functions at a finer granularity.
  - Enhances address space randomization effectiveness.

### Kernel Stack Randomization

- Linux:
  - Randomizes the kernel stack base address per process.
  - Makes stack-based attacks more challenging.

### Mandatory ASLR (MASLR)

- Windows:
  - Forces the rebasing of modules even when they were compiled without ASLR support.
  - Enhances protection against code reuse attacks.

### Bottom-Up ASLR (BASLR)

- Windows:
  - Works alongside MASLR to randomize allocation patterns.
  - Blocks 64KB allocations from requested base address up to a randomly selected number.
  - Repeats randomization each time the process restarts.

