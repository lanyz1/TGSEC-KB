## Methodologies

Systematic processes and tools for AI/LLM penetration testing:

### Foundational Methodologies

1.  **OWASP Top 10 for LLM Applications**: Use as a primary checklist and guiding framework for identifying common vulnerabilities (LLM01 Prompt Injection, LLM02 Insecure Output Handling, etc.).
2.  **MITRE ATLAS (Adversarial Threat Landscape for AI Systems)**: Provides a knowledge base of adversary tactics and techniques against AI systems. Useful for broader threat modeling beyond just LLMs.
3.  **NIST AI Risk Management Framework (AI RMF)**: While not a pentesting methodology per se, understanding its principles helps in assessing and communicating risks related to AI systems.

### Testing Phases & Techniques

1.  **Reconnaissance & Information Gathering**:
    - Understand the LLM's purpose, capabilities, and integrations.
    - Identify input vectors (direct prompts, API calls, file uploads, integrated tools).
    - Map out data flows and identify any external services or plugins the LLM interacts with.
    - Look for documentation on API usage, rate limits, and security features.
2.  **Automated Scanning & Analysis**:
    - **`garak`**: Open-source LLM vulnerability scanner. Probes for prompt injection, data leakage, jailbreaking, toxicity, etc., using various detectors and probes.
    - **`LLMFuzzer`**: Open-source fuzzing framework specifically for LLMs.
    - **Traditional Application Security Tools**: Use SAST/DAST on the surrounding application code that integrates with the LLM.
    - **API Fuzzers**: Test the LLM's API endpoints for standard API vulnerabilities.
    - **`NeMo Guardrails` / `Guardrails AI`**: Add input/output policy checks and schema enforcement; verify they fail closed.
    - **OpenAI Evals / promptfoo**: Build reproducible red‑team suites and regression tests for jailbreaks and data leaks.
3.  **Manual Testing / Red Teaming (Iterative & Creative Process)**:
    - **Prompt Injection Testing**:
      - Systematically try various injection techniques (direct, indirect, role-playing, obfuscation).
      - Attempt to extract the system prompt.
      - Test for privilege escalation if the LLM has different permission levels.
    - **Insecure Output Handling Testing**:
      - Craft inputs to make the LLM generate outputs that could be harmful to downstream components (XSS, SQLi payloads, command injection strings).
      - Verify if and how outputs are sanitized before use.
      - Enforce schemas for function‑calling; inject type confusion to test validators.
    - **Excessive Agency & Plugin Testing**:
      - Identify all available plugins/tools.
      - Attempt to make the LLM call these tools with malicious or unintended parameters.
      - Test for SSRF if plugins make external network requests based on LLM-influenced input.
    - **Sensitive Data Disclosure Testing**:
      - Craft prompts to try and elicit PII, credentials, or confidential information.
      - Analyze if the LLM "remembers" and might leak data from previous interactions or its training set.
    - **Denial of Service Testing**:
      - Send overly complex or recursive prompts.
      - Test input length limits.
    - **Business Logic Flaw Testing**:
      - Understand the application's business logic and how the LLM contributes.
      - Craft prompts to manipulate the LLM into making decisions that violate business rules or lead to unintended consequences.
4.  **Scenario-Based Testing**:
    - Define realistic attack scenarios based on the LLM's role and its integrations.
    - Example: "Attacker uses prompt injection to make a customer service LLM provide a fraudulent refund link."
    - Example: "Attacker crafts a malicious document that, when summarized by an internal LLM tool, exfiltrates data via an LLM plugin."
5.  **High-Impact Target Prioritization**:
    - Focus on LLMs handling sensitive data (PII, financial, health).
    - Prioritize testing LLMs with high agency (many plugins, ability to take actions).
    - Examine LLMs integrated into critical business processes.

### Defense‑in‑Depth Checklist (Practical)

- Strictly separate roles: system/developer/user prompts with unambiguous delimiters.
- Apply allow‑lists for tools, domains, file paths; deny‑lists are insufficient.
- Enforce JSON schemas on tool args and model outputs; reject on validation failure. Prefer strict validators that deny unknown fields and type coercion.
- Context provenance tags for RAG; treat external content as data only.
- Sensitive‑pattern filters pre‑ and post‑generation (secrets/PII, credentials).
- Put human‑in‑the‑loop for high‑impact actions (payments, code execution, data exfil candidates).
- Constrain network egress (egress proxy with DNS/IP/domain allow‑list) for agents.
- Log redacted prompts/outputs; avoid storing raw secrets. Enable per‑tenant logging & retention.
- Rate‑limit high‑cost tools; circuit‑break on repeated policy infractions.
- Canary tokens in context to detect unauthorized exfil in test/staging.

### Fail‑Closed Controls (Function‑Calling & Tools)

- Strict JSON Schema enforcement: reject on any mismatch, unknown fields, or oversize strings/arrays.
- Per‑tool allow‑lists: domains, file paths, and methods; deny by default.
- Human‑in‑the‑loop for high‑impact tools (filesystem, HTTP to non‑allow‑listed domains, shell).
- Output size/time guards: max tokens, timeouts, and circuit breakers on repeated violations.

### Egress & Provenance for Agents/RAG

- Route all HTTP/file operations via an egress proxy with domain/IP allow‑lists; block RFC1918/metadata IPs to prevent SSRF.
- Attach and verify content provenance (e.g., C2PA) where applicable; never action unauthenticated external instructions.
- Inject canary tokens in staging corpora and alert on attempted exfil.
- Enforce “data‑only” tagging for retrieved chunks, and block instruction‑like patterns at merge time.

### Incident Runbooks (short)

- Prompt injection with tool misuse: immediately disable the impacted tool, add temporary domain blocks in the egress proxy, reduce `max_output_tokens`, and enable human review. Post‑mortem with regression prompts.
- Sensitive text leakage: rotate exposed secrets, purge logs with sensitive data, enable redaction filters, and add targeted evals to prevent recurrence.

### Specialized Tools & Libraries

- **`LangChain` / `LlamaIndex`**: Understanding their components can help identify potential weaknesses in applications built with them.
- **Adversarial Robustness Toolbox (ART)**: Python library for ML security.
- **`promptfoo`**: Tool for testing and evaluating LLM prompt quality, adaptable for security testing.
- **PyRIT (Microsoft 2024)**: Python Risk Identification Toolkit for automated red-teaming; orchestrates multi-turn attacks, generates adversarial suffixes, and tracks objective completion.
- **Garak 0.9+**: Updated with 2025 probe sets for GPT-4o, Claude 3.5, Gemini Ultra; includes hallucination, toxicity, and PII leakage detectors.
- **NeMo Guardrails**: NVIDIA's runtime guardrails; test for bypass via nested JSON, prompt fragments, and policy conflicts.
- **Guardrails AI**: Schema-driven validation; attempt type coercion, over-long strings, and missing required fields to test fail-closed behavior.

