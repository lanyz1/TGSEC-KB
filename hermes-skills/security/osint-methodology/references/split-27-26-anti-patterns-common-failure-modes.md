## 26. Anti-Patterns & Common Failure Modes

A non-exhaustive list of mistakes that come up often.

- **Single-source attribution.** Three weak OR one strong + one weak.
- **Trusting vendor labels as ground truth.** Treat labels as hypotheses.
- **Assuming favicon-hash = ownership.** Shared infra, shared CMS templates, shared CDN.
- **Asserting 1:1 bridge flows.** Bridges mint and burn; aggregators rebalance.
- **Treating snippet-only Google dorks as confirmed.** TENTATIVE until you visit.
- **Pasting real PII / creds into cloud LLMs.** Local models for sensitive analysis.
- **Mirror-imaging the threat actor.** They don't think like you.
- **Attribution by IP geolocation.** IPs lie; VPNs and residential proxies exist.
- **Ignoring the 7-day optimistic-rollup challenge window.** L2 finality is delayed.
- **Ignoring CT-log lag.** New certs take minutes-to-hours to surface; absence ≠ doesn't exist.
- **Counting Wayback snapshots as "the site at time T."** Best-effort; many requests fail.
- **Trusting `whoami` from a discovered API.** Could be a honeypot.
- **Letting the asset graph carry untyped strings.** Every discovery is an asset.
- **Skipping the scope check.** Ask once when in doubt.
- **Forgetting UTC.** Local time creates correlation bugs.
- **Continuing to probe after a WAF block.** See §6.4 — back off.
- **Skipping confidence-upgrade documentation.** TENTATIVE assets need a path to CONFIRMED.
- **Treating exec-summary writing as an afterthought.** See §31 — plan deliverables at engagement start, not at the end.

---

