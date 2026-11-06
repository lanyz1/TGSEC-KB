## LLM / AI Features

- [ ] Prompt injection via user input passed to LLM
- [ ] Indirect injection via document/URL the AI processes
- [ ] IDOR in chat history (enumerate conversation IDs)
- [ ] System prompt extraction via roleplay/encoding
- [ ] RCE via code execution command-line abuse
- [ ] ASCII smuggling (invisible unicode in LLM output)

### Agentic AI Hunting (OWASP ASI01-ASI10)

When target has AI agents with command-line access, these are the 10 attack classes:

| ID | Vuln Class | What to Test |
|----|-----------|-------------|
| ASI01 | Prompt injection | Override system prompt via user input -- make agent ignore its rules |
| ASI02 | Tool misuse | Make AI calltools with attacker-controlled params (SSRF via "fetch URL", RCE via code command-line) |
| ASI03 | Data exfil | Extract training data / PII via crafted prompts that leak context |
| ASI04 | Privilege escalation | Use AI to access admin-onlytools -- agent has broader perms than user |
| ASI05 | Indirect injection | Poison document/URL the AI processes -- hidden instructions in fetched content |
| ASI06 | Excessive agency | AI takes destructive actions without confirmation -- delete, send, pay |
| ASI07 | Model DoS | Craft inputs that cause infinite loops, excessive token usage, or OOM |
| ASI08 | Insecure output | AI generates XSS/SQLi/command injection in its output that gets rendered |
| ASI09 | Supply chain | Compromised plugins/tools/MCP servers the AI calls |
| ASI10 | Sensitive disclosure | AI reveals internal configs, API keys, system prompts, user data |

**Triage rule:** ASI alone = Informational. Must chain to IDOR/exfil/RCE/ATO for paid bounty.

