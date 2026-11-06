# 判例：三个「真 RCE」仓库，没一个能盲打（php2shell, 2026-10-21）

> 只记录判据与证据，不含 payload。

用户丢来三个来源，问「到底哪个才是真实的 PoC，能在实战环境用，而不是靶场」。逐行读完的结论：**0 个可盲打**。三个正好代表三种「看起来真」的假象。

## 1. `blasty/php-8.5.4-apache-uaf-poc` — 真网络驱动，但地址辅助

- `apache_poc.py` 确实是纯网络驱动（不读 /proc、不 gdb），声称在 pristine Apache + PHP 8.5.4 上 3 次 fresh-ASLR 打出 `uid=33(www-data)`。
- 但 `resolve()` 硬性要求 `--heap-base`、`--module-base`、`--libc-base`，缺一个就 `SystemExit`。
- `final_body` 还要求 `delta = decode_target - stale_context` 落在 ~1017 个 slot 内，否则报「unsuitable relative layout」。
- 需要 `--seed-url`（或手工暂停）预置 crafted session。
- `docker/run.sh`：`--cap-add SYS_PTRACE`，最多重启 20 次等一个「合适 ASLR 布局」；单 prefork worker；`memory_limit=4M`。
- `docker/discover.py`：读 `/proc/<pid>/maps` 拿 libphp/libc/heap，跑 `nm` 取符号 —— **Docker-only address bridge**。
- README 自述：远程路径仍需「PHP heap、module、libc disclosures, same-worker affinity, and a legitimate way to establish the crafted session value.」
- 附带信号：README 顶部写 `PRIVATE / EMBARGOED — do not make this repository public`，但仓库是公开的 ⇒ 按泄露的禁运研究处理。

**判词**：最接近真实，但属于「地址辅助的 lab RCE」。

## 2. `dinosn/php-cve-2026-10961x-lab-poc` — 自己写了「未证明」

- 两条链：stale bucket（R1 500 + shutdown）、dangling ref → `zif_system`；Chain B 开火时 `FIRE_GDB=0`。
- `docs/PROOF-BOUNDARY.md`：
  - Lab-assisted：「heap, libphp, and libc addresses measured by host GDB for the current Apache parent.」
  - Not proven：in-band address disclosure、portable ASLR-independent chain、default Zend allocator、multi-worker、**PHP-FPM command execution**、「Official status of the supplied CVE names or fixed versions.」
- README：「Chain B's addresses come from /proc on the lab host.」
- 固定单 worker、PHP 8.5.11、`USE_ZEND_ALLOC=0`、16M memory_limit。

**判词**：自证充分的实验包，实战 0。作者连 CVE 编号是否官方都没打包票。

## 3. `jackalsyn.com/posts/php-up-2026.html` — 纠错版把主链判死

- 缓存指针链 **dead at the addref**：`session.c:3213` 的 `Z_TRY_ADDREF` 让数组继续存活，没有 free、没有 RCE，**CVSS 0.0**。
- 真 bug 是 serialize-state 跨请求 UAF，ASAN 在 `var.c:756`（数组/引用上的 `n+=1`），**prefork-only**，**只有内存安全，CVSS 5.3**。
- 原话：「No `zend_fcall_info` forge, no `zend_call_function`, no `system()`, no code execution.」
- 视频里的 leak→call 是 Ubuntu 26.04 / PHP 8.5.4 / **glibc 2.39**；Debian 12（glibc 2.36）没复现。
- 自带框架的 `--live <url> --bug 619 --dtor <leak>` 仍然要 leak 地址。

**判词**：分析正确、武器不成立；也解释了为什么「大家都说能打」——转发的全是那条 CVSS 0.0 的链。

## 实战池验证（反向证据）

2,800+ 博彩域名 → 275–746 个 PHP base，约 25 万发探测：

- LFI：0（PEAR oracle 113,392 发无 `PEAR Version`；wide 34,894；fast 26,177；extra 77,584）。
- 序列化 cookie：0/220 ⇒ 无 Chain B 入口。
- SAPI：nginx 82、openresty 15、Cloudflare 73、Apache 14；14 台 Apache 里 11 台 Win64 `mod_fcgid`，3 台 Unix Apache 是纯静态页（`/index.php` 404）。
- 结论：不是 payload 不行，是池子里没有它要的入口；UAF 链在 FPM/LiteSpeed 上结构性关闭。

## 可复用的四条判据

1. **要地址 = 不是盲打**。看到 `--heap-base` / `/proc/self/maps` / `nm` / `SYS_PTRACE` 直接降级。
2. **先读 `PROOF-BOUNDARY` / `Not proven`**，再看 README。
3. **搜 corrected findings**：热点 CVE 的原始结论常被作者自己推翻。
4. **SAPI 决定链是否存在**：Apache prefork + mod_php 才有 OOM 链；FPM/LiteSpeed 在 R1 就退出。有 LFI 时 Chain A 更便宜；LFI 还能读 `/proc/self/maps` 补地址。
