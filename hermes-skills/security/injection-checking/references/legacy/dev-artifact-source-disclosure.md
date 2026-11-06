<!-- archived from /root/.hermes/skills/security/dev-artifact-source-disclosure/SKILL.md on 2026-10-21 -->

---
name: dev-artifact-source-disclosure
description: "暴露.git/调试写文件/源码泄露:手工dump取源码与数据。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, source-disclosure, git, thinkphp, recon, data-leak]
    related_skills: [sensitive-dir-credential-hunt, ip-ban-bypass, cdn-origin-tracing-v51, rce-encyclopedia]
---

> 归档卡：原目录 `/root/.hermes/skills/security/dev-artifact-source-disclosure`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/dev-artifact-source-disclosure/…')`，不要相对 `references/legacy/` 解析。

# 开发残留源码泄露 → 取源码 → 取数据

**定位**:目标把开发期残留留在了生产上(`.git` 目录、调试写文件、未授权前端模板、phpinfo),这类暴露往往是**整条测试链里唯一不需要凭据就能拿源码/拿数据的口子**。本技能管「发现 → 全量取源 → 审计 → 兜出数据」。

与 `sensitive-dir-credential-hunt` 的关系:那本是「敏感文件/目录的猎取清单」,本技能是「命中之后怎么把源码完整拿回来并榨出可用漏洞」。

---

## 1. 四类高价值开发残留

| 类别 | 探测 | 拿到什么 |
|---|---|---|
| **暴露的 `.git`** | `GET /.git/HEAD` → `ref: refs/heads/master` | 完整源码 + `.git/config` 的 `remote url`（常暴露组织自建 GitLab/Gitea） |
| **调试写文件** | 源码里搜 `file_put_contents('<固定名>.txt', raw_param, FILE_APPEND)` | **web 根下可直接读回，且累积真实业务数据**（真实姓名/手机号等 PII） |
| **未授权前端模板** | `GET /tpl/_xxx.html` 等厂商约定路径 | 全量字段名 + 全部接口名 + 业务模型 |
| **phpinfo / 测试残留** | `/phpinfo.php`、`/test.php` | 禁函数表、`open_basedir`、内网 IP、会话机制、机器指纹 |
| **部署产物泄露** | web 根下 `dist.zip`、`*.jar`、`*.war`、`application.yml`、`*.sql`、`heapdump` | 前端整包(全 chunk)、数据库口令、令牌签名密钥 ⇒ 见 §3.5 |

---

## 2. 暴露的 `.git`:手工全量 dump

**顺序**:先试 GitHacker / git-dumper;**失败就手工 walk**。在「不支持 `git http-backend` 的裸静态站」上,这两个工具会直接失败(2026-09 实测),手工法反而最快最稳。

### 2.1 手工 walk 五步

```
1. GET /.git/HEAD                     -> "ref: refs/heads/master"
2. GET /.git/refs/heads/master        -> commit SHA
3. GET /.git/config                   -> remote url（拿到就走组织 GitLab 那条线）
4. GET /.git/objects/<sha前2>/<后38>   -> zlib 压缩的 git 对象
   解压后格式:  "<type> <size>\0<content>"
5. commit 对象里 "tree <sha>" -> tree 对象 -> 递归取 blob
```

`scripts/git_dump_manual.py` 已实现全部五步（含 tree 递归、目录还原、清单输出）。

### 2.2 必读 pitfall

- **`.git/index` 不是权威**。它可能只是旧索引（实测 3984 条目 vs 实际只列到 56 个目标目录文件），而且是活的工作区快照,会缺被 gitignore 的文件。以 `commit→tree→blob` 为准。
- `.git/index` v2 对齐公式写错会大量错位:`total = 62 + namelen; pad = 8 - (total % 8)`,**`pad==0` 时要补 8 而不是 0**（实测错写导致 284/3984 假阳性）。
- **`.gitignore` 掉的配置文件不在仓库里**。如 ThinkPHP 的 `App/Conf/config.php`(库密所在)—— 仓库没有;线上直接访问它是 **200 空 body**（被 PHP 执行,不是源码）,所以「拿源码 ≠ 拿库密」,别在这上面空耗。
- `.git/packed-refs` 404 只说明没有 packed refs;对象仍可能不全。对象取不到时 `HEAD` 一定 404。
- **`.git` 在 CDN/WAF 后面会即时封出口 IP** —— 见 `ip-ban-bypass` 的 `references/cdn-waf-ban-granularity-2026.md`。优先挑不在同一 CDN 上的兄弟域名下手。
- 顺手把 `.git/info/exclude`、`.git/logs/refs/heads/master`、`.git/COMMIT_EDITMSG` 也读一遍:提交者主机名与提交时间能确认这份代码是否就是线上版本。

### 2.3 从 `.git/config` 转场

`remote url = git@<IP>:root/<IP>_<域名>.git` 这种命名说明对方自建 Git 服务。立刻:

1. 探那台机器的 80/443 → 常见 GitLab（首页含 `devise-layout-html`）/ Gitea
2. `GET /api/v4/projects?per_page=100` —— **GitLab 该接口默认对公开项目免鉴权**,能一次列全公开仓库
3. 试着 `git clone http://<ip>/<ns>/<repo>.git`:公开仓库直接成功;私有仓库报 `could not read Username`
4. 注册口:`/users/sign_up` 返回 **302 = 注册已关闭**;200 才是开着。开着就有戏（Internal 可见性的仓库对所有登录用户开放）

---

## 3. 固定名 `.txt` 调试写入 → 未授权真实数据泄露

**这类漏洞直接产出数据（不只是源码）,优先级很高。**

**特征**:未授权的调试动作把 `raw_param` 或 `php://input` **逐条 append** 到 web 根下一个固定名文件:

```php
file_put_contents('1.txt',    json_encode(I('get.')).PHP_EOL,        FILE_APPEND);
file_put_contents('data.txt', file_get_contents("php://input").PHP_EOL, FILE_APPEND);
```

**利用**:
1. 源码里全文搜 `file_put_contents`,挑**文件名里没有变量**的那条
2. 直接 `GET /<固定名>.txt` —— `Content-Type: text/plain`,无需认证
3. 这类文件是**累积**的:历史真实业务数据都在里面（实测读到 7 年前至今的真实客户姓名+手机号）
4. 用一次自己的请求确认接口当前仍存活（自己的记录会立刻出现在文件里）

**边界**:`.txt` 不被解析 → **不是 getshell**。只有站内存在可用的 include/模板包含点时才可能升级。别把它当 RCE 交付。

**同类变体**:`var_dump($GLOBALS['HTTP_RAW_POST_DATA']); exit;` 这种调试回显;`file_put_contents('1.txt', $model->getlastsql())` 这种把**最后执行的 SQL** 落盘（泄露表名/前缀,甚至可配合注入做 SQL 回显 oracle）。

---

## 3.5 部署产物泄露:web 根下的 `*.zip` / `*.jar` / `*.sql` / `*.yml`

上线时把**构建产物/打包文件**留在 web 根(或其子目录)是这个生态的高频习惯,nginx 的静态规则又把它们当普通文件直接吐出来。**一次命中能顶掉几天逆向**:前端整包 = 完整前端"源码";后端包/配置 = **数据库口令 + 令牌签名密钥**(后者可直接伪造管理员令牌,直插调度任务/代码生成那条 RCE 链 —— 这是本类里最短的闭环)。

**波次**(命中第一个就立即铺开同类名,不要只试一个):

1. **前端整包**:`dist.zip`、`dist.tar.gz`、`www.zip`、`web.zip`、`admin.zip`、`h5.zip`、`tma.zip`、`src.zip`、`dist2.zip`(旧版)
2. **后端/部署包**:`<产品>.jar`、`app.jar`、`ruoyi-admin.jar`、`*.war`、`docker-compose.yml`、`Dockerfile`、`nginx.conf`
3. **配置与库**:`application.yml`、`application-prod.yml`、`.env`、`bootstrap.yml`、`*.sql`、`dump.sql`
4. **堆/日志**:`heapdump`、`*.hprof`、`logs.zip`

**命中判据**:`200` + `Content-Type: application/zip|octet-stream` + **首字节 `PK`**(gzip 为 `1f8b`)。**别只看状态码** —— SPA 站的 nginx fallback 会把任意未命中路径回 `200` + `index.html`,照状态码判就会把首页 HTML 当成"整包已下载"。

**取回:在跳板机直下,再 SFTP 回本机,落盘后两端对 sha256。** 经代理池拉大文件会慢到不可用(实测 8.4MB 经代理 420s 只下到 1.2MB;跳板机直连 **3.25 秒**下完)。

### 前端整包 = 免凭证的全量端点契约 + 鉴权面清单

解包后别只当"源码"摆着,按序榨:

1. **全量端点**:抽 `url:"/..."` 等模式,与旧清单**取并集** —— 平台每次改版都加端点,旧清单的阴性结论**不能覆盖**新端点(实测新包 376 条 vs 旧清单 106 条)。
2. **鉴权面端点(最值钱的一类)**:搜 `google|totp|auth|reset|unlock|secret|otp|pwd`。二开平台常把高危动作拆成独立端点,例:**GA/谷歌验证器重置**(调用后直接把新种子回吐到界面 ⇒ 一旦可达即等于卸掉动态码锁)、**登录解锁**、改密多入口。这些端点即使受保护,也是下一轮的首选靶。
3. **调用形状从调用点原文读,不要猜**:字段名(`account` vs `username`)、提交编码(JSON vs form-urlencoded)。字段名要**穷举别名后**才允许下阴性结论,否则"整批账号不存在"可能只是自己字段名写错造成的假阴性。
4. **硬编码值**:公钥、盐、`VITE_GLOB_*` 开关;但**必须回 bundle grep 该变量的读取点**确认不是死配置。
5. **版本指纹**:dist 与后端包里的版本号/构建哈希,用于把"已部署"与"前端契约"对齐,避免把已下线死链当攻击面。

`spa-request-contract-extraction` 有更细的调用点还原手法;本节的目的是**别把整包丢掉**。

---

## 4. phpinfo 指纹判定「两个域名是不是同一后端」

镜像域名/别名域名是这个生态的常态。**同一后端 = 你可以在没被封的那一侧自由打,而结论适用于被封的主目标。**

取每侧的 `SERVER_ADDR` 与 `DOCUMENT_ROOT` 比对:

| 域名 | SERVER_ADDR | DOCUMENT_ROOT |
|---|---|---|
| `jxck.a.com`（主,被封） | 172.x.x.120 | `/wwwroot/jxck.y.com` |
| `jxckdy.a.com`（别名） | **172.x.x.120** | **`/wwwroot/jxck.y.com`** |

两者完全一致 → 同机、同站点目录、同 PHP-FPM、**同 session 存储** → 别名侧拿到的会话等于主目标的会话。

注意区分:**同机但不同 DOCUMENT_ROOT** 是「同服务器的另一套实例」,不是镜像,结论不能互套。

---

## 5. 拿到源码后的审计清单（按产出排序）

1. **找出无鉴权的类**:老 ThinkPHP 用 `extends CommonAction` 做鉴权基类。**搜所有 `extends Action`** —— 任何直接继承框架基类的 Controller 都绕过了鉴权基类（实测拿到整个模块无鉴权 + 两个调试残留 Action）。
2. **找写文件**:见 §3。
3. **找登录里的哈希直通分支**:`if (strlen($pwd) != 32) { $pwd = md5(md5($pwd).$salt); }` —— 提交 32 字符即被当作**最终哈希直接比对**。利用方式:把常见口令的 md5 也当作口令投递（无需知道 salt）。
4. **判注入是否被输入层过滤**（ThinkPHP 3.2 必看,详见 `references/thinkphp32-source-audit.md`）:框架的 `DEFAULT_FILTER`（常为 `htmlspecialchars`）会把 `'` 转义,使**字符串拼接型注入全部失效**;而**数组型 `exp` 注入**（`where(array('username'=>array('exp','...')))`）因数组结构不受过滤器影响**依然有效**。别看到拼接就宣布有注入。
5. **验证码提交格式要实测**:源码里写 `I('vertify','','md5')` 不代表要提交 md5 —— 实测该站必须提交**原文**才通过（raw 4/4,md5 0/4）。**永远用「正确/错误」两种提交各试一次来定格式**,不要信源码的过滤器参数。
6. **上传点**:看 `$upload->savePath` 与 `allowExts` 白名单;老版本 ThinkPHP 的 `Upload` 类白名单外的后缀通常真的过不去。

---

## 6. 交付与沟通纪律（用户明确要求）

- **先讲清「这是什么系统」再往下打**:被问到时,用字段名/角色枚举/模块清单反推出**业务模式**（如「多级代理微商 + 货到付款 + 广告投流驱动的订单中台」）,并说明脱库拿到的究竟是什么资产、为什么值钱。用户会在深入前要求这一层解释。
- **阶段性梳理要成篇**:用户会要「梳理一下目前拿到了哪些信息 / 有哪些已发现的漏洞 / 目标是什么 / 下一步怎么办」。交付形态:一张资产表 + 一张漏洞表（编号/名称/证据）+ 已排除路径清单 + 按成功率排序的下一步；同时落盘成 md 文件。
- **没有战果不要刷屏**:用户明令「拿到最终目标再和我说」。中间过程只在**真的拿到数据/拿到 shell** 时汇报;未达成就如实说未达成,不要用「又发现一个可能性」凑进度。
- **本机是红线**:所有目标流量（含单条探测）必须从跳板机发出,本机只做 SSH 控制/转发。本机的 Clash/v2rayN 出口同样不算数。
- **不要停止在「已排除」上**:排掉一条路时,同轮就要给出下一条可打的路,避免把「空转汇报」当成交付。

---

## Pitfalls

- 别把「nginx 源站 403」当 WAF 封禁反复换出口 —— 看响应体指纹（`ip-ban-bypass`）。
- 别把 `file_put_contents('固定名.txt')` 当成 getshell 交付,先确认有没有包含点。
- 别只信 `.git/index`;也别指望仓库里有被 gitignore 的库密配置文件。
- 别看到源码里的字符串拼接就宣称 SQL 注入 —— 先按 §5.4 判断是否被 `DEFAULT_FILTER` 挡掉,再用时间盲注实测（响应恒空 = 多半被过滤,而不是表是空的）。
- 空间引擎查资产要带 `cert="<授权域>"` 这类受限条件,不做无域全网扫。
- **别把 `200` 当"文件存在"**:SPA 的 nginx fallback 对任意未命中路径回 `200` + `index.html`,抓产物必须核对 `Content-Type` 与 magic 字节。
- **别在代理池上拉大文件**:慢到会撞工具超时,下到一半的 `.part` 既不能续也不能当证据;跳板机直连 + SFTP 回本机才是正路。

## 关联

- `sensitive-dir-credential-hunt`:敏感文件/目录猎取清单（本技能是命中后的深挖件）
- `ip-ban-bypass`:CDN/WAF 封禁粒度与响应体指纹（为什么在 CDN 后面碰 `.git` 会即时封 IP）
- `thinkphp-modern-pentest` / `web-cms-pentest`:框架侧漏洞面
- `pentest-report-autogen`:把本轮结果落成正式报告
