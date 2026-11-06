<!-- archived from /root/.hermes/skills/security/web-deserialization/SKILL.md on 2026-10-21 -->

---
name: web-deserialization
description: "Web反序列化家族: PHP对象注入/Java gadget/pickle, 入口清单+ILIAS未认证链。触发: deserialization, unserialize, ysoserial, gadget chain, phar。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/web-deserialization`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/web-deserialization/…')`，不要相对 `references/legacy/` 解析。

# Web 反序列化家族(Deserialization)

核心公式:**反序列化入口(HTTP 参数/会话/缓存/队列/文件) × 可用 gadget 链 × 写/执行原语**。目标一般 RCE;拿不到 RCE 就退到任意文件写 / 凭据读取。

## 入口清单(先找哪个字段被 unserialize / readObject / pickle.loads)

```
PHP:    Cookie/会话存储(文件/DB/Redis)、缓存文件、?data=/?param=、上传 .phar、框架 session
Java:   序列化 Cookie/ViewState、T3/JNDI(ysoserial)、fastjson/jackson autoType、MQ 消息体
Python: pickle 会话、Redis 缓存、ML 模型文件(torch.load)、Celery 任务参数
Node:   node-serialize/`unserialize()` 用户可控、JSON→prototype 污染
```

## 实例: ILIAS 未认证 PHP 对象注入 → RCE(CVE-2026-80428,CVSS 9.8,exp-db 52682)

链结构极典型,当模板记:
1. **触发点 = 未认证但会 unserialize 会话表的端点**: `components/ILIAS/AuthShibboleth/resources/shib_logout.php`,`ilInitialisation` 把它标记为免认证;登出通知处理器**遍历会话表每一行**交给手写解析器 → 调 `unserialize` **无 class allow-list**
2. **写入点 = 另一个免认证入口**(LTI 认证端点)把序列化对象**种进 session 行**
3. 请求 shib_logout.php → 反序列化被种入的载荷 → gadget 构造
4. gadget **析构时**把攻击者可控 JSON 写到自身属性指定的路径(web 根下任意位置)
5. HTTP 请求该文件 = 以 web 用户身份执行代码

- 影响: < 9.22 / 10.0–10.9 / 11.0–11.2;修复 9.22 / 10.10 / 11.3(直接**删除**该端点的 logout-notification 实现)
- 临时缓解: 网络层封 `shib_logout.php` 与 LTI 认证端点;监控 web 根下新出现的 JSON 文件
- **打法泛化(重点)**: 遇到 PHP 站点先找"**免认证 + 会读/反序列化会话**"的端点(登出回调、SSO/SAML/Shibboleth 回跳、统计/埋点、cron 触发页),再看能否用**另一条免认证入口写入会话内容** → 两步拼一条链。**写入点与触发点分离**是这类洞的通用形态
- 判据/日志: 外网 IP 请求 `shib_logout.php` 带 logout-notification 参数;LTI 端点出现超长/二进制样参数(serialized payload)
- 来源: https://www.exploit-db.com/exploits/52682 | https://app.opencve.io/cve/CVE-2026-80428

## 通用打法
1. 有源码/公开 gadget 时:PHP `phpggc`(Laravel/Symfony/Monolog/Guzzle/WordPress 链)、Java `ysoserial`/`JNDIExploit`、Python pickle `__reduce__`
2. 无源码: 改一个字节看报错文案 / DNSLog 判断"是否真的走 unserialize"
3. 出网受限: 用写文件 gadget 落 web 根取代码执行(ILIAS 案例正是这条),别硬求反弹 shell
4. **未授权入口优先级最高** —— 免认证端点 = 可直接打,不需要任何账号

## Pitfalls
- "可触发"≠"可利用": 没 gadget 只能 DoS 或写垃圾文件,**先确认 gadget 再宣称 RCE**
- allow-list 绕过是常见修复面: `__PHP_Incomplete_Class`、`phar://` 触发、fastjson autoType 变形、签名只查 cookie 不查 body
- 序列化载荷过 WAF: 参数污染 / 分块 / 编码后再发,别一次全量送

## 关联
- 相关技能: php-webapp-security-audit、java-framework-deserialization-family、rce-encyclopedia、path-traversal-pentest、filament-admin-pentest
- **找不到 gadget / 找到了 sink 也打不动时走 `php-nday-sink-delivery-chain`**（补丁差分定位 sink → 投递链三段闸：sink 可达/入口可达/投递可达；含 unserialize 调用栈探针、session 写入原语穷尽表；缺一段就要定"纵深防御"而不吹可打通）
- 脚本: scripts/deser_exploit.py
