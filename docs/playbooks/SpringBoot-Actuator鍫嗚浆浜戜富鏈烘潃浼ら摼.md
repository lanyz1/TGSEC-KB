---
title: "SpringBoot-Actuator堆转云主机杀伤链.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# SpringBoot-Actuator堆转云主机杀伤链.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/spring-actuator-cloud-takeover/SKILL.md`

## 汇总内容

### spring-actuator-cloud-takeover

来源：`/root/.hermes/skills/security/spring-actuator-cloud-takeover/SKILL.md`

# Spring Boot Actuator → 云/主机接管

**前提**：目标在 `config/scope*.json`。静默扩权 API/ECS IP。

**不是** Spring Cloud Gateway SpEL 链。Gateway 指纹（`/actuator/gateway/routes`、白名单旁路）→ 读 `spring-actuator-cloud-takeover` rule + 对应 Playbook。

## 何时启用

- `/actuator` 列出 endpoints，或 `/actuator/heapdump` 可 HEAD/Range 
- 芋道/股票盘 API（`admin-api`、`tenant-id`）伴生 Druid/Swagger 
- 若同时出现 `mock-enable` / `file-config` / `df-user` → **并行** `yudao-daifu-mock-file-rce`（可能比 heapdump 更短）
- 用户点名：heapdump、阿里云 AK、RunCommand、syscache
- 案卷里已经有 `.hprof` / `.phd`：**先拆堆**（`heap_cred_scan.py`），不必等用户说蓝鸟 

## 强制顺序

1. `python3 tools/ops/actuator_probe.py --base https://API --out …/测绘/actuator/` 
2. 若 `gateway/routes` 像 SCG → **切换** Gateway Playbook，勿只扫 health 
3. heapdump：分桶下载（按 IP+HOSTNAME+total）→ `tools/ops/heap_cred_scan.py`（正则 + 蓝鸟对象图，见 `heapdump-credential-hunter`） 
4. 验证凭据：`LTAI` → Identity；JDBC/Redis 探针 
5. Root AK → `DescribeInstances` + Cloud Assistant `RunCommand`（22 可不开） 
6. 无云 Root → 超管/上传 RCE 写 SSH（参考 `bk_assets` CHAIN） 
7. `yudao_hidden_admin_sql.py` 生 SQL → 本机 mysql 植入 → `tenant-id: 201` 登录探针 
8. STATUS + 凭据 JSON；大 heapdump 可外置 

## 成功口径

- 云：`whoami`/RunCommand root 或 Identity 确认后可控 ECS 
- 业务：`syscache`（或等价）登录成功且可调管理 API 
- 仅 `health:UP` **不算**成功 

## 真源

- Playbook：`docs/playbooks/SpringBoot-Actuator堆转云主机杀伤链.md` 
- 总册：`docs/playbooks/近期成功接管手法总册.md` §C1–C2 
- 案卷：`admnrlytlhub_20260805/完整接管报告.md` · `bk_assets_20260806/接管/deep/rce_ssh/CHAIN_ACTUATOR_TO_SSH.md` 

## 禁止

- 未授权账号/桶扩展 
- 真删 ECS 全集群（先问） 
- 混节点合并 heapdump 
- 把报告第三方 UAT 扩进 scope 

## heapdump 白名单 → 免鉴权三连（LynxCode 2026-10）
1. `/actuator/heapdump` 下载 → 在 JVM 堆里找 `ignore-urls` / `security.ignore` / 自定义白名单
2. 白名单里常藏「内部免鉴权」路由，逐个只读验证：
   - `GET /<svc>/getLoginToken?userId=1&appKey=<白名单key>` → 直接下发任意用户 token（**免密登录原语**）
   - `POST /<svc>/api/v1/userRole {"userId":<自己>,"roleId":1}` → 任意登录用户自封超管（BFLA）
   - `GET /<svc>/getChatInfoByUuid/<uuid>` → 免鉴权读任意项目源码/对话（AI 构建平台）
3. 前端「自签名」网关：签名密钥 = 页面自己生成的随机 token → 按 JS 逻辑本地重算即可伪造
- 判据：白名单路由返回业务数据而非 401/302
- 纪律：`userId` 先用自己账号验证，别直接打 1；`userRole` 改前记录原 role
