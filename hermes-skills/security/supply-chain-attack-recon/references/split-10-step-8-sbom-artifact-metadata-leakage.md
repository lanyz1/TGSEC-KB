## Step 8 — SBOM / artifact metadata leakage

```bash
# Look for SBOMs published as releases (SPDX, CycloneDX format)
gh api "repos/$ORG/$REPO/releases" --jq '.[] | .assets[] | select(.name | test("sbom|cyclonedx|spdx"; "i")) | .browser_download_url'

# JSON dependency lockfiles in releases
gh api "repos/$ORG/$REPO/releases" --jq '.[] | .assets[] | select(.name | test("lock|deps"; "i")) | .browser_download_url'

# Exact-version-pinned deps → known-CVE chaining
# Compare versions to nuclei nvd templates or osv.dev for known vulns
curl -s "https://api.osv.dev/v1/query" -d '{"package": {"name": "lodash", "ecosystem": "npm"}, "version": "4.17.10"}'
```

---

