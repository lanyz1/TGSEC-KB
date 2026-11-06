# 多租户 OSS/云盘平台识别与匿名桶枚举

**适用**：一台服务器同时跑「对象存储网关 + 控制台 + 监控栈」，桶名随机、租户多。
典型实例：Cloudreve Pro（Go 后端 + openresty/Lua 自定义域名 + MySQL + Redis + MinIO）。

## 1. 识别指纹

| 信号 | 判据 |
|---|---|
| 平台身份 | 前端构建包内 `version.json` / `asset-manifest.json` → `{"name":"cloudreve-frontend-pro","version":"3.7.1"}` |
| Lua 指标 | Prometheus 里 `openresty_lua_script_events_total{event="load_bucket_config" / "load_custom_domains" / "load_user_config" / "cors_preflight_all_domain"}` → 桶/域名/用户配置全在 **MySQL** |
| 桶名规则 | `<用途/用户名>-<8~10位后缀>`（如 `laanzo-u132dems` / `system-u1i3hmko` / `backup-u1i3hmko`）→ 后缀**不能从零猜**（先从指标/配置拿清单），但**后缀相同 = 同租户**；拿到任一个桶名即可枚举同族兄弟桶（见 §3.3） |
| 网关错误体 | `NoSuchKey` + `<BucketName>xxx`（自定义域名访问时回显底层桶名） |
| 反代特征 | 自定义域名（`let`/`lalet`/`lat` 等子域）绑定到桶或内部应用，走 openresty Host 路由 |

## 2. 监控栈 = 内网拓扑外泄面（第一优先）

同机常见端口与价值（**全部默认无鉴权，先扫这几个再谈应用层**）：

```
:9090  Prometheus       ★★★ /api/v1/targets + /api/v1/status/config → 内网 IP/端口、软件部署路径
:9091  Pushgateway      ★★  运维自定义任务（bucket_usage/daily_stats）
:9100  node_exporter    主机全量（含 node_textfile 自定义指标）
:9104  mysqld_exporter  MySQL 全局变量/状态（mysql_up / port / version）
:9113  nginx_exporter   连接数与请求总量（判断生产规模）
:3000  Grafana          版本指纹；默认口令常失败，8.x 才有 CVE-2021-43798 路径穿越
:9104  → 对应内网 MySQL 的 IP 就从 exporter target 里读
```

**从指标里直接读内网**：`/api/v1/targets` 给出 `192.168.x.x:port` 全清单；`node_uname_info`、
`mysql_global_variables_datadir`、软件路径 `/data/<厂商>/software/...` 暴露**厂商名与部署根**。

## 3. 匿名桶枚举（无凭据）

```bash
# 列举（匿名 ListBucket）
curl -sk "http://IP:PORT/<bucket>?list-type=2"

# 权限判据 ★关键
#   AccessDenied  → 匿名不可读
#   NoSuchKey     → 匿名 GetObject 已放行（只是键不存在）
curl -sk "http://IP:PORT/<bucket>/nonexistent_key_xyz"

# 写入测试（做且只做一次，测完立即删；PUT 全 AccessDenied 即无破坏风险）
# 注意：PUT/CDN 可能对特殊字符直接 400，别误判成 WAF 封禁
```

**拿全量桶名**（随机后缀的唯一出路）：
```bash
# 任意带 bucket 标签的序列全捞出来
curl -skG "http://IP:9090/api/v1/query" --data-urlencode 'query={__name__=~".+",bucket!=""}'
# 桶总数（做清单完整度对照）
curl -skG "http://IP:9090/api/v1/query" --data-urlencode 'query=minio_cluster_bucket_total'
```
`minio_bucket_batch_replicate_objects`、`minio_node_scanner_*` 等指标常带 `bucket` 标签，
是随机桶名的**实际泄漏口**（此时故意 `AccessDenied` 的 S3 ListBuckets 也就不需要了）。

### 3.1 只列不读也是情报（LIST 与 GET 的权限常不同）

桶策略放行 `s3:ListBucket` 而收紧 `s3:GetObject` 是常态 → **全量可列、对象 GET 全 403**。
这时 listing 本身就是交付物：对象名 + size + 时间戳足以 (a) 判定管道是否在跑（毫秒级时间戳＝近期日志）(b) 挑出目标文件再换路取内容（presign / 内部端点 / 换 vhost）。

- **手里已有的每个桶名都必须发一发 `?list-type=2`** —— 配置 / 指标 / URL 里出现过的桶名（含被当成「日志桶」「系统桶」「别人的桶」而跳过的那几个）都是零成本探测面；
  在得出「网关全锁」结论**之前**先假定自己漏发了，判定闭锁以「每个已知桶名都试过」为前提。
- **匿名列举翻页**（超过 1000 必用，否则静静只拿 1000 条还以为桶里就这些）：
```bash
curl -sk "http://IP:PORT/<bucket>?list-type=2&max-keys=1000"
curl -sk "http://IP:PORT/<bucket>?list-type=2&max-keys=1000&continuation-token=<NextContinuationToken>"
```
解析 `<Key>` / `<Size>` / `<NextContinuationToken>`，清单按桶分别落盘（见 §5 文件名规则）。

### 3.2 桶内高分值目标 + 「下载→grep」闭环

桶是全平台杂物间，**厂商自己的发布包也常在里面** —— 拿全清单后先按名筛：

| 目标 | 名字特征 |
|---|---|
| 平台源码发布包 | `<平台名>-code.zip`、`*all-code.zip`、`*前端*.zip`、`*修改好的*.zip` |
| 用户 / 业务导出 | `*_insert.sql`、`users*`、`dump*`、`export*`、`*.xlsx` |
| 租户品牌配置 | `public/<品牌>/js/config.js`、`*.lua`（游戏/业务逻辑）、`config/` 目录 |
| 客户端与备份 | `*客户端*.exe`、`*.apk`、`backup*`、`*.dll` |

筛出文本类（`.json/.yaml/.yml/.env/.ini/.conf/.txt/.sql/.go/.js/.html`，≤1~3MB）后**批量下载到本地再 grep**：

```python
PAT = re.compile(rb"(access[_]?key|secret[_]?key|accessSecret|password|passwd|@tcp|dsn|jwt|token\s*[:=]|Authorization|WebConsoleUser\w*)", re.I)
```

命中即打印「关键词 + 前后 ~110 字符上下文」，文件按 `<bucket>__<key>` 落盘。
一个 `application.yaml` 就能换出整套生产凭据（DB / Redis / MinIO / 对象存储 AK-SK / JWT secret / 支付商户号 / 邮箱口令），
以及部署脚本里的 `expect` / `sshpass` **明文 root 口令**。

**AK 归属要分清**：`X-Amz-Credential=<AK>/...`（presign / 分享 URL）里的 AK 属于**活网关**，优先拿它去打 AK oracle；
而**配置文件里**的 AK 可能属于迁移前的旧主机 → 打活网关会回 `InvalidAccessKeyId`。
那不是「配置失效」，而是「打错了网关」，逐台独立验，别据此否定整套凭据。

### 3.3 桶家族旁路 + 「源码能不能直套线上」判定

**后缀 = 租户 ID**。拿到一个桶名后，把同后缀的常见用途前缀过一遍（零成本、纯读）：

```bash
sfx=u1i3hmko
for p in system backup account avatar file upload tmp test log data code dist asset share user db export; do
  curl -sk -o /dev/null -w "$p-$sfx %{http_code}\n" "http://IP:PORT/$p-$sfx?list-type=2"
done
```

- **策略逐桶独立**：`system-<sfx>` 只给 LIST、`backup-<sfx>` 的 `*.zip` GET 直接放行是实测常态 ⇒
  客户的源码 / 备份 / 导出包常**不在**名字像系统桶的那个里，而在备份/导出类的兄弟桶里 —— 别因系统桶 403 就放弃整个家族。
- **桶里挖到平台引擎源码后，先花一发请求做「源码 ↔ 线上同引擎」判定**：打该引擎的招牌公开路由
  （Cloudreve：`/api/v3/site/config`、`/api/v3/user/session`）并 grep 前端 bundle 的路径指纹（`/api/v3`、引擎名）。
  **全 404 + 前端零指纹 = 线上不是这个引擎**，那份源码只能当同开发者的另一条产品线借鉴，
  再审也不映射线上路由 —— 这一步省下的时间远多于审源码本身。
- 引擎内部地标（Cloudreve v3）：`routers/router.go` 是唯一权威路由表；**HMAC/JWT 签名密钥不在代码里，
  取 DB setting `secret_key`（`pkg/auth/auth.go`）** ⇒ 密钥只能从库 / 配置拿，拿代码常量离线化字典是白跑；
  分享族路由只挂 `middleware.ShareAvailable()`（只管分享自己的密码），不带用户鉴权中间件 ⇒
  分享面的枚举 / 爆破价值高于用户体系。

## 4. CDN 隐藏源站时的直连

```bash
curl -sk --resolve panel.example.com:443:<origin-ip> https://panel.example.com/ -o p.html
curl -sk --resolve panel.example.com:443:<origin-ip> -X POST \
  https://panel.example.com/api/xxx/login -d 'u=admin&p=1'
# Server: Fastcdn-189 / X-Cache 等 CDN 头出现 ≠ 直连失败；用「业务码是否真实回显」判定命中源站
```
源站定位：历史 DNS / crt.sh 子域的新解析（`lalet.x` 从旧 CDN 切到裸源站 IP 是最典型线索）。

## 5. Pitfalls

- **`/api` 前缀打在 MinIO 前端会被 STS 处理器吃掉** → 返回 `Invalid STS API version , expecting 2011-06-15`，不是应用路由，别在这条路上耗。
- **匿名桶可读 ≠ 可写**：`NoSuchKey` 只证明读；写必须单独测且只测一次。
- **TUN/代理环境下本机 TCP 扫描全 OPEN 是假象** → 一律以「真实 HTTP 响应/协议 banner」为判据。
  **同一端口在多台不相关主机上全部回同一个 `503`/空体**是同一类污染（代理代答），不是目标状态 → 换跳板机复测再下结论。
- **清单 / 下载落盘文件名必须带来源标识**（`bucket_objects_<bucket>.json`、`<bucket>__<key>`）——
  不同桶 / 不同来源共用同一文件名会在第二次写时静默覆盖，把几万条清单截成几十字节，等于当场毁掉证据。
- **Windows `schannel SEC_E_INTERNAL_ERROR`** 是本地 TLS 故障，不是目标封禁；同期同机其他端口正常 200 即可排除。
- **口令含特殊字符被 CDN 400** → 反向说明真口令不含特殊字符，可据此收窄字典（真实高信息量副产物）。
- **口令规则仅「6-16 位无复杂度」+ 无验证码/无锁定/无枚举差异 = 可爆破，但字典 ceiling 很低**：17,899 组零命中即说明真口令是个人化串（手机号/姓名/生日），别再堆字典，转外部泄漏源。

## 6. 爆炸半径（先答再动手）

多租户平台（`minio_cluster_bucket_total` 三位数）**共用一台机**时，打平台侧 = 波及其他租户。
若授权只覆盖具名域，**只做只读验证并单点标注**，不擅自横扩。
