## 5. Do NOT (hard rules)

- DO NOT paste creds, session tokens, API keys, real PII, infostealer logs, or unique pivots into cloud LLMs (ChatGPT, Claude.ai, Gemini, Perplexity). Use local models (Ollama, LM Studio, GPT4All) for sensitive analysis.
- DO NOT assume vendor labels are ground truth. Cross-label sanity: TRM, Chainalysis, Arkham can disagree. Treat every label as a hypothesis.
- DO NOT assume 1:1 bridge flows. Bridges/mixers/wrappers introduce mint/burn semantics; validate with on-chain proofs.
- DO NOT assert ownership from a single signal. Favicon-hash overlap, shared CT issuer, shared NS — each is a hypothesis. Need rule-of-three.
- DO NOT run fuzzing, SYN scans, masscan, or `nuclei fuzzing/*` templates outside an explicit DEEP / `--aggressive` mode.
- DO NOT use a credential validator to do anything except read-only verification (no create/delete/send).
- DO NOT mirror-image (assume the target thinks like you do). Separate capability from intent and sponsorship.
- DO NOT confuse correlation with control.
- DO NOT escalate when you encounter active defenses; back off and document (see §6.4).

---

