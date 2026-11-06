## Pitfalls
- **OSINT paralysis** — endless recon without translating findings to attack surface is wasted time. Every piece of OSINT must lead to a testable hypothesis.
- **Data aggregation without deduplication** — collecting 5000 subdomains with 80% duplicates wastes scan time. Deduplicate aggressively.
- **Passive vs active confusion** — passive OSINT (DNS, CT logs, WHOIS) doesn't touch the target. Active OSINT (port scanning, HTTP probing) does. Know which mode you're in.
- **Breach data ethical handling** — breach corpora contain real user credentials. Never use them without explicit authorization. Never store them unencrypted.
- **Tool overlap** — running subfinder, amass, assetfinder, and findomain all do the same thing. Pick one and use it well.


---

