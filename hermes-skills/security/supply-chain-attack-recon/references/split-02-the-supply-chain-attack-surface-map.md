## The supply-chain attack surface map

```
Target Org
├── Public GitHub Org → workflow files → secrets exfil opportunities
├── Internal package names in JS/Android bundles → dependency confusion
├── Docker images on public registries → secrets in layers, RCE on pull
├── SBOM / artifact metadata → exact dep versions for known-vuln chaining
├── npmrc / pip.conf in repos → internal registry URL disclosure
├── External package dependencies → typosquat name candidates
└── Build/release pipelines → injection if pull_request_target etc.
```

---

