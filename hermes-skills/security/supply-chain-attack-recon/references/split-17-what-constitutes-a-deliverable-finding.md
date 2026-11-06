## What constitutes a deliverable finding

A supply-chain finding needs ALL of:
1. **Concrete name/path** — exact internal package name, exact workflow file path, exact image tag
2. **Vulnerability mechanism** — dep-confusion / typosquat / injection / etc.
3. **Exploitability evidence** — proof the build/install would actually use the attacker's payload (not just "name is unclaimed")
4. **Severity** — calibrated to blast radius (one developer? all developers? all users of the package?)
5. **Recommendation** — specific (e.g., "register the unused name @target-internal/utils on npm AS YOUR OWN even if unused; configure `.npmrc` scope:registry mapping")

---

