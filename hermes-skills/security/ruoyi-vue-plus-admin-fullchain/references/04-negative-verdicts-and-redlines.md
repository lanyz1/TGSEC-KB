# 负面判据与红线(逐条实测,避免重复劳动)

> 写法要求:负面结论必须带**响应原文 / 返回值**,才算"已验证边界",不能写"没找到"。

## 1. 已排除路径与判据

| 路径 | 判据(原文) | 结论 |
|---|---|---|
| 代码生成器路径穿越(issue #33) | `/tool/gen/*` 全返回 `EL1007E: Property or field 'datasource' cannot be found on null` | 多数据源 SpEL 配置缺失 → **模块整体不可用**,连只读枚举都失败;不是"洞打不动" |
| SnailJob 未授权 RCE(CVE-2025-66916) | `/snail-job/*` 全落 SPA 兜底、POST 405;源站 8800/17888 未开放 | **组件不存在**(4.8.2 用 XXL-Job)→ CVE 不适用,别当"未利用" |
| XXL-Job 控制台/执行器 RCE | 库里 `xxl_job_user`=`MD5("123456")`,但 `xxl_job_registry` 空、`address_list=NULL`、示例任务停在 2018 | 控制台未部署 + 执行器未注册 → **当前不可利用**;写成"若日后部署即 RCE"的潜伏风险 |
| SQL 注入(orderByColumn / isAsc) | `参数不符合规范` / `排序参数有误` | 若依白名单拦截;`params[dataScope]` / `dataScope` 亦无注入 |
| phpMyAdmin 888 IP 白名单 | 任意路径固定 548B 403 | `X-Forwarded-For`/`X-Real-IP`/`Client-IP` 伪 `127.0.0.1`/内网 IP/自身 IP、随机 8 位面板路径、常见入口(`/pma/`、`/sql.php`、`/import.php`、`/signon.php`)全失败 → 需换白名单内出口 IP 才能推进 |
| PostgreSQL 5432 | `pg_hba` 拒绝外部来源 | 死路 |
| 未授权 SSRF(图片地址类参数) | OOB 监听 0 回连 | 死路 |
| 静态服务 / `/druid` / `/nacos` / `/manager/html` / `.git` / `application.yml` / 备份包 | SPA 兜底或若依 `非法请求` 过滤器 | 无泄露 |
| MySQL → 写马 | 无 FILE/SUPER,`secure_file_priv` 受限 | 见 `03-mysql-minio-object-storage.md` |

**方法论**:每排除一条就落一行「判据 → 结论」,收尾直接进报告的"已排除路径"章节。
区分「SPA 兜底」与「接口拒绝」要看响应体大小/内容类型——兜底页大小固定且是 HTML,`非法请求` 是应用自己拦的。

## 2. 红线动作(动手前必须问,不要自己权衡后执行)

| 动作 | 后果 | 处置 |
|---|---|---|
| 改**启用中**的 `sys_oss_config` endpoint 做 SSRF 内网探测 | 窗口期内真实用户上传失败 = 业务影响 | 不做;要做先出方案并获批准 |
| 用云 Root 密钥重置**别的业务**服务器口令 / 改安全组拿 SSH | 该机承载第三方真实业务,会锁掉对方运维 | 只读留证,不动 |
| 对生产源站全端口高并发扫描 | 出口 IP 被整机封禁 | 见 `01-origin-locate-bare-ports.md` §3 |
| 对 KYC / 资金表做写测试 | 真实用户数据被改 | 只读;要写先问并给还原方案 |

判据原则只有一句:**这一动会不会让真实用户受影响**——会,就停下报告,而不是先做了再说。
