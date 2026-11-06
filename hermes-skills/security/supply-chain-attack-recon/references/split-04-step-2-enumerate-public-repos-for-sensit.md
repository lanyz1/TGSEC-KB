## Step 2 — Enumerate public repos for sensitive artifacts

```bash
ORG="targetorg"

# List public repos
gh repo list "$ORG" --limit 100 --json name,description,visibility,defaultBranchRef

# Look for high-signal repo names
gh repo list "$ORG" --limit 100 --json name | jq -r '.[].name' | grep -iE "internal|infra|deploy|config|secret|setup|sdk|api"

# Clone all (small org) or selectively
gh repo clone "$ORG/$repo_name"
```

---

