## Day 6: Impact Assessment and Vulnerability Classification

- **Goal**: Learn to assess and classify vulnerabilities by their real-world impact and exploitability.
- **Activities**:
  - _Reading_:
    - [CVSS v4.0 Specification](https://www.first.org/cvss/v4.0/specification-document)
    - [CVSS v3.1 Specification (legacy, still widely used)](https://www.first.org/cvss/v3.1/specification-document)
    - [Exploit Prediction Scoring System (EPSS)](https://www.first.org/epss/)
  - _Online Resources_:
    - [MITRE ATT&CK Framework](https://attack.mitre.org/)
    - [Common Weakness Enumeration (CWE)](https://cwe.mitre.org/)
    - [National Vulnerability Database](https://nvd.nist.gov/)
  - _Exercise_: Classify 10 real CVEs by type, impact, and exploitability

### Understanding Impact Categories

**Remote Code Execution (RCE)**:

- **Definition**: Attacker can execute arbitrary code on the target system remotely without physical access.
- **Impact**: Highest severity - complete system compromise possible.
- **Examples from This Week**:
  - CVE-2024-27130 (QNAP): Stack overflow → RCE
  - CVE-2024-2883 (Chrome ANGLE): UAF → RCE via heap corruption
  - CVE-2023-4863 (libWebP): Heap overflow → RCE
  - CVE-2024-7971 (V8): Type confusion → RCE via arbitrary R/W
  - CVE-2023-35086 (ASUS Router): Format string → RCE via stack overwrite

**Local Privilege Escalation (LPE)**:

- **Definition**: Attacker with limited access can gain higher privileges (user → root/SYSTEM).
- **Impact**: High severity - allows persistence, defense evasion, lateral movement.
- **Examples**:
  - Windows Kernel TOCTOU (CVE-2024-26218): User → SYSTEM via race condition exploitation
  - Driver IOCTL bugs: Standard user → Administrator/SYSTEM

**Information Disclosure / Info Leak**:

- **Definition**: Attacker can read data they shouldn't have access to.
- **Impact**: Medium to High - often chained with other bugs to bypass ASLR.
- **Examples**:
  - Format string leaks: Bypass ASLR by leaking libc addresses
  - Speculative execution (Spectre): Leak kernel memory from userland
  - Uninitialized memory reads: Leak heap/stack contents

**Denial of Service (DoS)**:

- **Definition**: Attacker can make a service unavailable without gaining code execution.
- **Impact**: Low to Medium - disrupts availability but doesn't compromise confidentiality/integrity.
- **Examples**:
  - Decompression bombs: Exhaust memory/CPU
  - Algorithmic complexity attacks: Trigger worst-case performance
  - Crash bugs without exploitable primitives

### Exploitability Factors

**Attack Complexity**:

- **Low**: Attacker can repeatedly exploit with minimal effort.
- **High**: Requires complex preparation, rare conditions, or user interaction.

**Example Comparison**:

- **Low Complexity**: Buffer overflow in network daemon (CVE-2024-27130)
- **High Complexity**: Browser type confusion requiring specific JavaScript execution order (CVE-2024-7971)

**Attack Vector**:

- **Network**: Exploitable remotely over network (highest threat)
- **Adjacent**: Requires local network access
- **Local**: Requires local access to system
- **Physical**: Requires physical access

**Privileges Required**:

- **None**: No authentication needed
- **Low**: Standard user access required
- **High**: Administrative access required

**User Interaction**:

- **None**: Fully automated exploitation
- **Required**: Victim must perform action (click link, open file)

### CVSS Scoring System

**Base Score Components** (Intrinsic qualities):

- **Attack Vector** (AV): Network/Adjacent/Local/Physical
- **Attack Complexity** (AC): Low/High
- **Privileges Required** (PR): None/Low/High
- **User Interaction** (UI): None/Required
- **Scope** (S): Unchanged/Changed (does exploit affect resources beyond vulnerable component?)
- **Impact to** Confidentiality (C), Integrity (I), Availability (A): None/Low/High

**Temporal Score Components** (Change over time):

- **Exploit Code Maturity**: Not Defined/Proof-of-Concept/Functional/High
- **Remediation Level**: Official Fix/Temporary Fix/Workaround/Unavailable
- **Report Confidence**: Unknown/Reasonable/Confirmed

**Environmental Score** (Organization-specific):

- Modified Base Metrics based on local environment
- Considers organizational security requirements

**Score Ranges**:

- 0.0: None
- 0.1-3.9: Low
- 4.0-6.9: Medium
- 7.0-8.9: High
- 9.0-10.0: Critical

### Exercise: Classify 10 Real CVEs

For each CVE below, determine:

1. **Vulnerability Class** (Stack overflow, UAF, Type confusion, etc.)
2. **Impact Type** (RCE, LPE, Info Leak, DoS)
3. **CVSS Score Estimate** (Low/Medium/High/Critical)
4. **Exploitability** (Low/Medium/High complexity)
5. **Priority** (How urgently should this be patched?)

**Cases for Classification**:

1. **CVE-2024-27130** (QNAP Stack Overflow)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

2. **CVE-2024-2883** (Chrome ANGLE UAF)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

3. **CVE-2023-4863** (libWebP Heap Overflow)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

4. **CVE-2024-7971** (V8 TurboFan Type Confusion)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

5. **CVE-2023-35086** (ASUS Router Format String)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

6. **CVE-2022-34718** (Windows tcpip.sys EvilESP)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

7. **7-Zip Symlink Path Traversal** (CVE-2025-11001/11002)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

8. **CVE-2023-4155** (Linux KVM AMD SEV Double-Fetch)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

9. **CVE-2021-24105** (Dependency Confusion Attack)
   - Class: ?
   - Impact: ?
   - CVSS: ?
   - Exploitability: ?
   - Priority: ?

10. **CVE-2023-44487** (HTTP/2 Rapid Reset)
    - Class: ?
    - Impact: ?
    - CVSS: ?
    - Exploitability: ?
    - Priority: ?

### Common Mistake Patterns in Classification

1. **Confusing Impact with Exploitability**:
   - High impact doesn't mean easy to exploit
   - Critical CVE might have high complexity

2. **Ignoring Real-World Context**:
   - Lab exploit != Production exploitation
   - Mitigations affect real-world exploitability

3. **Over-relying on CVSS**:
   - CVSS is standardized but imperfect
   - Context matters: SQL injection in admin panel vs. public-facing

4. **Neglecting Chaining**:
   - Info leak alone: Medium severity
   - Info leak + RCE primitive: Critical
   - Consider full attack chain

### Industry Standards and Reporting

**Responsible Disclosure**:

1. Report to vendor through appropriate channel (security@, bug bounty)
2. Allow reasonable time for fix (typically 90 days)
3. Coordinate public disclosure
4. Publish technical details after fix available

**Reporting Templates**:

1. **Summary**: One-sentence description
2. **Impact**: What can attacker achieve?
3. **Affected Versions**: Precisely list versions
4. **Prerequisites**: Auth required? User interaction?
5. **Steps to Reproduce**: Detailed, repeatable
6. **Proof of Concept**: Code/commands to demonstrate
7. **Suggested Fix**: If applicable
8. **References**: Related CVEs, papers

### Key Takeaways

1. **Impact != Exploitability**: Critical bugs can be hard to exploit; easy exploits might have limited impact.
2. **Context is crucial**: Same bug class has different severity in different contexts.
3. **Standardization helps**: CVSS provides common language, but isn't perfect.
4. **Chaining amplifies impact**: Multiple medium bugs can create critical exploit chain.
5. **Reporting matters**: Clear, detailed reports help vendors fix vulnerabilities faster.

### Discussion Questions

1. How should organizations prioritize patching when faced with hundreds of vulnerabilities?
2. What are the limitations of CVSS scoring, and how can they be addressed?
3. When is it ethical to publicly disclose a vulnerability before a patch is available?
4. How do bug bounty programs affect the economics of vulnerability research and disclosure?

