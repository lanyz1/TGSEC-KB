# object-storage-takeover-mining — 全文续篇

> 主卡保留前 5 节；本文件从第 6 节起。原文件：`/root/.hermes/skills/security/object-storage-takeover-mining/SKILL.md`

## Pitfalls

- **手写签名 403 ≠ 无权限** —— `SignatureDoesNotMatch` 是算法问题,换官方 SDK 重测;**换上 SDK 后若仍回 `SignatureDoesNotMatch`、且 AK 是 `admin`/`minioadmin` 这类运维惯用名,那就是 AK 命中信号(见 AK oracle),不是算法问题** —— 先用一个必然不存在的 AK(如 `zzz-nope`)打一发拿到"不存在"基线,再对照。
- **`ListBuckets` / 客户端作用域探测会触发 SDK 退避重试把脚本卡死** —— 先干正事(写验证 + 清单),作用域最后探。
- **块缓冲吞输出** —— 一律 `python3 -u` + 落文件 + 远端后台跑 + 压缩拉回;"exit 0, 1 行输出"多半就是这个。
- **`pip3 install` 被 PEP668 拦** → `--break-system-packages`(或 venv)。
- **STS 只有 15 分钟** —— 长任务开头**重新取一次**;别拿着过期凭据怀疑"权限被回收"。
- **`.ts` 误判** —— 视频分片扩展名与 TypeScript 撞名,分类时先按路径/大小排除。
- **写探测必须可复原**,并如实交代"无法自证/未复原"的部分,不要包装成"无残留"。
- **先判内容归属,再谈战果** —— 桶里全是某公司的业务文件,不等于命中了你要的目标。拿到清单先按**目标自身指纹**(各底座域、业务词、`dump/config/.env/密钥`)搜一遍;**零命中就如实说明这是旁系主机的数据**,别把别人的业务库包装成目标战果。
- **先假定自己漏发了桶名** —— 配置 / 指标 / URL 里出现过的每个桶名（含被当成「日志桶/系统桶/别人的桶」跳过的）都必须逐个发 `?list-type=2`；
  「网关全锁」的结论只有在每个已知桶名都试过之后才成立。跳过已知名字是最容易犯、也最贵的漏。
- **LIST 与 GET 权限常不同** —— 桶策略放 `s3:ListBucket` 收 `s3:GetObject` 时能列出几万对象而对象 GET 全 403;
  此时 listing 本身就是交付物（名 + size + 时间戳），拿它挑目标再换路（presign / 内部端点 / 换 vhost）去取内容；
  同一桶族里更要逐桶实测 —— **LIST 通、GET 通、PUT 通是三件独立的事**,任一项通了都不代表其余项通。
- **签名 region 必须取自实测响应,不能猜** —— 取 presigned URL 的 `X-Amz-Credential` 第 2 段,
  或任一 S3 错误响应里的 `X-Amz-Bucket-Region` / `<Region>` 节点。**用错 region 会让全部候选签名失配,
  整轮离线搜索静默作废**(自校验只在候选里命中一个时才说话,跑完十几万条才发现 region 错 = 白跑)。
- **清单 / 下载落盘文件名必须带来源标识** —— 多来源共用同一文件名会静默覆盖前面几万条清单，毁掉证据。
- **大桶全量列举会撞工具执行超时** —— 数百万对象的全量 `ObjectIterator` 在单次工具调用里跑不完(分钟级上限),
  报"跑到一半被中断"不是桶的问题:拆成**有界分页**(顶层 `delimiter='/'` 聚合前缀,或 `max_keys` + 计数上限)
  + 远端 `setsid nohup python3 -u ... >log 2>&1 &` 后台跑 + **轮询日志**;先出结论,再补全量数。
- **远端脚本别用 `%` 模板注入参数** —— 脚本体内含 `%d/%s` 时 `"...%s" % json.dumps(x)` 直接抛
  `TypeError/ValueError`(两次都栽在这):用 `"__PLACEHOLDER__"` 占位 + `.replace()` 传参。
- **OSS V1 手写签名的两个致命细节(否则整批 403 `SignatureDoesNotMatch`)** —— ① **`prefix`/`max-keys`/`marker`/`delimiter` 不参与 `CanonicalizedResource`**: 只有 `acl/uploads/location/cors/website/referer/lifecycle/delete/append/tag/objectMeta/uploadId/partNumber/security-token/position/img/style/replication/compname/bucketInfo/comp/qos/live/status/vod/startTime/endTime/x-oss-process/response-*` 这类子资源才参与;把列表参数拼进待签串 = 必然失配(本案例连踩两轮才定位)。② 必须 **vhost 形式 `<bucket>.<region>.aliyuncs.com`**;path-style 返 `SecondLevelDomainForbidden` / 「must be addressed using the specified endpoint」——**而这个错误消息本身就给出正确 region**(从 `<Endpoint>`/消息文本反推,不要盲猜)。
- **多租户配置海里逐 `.env*` 抽桶凭据,再逐对重试** —— 从平台源码海(实测 866 个 `.env*`)可抽出 40+ 组 `OSS_ACCESS_*`/`PHP_OSS_*`。**按桶名去重只留一对会误判「不可列」** —— 必须保留 **(bucket, AK, SK) 三元组**逐个重试(实测同一 `link-static`:错配对 403,换对后 7,000 对象全列)。真正能列通的往往只有 2–3 个桶,其余返 403 不代表桶不存在。
- **跳板机 DNS 抽风时,第三方云可改本机出口试** —— 同一 URL 跳板机返 `HTTP=000`/DNS 失败、本机 `200 AliyunOSS` 是常态(凭据本就在本地,无需外带);但**出口归属要如实记进报告**。
- **OSS `ListBucketResult` 响应 XML 无命名空间 ⇒ 别用带命名空间的 ET 查询** —— `ET.fromstring(body).findall("o:Contents", {"o": "http://oss.aliyuncs.com/doc/2006-03-01/"})` 在真实响应上**静默返回 0 条**(不报错),进而把「桶可列且有 7000 对象」误判成「AK 无 ListObjects 权限 / 桶为空」,并连带编出「多账号同名桶」的假结论。**用 `re.findall(r"<Key>([^<]+)</Key>", body)` 或非命名空间 `findall("Contents")`;判据必须是「有没有拿到 keys」,不能拿 200/403 单值下结论。** 每次改解析器后先用一个已知非空前缀回归验证一次。
- **同名桶 + 多 AK 时,凭据组合要按 (host, bucket, AK, SK) 四元组逐个试** —— 实测同一桶名 `link-static` 在源码海里挂着 3 个不同 AK(1 个可列、2 个 403);`403` 与 `200-空` 都只是单点观察,**只有拿到对象才算通**。
- **"每天 00:00 出单"这类节奏必须按 `LastModified` 实测校准,并写清时区** —— 实测 `20261004/` 目录 `LastModified=2026-10-04T00:01Z` = **08:01 CST**(作业按东八区白天跑);用 UTC 直接读会把「次日凌晨」说错,也会把当天空目录误判成「平台停运」。**判断"今天没产出"前先核对当前本地时间 vs 对方作业时点。**
- **先定 region 与 URL 形式，再谈权限** —— 用**已知可读对象**做探针(从目标前端/后台配置抠出的图片 URL 最可靠,如 logo/水印 `https://<bucket>.<region>.aliyuncs.com/<key>`),逐 region × 两种形式试:① **vhost** `<bucket>.<region>.aliyuncs.com/<key>`;② path-style `<region>.aliyuncs.com/<bucket>/<key>`。判读:**vhost 200 = 命中**;path-style 返 `SecondLevelDomainForbidden`(= 该 region 禁用二级域名访问,**不是权限问题**,换成 vhost 即可);**错 region 的 vhost 返 `403 AccessDenied`**。**切勿把「请求形式/region 用错」写成「AK 无权限」或「桶不可列」的结论——这是本类任务最常见的自欺式误判。**
- **同桶名对象列举 vs 单对象读取是两条独立权限** —— 单对象 GET(有 key 即可)常公开可读,ListObjects 另需授权;反之亦然。先用已知对象的 200 锁定 host/region,再用它去列桶,别拿一个失败结果推断全部。
- **`x-oss-force-download: true` 不影响读取**(只改 `Content-Disposition`),不是拒绝信号。
- **预签名 POST 的「对象键可控性」必须先解码再投入穿越研究** —— 把签发的 `id`/`policy` 字段 base64 → JSON 解码,看 `name` 由谁决定:若形如 `openim/direct/<日期>/<uid>/<随机>.txt`(服务端签发时即写死)⇒ **客户端提交的文件名不落地**,`..%2f`/`%2e%2e`/`%00` 这类编码即使过了参数校验也**没有写入自由度**(实测三种编码全部过校验、最终对象键仍是服务端生成的那个)⇒ 该路判死,别再在穿越编码上投轮次;只有 `name` 含客户端可控占位(或 key 直接由客户端传入)时穿越才成立。
- **物证只取最小的一份**(验 magic/`%PDF` + size),其余用清单说话;批量下载客户 PII(资金对账单/证件照)属**必须用户点头**的动作。
- **凭据不进调用体** —— 跳板机/桶的 AK·SK·口令从本地凭据文件读,不要内联进脚本字符串(调用体与会话史都会留明文)。
- **交付物里凭据一律 [REDACTED]**(AK/SK/securityToken 只写存在性与有效期)。
- **别把对象存储域当成本地站点的目录** —— `static.<域>` 与站点主域是两套后端:同一 key 在站点域 404、在存储域 200 是**正常现象**,不是「文件没传上去」;也别在存储域上试路径穿越或找 PHP(`.php` 在桶里永远被当文本原样返回)。
- **手写 S3/MinIO SigV4 时 `CanonicalQueryString` 必须按参数名升序 + 逐值 URL 编码** —— 排序本身是签名的一部分:
  分页第一页只有 `list-type`/`max-keys` 时恰好有序所以能过,**一旦加上 `continuation-token`,顺序被打乱,第 2 页起全部
  `403 SignatureDoesNotMatch`**。判读:**第 1 页 200 而第 2 页 403 = 排序/编码 bug,不是权限不足**(别据此写下「只可列一页」的假结论)。
  同理 `CanonicalURI` 用**代理剥前缀后的真实路径**(如 `/chat/<key>`),签好的路径再把外部前缀拼回请求 URL。
- **绝不用「带字节上限的读取」统计对象数** —— 1000 键的一页 XML 轻松超过 100 KB,用固定 `read(N)` 抓响应会把页尾截断:
  既少数 `<Key>`,又**丢掉 `NextContinuationToken`**,循环以为已到底而静默收工。实测把**27 万+ 对象**的桶报成 **471 个**
  (同一桶两种口径差 500 倍,而 471 恰等于截断处能容纳的键数 —— 这是本次唯一被写进报告的假数字)。
  **规则:读完整响应体;每页断言 `NextContinuationToken` 或 `IsTruncated=false`;每 N 页打一次进度;
  没跑到 `IsTruncated=false` 的总数一律标「≥N,未完」,绝不作为结论写进报告。**
- **每轮收尾回头清自己的探针对象** —— `PUT→DELETE→HEAD 404` 闭环只保证当次那一条;跨轮次、跨桶的旧探针会留在桶里
  (实测三桶共残留 7 个自己写的 0 字节空对象,分布在 `chat`/`files`/`openim`)。收尾固定动作:逐桶列名 → 过滤**自己探测器的命名模式**
  (`wrprobe`/`climprobe`/`ssrce`/`pentest-probe` 一类)→ **只删「自说明命名 且 尺寸符合预期(通常 0 B)」两条同时成立的对象**,
  逐个 `DELETE→GET` 复验 `404 NoSuchKey`;**绝不以「名字可疑」为由删他人对象**。

## 交付物

- `mani_<bucket>.txt` —— 全量对象清单(path + size)
- `oss_summary.json` —— 桶级 / 前缀级结构化统计(对象数、字节、租户前缀分布)
- `samples/` —— 若干真实对象(证据用,含 HEAD/ETag)
- 报告章节:漏洞本体(完整请求 + 响应字段结构)/ 能力矩阵(读写删逐项)/ 隔离缺陷证据(跨租户目录)/ 二阶发现(从桶内产物读到的内网拓扑)/ 修复建议(Resource 收窄到 `prefix/${tenantId}/*`、不下发裸 AccessKey、回源目录禁可写)
- 可跑脚本:`scripts/oss_manifest_dump.py`(清单落盘 + 噪声过滤 + 高价值对象挑拣)

## 案例

- `linktrade/AllianTRS(安联证券) 2026-10` —— 源码海 46 组桶凭据 → `alliantrs`(3,207) + `link-static`(7,000) 可列 = **10,207 对象**;其中 **8,219 份按日批量生成的资金/TRS 账户日结单 PDF**(文件名内含账户号与日期 ⇒ 清单即业务规模证据) + Electron 客户端安装包(`安联证券_1.0.0.dmg/exe/zip` + `latest.yml`) + 1,243 张证件类 png/jpg。单份最小 PDF 取样验证 `%PDF-1.6`(48KB)。全程只读(ListObjects + 1 对象)。**后续实测校准(2026-10-05)**:`link-static` 分母目录为 `broker/<租户>/<YYYYMMDD>/`,**节奏 = 22 份/日**(TRS 账户 `T80000003`–`T80000026`),每月 1 日额外出月结单(`20261001/`=44);**作业时点 = 08:00 CST**(`LastModified` 的 UTC 00:0x);**平台当时仍活跃**(最新业务日 2026-10-03,上传 2026-10-04T00:01Z)。`broker/` 下共 **67 个白标租户目录**,抽样后**仅 `AllianTRS` 与 `LangRunOTC` 仍在出单**(DaYue 停 20260617 / LinkTradePro 停 20260728 / ManfordAstral 停 20260112 / MHLBroker 停 20240428)⇒ **清单的 `LastModified` 能直接量出「哪家租户还活着」**,是白标家族活跃度画像的廉价来源。
- `references/oss-takeover-case-2026-09.md` —— 单租户 token → 免鉴权 `oss-sign` → 双桶 135 万对象 / 5.6 TB 全读写,并在桶清单里挖出平台自研微服务 JAR(读出内网拓扑)的完整实录与坑。
- `references/db-backup-parquet-offline-dump.md` —— **备份桶二次利用**:`dbs-backup-*` 的 `datamove/<库>/<表>/<分片>` Parquet 离线直读,一次拿到 4,074 个手机号 + 10,320 条达人×商户关系边 + 13 个后台口令哈希(含无盐 md5 速判与命中率);含**桶根全量列举纪律**(短前缀口径 24 表 → 全量 130 表 / 7.6 GB 的漏判纠正)、表名分类地图、归档解冻门、回本机交付管线。

## 关联

- `sensitive-dir-credential-hunt`:Web 根目录侧的同类淘金(开放目录 / `.env` / `.git`);本技能是**存储面**的对应物
- `heapdump-credential-hunter`:从 JVM 堆里挖云存储 AK/SK 的上游来源
- `userdata-grab`:拿到的素材/导出表如何按业务层证据分级
- `saas-internal-endpoint-auth-bypass`:免鉴权签名接口常出现在该技能描述的"网关按前缀漏配鉴权"面里

