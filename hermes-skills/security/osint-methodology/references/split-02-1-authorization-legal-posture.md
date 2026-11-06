## 1. Authorization & Legal Posture

This skill is intended for assets the operator owns or has written authorization to assess (red-team rules of engagement, bug-bounty in-scope assets, ASM contracts).

**Soft scope check:** when a user asks you to act against a target whose authorization isn't established earlier in the conversation, ask once before proceeding:

> *"Quick scope check: is this a target you own or have written authorization to assess (e.g., a red-team engagement, in-scope bug-bounty asset, or your own infrastructure)? I want to make sure we stay on the right side of the engagement boundary."*

Once authorization is asserted, proceed without re-asking. If the user explicitly states the engagement type (e.g., "this is for our pentest of acme.com under contract"), you don't need to ask again.

**Always-on guardrails (regardless of authorization):**
- Never weaken auth, rate limits, banners, or any safety control that enforces scope on the target side.
- Never run destructive probes (true SYN scans on production, masscan at line rate, fuzzing/brute-force) outside an explicit DEEP / `--aggressive` mode.
- Never paste real PII, valid credentials, session tokens, API keys, or other secrets into cloud-hosted LLMs or third-party services.
- Never take action against assets outside the documented scope, even if "obviously related" (subsidiaries, vendors, employees' personal accounts, etc.).

---

