## Chaining and Escalation

AI/LLM vulnerabilities can be chained or escalated for greater impact:

### Prompt Injection leading to Excessive Agency & SSRF/API Abuse

- **Scenario**: LLM plugin fetches URL content or interacts with an internal API.
- **Chain**: Prompt Injection (LLM01) -> Controls LLM -> Plugin misuse (Excessive Agency - LLM08) -> SSRF or API abuse.
- **Escalation**: Internal network access, data exfiltration, unauthorized API actions.

### Prompt Injection leading to Insecure Output Handling & Client-Side Attacks (XSS)

- **Scenario**: LLM output rendered on a webpage.
- **Chain**: Prompt Injection (LLM01) -> LLM generates JS payload -> Unsanitized display (Insecure Output Handling - LLM02) -> XSS.
- **Escalation**: Session hijacking, defacement, phishing.

### Indirect Prompt Injection leading to Sensitive Data Disclosure

- **Scenario**: LLM ingests attacker-controlled external data.
- **Chain**: Malicious prompt in external data (Indirect Prompt Injection - LLM01) -> LLM processes, appends sensitive data -> Sensitive Information Disclosure (LLM06).
- **Escalation**: Exposure of confidential data, PII.

### Vulnerable Plugin leading to Command Injection on Host

- **Scenario**: Plugin uses LLM output unsafely in a system command.
- **Chain**: Prompt Injection (LLM01) -> LLM generates malicious string -> Plugin uses it in shell command (Insecure Plugin Design - LLM07) -> Command injection.
- **Escalation**: Server compromise.

### Model Theft enabling Further Attacks or Misuse

- **Scenario**: Attacker exfiltrates a proprietary LLM (Model Theft - LLM10).
- **Chain**: Offline analysis for weaknesses -> Fine-tune for malicious use (phishing, misinformation) -> Craft better attacks against similar models.
- **Escalation**: Competitive disadvantage, reputational damage, potent attack tools.

### Data Poisoning leading to Biased/Harmful Outputs & Overreliance

- **Scenario**: Attacker taints LLM training data (Training Data Poisoning - LLM03).
- **Chain**: LLM generates flawed info -> Users/systems trust it (Overreliance - LLM09) -> Act on flawed info.
- **Escalation**: Misinformation spread, discriminatory outcomes, flawed automated decisions.

### Chaining Multiple Prompt Injections

- Initial injection slightly reduces restrictions -> Subsequent prompts build on this -> Gradual escalation to perform complex unauthorized actions.

### ETC

- **Multi‑Model Orchestration Hijack** – seize an agent delegator (e.g., TaskWeaver) and funnel follow‑ups to a malicious shadow model.
- **Context‑Window Time‑Bomb** – embed triggers that activate only after several extra turns or once the summary pushes guardrails out of context.

### Model Autonomy → Infra Compromise

- **Scenario**: Agent with shell/HTTP tools. Weak output validation allows command strings to pass through.
- **Chain**: Prompt Injection → Tool argument injection → Command execution/SSRF → Credential theft/cloud lateral movement.
- **Escalation**: Host takeover, data exfil, persistence in MLOps pipeline.

