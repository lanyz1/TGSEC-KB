---
name: ruoyi-vue-plus-admin-fullchain
description: "若依/RuoYi-Vue-Plus后台下潜链:密钥面·源站裸端口·MinIO·云AK。"
version: 1.0.0
license: MIT
author: hermes-curator
metadata:
  hermes:
    tags: [pentest, ruoyi, java-scaffold, minio, mysql, cloud-ak, origin-trace, fund-ponzi]
    related_skills: [cn-admin-framework-pentest, ruoyi-fork-admin-pentest, ruoyi-quartz-whitelist-bypass-el-rce, admin-export-template-sqli, lowcode-admin-data-exfil, cloud-credential-leak-exploitation, object-storage-takeover-mining, cdn-origin-tracing, wallet-exchange-fund-verification]
---

# 若依-Vue-Plus 系后台:五层下潜全链

## When to Use

- 指纹 `RuoYi-Vue-Plus 4.x` / 二开 `com.ruoyi.<模块>.*` 自研包 / `POST /prod-api/login` → `/prod-api/getInfo` 返回 `permissions:["*:*:*"]`
- 用户要「打进去 / 拿全量数据 / 拿源码包」而目标是 Java 脚手架系后台
- **本卡是「下潜链」不是漏洞清单**:每层都给出「拿到什么 → 用它兑换下一层入口」

## 五层下潜链(顺序即性价比)

| 层 | 入口 | 兑换物 | 细节 |
|---|---|---|---|
| L1 后台 | 默认口令 + 服务端不校验验证码 | 超管 token → 全量业务 API | 见 §L1 |
| L2 密钥面 | `front/{key}` · `monitor/cache` · `sys_oss_config` · `api-docs` | DB/MinIO/云AK/短信/在线会话 | `references/02-ruoyi-secret-planes.md` |
| L3 源站 | Shodan `ssl:` / `http.title=` | 裸端口 3306/18080/19000 | `references/01-origin-locate-bare-ports.md` |
| L4 中间件 | 3306 弱口 → 全库；19000 SigV4 → 桶全读写 | 用户/资金/KYC + 桶对象 | `references/03-mysql-minio-object-storage.md` |
| L5 云 | `sys_config` 里的云 AK/SK | 账号级控制面(先定天花板) | `cloud-credential-leak-exploitation/references/tencent-root-ak.md` |

## L1 后台入口(三条,按序试)

1. **默认口令** `admin/admin123`(若依出厂值,生产不换极常见),删默认账号常被漏
2. **验证码服务端不校验**:`sys_config.captchaEnabled=true` 只是前端渲染开关 → body 里 `code` 随便填(`9999`/空)照样 200。判据=同一账号连用明显错误验证码仍登录成功
3. **逐接口漏配**:二开业务面(`/xxx/*`)鉴权是逐个接口手写的 → 读接口匿名可达、写接口 401。用「空 body 打全接口,按错误类型分三态」测绘可达面(`lowcode-admin-data-exfil` T3)

> GA/TOTP 在密码之前校验的若依分支 → 别爆破,转 `ruoyi-fork-admin-pentest`(druid 旁路 + 用户名枚举 oracle)。

## L2 密钥面(最值钱的一层)

登录后**别急着拖业务表**,先把密钥面扫完——一张 `sys_config` 加 `monitor/cache` 常等于整条下潜链:

- `GET /prod-api/system/config/front/{key}` 匿名可读(`configKey/{key}` 要鉴权,`front/` 前缀漏配)→ 初始口令/默认验证码/开关
- `GET /prod-api/monitor/cache/getKeys|getValue/{ns}` 读**任意 Redis 命名空间**:`online_tokens:` 枚举全部在线会话(可顶会话);`sys_config` 命名空间躺着 DB/MinIO/云 AK/短信商/邮件/TG bot token
- `sys_oss_config`(MinIO AK/SK + endpoint + bucket + domain)、`/v3/api-docs`(未授权路径全集)、`actuator/health`、SQL 报错回显类名

## L3~L5 速览

- **源站**:`shodan search 'ssl:"<域>"'` 证书 CN → 源站 IP;`http.title:"<后台标题>"` → **同源码第二套环境**(双环境是常态)。CF 只代理标准端口,IP 到手 3306/18080/19000 全直达;公共 DNS 被摘/委派被撤时必须 `--resolve` 或 Host 头
- **18080** = Spring Boot 裸端口,绕过 nginx 直通 `/v3/api-docs`、`/actuator/*`、`/system/config/front/*`
- **MySQL**:宝塔布局弱口令 → 先 `SHOW GRANTS` + `@@secure_file_priv` 判边界;**无 FILE/SUPER 就别在写马路上耗**
- **MinIO**:`sys_oss_config` 凭据 SigV4 直连 `:19000`(`GET /` 列桶、`?list-type=2` 列对象);nginx `/oss/` 反代内网 MinIO + 桶无策略 = `sys_oss` 表里的对象路径可直接 GET(KYC 证件照)
- **任意上传**:OSS 上传不白名单 → `.html` 落公开桶 = 在业务自己的引流域名下托管任意页面
- **云 AK**:只用只读 API 判身份/权限,不直接动资源(`sts:GetCallerIdentity` / `cvm|lighthouse:DescribeInstances` / `cam:ListAccessKeys`)

## Pitfalls

- **对生产源站别跑全端口高并发**:600 并发扫 65535 → 目标防火墙按出口 IP 整机封禁(仅我方通道受损)。生产源站只扫白名单端口 + 低频
- **负面结论要写成判据**(见 `references/04-negative-verdicts-and-redlines.md`):`EL1007E ... 'datasource' cannot be found on null`(代码生成器多数据源未配=模块不可用)、`/snail-job/*` 落 SPA 兜底(组件不存在,CVE 不适用)、`参数不符合规范`(orderByColumn 白名单)、`pg_hba` 拒外部、XFF 伪 127.0.0.1 对宝塔 phpMyAdmin IP 白名单**无效**
- **红线动作先问**:改**启用中**的生产 OSS 配置做 SSRF 探测会让真实用户上传失败 → 不做;同理改别人业务服务器口令
- 先把密钥面拿全再拖库:会话/密钥随时可能因对方应急响应失效

## 关联

- 总纲/分支: `cn-admin-framework-pentest` · `ruoyi-fork-admin-pentest` · `ruoyi-quartz-whitelist-bypass-el-rce`(写库→EL RCE) · `admin-export-template-sqli`
- 云与存储: `cloud-credential-leak-exploitation` · `object-storage-takeover-mining` · `cdn-origin-tracing`
- 业务定量: `wallet-exchange-fund-verification/references/ponzi-crosscheck.md`(刷单盘 试玩号灌水 + 真实回款率)
- 实战案例: `references/05-taskking-126310-case.md`

## /api/getToken 无凭据签发（2026-10 fuzhuFM 实锤）
- `GET /api/getToken` 无凭据返回固定令牌且绑定真实会员（根推广号），`/api/refreshToken` 可续 7 天
- 鉴权头是**裸 token**，加 `Bearer ` 反而 401（sa-token token-prefix 差异）→ 两种形态都要试
- `/api/member/getInviteData` 无分页单次全量（6.8MB / 3738 条 × 72 字段，含手机号/设备码/lastIp/openid）
- `/demo/**` 未授权族：/demo/cache/test1 写缓存、/demo/mail/sendMessageWithAttachment?filePath=（CVE-2025-6925 形态）、/demo/redis/pubsub/pub
