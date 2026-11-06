---
name: cloud-storage-bucket-recon
description: "Use when OSS/S3 bucket names leak. Classify ACL and keys."
version: 1.0.0
tags: [oss, s3, aliyun, bucket, recon, sts, cloud-storage, backup-leak]
---

# 云对象存储桶侦察（Aliyun OSS / S3 类）

APK、JS、图片 URL、错误文案里常泄露桶名。目标不是「列桶」，而是判断**哪个桶可能装 DB 备份/源码**，以及有没有匿名对象读或 STS 旁路。

## Triggers

- 自定义域 `oss.<domain>`、`<bucket>.oss-cn-*.aliyuncs.com`、S3/GCS 端点
- APK strings 出现 `cc12348`、`*-backup`、`*-data`、`*-app`
- 403/404 XML（`NoSuchBucket` / `AccessDenied` / `NoSuchKey`）
- 业务是 IM/App，头像/文件走 OSS；想知道备份桶

## 1. Aliyun OSS 403/404 语义（先读 `<Code>`，别只看状态码）

| 响应 | 含义 | 下一步 |
|---|---|---|
| 404 `NoSuchBucket` | 桶名不存在/可注册 | 换名 |
| 403 `must be addressed using the specified endpoint` | **桶存在，但在另一个 region** | 从 XML `<Endpoint>` 取真实 endpoint，换域重试 |
| 403 `Anonymous user has no right to access this bucket` / `AccessDenied` | 桶存在，匿名列目录被拒 | 仍要测对象 |
| 403 `PublicEndpointForbidden ... use CNAME instead` | 桶策略禁止 OSS 公网 endpoint | 用绑定的自定义域/CNAME |
| 403 `You have no right to access this object because of bucket acl` | 对象也私有 | 放弃匿名；找 STS/签名 URL |
| 404 `NoSuchKey` | **匿名对象 GET 可用**，只是 key 不存在 | 进入 key 爆破/路径推断 |

**核心：列目录 403 ≠ 对象不可读。** 桶 ACL 私有只挡 List，对象可能 public-read；反之亦然。永远用「随机 key」和「列目录」两个请求分别判定。

## 2. Procedure

1. **收集桶名**：APK strings（`grep -raoE '[a-z0-9-]{3,40}\.oss-cn-'`）、JS、头像 URL、错误文案、证书 SAN、公司命名（品牌+电话、`-backup`、`-data`、`-app`、`-im`、`-file`、`-static`、`-test`）。404 很便宜，20–30 个候选起步。
2. **定 region**：对每个桶请求 `https://<bucket>.oss-cn-beijing.aliyuncs.com/x`，从 403 XML 提取 `<Endpoint>`；再用正确 endpoint 重试。不要因为北京 endpoint 403 就判「私有」。
3. **分 ACL**：正确 endpoint 上 `GET /?prefix=`（列目录）+ `GET /nonexistent_<rand>.sql`（随机 key）。按上表分类。
3b. **匿名写测试（S3/OSS 都做，2026-10 实测）**：`PUT /hermes_probe_<rand>.txt` 带唯一 body——S3 回 **200** 即公开可写，随后 `GET` 同 key 验证、再 `DELETE` 清理（OSS 一般是 403 `AccessDenied`）。公开写桶 = 可托管钓鱼页/投毒图、可覆盖已知资源 key；但对象存储不执行 PHP/JSP，别写成 RCE。写完新 key 后，**用已知存在的旧 key 去测 CDN 域**：旧 key 也 404 = CDN 不是这个桶的源站，别把「新 key 在 CDN 404」误判成写失败。
4. **对象可读时**只爆破**确定性 key**：日期（`YYYYMMDD`/`YYYY-MM-DD`）、备份名（`backup.sql`/`db_YYYYMMDD.sql`/`cc_<date>.sql`）、配置（`config.json`/`.env`）、导出（`users.csv`/`users.sql`）、应用更新路径（`apk/<ver>/app.apk`）、已知文件的 MD5。**UUID/业务路径不可猜，200 个 key 不中即停。**
5. **自定义域**：`oss.<domain>` 可能只映射主桶；列目录可能回 `The bucket you access does not belong to you`，但对象 GET 正常（头像 `avatar/<uid>/<yyyymm>/<uuid>.jpg` 可匿名读）。CNAME 与 OSS endpoint 都要试。
6. **高价值 pivot = STS**：找 App 的上传/临时凭证端点（如 `file/getBigFileUploadInfo`），按错误文案补字段（`file_md5` 等），若返回 `accessKeyId/accessKeySecret/securityToken`，用 STS 列 `*-backup`。备选：JS/响应里的签名 URL、OSS Browser 泄露的 AccessKey。
7. **备份桶优先级**：名字含 `backup`/`data` 且在外区（如 `eu-central-1`）= 最像 DB dump；即使匿名不可读，也值得为它找 STS/凭据。

## 2b. 上传 token ≠ 只能传图片：CDN 内容类型就是攻击面（Qiniu 实证，2026-10）

App 的 `/v1/blob/qiniu`（或同类 upload-token 端点）即使返回**服务端固定 key**（policy `scope: bucket:cart/YYYYMMDD/<uuid>`，不能改 key、不能覆盖旧对象），也几乎总能控制**上传内容与 Content-Type**。一次探测就能判断桶域是不是 JS/HTML 宿主：

1. 取 token：`POST /v1/blob/qiniu`（Bearer）→ `{fileUrl, host, key, token}`。
2. 解 policy：token 形如 `AK:sign:base64url(policy)`，解出 `scope/deadline`；scope 锁 key 不影响内容。
3. 分别传 HTML 与 JS：multipart `token,key,file`，file 的 `Content-Type` 用 `text/html` / `application/javascript`。
4. `GET fileUrl` 看响应头：`Content-Type` 是否按上传值回显、`X-Content-Type-Options` 是否缺失。
   - `text/html` + 无 nosniff → 平台可信域上的钓鱼页；`application/javascript` + 无 nosniff → **可信域 JS 宿主**，可直接喂给存储型 XSS 的 `<script src>`，绕过只放行自家 CDN 的 CSP。
5. key 服务端分配 ≠ 死路：每次请求都给新 key，等于无限量托管；但**不能覆盖已知对象**，别写成「可篡改生产资源」。

**关键边界**：这只解决**托管**，不解决**投递**。没有存储型 XSS / 可发消息的真人通道时，它只是把钓鱼页换到更可信的域名——「传上去了」≠「打进去了」。

### S3 桶存在性三态 + ACL 误判（同轮实测）

- `GET https://<bucket>.s3.<region>.amazonaws.com/?list-type=2&max-keys=5`：**403**=桶存在但私有；**301 PermanentRedirect**=桶存在但在别的 region（按 XML `<Endpoint>` 换域）；**404 NoSuchBucket**=不存在。
- `?acl` 回 **200 且只授 `AllUsers READ_ACP`** ≠ 对象可读：ACL 可读只是元数据，List/Get 仍 403。别把 ACL 200 当突破口。
- website endpoint：`NoSuchWebsiteConfiguration` = 未开静态站；`AccessDenied` = 开了但策略拒（值得再试对象 key）。

## 3. Pitfalls

- **STS 场景全部 scope 到自有前缀（2026-10-21 IM 实测）**：`/sys/oss/directToken` 的 `user_avatar/chat_image/realname_image/group_avatar` 等 14 个场景，返回 STS 均只允许 `direct/session/<自己的uid>/`；逐场景 `list_objects(prefix=chat/|user/|realname/|group/|"")` 全 `AccessDenied`。`objectKey` 会暴露服务端真实路径（`direct/session/<uid>/<uuid>/user/realname/...`），但**不能跨用户读**；prefix/key 里塞 `../` 试图逃逸前缀同样 403——服务端按规范化后的资源匹配，别在 STS 上磨穿越。
- 403 一律当「存在但私有」是错的：region mismatch、endpoint policy、object ACL 是三种不同状态。
- **同后缀批量 403 ≠ 对象存在（腾讯 COS 实测）**：桶策略可能按扩展名/前缀统一拒绝——`app.apk`、`wanjun.apk`、`random123.apk` 全 403，而随机 `.txt`/`.zip`/`.sql` 才 404。看到一批同后缀 key 全 403 时，先打对照组（随机名同后缀 vs 另一后缀）再判断，否则会把不存在的 APK/备份当命中。
- **静态网站端点会掩盖 404（腾讯 COS `cos-website.<region>.myqcloud.com`）**：缺失 key 常回 **200 + HTML 兜底页**（SPA fallback），与真实对象同为 200。命中判定看 `Content-Type`/`Content-Length`/magic bytes，不看状态码；对比 `<bucket>.cos.<region>.myqcloud.com` 的 403/404 才是存在性信号。
- 腾讯 COS 常见组合：站点文件（index.html/css/logo）public-read 200、List `AccessDenied` 403 —— 与阿里云一样把「列目录」和「随机 key」分开判，别因为 List 403 就放弃对象层。
- **品牌/env 桶命名（`brand`、`brand-card`、`brand-dev`）常 object-public 但对象为空**：`NoSuchKey` 只证明匿名 GET 可用，不是数据泄露；`xcard-dev`/`xcard-card` 这类桶对象公开但确定性备份 key 全空，别把「桶存在 + 对象可读」写成「拿到备份」。
- **匿名 PUT 200 要回读确认**：PUT 成功不等于对象可读/可覆盖目标 key；先 GET 自己写的 key，再判断覆盖面。覆盖生产资源（礼包图/公告图）前先备份原对象，测完恢复原状。
- 不要对 UUID 路径做大规模爆破：命中率≈0，还可能触发云侧限流。
- **`oss2.Bucket(auth, endpoint, bucket_name)` 参数顺序（2026-10 实测）**：Python oss2 的签名是 `Bucket(auth, endpoint, bucket_name)`；写反会抛**客户端** `ClientError: The bucket_name is invalid`（status -1、request-id 为空），不是 OSS 服务端错误。看到 status -1/空 request-id 先查 SDK 参数顺序，别改桶名/region。
- **302 预签名 URL 只泄 AK ID**：`/object/<key>` 302 到 `...?OSSAccessKeyId=LTAI...&Signature=...`，Secret 仍在服务端；除非在泄露仓库/配置里拿到**同一对** AK/Secret，否则无法复用。拿到别的项目 AK 对时，先 `list_buckets`（空=无 List 权限）+ 目标桶 `list_objects`（`AccessDenied`=不同阿里云账号；`NoSuchBucket`=桶名/region 错）再判定，不要因 AK ID 前缀相同就认为同账号。
- **路径代理是哈希键**：`/object/<path>` 可能把 path 做 `md5` 后映射到 `openim/data/hash/<md5>`；`../`/编码穿越只会被哈希成另一个不存在的 key（回 200 错误 JSON 或 404），不是本地文件读取。判断法：已知对象 302 的 Location key 与请求 path 不同 = 哈希映射，放弃穿越。
- 列目录成功不代表能下载（ACL 可以 List 但对象 private）；列目录失败也不代表不能下载。
- `oss.<domain>` 与 `<bucket>.oss-cn-*.aliyuncs.com` 的 bucket policy 可能不同；两个都测。
- 拿到 STS 后先 `ListObjects` 目标备份桶，再谈下载；不要直接假设角色有全桶权限。
- 记录边界：桶名、endpoint、错误码、已试 key 数。报告里不要把「存在备份桶」写成「拿到备份」。

## 4. Support files

- `references/aliyun-oss-case-20261017.md` — 实战桶清单/错误串/key 爆破结果。
- `references/xcard-oss-case-20261019.md` — XCard/bitcoinscard 7 桶案例：object-public/List-403、dev 桶空、region mismatch。
- `scripts/oss_bucket_classify.py` — 输入桶名列表，自动探 region/列目录/随机 key 分类。
- `references/upload-token-cdn-content-type-host.md` — 上传 token 控 Content-Type → 可信域 JS/HTML 宿主（Qiniu 实证）；S3 桶三态/ACL 判读。

## 桶里最常见三类高价值物（2026-09 实战）
- **`.git` 目录**：`/.git/config`、`/.git/HEAD` 可读 → 用 `git-dumper` 拉全量源码（含 `.env`）
- **生产 APK/IPA**：`app-release.apk` 233MB 级，含硬编码密钥与后端域名
- **源码包**：`dist.zip`、`source.zip`、`backup.sql`
- 判定顺序：`GET /?list-type=2`（S3）→ `?prefix=` 分页 → 已知 key 直取；GCS 用 `storage.googleapis.com/<bucket>?prefix=`
- 交付：对象数、总大小、命中文件名（不下载全量业务数据）
