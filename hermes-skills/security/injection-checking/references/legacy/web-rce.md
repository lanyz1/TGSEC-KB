<!-- archived from /root/.hermes/skills/security/web-rce/SKILL.md on 2026-10-21 -->

---
name: web-rce
description: "Use when 找 web 应用 RCE 入口：调试 console/SSTI/反序列化/命令注入/文件写。"
---

> 归档卡：原目录 `/root/.hermes/skills/security/web-rce`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/web-rce/…')`，不要相对 `references/legacy/` 解析。

# Web 应用 RCE 技术

在 web 应用上拿代码执行（区别于越权/信息泄露/数据拖库）：调试模式 console、模板注入(SSTI)、反序列化、命令注入、任意文件写→RCE 等。

## 核心原则

- **先读框架版本再选利用**：`Server` 响应头（如 `Werkzeug/3.1.3 Python/3.10.12`）决定用哪个版本的利用算法——框架 minor 版本之间算法会变（Werkzeug PIN 的 3.0.x 与 3.1.x 就不同）。
- **触发未捕获异常收割信息**：让视图抛异常（缺 key、类型错）→ 调试页/栈回溯免费泄露源码路径、行号、SECRET、框架版本，比盲猜快一个数量级。
- **文件写原语 → RCE 要先判权限**：Redis RDB 写 `/etc/crontab` 只有在 Redis 进程是 root 时才成；`SAVE` 到 root 路径返回 `ERR`、到 `/tmp` 返回 `OK` 就是非 root，RDB→cron/ssh 这条路作废。
- **调试 console 的 PIN ≠ SECRET**：debug 页里打印的 `SECRET` 是签名请求用的随机盐，不参与 PIN 计算，别喂进 PIN 算法。
- **验证 PoC 时，预言机标记必须是源码里不存在的字面量**：若回显字符串（如 `echo "RCE_OK"`）也写在被执行的源码里，那「静态返回原文」和「成功执行」在响应里长得一样 → 假阳性。改成计算式（`echo "PWN_".(6*7)."_OK"`）才有区分度。

## 参考

- `references/werkzeug-debug-pin-rce.md` — Flask/Werkzeug 调试模式 PIN 破解 → RCE（含 3.1.x 算法变更）
- `references/php-builtin-server-smuggling.md` — PHP 内置服务器（`php -S`）请求走私：单包双请求 → 源码泄露 / 任意后缀当脚本执行（**含本机 docker 实测的三个必要条件**）
