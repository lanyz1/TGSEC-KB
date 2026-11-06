---
name: identity-federation
description: >-
  联邦身份路由卡。触发：SAML、OIDC、OAuth2 SSO、token 混淆、联邦认证、
  Passkey、WebAuthn、FIDO2、TLS 1.3 0-RTT、RFC9700。
  grant_type=password 立刻切 oauth2-password-grant-login-testing。
---

# 联邦身份（路由卡）

## 真源

1. `docs/playbooks/OAuth2-SSO越权手法.md`
2. `docs/playbooks/逆向技能缺口与路由手法.md`
3. `docs/playbooks/域渗透分流手法.md`

```bash
python3 tools/ops/hypothesis_route.py --signal "WebAuthn passkey"
python3 tools/ops/reverse_skill_route.py --hint "SAML OIDC"
python3 tools/ops/css_query.py list-skills --module 32
```

| 线索 | 走 |
|------|----|
| `grant_type=password` | `oauth2-password-grant-login-testing` |
| OAuth2 / OIDC 授权码 / `redirect_uri` | `oauth-oidc-flow` · `oauth_oidc_surface_probe.py` · `docs/playbooks/OAuth2-SSO越权手法.md` |
| Passkey / WebAuthn / 0-RTT | 长文 `docs/learning/hypothesis-pack/techniques/auth-modern.md` |
| JWT 算法/撤权 | `jwt-bypass-pentest` |
| 域身份 / AD | `ad-windows-router` |
| CSS IAM | `python3 tools/ops/css_query.py list-skills --module 32` |

GVA / 芋道业务身份仍走对应专卡，不要用本卡替代。
