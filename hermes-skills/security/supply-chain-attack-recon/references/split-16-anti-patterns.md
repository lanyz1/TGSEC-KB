## Anti-patterns

- **DO NOT publish a typosquat / dep-confusion package without explicit, signed, scope-clarified authorization** — this affects users outside the engagement
- **DO NOT submit PRs to client repos as part of testing without specific OK** — workflow injection PoCs may be needed but they touch CI/CD and other developers
- **DO NOT scrape entire npm/PyPI for typosquat candidates** — irresponsible and noisy
- **DO NOT confuse "name is unclaimed" with "exploitable dependency confusion"** — the build system matters; many orgs use proper scope-mapping that prevents the attack
- **DO NOT touch GitHub Actions self-hosted runners** — they may be inside the client network and outside the external scope
- **DO NOT pull large Docker images blindly** — image bandwidth can be 5-50GB; review tags first

---

