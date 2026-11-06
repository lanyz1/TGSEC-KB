## Step 9 — Internal registry URL leakage

```bash
# .npmrc patterns
grep -r "registry=" .                                            # in cloned repos
grep -r "_authToken=" .                                          # leaked npm token!
grep -r "@.*registry=" .                                          # scoped registry

# pip config
grep -r "extra-index-url" .
grep -r "index-url" .

# Gradle / Maven
grep -rE "(mavenCentral|maven\s*\{)" .
grep -r "url.*\(.*nexus" .

# Each leaked internal URL is intel — flag the URL itself even if not directly exploitable
```

---

