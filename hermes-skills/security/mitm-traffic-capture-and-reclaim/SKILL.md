---
name: mitm-traffic-capture-and-reclaim
description: "需要把渗透过程的 HTTP 交换录成可查、可取证的流量证据、按任务归档独占流量、控索引体积与回收磁盘时加载；抓 WebSocket 帧与 SSE 事件流前也要先过本卡的流式闸门。含 mitmproxy 显式代理接入、上游代理与 passthrough 直通判据、头部与正文落盘形态、256KiB 内联与 sha256 内容寻址分界、trigram 全文检索、按 host/端口/方法/状态/时间分页、blob 分段读取 8KiB 上限、5MiB 闸门造成的零记录、archive 与 reclaim 的数值边界。"
sources: art-content, operator_experience
---

## 定位

把渗透过程中的每一次 HTTP 交换落成「索引可查、正文可取、能按任务归档、能按判据回收」的热存储，给取证与漏洞绑定供料。

## 抓取层

- 进程内嵌 mitmproxy（go-mitmproxy v1.9.2）。`Open(dir, addr)` 建 `<dataDir>/traffic`、`_index`、`_blobs`、`_ca` 四个目录，起代理时 `Options{Addr: addr, SslInsecure: true, CaRootPath: dir/_ca}`；客户端信任 `<dataDir>/traffic/_ca/mitmproxy-ca-cert.pem` 即可解 HTTPS。
- 显式代理接入。`ProxyAddr()` 回 `http://<addr>`，裸 `:8788` 归一成 `http://127.0.0.1:8788`，默认监听 `127.0.0.1:8788`（启动参数 `-proxy`）。子进程按 `proxyEnv` 注入 `HTTP_PROXY`/`HTTPS_PROXY`/`http_proxy`/`https_proxy`/`ALL_PROXY`/`all_proxy` 与 `NODE_USE_ENV_PROXY=1`；录制开着时再注入 `SSL_CERT_FILE`/`CURL_CA_BUNDLE`/`REQUESTS_CA_BUNDLE`/`GIT_SSL_CAINFO`/`NODE_EXTRA_CA_CERTS` 指向同一张 CA，命令里不必手写 `-x`/`-k`。
- 无透明劫持代码。`SetShouldInterceptRule` 只裁 CONNECT 后是 MITM 解密还是裸隧道 `directTransfer`；前端 iptables/TPROXY 重定向不在本链路内，要抓非代理流量得自己在网关上做，或把工具的代理变量指到 `ProxyAddr()`。
- 上游代理。`SetUpstreamProxy(raw)` 收 `http`/`https`/`socks5`（`ValidateProxyURL` 校验 scheme 与 host，可带 `user:pass`），存进 `atomic.Pointer[url.URL]` 热切换；空串写回 nil 即强制直连，同时盖掉环境里 `HTTP_PROXY` 带来的默认回退，目标流量不会从系统代理漏出去。
- 直通（passthrough）。`RequestError` → `maybePassthrough` → `proxyCausedErr` 只认 `head request`、`http2`、`http/2`、`protocol error`、`protocol_error`、`malformed`；命中就按 `hostOnly()` 把主机写进 `pass sync.Map`，该 host 后续连接只透传、不再记录。目标侧错误（`connection refused`、`reset by peer`、`deadline exceeded`）不触发直通，仍然 MITM 记录。
- 脱敏：不做。头部按 `headerLines` 原样落盘，`requestHeaderLines` 只补 `Host`（net/http 把它存在 `Request.Host`，不补就丢）。

## 记录模型

三张表加一个 FTS 影子表，正文不进文件树。

- `exchanges(id, ts, host, method, url_template, url, status, content_type, req_len, resp_len, path)`；`url_template` 由 `db.TemplatePath` 折叠：数字段→`{id}`、UUID→`{uuid}`、≥16 位 hex→`{hex}`、≥24 位 `[A-Za-z0-9_-]`→`{token}`，`/user/123` 变 `/user/{id}`。
- `exchange_bodies(id, req_head, req_body, req_blob, resp_head, resp_body, resp_blob)`。
- `blob_refs(hash, exchange_id)`，主键 `(hash, exchange_id)`，GC 的唯一依据。
- `ex_fts(content)`，`tokenize='trigram'`、`content=''`、`contentless_delete=1`。
- id 形态 `%d-%04d`：秒级时间戳加 4 位序号（`seq%10000`），同秒过一万条会撞号并被 `INSERT OR REPLACE` 覆盖。
- 头部原文：请求是 `METHOD URI PROTO` 首行接 `Host: ...` 再逐行头；响应是 `HTTP <code>` 首行接逐行头（状态码后不带 reason，取状态看 `status` 列）。
- 大小分界：`maxInlineBody=256KiB` 以内整包内联进 SQLite；超过则整包写 `<dataDir>/traffic/_blobs/sha256/<hash 前 2 位>/<sha256>.bin`，行内只留 `blobPreview=8KiB` 预览——文本走 `truncateUTF8` 不切半个汉字，二进制留一行 `[binary <ct>, <n> bytes, magic=<前 4 字节 hex>]`。已入库的正文不截断，截断只发生在预览与工具返回值上。
- 二进制判定：`binaryTypes` 前缀表（`image/`、`audio/`、`video/`、`font/`、`application/zip`、`application/pdf`、`application/vnd.android.package-archive` 等）加「前 512 字节含 NUL」兜底；二进制正文只落 blob，一个字节都不进 FTS。
- 压缩不处理。上游 client 设了 `DisableCompression: true`，拿到的是线上原始字节，`gzip`/`zip` 按 Content-Type 归二进制原样封存；要看解压后的内容得自己从 blob 取。
- 去重键只有正文：sha256 内容寻址加 `blob_refs` 引用；exchange 本身逐条入库，同一 URL 打两次就是两行。

## 协议覆盖

判据全在抓取回调，不看配置项。

- HTTP/1.1：响应体读全后触发 `Response`，`record()` 取 `f.Request.Body` 与 `f.Response.Body` 全量落盘。
- HTTP/2：协商到 h2 时同一 handler 走 h2 server，`Response` 照样触发，记录与 h1 同形。
- 5MiB 闸门：`StreamLargeBodies` 默认 5MiB 且本链路未改，请求体或响应体一到 5MiB 即 `f.Stream=true`，`Response` 不再触发，该条交换整条不落盘——不是截断，是零记录。抓大备份、大导出前先确认体积。
- WebSocket：`Connection: Upgrade` 配 `Upgrade: websocket` 走 `handleWSS`/`handle`，flow 只有 Request，`WebSocketStart`/`WebSocketMessage`/`WebSocketEnd` 在本实现里没有回调体，帧只转发，`f.WebScoket.Messages` 随 flow 丢弃，库里查不到任何 WS 帧。要帧级证据就换 mitmdump 的 ws 落盘插件，或先记握手再单独抓业务 API。
- SSE：`Content-Type` 含 `text/event-stream` 即强制 `f.Stream=true` 并触发 `SSEStart`/`SSEMessage`/`SSEEnd`，同样没有回调体，事件不入库且 `Response` 不触发，整条流零记录。`curl -N` 直接落文件是本链路外唯一稳的取法。

## 索引与检索

- `Page(PageQuery, page, size)`：`size` 缺省 100、上限 500；`Host` 走子串，`Method` 精确（自动大写），`Path` 是 `url_template` 子串，`Status` 收 `404` 精确与 `4xx` 区间（首字符 1-5 配 `xx`），`RespMin`/`RespMax` 传 `-1` 跳过，`Query` 是六个元数据列 LIKE 与 FTS 的并集，`Body` 只打 FTS。排序白名单只有 `ts`/`status`/`resp_len`，尾部固定 `id DESC` 让翻页稳定，同时回 `total`。
- 面向 agent 的 `query(host, contains, bodyContains, page, limit)`：`host` 必填（裸主机、`host:port`、完整 URL 都收），`contains` 打 `url`/`url_template`，`limit` 缺省 3、上限 10，`page` 从 0 起。
- 全文门槛 `minTrigram=3`：短于 3 字符的正文关键词直接报「正文搜索关键词至少需要 3 个字符」，`Page.Body` 里则静默跳过。trigram 支持任意子串（`ssw0r` 命中 `P@ssw0rd`）与中文。
- 端口隔离：库里的 host 去端口（`URL.Hostname()`），带端口查询时补 `url LIKE '%://host:port/%'` 三种形态兜底；同 IP 多服务必须带端口，否则串包。
- 单条正文：`Get(id)` 拼 `req_head` 加空行加 body，命中 blob 的那侧尾部追加 `\n…[truncated] @blob sha256:<hash> (len=N)`。
- 分段读取：`BlobRange(hash, offset, length)`，`offset<0` 归零、`offset>=总长` 回空加总长、`length<=0` 或越界读到末尾；工具 `traffic_blob` 强制 `length <= maxBlobRead=8KiB`，回包首行给 `[offset= 本次= 总长=]`，二进制只回前 512 字节 hex。
- 工具侧另有两道截断：`traffic_get` 请求截 2500 字节、响应截 4000 字节；`traffic_search` 只回 `id`/`method`/`url`/`status`/`resp_len`。

## 归档与回收

- archive 时机：任务归档作业先 `ExportHosts(snapshot.Hosts, payload/traffic)`（38% 阶段），再 `StageDeleteHostsExactForArchive(snapshot.ExclusiveHosts, job.ID, job.TaskID)`（68% 阶段）暂删独占流量，`CompleteTaskArchive` 提交后才 `Commit()`；提交前任何一步失败都 `Rollback()` 还原。
- 导出物：`traffic.json`（`ArchiveSnapshot{version:1, exchanges[], blobs[]}`，每个 `ArchiveExchange` 带 `req_head`/`req_body`/`req_blob`/`resp_head`/`resp_body`/`resp_blob`）加 `blobs/<sha256>.bin`；大正文不做 base64，直接拷内容寻址文件保住去重。导出与导入都持 `wmu`，正文与索引行取自同一时点。
- `ImportArchive`：只补缺失 id（`INSERT OR IGNORE`，热行永远优先），先按 `^[0-9a-f]{64}$` 校验 hash 再逐个重算 sha256，随后重建 `ex_fts`，重复导入幂等。
- reclaim 判据：删除行数大于 0 才触发；`reclaiming` 原子单飞；后台分块，每块 `reclaimChunkPages=8192` 页（4KiB/页，约 32MiB）后放掉 `wmu`，`reclaimMaxSteps=512` 步封顶、`reclaimBudget=5min` 封顶；FTS 侧每块做一次 `merge -256` 页、最多 `reclaimMergeSteps=16` 次；收尾 `wal_checkpoint(TRUNCATE)` 才算真正还盘。
- 安全边界：`auto_vacuum=incremental(2)` 只在空库首次建表时能写进文件头。老库（`auto_vacuum=0`）里 `incremental_vacuum` 是空操作，此时只做 FTS 合并并打日志「索引未启用增量回收…需要执行一次存储压缩来转换」，唯一转换入口是 `DeleteAll` 的 `compactIndex`（`optimize` 加 `auto_vacuum` 加 `VACUUM` 加 `wal_checkpoint(TRUNCATE)`）。
- 删前移动：host 目录先进 `<dataDir>/traffic/_delete_staging/hosts-*/`（同盘 `rename`，原子），写 `journal.json{version:1, archive_id, task_id, hosts, moves}` 并 `fsync`，提交后由 `reapStage` 后台删。崩溃恢复走 `RecoverHostDeleteStages(archiveCommitted)`：归档未提交就还原目录，已提交则补删索引行再清暂存。
- 证据与可清理区分离：绑漏洞时 `ReadEvidence` 把正文复制成独立证据快照（`SourceTrafficID`/`CapturedAt`/`URL`/`Method`/`Status`/`ContentType`/`ReqHead`/`RespHead`/`ReqHash`/`RespHash`/`ReqLen`/`RespLen`，字段规整后单独算出快照 id）。host 级删除与 `DeleteAll` 都动不到已绑定证据。
- blob GC：从 `blob_refs` 取活引用，只有存在 `path<>''` 老行时才扫 `request.http`/`response.http` 里的 `@blob sha256:` 指针，删无引用 `.bin` 与空桶目录。

## 体积与性能闸门

- 没有 ring buffer：全部落盘。`wmu` 串行化 `record()` 与删除、回收；`record()` 在 mitmproxy 回包给客户端之前执行，写慢一次就拖慢那一条被录请求。
- 逐条事务：一次交换一个 `Begin`/`Commit`，写失败只打日志丢该条，不阻塞代理。
- 双写分离：正文超 256KiB 先落 blob 文件再开事务，文件 I/O 不占 SQLite 写锁。
- 膨胀主因：≤256KiB 的正文全在 `index.sqlite` 里，trigram 索引体积约为被索引正文的两倍；`indexBytes()` 把 `index.sqlite`、`-wal`、`-shm` 一起算。
- 超大正文三条路：≤256KiB 内联；256KiB~5MiB 落 blob 且全文可搜（FTS 从内存喂料，`maxIndexBody=4MiB` 封顶，超出部分能 blob 读到但搜不到）；≥5MiB 整条不录。
- 并发：多 worker 同时打同一代理时靠 `wmu` 排队，记录条数与请求条数一一对应（并发 50 的用例覆盖了 id 唯一与三表齐全）。

## 失败模式与判据

- FTS5 缺失：`fts=false`，记录与元数据搜索照常，正文搜索回「当前实例未启用全文索引」并拒绝该次查询。
- blob 目录建不出或写失败：退化成 8KiB 预览内联，该条正文拿不回完整版。
- 老库删了不缩盘：查 `PRAGMA auto_vacuum`，非 2 就别期待 host 级删除释放空间。
- 删除半途文件系统失败：`restoreTrees` 逆序还原已 `rename` 的目录，索引事务回滚，函数返聚合错误。
- 直通后无记录：日志出现「改为透传」即该 host 从此查不到新流量，属设计行为而非采集故障。
- hash 非法或缺失：`非法的 blob hash`、`blob <hash> 不存在`；只有 legacy 行才靠 `path` 回读，`Get` 报「exchange <id> 无正文记录」说明索引与 blob 两处都没有正文。

## 与既有卡衔接

- 取证链：`web-sec` 出 payload 与验证手法，回本卡走 `traffic_search` → `traffic_get` → `traffic_blob`，再把确认的 id 交 `bind_finding_traffic` 绑定。
- 靶场调度与阶段编排：`pentest-execution`、`tgsec-suite` 定目标与攻击面，本卡只管「录到、查到、归档、回收」这一段。
- 找相邻技术卡：`tgsec-arsenal-router` 按栈与症状检索，`secatlas` 补案例视角。
