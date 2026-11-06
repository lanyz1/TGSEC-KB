## References Index

| File | Coverage | Trigger phrases |
|---|---|---|
| `probes-and-wordlists.md` | API/Swagger/GraphQL paths, cloud-bucket arsenal, JS guess-paths, vendor & cloud-native fingerprints, K8s/CI-CD exposure, doc/wiki leaks, WHOIS/RDAP, DNS catalog, Wayback CDX, copy-paste curl probes, email security analysis, origin/CDN bypass | swagger discovery, graphql introspection, subdomain takeover, cloud bucket enum, S3/GCS/Azure enum, kubernetes exposure, CI CD exposure, vendor fingerprint, WHOIS RDAP, Wayback CDX, copy paste probes, curl one-liner |
| `identity-fabric.md` | Concrete endpoints for Entra/Okta/ADFS/Google/SAML, M365 deep (Teams federation, SharePoint, OneDrive), GraphQL field-suggestion enumeration, user-enum patterns | identity fabric, SSO discovery, IdP fingerprinting, okta enum, entra enum, azure AD enum, ADFS enum, SAML metadata, Microsoft 365 deep, Teams federation, SharePoint enum, OneDrive enum, graphql field suggestion |
| `secret-patterns.md` | 48-pattern secret-regex catalog (AWS, GCP, GitHub PATs, Stripe, Slack, JWT, private keys, Anthropic/OpenAI/HuggingFace, Cloudflare, DigitalOcean, npm, PyPI, Docker Hub, Atlassian, DataDog, Sentry, ngrok) with severity & FP notes | secret scanning, secret leak, leaked credential, JWT triage, AWS key triage, Anthropic API key, OpenAI API key |
| `secret-validators.md` | 9 read-only secret validators + post-discovery enumeration workflows for AWS/GitHub/Slack/Postman/JWT/Anthropic/OpenAI/npm/Atlassian/DataDog | secret validation, post discovery workflow, AWS key triage, JWT triage |
| `dork-corpus.md` | 80+ Google/Bing/DDG dork templates across 9 categories + 13 GitHub code-search dorks tailored for targets | google dorking, bing dorking, github dorking, dork corpus |
| `recon-stack.md` | Subdomain-source stack (passive & active), infrastructure & attack-surface OSINT (Shodan/Censys/crt.sh/JARM/favicon mmh3), TLS deep audit, reverse DNS, IPv6 enumeration | subdomain enumeration, certificate transparency, crt.sh, shodan recon, censys recon, JARM, favicon mmh3, TLS deep audit, JA3 JA4, reverse DNS sweep, IPv6 enumeration |
| `breach-and-credentials.md` | Breach & leak data sources (HudsonRock, HIBP, DeHashed, IntelX, infostealer logs), email-pattern inference, email-harvest source stack | breach lookup, have I been pwned, HudsonRock cavalier, infostealer, dehashed, intelx, email harvest |
| `people-osint.md` | Search engines, username & email investigation, people search, phone OSINT, social media, public records & company info | username investigation, people search, phone OSINT, social media OSINT, public records |
| `saas-public-surfaces.md` | Postman public workspace search (verified endpoint), Stack Exchange OSINT sweep, public SaaS dork stack (Notion, Confluence, Trello) | postman workspace, stack exchange OSINT, Notion public, Confluence anonymous, Trello board |
| `specialized-osint.md` | Threat intel & IOCs, cryptocurrency OSINT, media intelligence, geospatial intelligence, regional search engines, Telegram & messaging intelligence | threat intel, IOCs, cryptocurrency OSINT, media intelligence, geospatial OSINT, regional search, Telegram intelligence |
| `recon-techniques.md` | LinkedIn employee enumeration, job-posting tech-stack analysis, Slack/Discord/Telegram workspace discovery, package-registry leak hunting (npm/PyPI/Docker Hub/Quay/GHCR), sat imagery for physical recon | LinkedIn enumeration, job posting tech stack, Slack workspace discovery, Discord server discovery, npm token leak, PyPI token leak, Docker Hub leak, sat imagery physical recon |
| `severity-matrix.md` | 80+ worked examples mapping observed conditions → finding severity (CRITICAL/HIGH/MEDIUM/LOW/INFO) | severity decision, finding severity, severity matrix |
| `sector-notes.md` | Recon notes for healthcare (DICOM), finance (SWIFT), ICS/SCADA (Modbus/BACnet), IoT, government | sector specific recon, healthcare DICOM, finance SWIFT, ICS SCADA, Modbus, BACnet |
| `tooling-install.md` | Quick-install one-liners for Subfinder, Amass, httpx, nuclei, gau, katana, gowitness, dnsx, mapcidr, naabu, sslyze, testssl.sh, etc. | tooling install, install subfinder, install nuclei, install httpx |
| `helpers-and-automation.md` | AI-assisted OSINT, archiving & evidence preservation, automation & workflow patterns, cross-module sidecar coordination, runnable secret_scan.py / h1_reference.py / dashboard.py helper notes | AI-assisted OSINT, evidence preservation, automation, sidecar, hacktivity reference, recon console |


---

