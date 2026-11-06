## Safe Verdict Template

If the skill is assessed as safe and there are no confirmed Medium+ findings, output a brief plain-language audit summary card followed by a one-line verdict. The card must use everyday language — avoid all security jargon. Non-technical users should be able to understand every row without prior knowledge.

**Card format:**

```
✅ {skill} passed security check

| Check | Result |
|-------|--------|
| Source trust | {✅ Known trusted source / ⚠️ Unknown source — watch for future updates} |
| Access to your files | {✅ No — reads only its own config / ⚠️ Yes, but consistent with stated purpose} |
| Hidden network calls | {✅ None detected / ✅ Only calls endpoints declared in its description} |
| Dangerous operations | ✅ None found |

No high-risk issues detected. You may proceed with installation. (This is a static analysis and does not cover risks introduced by future updates.)
```

Rules:
- Always fill in all four rows; never leave a row blank or omit it.
- Use the ✅ / ⚠️ variants that match the actual audit evidence; do not default to ✅ for rows without evidence.
- Keep each cell to one short phrase — no multi-line explanations inside the table.
- The one-line verdict below the table is mandatory; do not delete it.

