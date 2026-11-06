---
name: vcs-repo-exposure
description: "触发: .git/.svn 暴露、git-dumper 失败、源码到手要审。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, recon, git, svn, source-disclosure, credential-hunt]
    related_skills: [sensitive-dir-credential-hunt, recon-discriminators, path-traversal-pentest, php-security-audit]
---

# 暴露的版本控制仓库(.git / .svn):判定 → dump → 枢纽 → 审计

## When to Use

- 发现 `/.git/HEAD` 可读(或 403/404,拿不准要不要试绕过)
- `git-dumper` 跑不动 / 卡住 / 超时,但 `.git/HEAD` 明明是 200
- 同类工具:`goop`（Go 版 .git 泄露利用）、`GitHack`、`dvcs-ripper` —— 同一逻辑,失败一律转「自己走对象图」
- 已经从 `.git` 拿到源码,想知道下一步该挖什么
- 报告里要写「`.git` 未授权可读」,需要证明并说清拿到了什么

**核心纪律**:`.git` 是本类里价值最高的一种命中(全量源码 + 远端地址 + 提交历史常留被删的口令),但**先花两次请求判定 deny 规则形状**,再决定投不投入 —— 判错了会白试几十次编码绕过。

---

## 1. 判定「谁在拦」

同一个 403 有三种来源,**分不清就会误判**:

| 页面形态 | 来源 | 含义 |
|---|---|---|
| `403 Forbidden` + `bgcolor="white"` + 多条 `<!-- a padding to disable MSIE ... -->`(~550-570B) | **源站 nginx 默认页** | 配置里有 deny 规则 |
| `ERROR: ACCESS DENIED` + `<你的出口IP>` + 节点号 | **CDN/WAF** | 规则命中,**且会按出口 IP 打标封禁** |
| ~205B `ACCESS DENIED` + `GMT 时间` + `<!-- web cache -->` | **CDN 边缘** | Host 未配置,被边缘直接拒 |

⚠️ **`.git*` 路径本身就是 WAF 特征,命中即封出口(实测 ~10-15 条可疑请求封 30-40 分钟)。** 判定用的两次请求要放在批次最后、并预留等待。

### 两次请求判定 deny 规则形状(关键步骤)

| 请求 | 结果 | 推论 |
|---|---|---|
| `/.gitignore` | **403** | 规则是**前缀式** `^/\.git`(连 `.gitignore` 也挡) |
| `/.git/HEAD.`(结尾加点) | **404 而不是 403** | 规则形如 `^/\.git[^.]*$` —— `.git` 之后一旦出现 `.` 就放行 |
| `/x/.git/HEAD`、`/.Git/HEAD` | 404 | 只匹配根路径、大小写敏感 |

**结论与止损**:上面这种规则**只放行 `*.sample` / `*.pack` / `*.idx`**。pack 名是 SHA1(160 位)不可猜、`.sample` 是无价值样板文件 ⇒ **`.git` 实际已封死,立刻停手**,不要继续试 `%2e`、`//`、`/./`、`..%2f`(nginx 在**位置匹配之前**就完成解码与归一化,这些全部无效)。

> 反例(值得继续):规则只挡个别文件名(如只 deny `HEAD|config|index`)时,traversal / 编码绕过才值得试。

---

## 2. dump:先抓这五个文件

| 文件 | 价值 |
|---|---|
| `/.git/HEAD` | 当前分支(`ref: refs/heads/master`) |
| **`/.git/config`** | **远端地址**(`git@<ip>:<ns>/<repo>.git`)—— 枢纽级线索,见 §3 |
| `/.git/index` | 全量文件清单 + 每个文件的 SHA1 |
| `/.git/logs/HEAD` | 提交人 / 时间 / commit message |
| `/.git/COMMIT_EDITMSG` | 最后一次提交信息 |

`.svn/entries` / `.svn/wc.db` 同样值得试(旧式工作副本直接写出仓库 URL 与文件清单)。

**`.git/index` 的第二用途:源码身份对账(高价值)** —— 手上已有同产品/同族的本地源码包时,用 `git -C <本地源码> hash-object <path>` 算 blob 哈希,与 index 里同名文件的 SHA1 逐个比对:全等才敢按行读源码下结论;有一个不等就说明本地是**同族另一版**,行级结论(比较原语/分支顺序/include 链)全部作废,只能当契约形状参考。**这一步放在审计前,否则整轮在审错的代码。**
- 状态判读:`objects/pack/` 403 且 `objects/info/packs` 404 = 对象已打包且**无 pack 名清单** ⇒ pack 名是 SHA1 不可猜,**内容拿不回,立即止损**;此状态下 index 就是唯一产出(全量清单 + 逐文件 SHA),别去猜 pack 名或试编码绕过。
- **index 给的是清单不是源码 —— 对象拿不回时照样能换成攻击面**:把 index 里每条路径当候选 URL 去 web 根逐个直取,尤其 `tests/**`、`cron.php`、`install/**`、`includes/lib/**`。**`.git` 可读往往源于同一次「文档根配错」,这些路径常常一起裸奔**,比继续磕 pack 划算得多;index 里的加固件类名(如 `*AuthFilter.php`、`*Policy.php`)同时是后续源码审计的靶点清单。
- **PHP 站的 `tests/**` 常常被部署且允许执行**(恰与 `/includes`、`/plugins` 的 deny all 形成反差)⇒ 逐个 curl 测试文件即得:①**PASS 行 = 该分支加固设计的自白书**(凭据重哈希/legacy 兼容、TOTP 挑战时长、授权时效、SSRF 策略、明文口令缓存);②**无 DB 依赖的测试回 200+PASS,需 DB 的回 500/0B** ⇒ 200/500 本身就判「该测试是否触库 / web 进程能否连库」;③CLI-only 测试(500/0B 且**传参怎么变都同一结果**)= 死路,别做参数 fuzz。
- `tools/`、`install/`、`tests/` 的鉴权策略各不相同(实测 `tools/`=403 而 `tests/`=200)⇒ **逐个探,别因一个 403 放弃整类**。

### `git-dumper` 失败时的备用:自己走对象图

**脚本:`scripts/git_walk_dump.py`**(本技能内置,直接用)。

```bash
python3 scripts/git_walk_dump.py https://target/.git/ ./out            # 只抓自研目录与配置
python3 scripts/git_walk_dump.py https://target/.git/ ./out --all      # 全量落盘
```

原理要点(便于自己改):

1. 取 `.git/HEAD` → `refs/heads/<branch>`(或 `.git/logs/HEAD` 首行末列)定位 commit
2. 取对象:`GET /.git/objects/<sha[:2]>/<sha[2:]>` → `zlib.decompress(raw)` → 形如 `b"<type> <size>\0<content>"`
3. `commit` → `tree` → 递归子树 → 每个 blob 落盘

**踩过的坑**:

- 自己解析 `.git/index` v2 时,每条 `total = 62 + len(name)`,`pad = 8 - total % 8`,且**整除时补 8 而不是 0**。错位后只解析出 284/3984 条就是这个 bug。
- 仓库若被打包(`objects/pack/*.pack`),loose 取回会 404 ⇒ 需另取 `.pack` + `.idx`;此时脚本只报 miss。
- 优先只抓应用自研目录(如 `App/`、`application/`、`config/`),框架与 vendor 目录(ThinkPHP/、node_modules/)对拿凭据没帮助,且慢。

---

## 3. 枢纽:从 `remote url` 跳到组织 Git 服务

`.git/config` 拿到 `git@<ip>:<ns>/<repo>.git` 后:

- 直连该 IP 的 Git 服务:
  - **GitLab:`/api/v4/projects` 匿名即可列出公开仓库**;`/api/v4/metadata` 免认证取版本
  - Gitea:`/api/v1/repos/search`
- 仓库命名常带规律(如 `<IP>_<域名>`)⇒ 可反推组织还有哪些站点/服务。
- 注册面判定:`/users/sign_up` 返回 **302** = 已关;返回 200 且有表单 = 开放(注册后可见 `internal` 可见性仓库)。
- 私有仓库:`.../info/refs?service=git-upload-pack` 返回 `HTTP Basic: Access denied` ⇒ 别再试,换路径。

---

## 4. 源码到手后:先验注入真假,再谈利用

**这是最容易自欺的一步** —— 源码里明明有拼接注入,却怎么打都不通。ThinkPHP 3.2 实战结论:

- **字符串拼接型注入通常已被 `DEFAULT_FILTER`(默认 `htmlspecialchars`)在 `I()` 层拦死**:`'` 变 `&#039;`,SQL 退化成纯字符串,UNION / 布尔 / 时间盲注**全部零差异**。**别在同一参数上反复换注释符**(`#` / `-- -` / `/**/`)浪费轮次。
- **仍可能有效的是「数组型 exp 注入」**:`username[0]=exp&username[1]=...` → `where(array(k=>array('exp',…)))`,数组结构不受过滤器影响。
- **但**前置代码若有 `array_map('trim', I('post.'))`,`trim(array)` 返回 null 会把数组打平,照样打不动 —— 审计时**先看这一步**。
- **行动准则:一次「对照 vs 注入」时间盲注定生死,零差异就换参数/换入口。**

### 鉴权边界:看谁继承谁

老 TP 应用里,`class X extends Action`(而**不是** `extends CommonAction`)= **整块无鉴权**;若整个模块目录下没有 `CommonAction.class.php`,该模块全部方法对外。**这是这类应用最稳的入口**,审计时优先 grep `extends Action`。

### 固定文件名写入 = 现成的信息泄露源

源码里出现 `file_put_contents('1.txt', ...)` / `'data.txt'` / `'test_log/'.date(...)` 这类**固定名、无鉴权**的调试写入时:

- **立刻去 web 根按同名 GET**。实测命中过长期累积的**真实客户姓名 + 手机号**(写入方是未鉴权的 `extends Action` 调试方法)。
- 这类文件按请求累积,是**持续泄露**;但文件名固定且 `.txt` 不被 PHP 解析 ⇒ **通常只是信息泄露,不是 getshell**,别在报告里当 RCE 卖点。
- 想升级成 shell 需要「可控文件名」或「包含点」—— audit 时同时 grep `display($` / `fetch($` / `include` 找 LFI,找不到就止步于信息泄露。

---

## 5. 交付口径

写报告时把三件事分开说清,否则会被质疑:

1. **可达性证据**:`GET /.git/HEAD` → `200 ref: refs/heads/master`(附原始响应)
2. **实际拿到什么**:文件数 / 关键文件名 / `remote url` / 提交时间线
3. **没拿到什么**:如「`.git/config` 里无数据库口令,`App/Conf/config.php` 被 gitignore 不在仓库」——**这一句必须有**,否则等于夸大战果

---

## Pitfalls

1. **先判 deny 规则形状,再决定绕过**。规则是 `^/\.git[^.]*$` 一类时直接止损;nginx 的解码/归一化在位置匹配之前,编码绕过全无效。
2. **`.git` 探测是 WAF 高危特征**,出口会被打标封禁 30-40 分钟。判定请求要精打细算、放批次最后。
3. **404 ≠ 不存在**:404 可能恰恰说明「这条路径没被 deny」,是有价值的判据(见 §1)。
4. **`git-dumper` 不是唯一解**,失败就自己走对象图;但注意 pack 仓库需另取 pack/idx。
5. **别把「源码里有注入」直接当「可利用」**。先用一次盲注对照验真假,`DEFAULT_FILTER` 与 `array_map('trim', …)` 是两个最常见的否决者。
6. **转储远端地址后优先打 Git 服务**,它常把组织所有项目摆在一起;但注册关闭 + 私有仓库时代不要恋战。
7. **`.txt` 落地文件是信息泄露不是 shell**,除非找到可控文件名或包含点。
8. **源码包 ≠ 线上代码**:同产品 fork 遍地,审计前先拿 `.git/index` 的 blob SHA 与本地 `git hash-object` 对账;不等就只当契约参考,别把本地行号/比较原语当线上事实。

## 关联

| 技能 | 定位 |
|---|---|
| `sensitive-dir-credential-hunt` | 更广的敏感目录/凭证猎取面(.env、日志、备份) |
| `recon-discriminators` | 判读总纲(含 `references/cdn-origin-and-waf-discriminators.md`:CDN 边缘 vs 真源站、WAF 页面分类) |
| `path-traversal-pentest` | 路径穿越与 LFI(把落地 `.txt` 升级成 shell 的那一环) |
| `php-security-audit` / `php-webapp-security-audit` | PHP 源码审计方法论 |
