# 案例:单租户 token → 桶全接管 → 清单挖出平台自己的微服务 JAR(2026-09)

> 目标族:多租户 SaaS(Spring Cloud Gateway + 自研 `micro-*` 微服务前缀)。凭据一律 [REDACTED]。

## 1. 签名面(免鉴权,低权限账号即可)

```
GET /micro-creation-publish/oss/material/oss-sign?isUse=true
     Header: creation-authorization: Bearer <任意租户用户的 token>
→ { "accessKeyId":"STS.xxx", "accessKeySecret":"[REDACTED]",
    "securityToken":"[REDACTED]", "expiration":"...", "bucket":"yx-aicontent-local",
    "region":"oss-cn-hangzhou", "durationSeconds":"900",
    "prefix":"aicreate/prod/<tenantId>/<yyyy_MM_dd>/" }
```

判据全中:
- 签名接口**没挂鉴权**(用租户 113 的普通 token 直接过)
- STS **15 分钟**时效
- `prefix` 里带 `<tenantId>` —— 看起来像做了隔离,**但策略 Resource 实际是 `*`**

## 2. 实测能力矩阵

| 能力 | 结果 |
|---|---|
| 列 `yx-aicontent-local` | ✅ 511,370 对象 / 335 GB |
| 列 `yx-aicontent-creation` | ✅ 842,806 对象 / 5,280 GB |
| `PutObject` 探针 | ✅ 通过 |
| `GetObject` 回读 | ✅ 与写入字节一致 |
| `DeleteObject` + `HEAD` | ✅ 已复原(404) |
| 跨租户目录 | ✅ `aicreate/prod/<tenantId>/` 下能列出 47 / 90 / 1 / 104… 多个租户 —— **存储层无隔离** |

合计 **≈135 万对象 / 5.6 TB**,一个租户的凭据 = 全平台素材的读写删权限。

**踩过的坑**:手写 OSS V1 签名一律 `403 SignatureDoesNotMatch` —— 误判成"权限不足"会得出完全相反的结论。换 `oss2` 官方 SDK 后立即全通。

## 3. 清单挖掘:本轮真正的杠杆

清单格式实测是 **`<size>\t<key>` 一行一条**(不是"key 在前")—— 解析方向搞反会让所有 size 变 0,分类全错。

第一次扫出 "76 万个 `.ts` 代码文件"这种荒唐数字 → 原因:**HLS 视频分片扩展名 `.ts` 与 TypeScript 撞名**,必须先按大小/路径排除媒体噪声(实测噪声占 90%+)。

清洗后:非媒体对象仅 3k 余,其中命中:

| 对象 | 价值 |
|---|---|
| `creation/test/disassemble/20250423/micro-creation-ai-sidecar-0.0.1-SNAPSHOT.jar`(70 MB) | **平台自己的微服务构建产物** |
| `models/testing/log/server.py` | 内部 AI/TTS 服务源码(无鉴权 + CORS `*` + 任意路径读写) |
| `*/使用说明-*.txt`、模板 `.xlsx` | 业务接口契约 |

**JAR 解包读 `BOOT-INF/classes/application*.yml`,一个文件换来整张内网地图:**

```
rocketmq.namesrv            172.17.98.204:5100        (gray 环境)
ai.http.endpoint            http://10.9.50.123:5000/invoke
oss.local-prefix            /data/oss                 ← 对象存储在该主机的本地挂载点
download.base-path          /wwwroot/download
test profile                10.9.50.214:31003
```

这些内网 IP/端口随后被用作 SSRF 与横向的靶标清单。

## 4. 邻接教训:别把第三方抓取当 SSRF

同一轮里另一个端点描述写着「解析 url 保存录制任务」,参数就叫 `url` —— 看着像教科书 SSRF。三方差分后:

| 载荷 | 结果 |
|---|---|
| 公网真实可达的 pdf | **`code:0 操作成功`** |
| `http://127.0.0.1:<内网口>/actuator/health` | 失败 |
| `http://100.100.100.200/latest/meta-data/` | 失败 |
| 不可解析域名 | 失败 |

结论:**抓取发生在第三方云产品侧(报错文案自带答案:「添加文件至<云产品>数据管理失败」),不是目标服务** → 不是 SSRF,从报告里撤掉。
`file:///etc/passwd` 的失败**不构成任何证据**。判定法见 `pentest-finding-verification` 的假阳性判据。

## 5. 交付与口径

- 交付:`mani_yx-aicontent-local.txt`(51 万行)、`mani_yx-aicontent-creation.txt`(84 万行)、`oss_summary.json`、`samples/`(10 个真实对象)、报告
- 规模只用**清单统计**口径(对象数 / 字节 / 前缀分布),不写"下载了多少 GB"
- 修复建议:STS 策略 Resource 收窄到 `aicreate/prod/${tenantId}/*`、不下发裸 AccessKey、CDN 回源目录禁可写

## 6. 流程坑(每次都踩)

- **`pkill -f <脚本名>` 会连自己一起杀**(命令行里含该字符串)→ 用 `[o]ob.py` 写法
- **块缓冲** → `python3 -u` + 落文件 + 远端后台跑,再压缩拉回;否则"exit 0, 1 行输出"
- **`ListBuckets` / 跨桶探测会触发 SDK 退避重试把脚本卡死** → 放到最后做,先干写验证与清单
- **`pip3 install oss2` 被 PEP668 拦** → `--break-system-packages -i <国内镜像>`
- **OOB 回调不可用**(云安全组封入站)→ 一律走 in-band 回显
