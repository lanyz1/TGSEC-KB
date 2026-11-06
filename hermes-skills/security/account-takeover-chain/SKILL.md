---
name: account-takeover-chain
description: >-
 授权目标上认证强绑定、API key/secret 绑用户 token、IDOR 直读失败时的账号接管链：
 OAuth redirect/DCR、密码重置、JWT 混淆、Host 头污染重置链接。
 用户提到 ATO、账号接管、直读失败、OAuth 绑死、密码重置、量化/交易所 key 绑用户时使用。
 盘口重置优先看扩展包 gambling-password-reset-ato；GVA 走 ginvue-admin-stealth-takeover。
---

# 账号接管链

IDOR 全阴不是结案，是换认证生命周期。只打自己的号。

## 四刀（按序，阴性才换）

1. **重置面** — 短 token / 任意 code / Host 污染重置链  
   `python3 tools/ops/ato_reset_withdraw_probe.py chain --base https://授权站 --case <案> --exist-user SELF`  
   盘口：`gambling-password-reset-ato`（dummy-reset → bola-reset → 提现三件套）
2. **OAuth/OIDC** — `redirect_uri` / 缺 `state` / 隐式流  
   `python3 tools/ops/oauth_oidc_surface_probe.py --base https://授权站 --case <案>`
3. **JWT** — `alg:none` / 弱 HS256 / kid  
   `python3 tools/ops/jwt_forge_probe.py --help` · Skill `jwt-bypass-pentest`
4. **会话** — 改密后旧票仍活；Session Fixation。重置 token 外泄走 `reset-token-surface`

## 不要做

- 未授权对第三方用户发钓鱼 / 定向重置别人
- 把「能注册」当成接管
- GVA `authorityId=888` → `ginvue-admin-stealth-takeover`
- 工具不是 `case_report.py`

真源：`docs/learning/extended-pack/skills/account-takeover-chain/SKILL.md` · `docs/playbooks/OAuth2-SSO越权手法.md`
