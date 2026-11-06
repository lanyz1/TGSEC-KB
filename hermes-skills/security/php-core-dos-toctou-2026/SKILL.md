---
name: php-core-dos-toctou-2026
description: Use when PHP worker churn/DoS is in scope — 23-byte C: crasher, GC double-free, flock TOCTOU, session-wipe.
---

# PHP 核心 DoS / TOCTOU 面（2026-10 存活集）：23 字节打死 worker、flock 空窗、GC 双释放

> 来源：`github.com/ACD421/PHP` zero2 / zero7 / zero10（2026-10-23）。全部 ASLR-on 实测、带 strace/gdb 回执。
> 这一族不是 RCE，但**"memory_limit 加大就行"的防御叙事在这里全灭**——成本与包体大小无关。

## 0. 成本函数（为什么按字节做防护没用）

| 原语 | 线上字节 | 受害者成本 | 单点致死 |
|---|---|---|---|
| `C:` 空对象 worker 杀（`C:11:"Dom\Element"` / `HashContext`） | **23 B 裸 / 41 B 上线** | 进程生命周期 | php -S：**1–5 个请求**整池死 |
| FPM respawn churn | 23 B/请求 | fork+模块初始化 | **34.1 次杀/秒**，N=10,000 → 10,000 SIGSEGV / 334.5 s |
| GC 双释放 | 序列化串 | tcache abort / 野写 | 远程 kill 4/4 |
| flock-hold drip | 2 MB 一次 + 滴灌 | 锁 + 解码攻击者大小的 session | jammy Apache：5 请求到池死 |
| duplicate-header 放大（jammy） | 6 B/头 | 分配 303 B/6 B 行 | 池耗尽 |
| no-CD part flood | 26 B/part | 解析器 CPU 无上限 | 池耗尽 |

## 1. `C:` 格式 crasher（zero7，CVSS 7.5）

- 8.4/8.5 发布分支**从未合入** `b50b30c`（GH-22046，非 Serializable 类用 `C:` 应失败）与 `4bf700e`；
  `object_custom()` 里还是老的 `object_init_ex` → 任意类被"空构造"。
- 实测 **224 个声明类里 141 个**可被 `C:` 实例化，包括只有原生构造才合法的内部类 → 属性访问即崩（SIGSEGV）。
- 回执：8.5.12、3v4l.org 在线（`Process exited with code 139`）、8.5.13 preview 全崩。
- 用法：

```bash
# 单发
curl -s http://T/ --data 'x=C:11:"Dom\Element":0:{}'    # 端点需有 unserialize
# 或交给武器
python3 weapons/php2shell.py --target http://T/          # cformat 链
```

## 2. FPM / php -S worker 屠杀（zero10 §1–2）

- **php -S**：4 worker 池，N=100 crasher → 100/100 杀，**池 4→0 仅 0.6 s，且 0 respawn**；
  之后僵尸 master 仍占监听套接字 → 客户端拿 **RST**，看起来像"卡死"而不是"拒绝"。
- **FPM**（8.5.12，pm dynamic 4 children）：N=100 → **34.1 req/s 稳定杀率**，100/100 SIGSEGV + respawn；
  N=10,000 → **29.9 req/s 持续 334.5 s = 10,000 次 SIGSEGV**，池最少 1 个 child 存活，master RSS 漂移 4 KB，
  跑完服务照常 → **一个未授权连接可无限期维持 ~30 杀/秒**，每次杀都让运维付 fork + 模块初始化 + core 采集成本。
- 良性对照（N=10,000 正常请求）：68.4 req/s、10,000/10,000 OK → 不是负载问题，是 crasher 特性。
- **缓解剧场**：`memory_limit=2048M` + `post_max_size=64M` + `max_input_vars=10000` 下 **20/20、100/100 同样被杀**。

## 3. flock-hold TOCTOU（zero10 §1c，jammy Apache + mod_php 8.1.2）

- `ps_files_open` 在**打开 session 时**取 `flock(LOCK_EX)`，p99 **0.1 ms**；攻击者用滴灌上传让解码拖住锁，
  合法请求排队；持锁者若被 crasher 打死，内核释放锁 → **7–41 µs 的可写窗口**。
- 结果：**5 个请求打到池死**；窗口内可插入写（RCE 插入面），但作者只回执到"锁/窗口"，未把它做成稳定 RCE。
- 同一族还有：**重复 header 放大**（jammy：6 B 头 → 303 B 分配）、**no-CD part flood**（26 B/part 吃解析器 CPU）。

## 4. GC 双释放（zero2，CVSS 7.5）

- 2026-10-21 补丁带出的武器化 GC double-free：`SimpleXMLElement` 属性表，
  第一次 free `Zend/zend_gc.c:2142`（free_obj 路径），第二次 → tcache。
- 回执：`free(): double free detected in tcache 2` **4/4 必现**（glibc ≥2.35 tcache key 检查）；
  默认 ZendMM 下**静默**（ASAN 只在双释放时响）。
- 双释放表的**键和值都来自攻击者输入** → 可控间接调用已在 gdb 下回执（`free_obj` = 攻击者选定），距可控 RIP 还差
  一次堆布局（bin-6 两周期环）。GH-24488 已由 evankford 报，修复 pending。
- 打点：找 `simplexml_load_string()` / SoapClient / `unserialize()` 处理 XML 的地方。

## 5. 检测（给防守/自检用）

- **每请求 SIGSEGV 计数**才是告警信号（FPM log `exited on signal 11` ×N），不是内存曲线；
- `memory_limit` / `post_max_size` / `max_input_vars` 对上面全部原语**无效**（实测）；
- php -S 池死后是 RST 而非 503 → 监控"RST 突增 + 无 respawn"；
- 会话文件 0 字节但无告警 = session-wipe（8.1.x 静默，见 `php-session-handler-gap-rce` §1C）。

## 6. 判修复

- `C:` guard：`b50b30c` / `4bf700e` 只在 master，**8.4/8.5 分支头都没有**（8.5.13 也没有）。
- GC：GH-24488 pending。
- 应用侧：`unserialize($x, ['allowed_classes'=>false])` 能挡 `C:`/`O:` 两类；关掉不用的 `session.upload_progress`；
  `php -S` 永不上生产（无 respawn）。

## 7. 坑

- 打 FPM 时**别指望服务直接 502**：它 30 杀/秒还在正常服务，只有 core 文件和 log 里的 signal 11 能看出来。
- `C:` 载荷里的类名要给**真实存在的类**（Dom\Element、HashContext、SplFileObject…），拼错只会 500。
- jammy 的 header 放大 / flock 窗口只在 mod_php 8.1.2 上量过，别套到 FPM 8.3。
- 这些面全都不需要 PHP 配置前提（除 flock 需 session），但都需要一个 `unserialize()`/session 端点。
