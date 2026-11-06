## Step 10 — npm/PyPI organizational presence

```bash
# Some orgs maintain a public npm scope mirroring their brand
curl -s "https://registry.npmjs.org/-/v1/search?text=scope:$ORG&size=50" | jq '.objects[].package.name'

# Public PyPI presence
curl -s "https://pypi.org/simple/" | grep "$ORG" | head -20

# Check if scope is taken — if it's NOT, an attacker could register
# (relevant for any internal package using that scope)
curl -sI "https://registry.npmjs.org/-/org/$ORG"
```

---

