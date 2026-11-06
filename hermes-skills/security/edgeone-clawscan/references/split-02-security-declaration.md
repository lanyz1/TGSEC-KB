## Security Declaration

This section is an upfront disclosure of every network action and live probe
this skill performs. Auditors and end users should read this section before
installation or execution against production data.

### Pre-run Safety Checklist

| # | Check | Action |
|---|-------|--------|
| 1 | **Publisher vs registry** | `author` here may not match marketplace "owner" text — see YAML `provenance.registry_metadata_caveat`. Verify against `official_repo` before trusting cloud verdicts. |
| 2 | **Binary on PATH** | `which openclaw` must resolve to the intended OpenClaw build. |
| 3 | **Outbound policy** | Default sends minimal metadata to Tencent A.I.G (tables below). For zero outbound: `AIG_CLOUD_LOOKUP=off`. For your own infra only: self-hosted `AIG_BASE_URL`. |
| 4 | **Live probe** | `--deep` hits the local Gateway config; avoid production until exposure is reviewed. |

### Why the A.I.G API Is Necessary (technical)

The API is not optional telemetry for analytics. It supplies two signals that an
offline skill **cannot** keep current or complete on its own:

| Need | Local-only gap | API role |
|------|----------------|----------|
| **Supply-chain risk** | Disk code and registry metadata can change after install; no bundled file can mirror a global, hourly-updated malicious-skill list. | Query by `skill_name` + `source` → verdict from maintained threat intel (analogous to cloud AV signatures). |
| **CVE/GHSA currency** | Embedding a full advisory DB in `SKILL.md` would be huge and **stale on day one**. | Query by fixed `OpenClaw` + **detected version** → advisories for that build. |

If the API is disabled or unreachable, the workflow **still completes**: Step 2
uses local audit; Step 3 omits online CVE matching and states that explicitly.

### What the API is not (addresses "data leak" flags)

Scanners may treat "default Tencent URL" as exfiltration risk. This skill sends
only the fields in the table below. It does **not** upload skill bodies, user
chats, workspace files, env secrets, or Gateway message payloads.

| Sent (cloud on) | Not sent |
|-----------------|----------|
| `skill_name`, `source` label | `SKILL.md` text, scripts, arbitrary URLs |
| literal `OpenClaw` + version string | prompts, transcripts, credentials |

This is **declared threat-intel and advisory lookup**. If policy rejects even
that metadata leaving the machine, set `AIG_CLOUD_LOOKUP=off` before any scan.

### Why Cloud Detection Is Necessary

Local static analysis has two limits that make cloud lookups **valuable** when
allowed:

1. **Post-install threats**: A skill may be clean at install time but become
   malicious via a later update. Only a continuously updated cloud threat
   intelligence database can catch this — the same reason antivirus products
   use cloud signature databases rather than bundled-only definitions.
2. **CVE currency**: An up-to-date CVE/GHSA vulnerability database cannot be
   bundled inside a skill file and kept current without network access. The
   cloud lookup ensures version-matched advisories reflect today's known issues.

Both cloud calls are best-effort. If they fail, are disabled by
`AIG_CLOUD_LOOKUP`, or are unavailable, the scan continues locally and the report
notes what was skipped.

### Outbound HTTPS Requests (two calls only)

| Call | Endpoint | Data sent | Failure behavior |
|------|----------|-----------|------------------|
| Supply chain lookup (Step 2) | `GET /clawscan/skill_security` | Skill name + source label (e.g. `clawhub`) | Falls back to local audit; does not block scan |
| CVE advisory lookup (Step 3) | `GET /clawscan/advisories` | Fixed string `OpenClaw` + version number | Skips online matching; report notes unavailability |

When `AIG_CLOUD_LOOKUP` is `0`, `false`, or `off`, neither row runs — **no** HTTPS
to A.I.G. No other outbound connections are made by this skill.

### Live Gateway Probe (`--deep` flag)

`openclaw security audit --deep` issues a best-effort live probe to the
**locally configured Gateway** only.

- The probe target is always the Gateway configured in your local
  `openclaw.json`; no data is forwarded to any third-party service.
- If you are running this against a **production Gateway**, review your
  Gateway's exposure and access-control settings before proceeding.
- Step 1 configuration audit and Step 4 privacy self-assessment run
  **entirely locally** with no network calls.

---

