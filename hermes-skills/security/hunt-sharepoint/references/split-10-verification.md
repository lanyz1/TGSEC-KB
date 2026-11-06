## Verification

Run this self-test to confirm sharepoint hunting readiness:

1. **Skill integrity** — confirm the skill file is readable and well-formed:
   ```bash
   grep -q "name: hunt-sharepoint" SKILL.md && echo "PASS: skill frontmatter present" || echo "FAIL"
   grep -q "revision_date:" SKILL.md && echo "PASS: revision date present" || echo "FAIL"
   ```

2. **Category check** — confirm the skill has a category:
   ```bash
   grep -q "category:" SKILL.md && echo "PASS: category present" || echo "FAIL"
   ```

3. **Pitfalls section** — confirm pitfalls are documented:
   ```bash
   grep -q "^## Pitfalls" SKILL.md && echo "PASS: pitfalls section present" || echo "FAIL"
   ```

All 3 tests verify the skill is properly structured and ready for use.

---

