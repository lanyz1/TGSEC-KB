---
name: object-storage-takeover-mining
description: "OSS/S3桶接管:触发oss-sign取STS→SDK列桶→清单挖产物。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, cloud-storage, oss, s3, sts, credential-leak, artifact-mining, tenant-isolation]
    related_skills: [sensitive-dir-credential-hunt, userdata-grab, heapdump-credential-hunter, spa-api-discovery, saas-internal-endpoint-auth-bypass]
---

# 对象存储桶接管与内容挖掘(Object Storage Takeover & Mining)

一套可横向替换的攻击面族:**「后端边车把云存储签名白送前端」×「签名策略从不按租户收窄」×「桶是全平台共用的杂物间」**。
适用于任何把 OSS / S3 / COS / MinIO 签名下发给客户端直传的 SaaS 与自研平台。

## 何时用

- 抓包/前端 bundle 里出现 `oss-sign`、`upload-sign`、`getSts`、`sts-token`、`presign`、`policy` 这类接口
- 响应体里直接含 `accessKeyId` / `accessKeySecret` / `securityToken` / `expiration` / `bucket` / `region`
- 已拿到某租户低权限账号或 token,要验证**存储层有没有做租户隔离**
- 拿到泄露的 AK/SK(前端硬编码、`.env`、heapdump、公开仓库)
- **目标的静态资源域 / 上传口落点是对象存储**(上传回 `https://static.<域>/<md5>.<ext>` 一类 URL)—— 此时**桶名与 APPID 已被白送**,即使没拿到任何密钥也值得先做只读指纹 + 拿桶名去找密钥
- **反编译产物里出现「节点清单 / 远程配置」URL**(`NODE_LIST_URL`、`OBS_CONFIG_BASE`、`*_CONFIG_URL`、多节点选路实现)—— 桶名与**完整对象键名**都被白送,按名 GET 常直接可读 ⇒ 见 §0b

## 核心判据(先钉死这 3 条)

1. **"给了签名" ≠ 漏洞,"给了能开整桶的签名"才是。** 漏洞本体是**签发方的策略(Resource/Policy)从不按租户收窄** ——
   前端直传是正常设计;判据是**用租户 A 的凭据能不能读到租户 B 的目录、或列到桶里别人的对象**。
2. **必须用官方 SDK 实测才算真访问。** 手写 OSS/S3 V1 签名极易 `SignatureDoesNotMatch` ——
   那是**签名算法写错,不是权限不足**,据此写"无法访问"是假阴性。
   ```python
   import oss2
   auth = oss2.StsAuth(AK, SK, ST)
   b = oss2.Bucket(auth, "oss-cn-hangzhou.aliyuncs.com", bucket)
   sum(1 for _ in oss2.ObjectIteratorV2(b, max_keys=1000))   # 真实对象数
   ```
3. **写权限验证必须闭环可复原**:`PUT 探针 → GET 回读 → DELETE → HEAD 确认 404`,
   key 用 `pentest-probe/delete-me-<日期>.txt` 这类自说明路径;报告里只写"已验证并复原",**不要声称"无残留"**。

## AK 存在性 oracle(AK 已知但 SK 未知时 —— 把 AK×SK 搜索量砍成只剩 SK)

S3 兼容端点(MinIO / Ceph RGW / 云厂 S3)**只给 AK** 时回两种互斥且稳定的错误,构成一个免费的 AK 枚举 oracle:

| 响应文本 | 含义 |
|---|---|
| `The Access Key Id you provided does not exist in our records` | **该 AK 不存在** → 立刻换下一个 AK 名,不要浪费 SK 候选 |
| `The request signature we calculated does not match`(`SignatureDoesNotMatch`) | **该 AK 存在!只是 SK 错** → 锁定 AK,只爆 SK |

- **判据的硬逻辑**:不存在的 AK 没有密钥可比对,**永远不会**回 `SignatureDoesNotMatch`。所以后者出现 = AK 命中的字节级证据,不是"算法写错"
- 命中 AK 后 SK 空间骤降(运维惯用 AK 名如 `admin` 配的常是 `12345678` / `admin123` / 同段其它服务口令),**几十个候选就能进**
- **SDK 配置(MinIO 必配,否则预检就失败)**:
  ```python
  from botocore.config import Config
  cfgp = Config(signature_version="s3v4", s3={"addressing_style": "path"},
                connect_timeout=8, read_timeout=25, retries={"max_attempts": 0})
  c = boto3.client("s3", endpoint_url=ep, aws_access_key_id=ak, aws_secret_access_key=sk,
                   region_name="us-east-1", config=cfgp, verify=False)
  c.list_buckets()          # 唯一的判定动作
  ```
- **`retries={"max_attempts": 0}` 是必需项**:默认退避重试会让整轮爆破看起来"卡死"
- **端口分离**:MinIO 的 S3 API 与 console 常不同口(API `19000` / console `9001` 之类)。`GET /minio/health/live` → 200 且免鉴权,是用来的**存活+类型指纹**,不是漏洞
- **凭据不通用**:同段多台 MinIO 的 AK 可能重名而 SK 各异(一台 `admin` 能进、另一台同 AK 回 `SignatureDoesNotMatch`)→ **逐台独立爆**,别把单台命中当整段通杀
- **SK 可以完全离线爆**:拿到该 AK 签发的 **presigned URL**(含 `X-Amz-Signature`)时,可在本地复算签名比对候选 SK —— **零流量、零限流、不受 WAF/出口封禁影响**、随时可停。自校验必须用 `botocore.auth.S3SigV4QueryAuth`(真实 presigned 用 `UNSIGNED-PAYLOAD`,通用 `SigV4QueryAuth` 的空体 sha256 会让自校验假失败);`X-Amz-Credential` 是 URL 编码的,先 `unquote` 再 split。**只有自校验通过后的「未命中」才是可信负结论**;真未命中就停(随机长串不可字典化),转去找能读服务端配置的原语。完整步骤与判据见 `references/presigned-url-signature-secret-recovery.md`

## 步骤

### 0. 零凭据的桶发现: 上传口/静态域落点(先做这个)

- **判据: 上传口回 `https://static.<域>/<hex|md5>.<ext>`,而同一 key 用站点域/源站 IP 取 = 404** ⇒ 本地无副本 ⇒ 该静态域是对象存储,应用只是把文件 PUT 进桶。
- **只读指纹(零凭据)**: `dig <静态域>` 看 CNAME + `curl -I` 看 `Server:` 头 —— **腾讯云 COS** 露 `Server: tencent-cos` 且 CNAME 形如 `<bucket>-<appid>.cos.<region>.myqcloud.com`;**阿里 OSS** 露 `Server: AliyunOSS` 且 CNAME 指向 `<bucket>.<region>.aliyuncs.com`。`HEAD` 一个不存在的 key: 返 XML `<Error><Code>NoSuchKey</Code><Resource>/<bucket>/<key></Resource></Error>` = 桶存在且该域指向它(云厂 COS/OSS 都带 `Resource` 节点,直接读出桶名);匿名 `?list-type=2` 回 `403 AccessDenied` 是常态 —— **匿名列桶被拒 ≠ 桶没价值**。
- **收益不是那几个上传文件,而是「桶名 + APPID(账号 ID)」白送** ⇒ 拿它去站内配置面找密钥: 存储驱动/云存储类插件参数、系统配置接口、前端 bundle 里的 `secretId/secretKey`、`.env`。**本类目标的第一个高价值动作是「桶名到手 → 找服务端凭据」,不是继续在上传口上传。**
- **同时判死一条常见误路**: 对象存储**不解析 PHP/脚本**,且上传口常把文件名重命名为 `<内容md5>.<末段ext>`(或纯随机) ⇒ 双扩展名(`x.php.jpg`)、多语言马、`.user.ini` 全无意义。**落点是对象存储时,上传→RCE 直接判死**,把轮次投到找凭据上。

### 0b. 客户端节点清单 / 配置对象 = 运营方域名轮换清单(反编译常量直接给键名)

客户端(APK/桌面端)的「多节点选路」实现会把节点清单放在**对象存储上的一个固定对象**里,靠远程更新域名池。这条线比被动 DNS / 证书透明更**新**:

1. **键名从反编译常量取,不要猜** —— grep `NODE_LIST_URL` / `OBS_CONFIG_BASE` / `*_CONFIG_URL` / `DEFAULT_NODES` 一类字面量与配置文件名。实测同一个 App 给出 `https://<bucket>.oss-<region>.aliyuncs.com/<ns>/keepbit.txt` 与 `https://<bucket>.obs.<region>.myhuaweicloud.com/config<品牌>.txt`。App 内硬编码的 `DEFAULT_NODES` 是**出厂兜底**,桶里的那份才是**运营方当前生效**的(会随轮换被改写 —— 判据:桶内值与出厂值不同即证该对象仍在维护)。
2. **匿名列举被拒 ≠ 对象不可读** —— `ListBucket` 回 `AccessDenied` 是常态,但**按完整键名 GET 常直接 200**。拿到键名立刻按名读;再按命名空间横向试兄弟键(`<ns>/config.txt`、`<ns>/<另一品牌>.txt`、`node.txt`、`nodes.txt`)。
3. **收益是域名池扩张,不是对象里的几个字符串** —— 配置对象通常就是「chat / 钱包 / IM / 交易所」各线活体域名(含轮换与备用域)。**备用/轮换域加固程度普遍低于主域,是第一梯队新面**;同桶多份同名不同品牌的配置同时确认品牌族(一码多白标)。
4. **读对象的姿势**:经 SOCKS/代理读时**不要把 `Host` 覆写成桶名以外的值**(带自定义 Host 会拿到**假 404**,把活对象读成不存在);文本对象直接落盘再 grep。

**附带判据:免鉴权「按 key 取对象」代理端点**(形如 `GET /api/v1/file?key=<前缀>/<路径>`)
- 先用**一个已确认存在的对象**做基线:回**原始字节**(图片 magic)、Content-Type 为二进制 ⇒ 该端点 = **桶读代理**,key 前有前缀白名单(`startsWith("<ns>/")` 之类)。
- **穿越探测的读法**:`..`/`%2e%2e` 被对象存储 SDK 的 URL 归一化后,后端会把「上游 404 页 HTML」当对象内容解析并 500 —— **错误体里出现「解析上游 nginx 404 HTML 失败」本身,就是「该端点在远端取件」的正面证据** ⇒ 本地 LFI/SSRF 判死,别再在穿越编码上投轮次。
- 该端点即使不越权,也是**桶内容的免鉴权读取通道**;配任意一张同族后台票(列/上传/删除面)即成完整文件读写原语。

### 1. 找签名面(通常免鉴权或低权限即可)
```bash
GET /<service-prefix>/oss/material/oss-sign?isUse=true      # 典型: 参数是个没用的布尔
GET /<service-prefix>/file/sts-token , /upload/policy , /v1/sts
```
- 先用**任意已登录的低权限账号**试;很多平台的签名接口**根本没挂鉴权**(常落在"网关按前缀漏配鉴权"的那一片里)
- 响应体通常顺带给出 `bucket` / `region` / `prefix` 规则(`aicreate/prod/<tenantId>/<yyyy_MM_dd>/`)—— **prefix 里的 tenantId 直接暴露隔离设计**

### 2. 实测能力矩阵(逐项记录,这就是报告的证据)
| 能力 | 命令 | 判定 |
|---|---|---|
| 列桶 | `ObjectIteratorV2` 计数 | 对象数 + 总字节 |
| 跨桶 | `ListBuckets` / 换 bucket 名再列 | 是否只授了单桶 |
| 读 | `GET` 一个真实对象 | 内容回读一致 |
| 写 | `PUT` 探针 | 200/201 |
| 删 | `DELETE` 探针 | 204 → 再 HEAD 404 复原 |

### 2b. 桶家族枚举(桶名 = 用途-租户哈希,同后缀 = 同租户)

服务端自建网盘/云盘平台的桶名常带客户标识,格式是 `<用途>-<8位后缀>`(如 `system-u1i3hmko`、`backup-u1i3hmko`)。
**后缀相同 = 同一个客户**,而**策略是按桶单独配的** —— 同客户下常出现「系统桶只给 LIST、备份桶 GET 全放行」。
已知任一个桶名就能把整个家族挖出来:

```bash
# 1) 从任一已知桶名抽出后缀,枚举常见用途前缀
sfx=u1i3hmko
for p in system backup account avatar file upload tmp test log data code dist asset share user db export; do
  curl -s -o "NUL" -w "$p-$sfx %{http_code}\n" "https://s3.<平台域>/$p-$sfx?list-type=2"
done
# 2) 命中(200/存在)的桶逐个跑「能力矩阵」:LIST → GET 一个真实对象 → PUT 探针(闭环复原)
```

- **只要有一个桶可读,就把它的清单当索引去读同类兄弟桶** —— 客户源码/备份/导出包常不在系统桶里,
  而在名字看着像备份/导出的那个桶里(实测:`system-<hash>` LIST-only 403,`backup-<hash>` 的 `*.zip` GET 直接放行)。
- **读放行不蕴含写放行**:同一批桶 LIST+GET 全 200 而 PUT 逐个 403 是常态 ⇒ 写权限必须逐桶单独实测,
  且走「PUT → GET 回读 → DELETE → HEAD 404」闭环;探针 key 自说明(如 `pentest-probe/delete-me.txt`),
  报告只写「已验证并复原」,不声称「无残留」。
- **不要花轮次去读策略本身**：`?policy` `?acl` `?location` `?cors` `?tagging` 在匿名面几乎全 403；
  策略差分是**实测出来的**（哪个动词通、哪个不通），不是读出来的。
- 家族枚举的实战判据、以及「桶里挖到的引擎源码能不能直套线上」的判定，见
  `references/multitenant-oss-platform.md` §3.3。

### 3. 全量清单落盘(别下 TB 级内容)
```python
for i, obj in enumerate(oss2.ObjectIteratorV2(b, max_keys=1000)):
    f.write("%d\t%s\n" % (obj.size, obj.key))     # 清单 = "全部能拿到什么"的权威枚举
```
- 加 `python3 -u` + 每 N 条进度打点,否则大桶块缓冲 + 超时 = 跑完没落盘
- **清单即交付物**:TB 级内容既无必要又会冲击对端带宽,真下载了在报告里是减分项

### 4. 离线挖矿(本技能最大杠杆 ★)
桶是**全平台共用的杂物间**:运营/测试把构建产物、脚本、备份、导出表、配置模板顺手传进去。
在**本地**对清单做分类,**先排除媒体帧噪声**(`.ts .jpg .mp4 .m3u8` 常占 90%+,不清洗就会出现"命中 76 万代码文件"的假象):

| 类别 | 扩展名 / 关键词 |
|---|---|
| 构建产物 | `.jar .war .zip .rar .tar.gz .exe .apk .dmg` |
| 源码 / 脚本 | `.py .pyc .sh .js .java .go .php` |
| 配置 | `.yml .yaml .properties .xml .env .conf .ini .json` |
| 备份 / 导出 | `.bak .sql .dump .xlsx .csv .log` |
| 情报型文本 | `使用说明`, `README`, `template`, `模版`, `test/`, `gray/` |
| 平台源码发布包 | `<平台名>-code.zip`、`*all-code.zip`、`*前端*.zip`、`*修改好的*.zip`（厂商把自家全栈源码传进自家桶） |
| 用户 / 业务导出 | `*_insert.sql`、`users*`、`dump*`、`export*`、`*.xlsx` |
| 租户品牌配置 | `public/<品牌>/js/config.js`、`*.lua`、`config/` 目录 |

清单拿到后**先按名筛再下载**，而非按体积盲下；筛出的文本类批量落到本地目录再统一 grep 凭据关键词，命中即打上下文（见 `references/multitenant-oss-platform.md` §3.2、同桶家族与引擎源码判定见 §3.3）。

只下载命中的几十~几千个小文件。

### 4b. 备份桶 = 全库旁路(DBS / dump / export)
桶里若出现 `datamove/<库>/<表>/0` 这种键(或 `*-sql-dump`、`*-bak`),那是**数据库表级导出的 Parquet/SQL 快照** ——
用 `pyarrow` 在**本机**直读即可拿到联系方式、口令哈希与业务关系边,**不用连库、不用碰线上**。

- **★ 先桶根全量列举、再按段聚合,绝不按想当然的短前缀过滤** —— 真实键形如
  `<rand>/<full|incr>/<快照ID>/datamove/<库>/<表>/<分片>`，`datamove` 不在根下。
  `prefix="datamove/"` 这类口径**会静默少给几十上百张表**(同一个桶实测:短前缀口径 24 表 / 8.5 MB;
  桶根全量口径 **130 表 / 3,599 对象 / 7.6 GB**)。一次 `ObjectIterator(bk, prefix="", max_keys=1000)`
  后按 `/` 切段聚合 `tabs[库][表]` —— **「能不能拿到全库」只有全量列举能回答**,抽样列举不能。
- **分片 ≠ 完整**:大表(订单明细/达人日表)切成上千片(`<表>/0..1437`),按表聚合必须求和,别只取 `/0`。
- **0 字节对象 = 空表**,不是下载失败;导出空 CSV 并如实标注,别当缺件无限重试。
- **归档存储类读不了**:`head_object()` 的 `x-oss-storage-class` 为 `Archive`/`ColdArchive` 时 GET 回
  `InvalidObjectState` —— 要先 `RestoreObject` **解冻**(不可逆 + 计费)⇒ **属于必须用户明确点头的动作**,
  不要默默解冻。同账号下逐桶查,Standard(`dbs-backup-*`)与 Archive(`*-order-filie`)常混着放。
- **新鲜度必须量出来并写进交付**:对象 `LastModified` = 备份上传日,库内 `max(add_time/last_time)` = 数据截止日
  (实测备份是 3 年前的库快照)。回答"能不能拿下全部数据"时给**「快照全量 + 增量缺口」两句话**,
  不是一句"全部到手";增量另走 `*-sql-dump` 归档或后台导出接口。

表名分类地图、Parquet 直读与回本机管线、交付形状见 `references/db-backup-parquet-offline-dump.md`。

### 5. 二阶利用:配置 = 内网拓扑
`.jar/.war` 解开,**优先读 `BOOT-INF/classes/application*.yml` / `*.properties`** —— 一个文件换整张内网地图:
- 消息队列 / 注册中心 / DB / Redis 的**内网 IP:port**
- 内部 AI / 推理 / 转码服务的**内网地址**
- 对象存储的**服务端本地挂载路径**(如 `/data/oss`)、临时目录、下载根目录(如 `/wwwroot/download`)
- dev / test / prod 各 profile 差异(测试环境的弱口令与调试开关)
- 桶里的 `<业务域>/使用说明-*.txt` 与模板 `.xlsx` → **反向补全业务接口契约**,比盲扫端点高效得多

## 影响定级口径(报告必写)

| 级别 | 条件 |
|---|---|
| 高 | 单租户凭据可列/读**全桶**(含其他租户目录),或**可写可删** |
| 中 | 仅可写自己的 prefix,但签名策略 Resource 未收窄(结构性隐患) |
| 低 | 只能读自己 prefix,且 STS 短时效 + Resource 精确到 tenantId |

**规模数字只用清单统计口径**(对象数 / 总字节 / 前缀分布),别用"下载了多少 GB"。


## 全文导航（已拆分）

主卡保留前 5 节；其余 4 节在 `references/full.md`：

- Pitfalls
- 交付物
- 案例
- 关联

加载：`skill_view(name='object-storage-takeover-mining', file_path='references/full.md')`

## 一把 AK 的权限边界判定（2026-09 yzitc 实战）
- 先 `GetCallerIdentity`：返回 `acs:ram::<uid>:root` = **主账号根钥**（不是 OSS 子账号），权限面最大
- 同一把钥对多个桶/网盘 `uploads/` **读/写/删**都成立：只写 marker 验证，随后删除
- 列举：`ossutil ls oss://<bucket> -s`；对象数/总量写进报告口径
- 根钥到手后顺着 `RAM` 列表看有没有别的子号（常给运维/CI）

## 预发环境裸奔 + 回调伪造入账（2026-09 GOODLUCK777 实战）
- STG 预发域名无鉴权注册 + 支付回调无签名 → 自造回调入账
- 未授权全量封禁库（95,824 条）说明「封禁表」也常是独立服务，别只盯主 API
- 前端硬编码支付 AES 密钥 + 第三方 OAuth secret → 直接构造合法回调密文
