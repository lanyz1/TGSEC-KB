## ⚠️ Language Detection Rule — EXECUTE BEFORE ANYTHING ELSE

> **This is the FIRST and HIGHEST-PRIORITY rule. Violating it invalidates the entire run.**

**Step 1 — Detect language immediately. Do this BEFORE calling any tool or running any command.**

Read the user's triggering message carefully and identify its language.

| User message language | Output language |
|-----------------------|-----------------|
| English (e.g. "run a security audit") | **English — entire report in English** |
| Chinese (e.g. "开始安全体检") | Chinese |
| Japanese / Korean / French / other | Match that language |
| Cannot determine | Default to Chinese |

**Step 2 — Lock the output language for the entire run.**
Every piece of user-visible output produced during this skill run — including
progress updates, section titles, table headers, status labels, prose,
recommendations, and the final report — **must** be written exclusively in
the detected language.

**Step 3 — Enforce consistency end-to-end.**
- Do **not** mix languages at any point.
- Do **not** start in one language and silently switch to another mid-run.
- **Common failure pattern to avoid**: user writes in English → you default to Chinese template → WRONG. Always match the user's input language.
---

