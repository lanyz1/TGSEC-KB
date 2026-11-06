## Day 4: Format String and Injection Vulnerabilities

- **Goal**: Understand vulnerabilities arising from mixing code and data, especially format string bugs and complex parsers.
- **Activities**:
  - _Reading_:
    - "Hacking: The Art of Exploitation, 2nd Edition" by Jon Erickson - Chapter 0x350: "Format Strings"
    - "Attacking Network Protocols" by James Forshaw - Chapter 3: "Network Protocol Structures"
    - [OWASP Format String Vulnerability](https://owasp.org/www-community/attacks/Format_string_attack)
  - _Online Resources_:
    - [Exploiting Format String Vulnerabilities](https://cs155.stanford.edu/papers/formatstring-1.2.pdf)
    - [Use of Externally-Controlled Format String](https://cwe.mitre.org/data/definitions/134.html)
    - [The Fuzzing Book](https://www.fuzzingbook.org/)
  - _Concepts_:
    - Format string functions and their dangers
    - Arbitrary read and write primitives
    - Parser complexity and bug surface
    - Protocol implementation vulnerabilities

### Format String Vulnerabilities

**What They Are**: Format string vulnerabilities occur when user-controlled data is passed as the format string argument to functions like `printf`, `sprintf`, `fprintf`, `syslog`, and similar functions in C/C++.

**The Core Issue**: Format functions use special directives (e.g., `%s`, `%x`, `%n`) to interpret subsequent arguments. When an attacker controls the format string, they can:

1. **Read arbitrary memory** using `%s` and `%x` directives
2. **Write arbitrary memory** using the `%n` directive (writes number of bytes output so far to a pointer)
3. **Crash the program** by causing invalid memory access

**How They Work**:

**Safe Usage**:

```c
printf("%s", user_input);  // user_input is data, not format string
```

**Vulnerable Usage**:

```c
printf(user_input);  // user_input IS the format string - DANGEROUS!
```

**Real-World Example - CVE-2023-35086 (ASUS Router Format String RCE)**:

**Background**: ASUS RT-AX56U V2 and RT-AC86U routers contained a format string vulnerability in their web administration interface (httpd daemon).

**The Bug**: The `do_detwan_cgi` module's `logmessage_normal` function directly used user-controlled input as a format string when calling `syslog()`, without any sanitization:

```c
void logmessage_normal(char *user_input) {
    syslog(LOG_INFO, user_input);  // VULNERABLE!
}
```

**The Attack** (Multi-Stage):

_Stage 1 - Information Leak_:

```
1. Attacker authenticates to router admin interface (or exploits auth bypass)
2. Sends HTTP request with format string: %p.%p.%p.%p
3. Router logs this to syslog, leaking stack addresses
4. %p directives reveal stack layout and defeat ASLR
5. Attacker maps out memory layout for reliable exploitation
```

_Stage 2 - Arbitrary Write_:

```
6. Attacker crafts format string with %n directive
7. Sends: %<offset>$<width>x%<target>$n
8. Overwrites function pointer or return address on stack
9. Redirects execution to attacker-controlled shellcode
10. Result: Remote Code Execution with root privileges
```

**Mitigations Bypassed**:

- **ASLR**: Bypassed via format string information leak (%p directives)
- **Stack Canaries**: Format string write can overwrite return address directly without touching canary
- **Authentication**: Initially required admin access, but later found exploitable without authentication

**The Fix**: ASUS firmware updates

```c
void logmessage_normal(char *user_input) {
    syslog(LOG_INFO, "%s", user_input);  // Safe - user input is data, not format
}
```

Additionally implemented input validation and enabled `-Wformat-security` compiler warnings.

**Why It Matters**: Format string vulnerabilities in embedded devices and routers are particularly dangerous because:

- Devices often run outdated firmware
- Many are internet-facing (UPnP, remote administration)
- Compromise provides persistent network access
- Can be chained with other vulnerabilities for full device takeover

### Application-Specific Parser and File Handling

**What They Are**: Vulnerabilities in parsers for archive formats, office documents, and other non-web file types. These provide initial access vectors through malicious file sharing.

**Case Study - CVE-2023-38831 (WinRAR Archive Parsing RCE)**:

- **The Bug**: WinRAR's archive handling code improperly processed archives containing both a folder and a file with the same name. When extracting, WinRAR could be tricked into executing a file when the user double-clicked what appeared to be a folder in the archive.
- **The Attack**: An attacker created a specially crafted RAR archive containing:
  1. A folder named "document.pdf" containing malicious executable
  2. A file named "document.pdf" containing benign PDF

  When a user double-clicked the entry in WinRAR, it would extract and execute the malicious executable instead of opening the PDF.

- **The Impact**: Remote code execution with user privileges when opening crafted archives. Widely exploited by multiple threat actor groups (trading firms, cryptocurrency targets). Affected WinRAR versions before 6.23.
- **The Fix**: WinRAR 6.23 corrected the handling logic to prevent ambiguous filename processing and added warnings for suspicious archive structures.
- **Why It Matters**: Archive parsers (ZIP, RAR, 7z) are common attack vectors for initial access via email attachments and file sharing. Logic flaws in extraction handling complement traditional memory corruption bugs.

**Document/Formula Parser Issues**:

**Case Study Context - CVE-2023-21716 (Microsoft Word RTF Remote Code Execution)**:

- **The Bug**: Microsoft Word's Rich Text Format (RTF) parser contained a heap-based buffer overflow vulnerability. When processing specially crafted RTF documents, the parser failed to properly validate the size of font table entries before copying data into a heap buffer.
- **The Attack**: An attacker could craft a malicious RTF document with oversized font table entries. When a victim opened the document in Microsoft Word, the parser would overflow the heap buffer during font processing, corrupting adjacent memory structures.
- **The Impact**: Remote code execution with user privileges when opening a malicious RTF file. No user interaction beyond opening the document was required.
- **The Fix**: Microsoft released patches in February 2023 (KB5002289 and related updates) that added proper bounds checking to the RTF font table parser and implemented safe buffer copy operations.
- **Defense**: Apply patches immediately, use Office in protected view for untrusted documents, implement email attachment filtering, and enable Microsoft Defender Application Guard where available.
- **Why It Matters**: Legacy parser components in office suites remain valuable targets due to widespread deployment and slow patching cycles. Document-based exploits are effective for initial access in enterprise environments. RTF parsers are particularly attractive because RTF files are often trusted more than macros and can bypass some security controls.

### Key Takeaways

1. **Code/Data separation is fundamental**: Format string vulnerabilities demonstrate the danger of treating user input as format specifiers rather than data. When code and data mix (user input as format string), attackers gain powerful primitives.
2. **Format strings provide dual primitives**: The `%x` and `%s` directives enable arbitrary memory reads (information disclosure for ASLR bypass), while `%n` enables arbitrary memory writes (overwriting return addresses, function pointers).
3. **Archive and document parsers are high-value targets**: File formats are shared via email and messaging, automatically processed, and often trusted by users. Logic flaws (WinRAR filename confusion) and memory corruption (Word RTF heap overflow) both lead to RCE.
4. **Parser complexity breeds vulnerabilities**: Archive formats (ZIP, RAR, 7z) and document formats (RTF, PDF, Office) have complex specifications, legacy compatibility requirements, and performance optimizations that introduce security bugs.
5. **Embedded devices amplify risk**: Format string bugs in router firmware (ASUS) are particularly dangerous because devices run outdated software, are internet-facing, and provide persistent network access when compromised.
6. **Defense requires safe APIs and validation**: Using `printf("%s", user_input)` instead of `printf(user_input)`, enabling compiler warnings (`-Wformat-security`), implementing input validation, and sandboxing parsers are essential defense layers.

### Discussion Questions

1. Why do format string vulnerabilities provide both information disclosure and arbitrary write capabilities? How does the `%n` directive enable memory writes, and why is this more powerful than traditional buffer overflows?
2. How do format string exploits differ between 32-bit and 64-bit architectures in terms of stack layout, argument passing conventions, and exploitation techniques?
3. Compare the WinRAR filename confusion vulnerability (logic flaw) with the Word RTF heap overflow (memory corruption). Which is easier to exploit reliably, and why do both attack vectors remain prevalent?
4. Why do parser vulnerabilities in archive and document formats continue to be common despite decades of research into safe parsing? What makes formats like RTF, PDF, and ZIP particularly prone to security bugs?
5. How can organizations defend against malicious document and archive attacks? What role do sandboxing (Protected View, containers), static analysis, and user education play?
6. What compiler flags, static analysis tools, and runtime protections can help prevent format string vulnerabilities in C/C++ code? Why do these bugs still appear in embedded device firmware?

