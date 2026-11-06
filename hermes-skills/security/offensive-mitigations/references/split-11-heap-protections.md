## Heap Protections

### Heap Cookies

- Windows:
  - Places a 1-byte value in the metadata of heap chunks.
  - Detects heap metadata corruption before exploitation.

### AMSI Heap Scanning (Jan 2025)

- Windows:
  - AMSI (Antimalware Scan Interface) scans newly committed **writable** heap pages _before_ they are flipped to `PAGE_EXECUTE_READ` or `PAGE_EXECUTE_WRITECOPY`.
  - **Safer allocation pattern to avoid AMSI heap scanning:** Reserve memory with `PAGE_NOACCESS`, decrypt/deobfuscate payload in‑place, then change protection to `PAGE_EXECUTE_READ`.
  - The classic "patch the `AMSI` ASCII tag in `amsi.dll`" trick no longer works reliably; consider patching the COM VTable entry for `IAmsiStream::QueryInterface` or using a proxy‑DLL hook instead.

### Low Fragmentation Heap (LFH)

- Windows:
  - First 32-bit of metadata gets XORed with canary to ensure integrity.
  - Allocates blocks in predetermined size ranges by organizing blocks into buckets.
  - Reduces heap predictability and exploitation potential.

### Safe Unlink

- Windows/Linux:
  - Checks integrity of pointers before freeing memory chunks.
  - Prevents unlink exploitation in heap management.

#### Bypass Techniques

- **Heap Overflow**: Using malloc maleficarum techniques.
- **Chunk-on-Lookaside Overwrite**: Targeting specific heap management structures.

### Heap and Stack Protections

- Windows:
  - Implements guard pages and heap allocation randomization.
  - Detects and prevents buffer overflows and stack smashing.

