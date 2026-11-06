# php2shell 仓库审阅案例（2026-10-21）

> 仅记录审阅结论与证据，不提供可利用 payload。

## 元数据

- 仓库：`syrex1013/php2shell`
- 创建：2026-10-21T15:06:33Z
- 最后 push：2026-10-21T15:06:49Z
- 审阅时间：约 15:38 UTC（仓库出生约 32 分钟）
- commits：2；stars：2；forks：1；无 release
- 提交含 `Co-Authored-By: Claude Sonnet 4.6`
- 仓库自带 `lab-uaf/`（Dockerfile + entrypoint + scripts）和 PHP 靶场文件

## 官方 CVE

- CVE-2026-109618：OOM 条件导致的内存破坏
- CVE-2026-109619：stale global state
- 官方修复：PHP 8.2.35 / 8.3.36 / 8.4.27 / 8.5.12
- PHP 8.1 及以下已 EOL，需升级或厂商 backport
- 官方公告口径：FPM 在源码分析上 susceptible；**没有公开完整的 FPM 利用演示**

## 仓库声称 vs 代码实际

| README 声称 | 代码实际 | 结论 |
|---|---|---|
| session.upload_progress heap UAF → 完整 RCE | `poc.py` 主要是 session 文件投毒 + LFI、日志投毒 + LFI、直连 FastCGI、PEAR 写 webshell | 没有实现 109618/109619 的堆 UAF |
| 只要 PHP 版本旧就能打 | 需要目标已有 LFI（`--lfi-param`），或 FPM 9000 暴露 / PEAR 可达 | 不是无条件 RCE |
| lab 已复现 | `lab-uaf` 的 `Armed: YES` 只说明 session 里出现 upload_progress key | 不是 UAF 证明 |
| 隐蔽、无 AV 检测 | PEAR 分支会写 `p2s_<hex>.php` 的 system 马且不清理 | 有落盘痕迹 |

## 静态安全发现

- `poc.py` 的 import 主要是 `socket` / `ssl` / `urllib` / `threading` / `struct` 等；**未发现本地后门、本地命令执行、写本机文件**。
- 但它是远程武器：会投毒 session、写 webshell、外带命令输出、默认多轮并发，且**没有清理逻辑**。
- `--callback`：将命令结果 base64 外带到指定 URL；不可指向第三方。
- `--no-verify`：关闭 TLS 校验。
- `probe-only`：只看 `Set-Cookie` 就报 `upload_progress_writable=True`，不解析 PHP 版本，**任何 PHP 站都可能被骗**。
- PEAR 分支：`/pearcmd.php` + 写 webshell；适合检测，不适合生产验证。

## 审阅结论

- **不能当 CVE 验证器**：它的成功输出不能证明目标存在 CVE-2026-109618/109619。
- 可当 **PHP LFI/提权手法索引** 和 **lab 草稿**。
- 禁止对生产、客户目标、未书面授权主机运行；PEAR 分支会留马，`--callback` 会外带数据。
- 真验证：隔离 lab + 快照，或直接看官方 patch diff / ASAN build。

## 防守要点

- 先打补丁到 8.2.35 / 8.3.36 / 8.4.27 / 8.5.12。
- 临时缓解按官方：内存上限、请求体上限；`memory_limit=-1` 必须配 cgroup/容器上限，别裸奔。
- 加固：`session.upload_progress=Off`（不用时）、`allow_url_include=Off`、session 目录移出 webroot、webroot 不可写、删除 PEAR、FPM 只听 Unix socket。
- 检测：慢速 multipart + `PHP_SESSION_UPLOAD_PROGRESS`、LFI 指向 `sess_*`、`pearcmd.php` 的 `config-create`、`p2s_*.php` 落盘、UA 含 `<?php`、外部直连 FPM 9000、FPM worker 频繁 502/重启。
