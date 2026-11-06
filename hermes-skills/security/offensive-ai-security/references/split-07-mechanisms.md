## Mechanisms

AI/LLM vulnerabilities stem from several core mechanisms:

- **Instruction Following & Ambiguity**: LLMs are designed to follow instructions (prompts). Ambiguous, malicious, or cleverly crafted prompts can trick them into unintended actions. The boundary between instruction and data is often blurry.
- **Data Dependency**: Models learn from vast datasets.
  - **Training Data Issues**: Biased, poisoned, or sensitive data in training sets can lead to skewed, insecure, or privacy-violating outputs.
  - **Input Data Issues**: Untrusted input data (user prompts, documents, web content) can be a vector for attacks like indirect prompt injection.
- **Complexity and Lack of Transparency ("Black Box" Nature)**: The internal workings of large models are complex and not always fully understood, making it hard to predict all possible outputs or identify all vulnerabilities.
- **Integration with External Systems (Agency & Plugins)**: LLMs are often given "agency" – the ability to interact with other systems, APIs, and tools (plugins). If these integrations are insecure or the LLM has excessive permissions, it can become a powerful attack vector.
- **Output Handling**: How the LLM's output is used by downstream applications is critical. If unvalidated output is fed into other systems, it can lead to code execution, XSS, SSRF, etc.
- **Resource Consumption**: LLMs can be resource-intensive. Specially crafted inputs can lead to denial of service by exhausting computational resources.
- **Supply Chain**: Vulnerabilities can exist in pre-trained models, third-party datasets, or the MLOps pipeline components.
- **Overreliance**: Humans placing undue trust in LLM outputs without verification can lead to the propagation of misinformation or the execution of flawed, AI-generated advice/code.
- **Policy‑Layer Conflicts** – layered provider, vendor and application rules can clash, creating latent bypass windows.
- **Sparse Fine‑Tuning Drift** – lightweight adapter training frequently overrides base‑model safety alignment.
- **Multi‑Modal Expansion** – V‑L and audio‑language models inherit text flaws while adding steganographic channels.
- **Model Extraction via Embeddings** – probing embedding space boundaries through carefully crafted prompts can leak training data membership or approximate model parameters.
- **Virtualization Attacks** – convincing the model it operates in a test/sandbox environment to bypass production safety rules.
- **Constitutional Jailbreaks** – exploiting conflicts between layered safety rules (provider policy vs. developer system prompt vs. user context).
- **Tool Chaining Escalation** – multi-agent frameworks allowing Agent A to delegate to Agent B to reach privileged Agent C, bypassing single-hop restrictions.
- **Memory Poisoning** – injecting persistent malicious instructions into agent memory systems (AutoGPT, CrewAI, LangChain Memory).
- **Tokenization Exploits** – zero-width characters, Unicode normalization mismatches between input sanitizers and model tokenizers.

