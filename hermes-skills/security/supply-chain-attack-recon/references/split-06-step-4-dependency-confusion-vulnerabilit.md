## Step 4 — Dependency-confusion vulnerability check

For each internal-looking package name discovered:

```bash
NAME="@target-internal/utils"   # example

# npm check
curl -sI "https://registry.npmjs.org/$NAME" | head -1
# 404 → name is registerable → DEPENDENCY-CONFUSION POSSIBLE

# pypi check (no scopes, just name)
NAME="target_utils"
curl -sI "https://pypi.org/project/$NAME/" | head -1
# 404 → name is registerable

# rubygems
curl -sI "https://rubygems.org/api/v1/gems/$NAME.json" | head -1

# Go modules — slightly different, since module names are URLs
# Check if module path is reachable
curl -sI "https://proxy.golang.org/github.com/$ORG/$NAME/@latest" | head -1
```

**Severity calibration:** Just because a name is unclaimed doesn't mean it's exploitable. You also need:
1. Evidence the target's BUILD SYSTEM resolves names from public registries (not just their internal one)
2. OR evidence the target's package manager is configured insecurely (e.g., `.npmrc` without `@scope:registry=` mapping)
3. OR the package would be installed by their builds (it's actually in package.json, not just referenced in dead code)

A 404 on registry without supporting context is INFORMATIONAL only.

---

