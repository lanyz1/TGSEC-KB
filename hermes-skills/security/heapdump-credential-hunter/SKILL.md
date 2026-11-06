---
name: heapdump-credential-hunter
description: "Java堆转储抽凭据时使用。触发: heapdump, hprof, JDumpSpider, 蓝鸟猎手。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, heapdump, credentials, jdumpspider, actuator, surveyengine-absorbed]
    related_skills: [surveyengine-knowledge-pack]
---

# 蓝鸟猎手 — heapdump 对象图抽凭据

来源: 测绘引擎知识包吸收(镜像 `.cursor\skills\heapdump-credential-hunter\SKILL.md` + `tools\heap-hunter\`)。

**授权离线拆堆。不是目录猎杀。没有抽出 HEAP_CREDS 不算拆完。**

## 触发(见到即用,不用等用户说"蓝鸟")
`/actuator/heapdump`、heapdump.hprof、heapdump.bin、.hprof、.phd、堆转储、heapdump_exposed、JDumpSpider、encryptionCipherKey、ProcessEnvironment、DruidDataSourceWrapper、CookieRememberMeManager

## 工具(本技能自带,已复制到 scripts/)
- `lanniao-hunter.jar` — JDumpSpider 1.1-SNAPSHOT 增强版(Main/HunterLauncher)
- `spiders.json` — 17 只蜘蛛规则表(Spring DS/Druid/Hikari/Redis/Shiro钥/PropertySource/Consul/环境变量/OSS Map/Cookie)
- 用法:
  - 单文件: `java -jar scripts/lanniao-hunter.jar <dump.hprof> -out report.txt`(JDK17 可跑 Main)
  - 批量: `java -cp scripts/lanniao-hunter.jar cn.wanghw.HunterLauncher -batch <dir>`
  - 对象图行走依赖 VisualVM/NetBeans heap 解析;**无 Java 时只做字节正则+类名指纹**,仍出报告
  - 不要默认 `--export-strings`(全堆 String 会爆)

## 正则层(无 Java 也立刻做)
在 heapdump 二进制上正则找:
- JDBC URL + 明文口令: `jdbc:(mysql|postgresql|oracle|sqlserver)://...password=...`
- `ProcessEnvironment` / `environment` 段: `(AWS_SECRET|ACCESS_KEY|SECRET_KEY|PASSWORD|TOKEN|DSN)=...`
- Shiro `CookieRememberMeManager` 附近 Base64 密钥
- `ENC(` 前缀(jasypt 加密值)

## 对象图蜘蛛(有 Java,17 只重点)
| 蜘蛛 | 目标类 | 抽什么 |
|---|---|---|
| DataSource01 | SpringBoot DataSourceProperties | driverClassName/username/password/url 明文 JDBC |
| DataSource02 | WebLogic DataSourceConnectionPoolConfig | 口令在 defaultConnectionInfo |
| DataSource03 | com.mongodb.MongoClient | host/credentialsList 嵌套凭据 |
| DataSource04 | AliDruidDataSourceWrapper | 芋道/若依常见 Druid 包装类 |
| DataSource05 | Hikari DriverDataSource | jdbcUrl/driverProperties 表 |
| Redis01 | RedisStandaloneConfiguration | host/port/password |
| Shiro 钥 | CookieRememberMeManager | Base64 密钥 → 反序列化链 |

规则表全文见 `scripts/spiders.json`(17 蜘蛛完整字段路径)。

## 抽出后交接(不在本技能结案)
| 东西 | 下一步 |
|---|---|
| LTAI / OSS AK | 阿里云 AK-SK → 云资产接管 |
| JDBC / Druid | 数据库登录/拖库 |
| Redis 口令 | Redis 未授权/写 SSH key |
| Shiro Base64 钥 | Shiro rememberMe 反序列化 |
| ENC( | jasypt 解密链 |

## 工作纪律
- 多个 dump 按 **IP+HOSTNAME 分桶**,别混
- 没有 `HEAP_CREDS.json` 不算拆完
- 配置从文件/env 读的(非常量)不会在堆里 — 别浪费时间在 heap strings 找运行时密钥(实测:OKPay token/MySQL DSN 不在堆采样,见 kk8 卡)

## Pitfalls
- jar 是 classfile 70(Java 26)的 HunterLauncher 只走 batch Main 的 jar 主类 JDK17 即可
- 全堆 String 导出会爆磁盘 → 不加 export-strings
- actuator heapdump 端点通常需登录或限 IP;下堆前先确认授权范围


---

## 去重合并：`heapdump-lanniao-hunter` 独有段（2026-10-17）

## 立刻执行

```bash
python3 tools/ops/heap_cred_scan.py doctor
python3 tools/ops/heap_cred_scan.py \
  <heapdump.hprof> --out exports/<案>/接管/heap_creds/
# 一目录多份堆：
python3 tools/ops/heap_cred_scan.py batch --dir <目录> --out exports/<案>/接管/heap_creds/ --case <案>
# actuator probe 已出：
python3 tools/ops/heap_cred_scan.py from-probe \
  --probe exports/<案>/测绘/actuator/probe.json \
  --dump-dir exports/<案>/测绘/heapdump \
  --out exports/<案>/接管/heap_creds --case <案>
```

有 Java：正则 + 17 只蜘蛛（Spring DS / Druid / Hikari / Redis / Shiro 钥 / PropertySource / Consul / 环境变量 / OSS Map / Cookie）。  
无 Java：正则+类名指纹仍出报告；去装 `tools/spring-gateway-killchain/bin/install_vendor.sh`。  
不要加 `export-strings`。

抽出后交接，不要在本卡结案：

| 东西 | 下一卡 |
|------|--------|
| LTAI / OSS | 阿里云 AK-SK |
| JDBC / Druid | Actuator 堆转云 / 芋道 syscache |
| Redis | Redis 卡 |
| Shiro Base64 钥 | Shiro rememberMe |
| ENC( | Gateway jasypt |
