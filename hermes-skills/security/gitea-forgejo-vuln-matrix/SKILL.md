---
name: gitea-forgejo-vuln-matrix
description: "Use when 打自建 Gitea/Forgejo：12 条 IDOR、SSRF、restore 文件读、PAT 越权、artifact 越权读。"
---

# Gitea / Forgejo 漏洞矩阵（12 条，abraxas 2026-10 批次）

## 一句话
`github.com/abraxas` 在 Gitea / Forgejo 上一次性产出 12 个独立漏洞，每条都有 PoC + README（Class / Reach / 受影响精确版本 / 源码行号）。本卡把它们压成一张矩阵，命中的直接去抓 README 取触发条件。

## 清单
| 仓 | 级别 | 可达 | 类型 | 要点 |
|---|---|---|---|---|
| `forgejo-hostmatcher-0001-ssrf` | High | Remote | SSRF | hostmatcher allows 0.0.0.1 as a public IP |
| `forgejo-keys-idor` | High | Remote | IDOR | GET /api/v1/user/keys/{id} returns other users SSH and deploy keys |
| `forgejo-openid-discovery-ssrf` | High | Remote | SSRF | OpenID discovery fetches attacker-controlled URLs |
| `forgejo-restore-file-open` | High | Remote | File read | restore-repo follows dump-side file:// into attachments |
| `gitea-artifact-v4-readall` | Gitea | Medium 6.5 | Authenticated POST /twirp/github.actions.results.api.v1.... | Denial of Service (Unbounded Artifact v4 ReadAll) |
| `gitea-follow-existence` | Gitea | Medium 4.3 | Authenticated PUT /api/v1/user/following/{username} | Account Enumeration (Follow 204 vs 404) |
| `gitea-git-redir-ssrf` | Gitea | High 7.7 | Authenticated POST /api/v1/repos/migrate | Authenticated SSRF (Git HTTP Redirect Follow) |
| `gitea-hostmatcher-0000-ssrf` | Gitea | High 7.7 | Authenticated POST /api/v1/repos/{owner}/{repo}/hooks | Authenticated SSRF (0.0.0.0/8 hostmatcher residual) |
| `gitea-public-only-pat-org` | Gitea | Medium 6.5 | Authenticated POST /api/v1/orgs | Authorization Bypass (Public-Only PAT Creates Private Org) |
| `gitea-restore-file-open` | Gitea | Medium 4.2 | Authenticated CLI gitea restore-repo | Local File Inclusion (restore file:// os.Open) |
| `gitea-stargazers-hidden` | Gitea | Medium 5.3 | Unauthenticated GET /api/v1/repos/{owner}/{repo}/stargazers | Information Disclosure (Hidden Usernames via Stargazers) |
| `gitea-user-keys-idor` | Gitea | High 7.5 | Authenticated GET /api/v1/user/keys/{id} | Authenticated IDOR (SSH / Deploy Key Disclosure) |

## 逐条要点（Class/Reach 原文摘录）
（该产品批次未逐条摘录，直接取 README）

## 怎么用
1. **先定版本**：这批洞全部绑定精确小版本（如 `4.2.0` / `3.53.4` / `7.2.20`），版本不对别浪费时间。
2. **取原文**：`curl -sL https://raw.githubusercontent.com/abraxas/<仓名>/main/README.md` —— README 里 `Class` / `Reach` / 受影响版本 / 源码定位四段就够判断能不能打。
3. **按可达性分流**：`Remote` 的先打；`Local`/`Authenticated` 的留到已有 shell 或低权账号之后。
4. **一条一条验**：这批是同产品的平行洞，别把一个的结论套到另一个上（同产品不同入口的前置条件常常不一样）。
