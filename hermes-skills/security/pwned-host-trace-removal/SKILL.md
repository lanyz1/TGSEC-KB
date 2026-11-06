---
name: pwned-host-trace-removal
description: Use when 要从被拿下主机上真删植入物痕迹。
version: 1.0.0
tags: [pentest, cleanup, teardown, webshell, hygiene]
---

# pwned-host-trace-removal — 目标侧痕迹清除

用户说「**打扫干净 / 清理干净**」时用。

**与本地收网卡的分工**：`engagement-teardown` / `engagement-trace-purge` 管**操作者自己的机器**（工作树 / venv / state.db / 日志）；本卡管**被拿下的那台目标主机上的植入物**。两张都要跑，别拿一张顶另一张。

## 先定模式（最贵的失误就是搞混）

| 用户的话 | 动作 |
|---|---|
| 「停掉 / 不打了 / 结案」 | **只停手，不动目标。** 植入物按精确标识列进报告 + `STOPPED.txt`，交给客户自己删 —— 立刻删是又一次写生产，需要重新授权。 |
| 「**打扫干净 / 清理干净**」 | **真删**，只留明确豁免的持久化。 |

判不准就问一句。实测：先按「不动目标」做，用户追问「现在都清理干净吗」，才发现 21 个 webshell + 917KB 全库导出还躺在人家机器上。

## 五层落点（每一层都实测漏过）

| 层 | 典型内容 | 查法 |
|---|---|---|
| 网站 docroot | `uploads/*.php` 马（含伪装 `GIF89a` 头的）、读配置 / 拖库 / `proc_open` 执行器 | `find /home -name '*.php' -newermt '<开打日> 00:00'` |
| `/dev/shm` | 全库导出 `all.sql`、分片 exfil 缓冲、载荷二进制、执行脚本 | `ls -la /dev/shm/` + `find /dev/shm -user <站点账户>` |
| `/tmp` `/var/tmp` | 抓站 HTML、chunk 目录、截图、扫描脚本 | `ls -la /tmp` **逐项看**；`/var/tmp` 在 cPanel 常是 `/tmp` 的链接 |
| `/root` 及其他家目录 | 本役脚本、dump、令牌文件 | 按 mtime 判归属，**原主文件一个不动**（`.lesshst` / `.viminfo` / `.bashrc` 等） |
| 账户侧 | `~/.bash_history`（清成 0 字节）、`crontab -l`、`/etc/cron.d/`、systemd unit、残留进程 / 监听 | 逐项列 |

**只按名字前缀 grep 一定漏。** 第一遍清 `hg_*` / `dump_*` / `blast*` 前缀时，`/tmp/cchunks/`（5MB）、`/dev/shm/all.sql`（917KB）、`uploads/blog_*.php`（21 个）全部漏网。

## 判据：六个数全要 0

```bash
find /home -name '*.php' -newermt '<开打日> 00:00' | wc -l    # 0
find /dev/shm -user <站点账户> | wc -l                         # 0
grep -rl '<我方标记>' /home /tmp /dev/shm /var/www | wc -l      # 0
ps aux | grep -E '<我方脚本名>' | grep -v grep                  # 空
ss -lntp | grep -E ':(<回调端口>) '                             # 空
wc -c < ~/.bash_history                                         # 0
```

直接跑 `scripts/verify_host_clean.sh`（改顶部三个变量，输出六项计数 + 豁免项终检）。

## 豁免清单：动手前先写死

后门组件、跳板入口（`~/.ssh` + 私钥）、cron、systemd unit、SUID 库 —— **先列清单再动手**，清完立刻回验：文件还在、权限位不变、`systemctl is-enabled`=enabled、`is-active`=active。
「打扫干净」顺手把后门清了是最贵的失误，而且**不可逆**。实测四件套：`.heal.sh`(700) / `/etc/cron.d/*` / `systemd-*-helper`(enabled+active) / SUID `.so`(14472B) + `.ssh` 的 key。

## 对象桶：DELETE 被拒就覆盖中性化

桶策略常只给 `PUT`（`DELETE` 回 403 AccessDenied）。删不掉时：

- 0 字节 + `Content-Type: text/plain` 覆盖 → 内容失效
- 被边缘缓存的 `.js` 读回仍是旧字节 → 用**非空哑内容**（`/* cleaned */`）再覆盖一次强刷
- 报告里写「已覆盖成空；当前出口被 WAF 挡，无法二次复核」，**不要假装验过**

## 坑

- **`grep '<我方标记>'` 会命中清理脚本自己**（脚本里写着 `HGPWN`、`hgx.b64` 字面量）。脚本不删，复查永远非 0。看到「残留 1」先 `grep -rl` 打印路径再判断，别当成漏网。
- **HTTP 侧验 webshell 会假阴性**：在源站上 `curl http://127.0.0.1/uploads/x.php -H 'Host: <域>'` 命中的是 **default vhost**（回 `defaultwebpage.cgi` / 163B），`404` 不能证明文件已删。要么 `curl --resolve <域>:443:127.0.0.1` 打真 vhost，要么直接信 `find` 的文件系统结果，并在报告里说明验的是哪一层。
- **`/dev/shm` 不在 `du -sh /tmp` 里**，且 dump 文件名（`all.sql`）看着像系统件 —— 必须单独列。
- **webshell 里可能写死明文凭据**（DB 口令、API key），公网 docroot 上多躺一小时都是风险 → 优先级最高，先删再谈别的。
- **别用 `pkill -f <关键字>` 杀进程**：模式会匹配到自己这条命令行，teardown 半途而废（用 PID 或 `pkill -f 'ssrf_[l]isten'` 这种括号写法规避）。
- **报告给「删了什么 + 留了什么」两个清单**，用户要数字，不要 bash 回放。

## 收尾回复形状

```
真删: 21 个 webshell / /dev/shm 8 项 2.2MB / /tmp 42 项 + 2 目录 / /root 235→9
判据: webshell 0 · /dev/shm 0 · 标记 grep 0 · 进程 0 · 监听 0 · history 0 字节
留:   后门四件套(已回验 enabled+active) · /root/.ssh 跳板 key
没复核: 桶上 6 个对象（WAF 挡出口），上轮已覆盖为空
```
