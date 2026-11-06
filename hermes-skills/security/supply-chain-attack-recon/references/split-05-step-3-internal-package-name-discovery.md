## Step 3 — Internal package-name discovery

### From JS bundles

```bash
# JS bundles are the easiest source of internal npm names
curl -sk https://target.com/main.js | grep -oE '@[a-z-]+/[a-z-]+' | sort -u
curl -sk https://target.com/main.js | grep -oE 'require\("[^"]+"\)' | sort -u

# Look for scoped names that are NOT public on npm
for pkg in @target/utils @target-internal/api @companybrand/sdk; do
  status=$(curl -sI "https://registry.npmjs.org/$pkg" | head -1 | awk '{print $2}')
  echo "  $pkg → $status"
  # 404 → name unclaimed on public npm → DEPENDENCY-CONFUSION CANDIDATE
done
```

### From GitHub repo package.json files

```bash
# Public repos with package.json that reference internal scopes
for repo in $(gh repo list "$ORG" --limit 50 --json name --jq '.[].name'); do
  pkg=$(gh api "repos/$ORG/$repo/contents/package.json" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null)
  echo "$pkg" | jq -r '.dependencies // {} | keys[]' 2>/dev/null | grep -E '^@[a-z-]+/'
done | sort -u
```

### From Python projects

```bash
# Internal pip package names
for repo in $(gh repo list "$ORG" --limit 50 --json name --jq '.[].name'); do
  gh api "repos/$ORG/$repo/contents/requirements.txt" --jq '.content' 2>/dev/null | base64 -d 2>/dev/null
done | sort -u | grep -vE '^(requests|django|flask|numpy|pandas|...common)'
```

---

