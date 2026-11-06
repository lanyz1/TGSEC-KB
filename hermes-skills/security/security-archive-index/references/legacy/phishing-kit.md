<!-- archived from /root/.hermes/skills/security/phishing-kit/SKILL.md on 2026-10-21 -->

---
name: phishing-kit
description: >-
  Phishing toolkit — page cloning, email spoofing, credential harvesting, pretext generation. Trigger: phishing, phish, credential harvest, spoof email, clone page, 钓鱼, 伪造页面.
---

> 归档卡：原目录 `/root/.hermes/skills/security/phishing-kit`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/phishing-kit/…')`，不要相对 `references/legacy/` 解析。

# Phishing Kit

Automated phishing infrastructure generation.

## Workflow
1. Clone target page → extract HTML/CSS/JS → rewrite form actions
2. Configure credential capture → email/webhook delivery
3. Generate pretext email → spoof sender → embed tracking pixel
4. Deploy landing page → ngrok/serveo/VPS → test capture
5. Optional: MFA token capture via reverse proxy (evilginx-style)

## Tools
- page_cloner.py: Clone target login page with form rewriting
- pretext_gen.py: Generate convincing email templates
- spoof_tools.py: Email header manipulation and SPF/DKIM analysis

## Output
Write cloned page + capture server + email templates to disk.
