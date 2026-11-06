## Step 11 — Frontend and third-party dependency checks

### Compromised CDN detection (polyfill.io, etc.)

Known-compromised CDNs and analytics services have been weaponized. Check target's public HTML/JS:

```bash
# Detect usage of polyfill.io and similar historically-compromised services
curl -s https://target.com | grep -i polyfill
curl -s https://target.com | grep -iE '(polyfill\.io|cdn\.jsdelivr\.net.*polyfill|babel\.min\.js)'

# Check JavaScript bundles
for bundle in public/*.js main.*.js app.*.js; do
  grep -i polyfill "$bundle" && echo "FOUND: $bundle"
done
```

Reference: polyfill.io was compromised in 2024 to serve malicious payloads. Presence = supply-chain risk.

---

