## Shortcut

- Understand the AI system, its components (LLM, APIs, data sources, plugins), and functionalities. Identify critical assets and potential business impacts.
- Collect details about the model, underlying technologies, APIs, and data flow.
- Vulnerability Assessment:
  - Use tools like `garak`, `LLMFuzzer` to identify common vulnerabilities.
  - Craft prompts to test for injections, jailbreaks, and biased outputs.
  - Probe for data leakage and insecure output handling.
  - Assess plugin security and excessive agency.
- Attempt to exploit identified vulnerabilities and chain them for greater impact (e.g., prompt injection leading to data exfiltration via excessive agency).
- If access is gained, explore possibilities like model theft, further data exfiltration, or lateral movement.

