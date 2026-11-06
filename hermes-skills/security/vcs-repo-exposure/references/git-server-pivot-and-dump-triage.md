# `.git` 暴露 → 自建 Git 服务枢纽:判定顺序与入口清单

本文件是 `vcs-repo-exposure` 的补充:讲清**从 `.git` 命中到「组织代码中心」的那一跳**,
以及**自建 GitLab 的入口逐条结论**(哪些通、哪些看起来通其实不通、为什么)。

---

## 一、判定顺序:三发请求定生死,再决定投不投入

拿到 `/.git/HEAD` 是 200 之后,**不要**直接开始 dump。按这个顺序打三发:

| 顺序 | 请求 | 作用 |
|---|---|---|
| ①  | `/.git/logs/HEAD` | **值不值得挖** —— 见下 |
| ②  | `/.git/config` | **枢纽线索** —— `remote url` = 开发者的 Git 服务 |
| ③  | `/.git/info/refs?service=git-upload-pack` | **用哪种 dump 方式** |

### ① `logs/HEAD` —— 一行 `Initial commit` 就是止损信号

```
<old-sha> <new-sha> <作者> <时间戳> <message>
0000000000000000000000000000000000000000 2cd78059... root <root@host> 1645673739 +0800	commit (initial): Initial commit
```

- **只有 1 行 `commit (initial): Initial commit`** ⇒ 仓库自建立起零历史。
  被 gitignore 的 `config.php` / `.env` / 库口令**从未进过仓库**,
  dump 出来 = 工作树 = 你已经能直接 GET 到的东西。**零增量,立刻止损。**
- **多行 / 有 `update by push`** ⇒ 有真实历史,值得 dump,
  并跑 `git log --all --diff-filter=D --name-only` 找**被删过的**配置文件。

> 实证:一个站点 `.git` 完整暴露(HEAD/config/index 519KB/logs/refs 全 200),
> 兴奋投入 git-dumper、折腾依赖,最后发现只有 1 个 Initial commit,
> `App/Conf/config.php` 从第一天就是 gitignore 的。
> **一个一两百字节的请求就能提前否掉整条路。**

### ③ `info/refs` —— 区分「smart HTTP」与「纯静态目录暴露」

| 响应 | 含义 | 做法 |
|---|---|---|
| 以 `001e# service=git-upload-pack` 开头的 pkt-line | 支持 smart HTTP | `git clone http://host/.git/ out` **最快** |
| 普通 HTML(报错页 / 首页 / 登录页) | `.git` 只是被当静态文件目录暴露 | clone 永远不会成功 ⇒ 用 `scripts/git_walk_dump.py` 逐对象抓 |

---

## 二、`root/` 的仓库命名规律会反向暴露资产地图

远端形如 `git@<ip>:root/<某站点标识>` 时,`<repo>` 名本身就是情报:

- 实测见过 **`root/47.75.214.54`** 这种「**用服务器 IP 当仓库名**」的习惯。
  ⇒ 说明组织**每台机器一个仓库**,把 IP 列表推出来 ≈ 资产清单推出来。
- 同一个 GitLab 上往往还躺着**同组织的其他目标**(同一个开发者 / 同一台开发机)。

---

## 三、自建 GitLab 入口清单(逐条实测结论)

判定「这是什么平台」:页面 title / `Sign in · GitLab` / `/api/v4/version`;
**免认证取版本更稳的是 `/help`页面**(响应里含 `GitLab Community Edition <x.y.z>`)。

| 入口 | 实测结果 | 结论 |
|---|---|---|
| `/explore` `/explore/projects` `/explore/groups` | 200 | 只列 **public** 项目 |
| **`/api/v4/projects`** | **200 免认证** | 列出全部 public 项目(公开面完整清单,先打这个) |
| **`/api/v4/projects/<id>` 顺序枚举 ID** | 只有个别 ID 回 200 | GitLab 项目 ID 自增;**可枚举出所有 public 项目**,其余 404。实测 1–200 只有 1 个命中 |
| `/api/v4/users` `/api/v4/version` | 403 / 401 | 需认证 |
| `/root/` (admin 用户名常为 root) | 200 | 未登录也能看 admin 的**公开**资料页 |
| `/users/sign_up` | **302** | **注册已关**;返回 200 带表单才是开放(开放时注册即可看 `internal` 仓库) |
| `/-/metrics` | 无 | 老版本有时裸奔,值得试但不常见 |
| **`.../<path>.git/info/refs?service=git-upload-pack`** | **全 401** | ⚠️ **既有私有项目与不存在的路径都回 401** ⇒ **没有 oracle,项目名/路径枚举无效**,别再花轮次 |
| avatar SSRF(CVE-2020-13379 一类,端点多达 6 种路径) | 全返回登录页 / 401 | 不是「版本老就一定中」,路径不对就是不通 |
| web 弱口令登录 | 目标性 ≤10 组 | 见 §四 |
| 同主机 `:22` SSH | 目标性 ≤5 组,失败后 **fail2ban 触发** | 见 §四 |

### 版本 → CVE 适用性(别凭「版本老」就认定能打)

- **CVE-2021-22205(ExifTool 未授权 RCE)需要 GitLab ≥ 11.9**:
  **11.7.5 不适用**,已在实测前排除,不要浪费轮次。
- 判定顺序应是:**先拿准确版本号 → 再对 CVE 的 affected range 做区间比较**,
  而不是「版本老 = 一定能打」。
- 本机 `web_search` 不可用时**不要凭记忆瞎试 PoC** —— 浪费时间且容易误报「已验证」。
  正确做法:如实说明「受 PoC 检索阻塞」,把这条列为未测,而不是硬打。

---

## 四、凭据尝试的纪律(与「禁止爆破」对齐)

- **只做目标性尝试,数量硬上限**(实测:web 10 组 + SSH 5 组即止)。
- **从组织的其他命中里提炼候选**,而不是通用字典。典型来源:
  - 公开仓库里的 `.env.sample` / `config.sample` / `docker-compose.yml`
    → 里面的 `root/root` 一类**多为框架默认样例值**,值得测但**不要当成真实口令**去下结论。
  - 把这些候选拿去测**同组织的其他服务**(MySQL 3306 等)。
- **失败要如实记录为「未命中」**,不要因为「开发者习惯用 X」就推定「所以他这里也是 X」。
- 触发 fail2ban 就是该停手的信号:继续只会把你自己的出口搭进去。

---

## 五、交付口径

写报告时必须把三件事分开,否则等于夸大:

1. **可达性证据**:`GET /.git/HEAD` → `200 ref: refs/heads/master`(附原始响应)
2. **实际拿到什么**:文件数 / 关键文件名 / `remote url` / 提交时间线
3. **没拿到什么**:如「`.git/config` 里无库口令;`App/Conf/config.php` 被 gitignore 且仓库仅 1 次提交 ⇒ 历史不存在该文件」
   **这一句必须有。**

以及:**未测 ≠ 不能打**。因外部条件(出口被封、PoC 检索不可用)没做的,要标成「未测 + 阻塞原因」,
不要写成「不可利用」,也不要写成「已验证」。
