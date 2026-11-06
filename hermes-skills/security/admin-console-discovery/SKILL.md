---
name: admin-console-discovery
description: "找不到管理端时用:通配证书反查兄弟域+vhost枚举。"
version: 1.0.0
license: MIT

---

# 隐藏管理端发现（通配证书下的定点破局）

## When to Use

- 开放面(玩家/租客/会员 API)已穷尽 —— IDOR 阴性、参数注入阴性、路径规范化阴性、无导出接口
- **管理端域名未知**,而诉求是"拿全量数据"(管理端导出是 100% 全量最短杠杆)
- 主域是**通配证书**(`*.brand.com` 单证书),子域暴力打不出结果
- 白标 / 包网 / 多租户 SaaS:同一套产品下有几十个**兄弟品牌各自独立部署**
- 拿到一个"只有 IP"的源站,想知道上面还挂了什么

配套: 拿到管理端后走 `lowcode-admin-data-exfil`(导出脱库)、`userdata-grab`(脱库决策树)。
前端签名逆向详见 `webapp-api-crypto-reverse`。

---

## 核心心法

**主域打不动时,横向去兄弟域和源站找同款后台。**
兄弟品牌跑的是**同一套产品、独立部署**,配置参差不齐;
只要一个漏了,就拿到同款后台 → 后台里通常有「站点 / 渠道 / 租户」页 →
反推目标品牌的租户令牌,拼出目标的管理地址。

一句话:**通配证书不是终点,是"换维度"的信号。**

---

## 四步法

### 步骤 1 —— 先证伪,再转向(5 分钟)

拉主域证书,看是否通配:

```bash
curl -s "https://crt.sh/?q=%25.<brand>.com&output=json" | grep -o '"name_value":"[^"]*"'
# crt.sh 常 502/429，备选：
curl -s "https://api.certspotter.com/v1/issuances?domain=<brand>.com&include_subdomains=true&expand=dns_names"
```

- 结果只有 `*.brand.com` + `brand.com` → **管理端不在这个域下**
- **判据:`*.brand.com` 单证书 = 子域暴力结构性无效,立刻停手**,
  不是运气不好,是数学问题(通配证书不为子域签发独立记录)

顺手排除被动 DNS 噪声:`hackertarget hostsearch` / OTX / rapiddns 会吐出一堆
**历史遗留**子域(`anne/derek/tofu/yun` 这类人名式),打过去被通配吞掉,别浪费请求。

### 步骤 2 —— 兄弟域 CT 反查(最高性价比)

对每个兄弟品牌跑一遍步骤 1 的 CT 查询。实战命中的命名模式(可直接作字典):

| 模式 | 实例 | 用途 |
|---|---|---|
| `<role>-<token>.<brand>` | `admin-svrxwmnptdgvvibt2epdqd3.5151.com` | **每租户一个随机令牌的管理端** |
| | `agent-s91moevps1k0a5jprui5a8v.5151.com` | 代理端(低权,常可自助注册) |
| `admin.control.<brand>` | `admin.control.98.com` | 总控 |
| `admin.beta.<brand>` / `beta.<brand>` | `admin.beta.98.com` | beta 后台(常无验证码/无锁定) |
| `yunying.<brand>` | `yunying.98.com` | **运营管理系统**(中文 SPA) |
| `db.w.<brand>` / `db1.w.<brand>` | `db.w.5151.com` | 数据库主机(证书存在即主机存在) |
| `pmm.ops.<token>.<brand>` | `pmm.ops.ce22169124a9.5151.com` | Percona PMM(内嵌 Grafana 需鉴权,但暴露拓扑) |
| `grafana-ui.dev.<token>.<brand>` | `grafana-ui.dev.test111f213.5151.com` | Grafana(偶发公网 200) |

**确认"同族"要拿硬证据** —— 比"共用 CDN 前缀"强得多:
找一个**业务特征串**(错误消息 / 网关 404 文案),在两个站 diff,**逐字节相同即同族**。

```bash
curl -s https://game-service.<A>.com/api/hall/version    # {"code":"404","msg":"404 - Interface não existe"}
curl -s https://game-service.<B>.com/api/hall/version    # 同上 → 同族坐实
```

### 步骤 3 —— 源站 IP + Host 头 vhost 枚举

API 主机名**经常根本没在 CDN 后面**,一条 `getent hosts` 就出源站:

```bash
getent hosts api.<brand>.com          # -> 47.93.153.70   (阿里云 ECS，直连即可)
```

拿到 IP 后**两件事都做**(都便宜):

**(a) 全端口扫** —— 成本几秒。本例空手(安全组只放 80/443),但换个目标可能就是 Nacos 8848 / Redis 6379 / MySQL 3306。

**(b) Host 头 vhost 枚举 —— 收获点**。关键在**判定标尺**:
未配置的 Host 一律回 nginx 默认 `403 Forbidden`;已配置的返回别的东西。

```bash
IP=47.93.153.70
for H in api.x.com admin.x.com manage.x.com ops.x.com boss.x.com control.x.com \
         beta.x.com dev.x.com uat.x.com staging.x.com localhost 127.0.0.1 \
         <兄弟品牌全家桶> ; do
  C=$(curl -s -m 8 -k -o /tmp/v.out -w '%{http_code}' --resolve "$H:443:$IP" "https://$H/")
  [ "$C" != "403" ] && [ "$C" != "000" ] && echo "[✔] $H -> $C $(head -c 80 /tmp/v.out)"
done
```

> ⚠️ 先跑一个已知 Host(如 `api.x.com`)确认它**不是** 403,否则标尺不成立。
> 若所有 Host 都 200,说明源站有 catch-all,**此手法失效**,改用响应体 diff。

**别忘了默认 TLS 证书**:`openssl s_client -connect $IP:443`(不带 SNI)。
有时是多 SAN 证书 → 直接列出该机器上所有 vhost。

### 步骤 4 —— 管理端 SPA 主包 = 图纸

Vue-CLI / webpack SPA 的 `js/app.<hash>.js` 里常**整块配置明文**,并且
**请求拦截器就是签名算法原文**(详见 `references/token-gateway-and-replay.md`):

```js
t.headers["x-access-appid"] = appid;
i.timestamp = Date.now();
i.signature = md5( encodeURI( JSON.stringify(i) ) + secret );
```

拿到 `appid` + `secret` + 算法 = **可伪造任意合法请求**。
网关是**双层鉴权**,用报错区分走到哪一层:

```
不带 appid -> {"msg":"appid不存在","errcode":10103}     ← 层1没过
带 appid   -> {"code":9,"msg":"用户访问令牌token缺失",
               "errcode":10306}                         ← 层1已过,只差用户 token
```

**这一步的价值**:走到第二句之后,只剩"一个 token"。此后**任何渠道泄漏的任意一个 token**
(前端 localStorage / 日志 / 分享链接 / CDN 缓存 / 低权代理账号)都能驱动全部管理 API,
不必再破签名。所以下一步应转向 **拿低权 token**,而不是继续攻管理端本体。

---

## 拿 token 的优先顺序(比破管理员密码划算)

1. **代理端 / 子账号端** —— 普通用户量级,口令弱、常有自助注册或找回,拿到的 token 先测
   它能访问哪些管理端点(服务端若只验"token 有效"不验角色 = 直接提权)
2. **beta / dev / uat 环境的同款后台** —— 常无验证码、无锁定、口令更弱
3. **token 泄漏面** —— 前端 localStorage 残留、日志、分享链接、CDN 缓存
4. 最后才是打管理员密码

---

## Pitfalls

- **继承的报告必须先证伪再引用**。接手别人的渗透报告时,把每条"已验证"当**待验证假设**。
  实战踩过两条假结论:`X-Document` 换任意值被宣称是"跨租户 IDOR",实测换值直接 **500**
  (租户其实是绑定的,那 79 条是测试方**自己**商户的数据);另一条"`GET /users` 明文泄漏
  `resetPasswordToken`",实测该字段**根本不存在**。
  **差分测试(只改一个变量、看响应差异)是最低成本的证伪手段。**
- **QA/dev 环境会被误当生产 PII**。环境标识先认:域名含 `-qa` / `-dev`,桶名含 `-development`,
  账号形如 `qa_*@proton.me`,dashboard 计数是个位数,种子数据是"精酿啤酒/建材店/汽修店"
  → 这是**夹具数据**,不是真用户。定性前先确认环境,否则报告里会写出假战果。
- **字符集白名单报错 ≠ 登录失败 ≠ 命中**。密码字段常带
  `只能字母/数字/下划线/破折号` 类白名单,含 `'` `#` `@` `.` 的 payload 返回**白名单报错而非密码错误**。
  实战脚本在此打过一次 `<<<<< HIT` 误报 —— 它既不是 SQLi 成功也不是登录成功。
  **看到非「密码错误」的响应先分类再下结论。**
- **`<role>-<token>` 主机返回 404 不等于没价值**:中文 404 页说明**主机在、应用已下线**,
  是租户存在的证据,可以据此推断命名与租户数量。
- **别把 TP5 RCE payload 当默认手段**:`/index.php?s=...invokefunction` / `request/input` /
  `view\driver\php` 三件套在现代框架上全部无回显;`?lang=../../etc/passwd` 的 500 只是参数进了解析器,
  **不是文件读成功**。
- **OOB(带外)监听会被互联网背景扫描器污染**:跳板机公网端口一天能收到几十条 zgrab /
  visionheight / Go-http-client 的探测。判定"目标回连"必须比对**你的 payload 特征**,
  不能看到 hits.log 有记录就当成功。

---

## Verification

- 步骤 1 判据可复现:通配证书域名 → 任意子域返回**完全相同**的页面大小/哈希
- 步骤 3 判据可复现:同一 IP 上未配置 Host → 403,已配置 Host → 非 403 且大小/标题不同
- 步骤 4 判据可复现:同一请求不带 appid → `appid不存在`,带 appid → `token缺失`(证明分层)

## 支持文件

- `references/token-gateway-and-replay.md` —— 网关签名算法 Python 复现、登录字段名「报错推进」法、
  字符集白名单误报纪律、本例完整证据表(CT / vhost / 端点清单)


---

## 外部库增量（2026-10-11 分享包）

## 凭据来源优先顺序(先读后爆)

**管理端登录打不进去时,不要在口令上加大投入 —— 先扫凭据来源面。** 口令几乎从不"被猜出来",
而是**被读出来**或**被伪造出来**。在线爆破要同时突破 bcrypt + 验证码 + 失败锁定 + IP 风控,
是结构性走不通,不是字典不够好。固定顺序:

1. **先读,别先猜** —— `/robots.txt`、`/sitemap.xml`、`/api/docs`、`/swagger`、`/openapi.json`。
   这一步比 5000 条字典便宜几个数量级,跳过它是最常见的时间浪费。
2. **判 catch-all 基线 / 判验证码 / 判锁定** —— 不判基线,后面满屏假阳性;不判锁定,
   打 200 次后账号已锁死且自己暴露。
3. **跑凭据来源清道夫** —— `scripts/admin_cred_hunter.py`(纯 stdlib 零依赖):
   ```bash
   python3 scripts/admin_cred_hunter.py -u https://target/acme/admin -o D:/渗透/acme_admin
   python3 scripts/admin_cred_hunter.py -u https://target/acme/admin -o D:/渗透/acme_admin \
       --probe-login --login https://target/prod-api/login   # 登录探测默认关闭,命中即停
   ```
   出 `report.md`(按价值分层,tier1 命中直接贴文件内容)+ `findings.json` + `js/`(供继续逆向)。
4. **拿到密钥就不登录** —— `.env` 的 `JWT_SECRET` 或 heapdump 里的签名钥 → 本地自签 admin token
   (**无痕**);`.env` 的 DB 口令 → 连库改 admin(**有痕**,先答"能不能恢复")。
5. 以上全空才轮到定向小字典;必须先测锁定策略,串行限速。

凭据来源分层清单 + 登录绕过家族决策表见 `references/admin-console-credential-sources.md`。

**★ 观测栈优先于口令**:同机的 Grafana / Prometheus / Loki / Pushgateway / exporters **常整片未鉴权**,
`GET <grafana>/metrics` 未鉴权必探(定版本/活性);**但别指望 `/metrics` 出数据源或 DSN** ——
它是 Prometheus 自指标(`go_*`/`http_*`/`cache_*`),**不含 datasource 标签**(实测 464KB 全量 grep 零命中),
数据源清单在 `/api/datasources`(需鉴权)。**要拓扑/DSN 就去 Prometheus 侧**:`/targets` 列出全部抓取目标、
`/status/config` 回抓取配置(常含 DSN/口令);Grafana 默认口令改过时 `/api/*` 整片 401,
此时它是**只读情报源**(版本/拓扑),不是入口 —— 别在它上面磨口令。**拿到任意一个 Grafana 账号（哪怕 Viewer）
就相当于拿到一台 SQL 代理**（`POST /api/ds/query` 由服务端带着数据源凭据查库,不需要知道 DB 口令）。
⇒ 这一步把目标从「破 DB 口令」换成「破 Grafana 口令」,而且 Grafana 默认**无失败锁定**,比业务后台好打得多。
服务指纹、判据、Prometheus/Loki 取据点与报告口径见 `references/observability-plane-recon.md`

---

## 2026-10 盾/加速器 Ops 面板：源站拓扑倍增器
- 指纹：`/ops/session`、`/ops/apps/...`、`yunding`、面板标题含「云顶盾/Ops」
- 弱口令 `admin/admin123` 直接进（同族多实例常同口令）
- 进后台先拉三类：`rules`（**回源表：域名→源站IP:端口**）、`private-nodes`（节点网关）、`credential`（SDK pid/key）
- `rules` 一出，CDN/WAF 后的宝塔(:20531)、FTP(:21)、MySQL(:3306)、MinIO(:9000/9001)、彩票后台(:8090) 全部现形
- 宝塔假 404 基线：先取 `len`+`md5`，再跑 4 位 hex 全空间；hits=0 说明入口不在该空间，别死磕
- DoH 短记录 `_ydt-short-<pid>.<domain>` TXT 可由 Ops 解出节点 IP

---
