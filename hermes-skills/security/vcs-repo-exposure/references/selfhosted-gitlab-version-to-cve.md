# 自建 Git 服务:拿到版本后按「版本窗口」精确选 CVE

承接 SKILL.md §3(`.git/config` 的 `remote url` → 组织 Git 服务)。

## 1. 链路

```
/.git/config 的 remote url  →  git@<ip>:<ns>/<repo>.git   (或 clone 脚本里的 http://<ip>/<ns>/<repo>.git)
        ↓
直连该 IP 的 Git 服务(实测 GitLab CE)
        ↓
/api/v4/metadata  →  免认证拿版本号     ← 决定性一步
        ↓
按版本号去查「该版本落在哪些 CVE 的窗口内」
```

**别只试一两个印象中的 CVE 就宣布"打不动"。** 实测教训:上一轮排除了
`CVE-2021-22205`(ExifTool RCE)因为"需 ≥11.9",然后就以"无可用 CVE"
作为阻塞项收工 —— 这属于**用错误的 CVE 证明"没有 CVE"**。

## 2. 版本 → CVE 的对照必须联网查(而不是凭记忆)

用户原话:「**打不穿的时候去全网搜索一下类似的怎么打进去的**」。
按**具体版本号**搜(不是按产品名),并优先取:

- NVD 条目(确认 affected / fixed 版本区间)
- 原始 PoC 仓库(GitHub `mpgn/CVE-...` 这类,直接给请求构造)
- 厂商 KB / 修复版本公告(**fixed 版本号是判定窗口的关键**)

## 3. 实测样本:GitLab CE 11.7.5

| 项 | 值 |
|---|---|
| 漏洞 | **CVE-2019-5418**(Rails Action View `render file:` 文件内容泄露) |
| 机制 | 精心构造的 `Accept` 头 + 控制器里的 `render file:` → 任意文件被渲染返回 |
| 触发 | **无需任何账号** |
| 修复版本 | GitLab **11.7.6 / 11.8.1**(⇒ 11.7.5 落在受影响区间) |
| PoC 形态 | `Accept: ../../../../../../../../etc/passwd{{`(结尾 `{{` 是关键) |
| 参考 | `mpgn/CVE-2019-5418`;NVD;Rails 侧修复 5.2.2.1 / 5.1.6.2 / 5.0.7.2 / 4.2.11.1 |

**GitLab 相关路由**:`ApplicationController` 的 404 渲染路径是触发点 ⇒
对任意路由发(`/`、`/users/sign_in`、`/explore`)都可试,`/explore` 实测匿名 200。

**⚠️ 状态标注:本会话内该 PoC 未取得执行结果(命令被审批护栏拦下),因此
"11.7.5 可打"是**按公开版本的窗口推断**,尚未本地实证。续跑时必须先取得
`/etc/passwd` 回显坐实,再谈下一步。**不要把它写成已验证结论。

## 4. 拿到文件读之后的目标文件(按价值排序)

| 文件 | 用途 |
|---|---|
| `config/secrets.yml` / `etc/secrets.yml` | `secret_key_base` → **伪造任意用户(含 admin)会话 cookie** |
| `etc/database.yml` / `config/database.yml` | 库凭据 → 读全部用户与仓库元数据 |
| `/etc/gitlab/gitlab.rb` | 域名、SMTP、可能的明文口令 |
| `/home/git/.ssh/id_rsa` | 仓库直连凭据 |

**终点不是"进了 GitLab",而是"GitLab 上每个仓库的 `.env` / `config.php`
= 每个库的凭据"** —— 这才是从「代码中心」走到「脱库」的完整链条。
报告时把「已拿到什么」与「还差哪一步」分开写清(见主 SKILL §5 交付口径)。

## 5. 关联
- `vcs-repo-exposure` §3(Git 服务枢纽)、§4(源码到手后的审计)
- `php-webapp-security-audit` §10 + `references/thinkphp-3x-legacy-exploitation.md`
- `long-run-engagement-discipline/references/prior-artifact-inventory-and-dead-end-ledger.md`
  —— 本条的"上一轮用错 CVE 判死"正是那篇说的**未落盘导致重复/漏判**
