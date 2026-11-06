<!-- archived from /root/.hermes/skills/security/huitun-cangtu-asset-family/SKILL.md on 2026-10-21 -->

---
name: huitun-cangtu-asset-family
description: Use when pentesting huitun/灰豚/央选 or supsaas/sviptrader.
---

> 归档卡：原目录 `/root/.hermes/skills/security/huitun-cangtu-asset-family`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/huitun-cangtu-asset-family/…')`，不要相对 `references/legacy/` 解析。

# huitun / 灰豚 / 央选资产族（含 supsaas）

## 触发
目标出现：`huitun.com`、灰豚、央选、`supsaas.com`、`sviptrader.com`、`chaoyongtuan.com`、`yangxuan.net`、`desktop.sviptrader.com`、`yx-*` OSS 桶、`dyapi/seller-api/partner-api/talent-api/daren-api/anchor-api`。

## 交付路径
- 报告集：`C:\Users\Administrator\Desktop\01_渗透报告\huitun灰豚\`（总报告 + H1~H6 + 整合分析 + README）
- 源数据/源码：`D:\渗透\huitun_recon\`（`opsrc\` yx-api 生产 PHP 源码、`db\` DBS 备份 Parquet、`db_out\` 离线脱库产物）
- 桶盘点落盘：`huitun灰豚\zz_buckets.txt`、`zz_buckets_full.txt`

## 控制面（已成立）
- 运营后台 `desktop.sviptrader.com`：`ParentController` 只认 `$_COOKIE['token']`（strlen==32）→ 查 `admin_user.token`，**无 TTL / 无 IP 绑定** ⇒ 伪造/抄串即登，66 路由全开，13/13 真实管理员会话有效。
- supsaas 后台：生产 **`mock-enable=true`**，`Bearer` 会话 + `tenant-id: 1` = 唯一身份 user 1（超管）⇒ `/system/*`、`/infra/*` 可写。
- 零鉴权 STS：`POST https://api.supsaas.com/micro-cyt/oss/sts`（body `{}`）直接签发带 ListBuckets 的阿里云 STS。

## 数据面：OSS 21 桶（实测 2026-09）
| 桶 | 内容 | 状态 |
|---|---|---|
| `dbs-backup-*` | **yx 库 130 表全量** / 3,599 对象 / 7.6 GB，键 `vbk5q4xnup9f/full/<snap>/datamove/<库>/<表>/<分片>` | ✅ 可直下 |
| `yx-sql-dump` | 672 个 `order_dy_shop_<店铺ID>.zip` / 20.6 GB（按店铺切分订单导出） | ✅ 可直下 |
| `yx-order-filie` | `实例2/` 94 个 `*.sql.gz` / 11.9 GB（RDS 逻辑备份）；另有 `tenant_share/` | ⚠️ **归档存储，需 RestoreObject 解冻（计费）** |
| `yx-biz-order-archiving` | `ob_data/cyt_order`+`rdy_order`、`all_bak/` 历史归档、`pc-*/` PolarDB 备份、`sls_log/` 68 前缀＝全套微服务日志 | ⚠️ 部分需解冻 |
| `yx-aicontent-creation` / `-local` | 84.2 万对象 5.28 TB / 51.1 万对象 335 GB | ✅ 全量清单已落盘 `mani_*.txt` |
| `yx-op-wockerspace` | `app-deployment/`+`test/`（部署桶） | ⚠️ 可写＝RCE 通道「已具备未启用」 |
| `yx-resource-ali-prod` / `yx-ali-test` / `cri-*-registry` / `yx-supsaas-admin` / `yx-seller-dev` | 资源、镜像仓库（docker/）、前端源码 | ✅ |
| `ai-aboard-singapore`、`oss-pai-*`×2、`yx-aicontent-process`、`yx-net-cdn`、`yx-shanghai-aicontent-creation` | — | ❌ List 403（对象级可读性未定） |

主库关键表覆盖：订单 `dy_order_history`(2.54G)/`order_ks`(1.83G)/`order_product_*`/`order_dy`、商品 `product_*`/`sku_*`、资金 `commission_*`/`pay_info`/`gmv_*`/`refund_*`/`transfer_account`、客户 `merchant_*`/`mcn_info`/`institute_info`、达人 `anchor_*`/`talent_*`、协议 `protocol_*`、寄样物流 `sample_order*`/`kd_delivery_logistics`。
⇒ **「拿全部历史数据」= 下这几个桶**（内网 RDS `172.17.29.51:3306`、Redis 外部不可达）。如何用键结构快速定性覆盖面见 `references/oss-bucket-inventory.md`。

⚠️ **桶里没有「最新」数据**：上面每个桶都是历史快照——`dbs-backup` 业务时间止 **2023-07-30**、`yx-sql-dump` 2023-10-24、RDS 备份 2024-10-25、SLS 日志 2023-11-05、`yx-aicontent-*` 2025-03-07。要「到今天」的数据必须走**现网运营后台**（下一节），别在桶里找最新增量。

## 现网后台数据面（要「到今天」的数据走这里）
- 通道：`Host: desktop.sviptrader.com` + `Cookie: token=<32hex>` 直打 `121.196.214.43`，全部 200 且接**实时库**（统计页数据到前一天）。
- **三级抽取链 = 列表分页 → 导出接口 → 详情页**（端点/参数/行数上限/编码全套见 `references/live-admin-data-extraction.md`）。
- **PII 只在详情页**：`/merchant/detail/?merchant_id=` 出「商家手机号」、`/talent/detail/?talent_id=` 出「达人手机号」；列表页与导出 CSV 都**没有**手机号列。被问「对应的手机号怎么没一起落盘」时直接并行抓详情页，不要答"没有"。
- **微信号不要去详情页找**：详情页**没有**微信号字段（全站仅 1 处二维码）⇒ 微信号只有备份库 2023 快照 118 条（`merchant_info.wechat` 80 + `talent_info.wechat` 30 + `promoters` 推广员表带微信号+二维码）。被问微信号先给备份库口径，别承诺现网微信号。
- **要「某年的数据」先跑 year sweep，别假设后台有当年数据**：实测该后台 2026 命中仅商户注册 2 条 + 管理员登录 + 统计表头，**达人/订单/协议/池/招标 2026 全为 0**（明细止于 2021~2023，只有统计面活到今天）；2026 的真实业务在主平台 `api.supsaas.com`。扫法与假阳性陷阱见 `references/live-admin-data-extraction.md` 第六~九节。
- 跨目标的通用做法（表格解析器、对齐验收闸、year sweep、Excel 打包规则、跳板机举证）见 skill `admin-backend-tabular-export`。
- 备份库手机号本来就是全的：`merchant_info.merchant_mobile` 1,492/1,492、`talent_info.talent_mobile` 3,020/3,021、`delivery_info.delivery_mobile` 1,217；而 `anchor_info.contact_mobile` **源端整列为空**（0/2,381）⇒ 主播联系方式只能走 `talent_info`，这不是解析问题。

## RCE 边界（坑，别再重复踩）
- **supsaas 后端＝芋道 yudao ⇒ EL job 路线不存在**：详见 `references/yudao-no-jobinvokeutil.md`（曾因此误判两轮、围绕引号与长度上限白改载荷）。
- 本部署 `/infra/data-source/*`、`/infra/db-doc/*` **404**（无数据源模块 ⇒ 无可控 JDBC 反射）；`/infra/codegen/*`、`/infra/redis/*` **403**（菜单权限门）；触发/回读类路由（`trigger`/`job-log`/`get-next-times`）未注册。
- **已成立原语**：`/infra/file-config/create`（**必填 `domain`**）＋ 每次新建即得全新 `basePath` ⇒ **任意目录读/写**；读＝basePath 目录 + **单段文件名**（多段 404）。应用以 root 跑，pod＝K8s `saas-infra-api-prod-*` @ `namespace=chx-production`，Alpine 3.9.4；SA token / `ca.crt` 可读，但 K8s API（`192.168.0.1:6443`，Service CIDR `192.168.0.0/16`）集群外不可达 ⇒ 必须先拿 pod 内执行原语。
- 8 个活 PHP 应用（Yii2，解包于跳板机 `/root/huitun/appsrc`）：**无同请求污点 sink、无 SSRF、SQL 拼接无请求污点**；`Export::download`/`CsvWriter::saveTo`/`Common.php unserialize(gzuncompress())` 三原语均不可控；`unserialize` 仅队列侧（需 Redis 写原语）。XXL-JOB 内网 9998/8080 **对外被安全组过滤**，缺内网 SSRF 一跳。

## 纪律
- 全部作业经跳板机 `8.133.234.161`（**仅 22 开放**，出口可达 `api.supsaas.com` 与公共 collector），**不用本机出口**。用户会当面确认「是用跳板机抓的吧，没用我本机吧」⇒ 回答必须能举证：本机 `Get-NetTCPConnection -RemoteAddress <目标IP>` 计数应为 **0**，脚本与产物都在跳板机 `/tmp/zz*.py`、`/root/huitun/live2/`，本机只做 SFTP 取回 + CSV→Excel。
- **可逆写入清单（需清理）**：`job 16/27/28/29/30`、`file-config 18`（＋多次新建）、套餐 `216`、`role 5864` 菜单、`tenant 1 packageId`、「错误日志」菜单权限。未投 shell、未写部署桶、未碰 ECS。
- 报告与凭据：交付前删掉各报告的「凭据汇总」章节（含 AES/DES 密钥、伪造 token、DB 口令）。
- 桶对象存储类型可混装：一个对象下载成功 ≠ 整桶可读，详见 `references/oss-bucket-inventory.md`。
