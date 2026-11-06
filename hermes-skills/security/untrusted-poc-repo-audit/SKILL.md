---
name: untrusted-poc-repo-audit
description: Use when auditing a public PoC/exploit repo.
---

# 公开 PoC / Exploit 仓库审阅

## 适用场景

- 用户丢来一个 GitHub 仓库，说「看看这个」「这个 CVE 的 PoC」「能不能用」「是不是真的」。
- 仓库声称复现某个 CVE、提供完整 exploit、带 lab、带扫描器，但你还没在授权目标上验证过。
- 你要决定：把它当权威 PoC、当线索、当学习材料，还是直接拒绝使用。

**核心原则：仓库自述不是证据。** 先审来源，再把 README 的每一条声明映射到代码，最后看 lab 到底证明了哪一级。没有独立复现的仓库，默认按「未验证」处理。

## 铁律

1. **只读审阅**：`git clone --depth 1` 到隔离目录；不 `pip install`、不跑 `poc.py` / `entrypoint.sh` / `trigger.py`、不连它的外网。
2. **不在真实目标上试**：除非目标在书面授权范围内，且你已单独评估过它的副作用（写文件、留 webshell、打崩 worker、外带数据）。
3. **不把仓库 payload 原样贴进报告**：只写能力、前置条件、检测点和防御建议。
4. **官方源优先于仓库**：CVE 编号、受影响版本、修复版本，以厂商 advisory / CVE / 项目公告为准。
5. **没有证明的就写「未证明」**：不要用「代码看起来完整」替代「在目标版本上跑通」。

## 审阅流程

### 1. 来源与时间线

```bash
curl -sS https://api.github.com/repos/OWNER/REPO
curl -sS 'https://api.github.com/repos/OWNER/REPO/commits?per_page=10'
```

记录：`created_at`、`pushed_at`、commit 数、stars/forks、release、license、默认分支、贡献者。

判读：
- **CVE 公告当天/数小时内创建**、commit 很少、无 release、无独立 issue/讨论 ⇒ 可信度低，先按「热点传播 / 学习材料」处理。
- 提交里有 AI co-author（如 `Co-Authored-By: Claude ...`）⇒ 不代表一定是假，但代表**没有独立复现**，不能自证。
- 仓库自称的 CVE 编号必须回到官方 advisory 核对；不要只读 README 的「CVSS 9.x」「no AV detects」。
- 看仓库有没有关联的独立复现、issue 讨论、安全厂商分析；没有就降级。

### 2. 安全隔离

- 克隆到 `/root/<name>_audit` 这类独立目录，不放进现有案卷。
- `python3 -m py_compile <file>` 只验语法，不执行。
- 需要动态验证时：单独 lab + 容器/VM 快照 + 无外网；先约定清理步骤。
- **禁止**把 `--callback` / webhook / 外带地址指向任何第三方；只可用你自己控制的隔离接收端，且仅在授权 lab。

### 3. 仓库结构与代码规模

- 列文件树，区分：
  - `poc.py` / `exploit.*`：真正的利用代码
  - `lab/` / `Dockerfile` / `entrypoint.sh`：靶场脚手架
  - `README` / 文档：声明
- `wc -l` 看规模；`py_compile` / 对应语言语法检查；不要因为「文件很多」就认为链路完整。
- 标出**编排器 vs 漏洞原语**：很多 PoC 只是把 LFI、session 投毒、日志投毒、PEAR、FastCGI 串起来，不是 CVE 本身的内存破坏。

### 4. 声明 → 代码矩阵（最重要）

把 README 的每个宣称环节列成表：

| README 声明 | 代码落点 | 真实前置条件 | 证据等级 |
|---|---|---|---|
| 完整 RCE | 哪个函数/文件 | LFI / FastCGI / PEAR / 上传 / 仅 lab | 代码存在 / 走到路径 / 真 RCE |

逐条问：

- **它真的实现了漏洞原语吗？** UAF 要有 free 后重用、堆布局、受控写；只有 session key、5xx、crash 不算。
- **它需要目标已有 LFI 吗？** 需要 LFI 的「CVE PoC」证明的是 LFI 前置暴露，不是 CVE 本体。
- **它检查目标版本/补丁吗？** 不检查版本的 `probe` 很可能把已修复目标判成 vulnerable。
- **它的 oracle 有区分度吗？** 只看 `Set-Cookie`、HTTP 200、任意 5xx 或超时，通常没有。
- **它有没有清理逻辑？** 只负责打、不负责还原的 PoC，不适合生产；尤其会写 `p2s_*.php` / `p2s_<hex>.php` 这类 webshell 的。
- **它有没有外带/并发/TLS 风险？** `--callback`、默认多线程/多轮、`--no-verify` 是操作风险，不是漏洞价值。

### 5. 静态安全审计

只读扫描危险调用和外联特征：

```bash
grep -RInE 'subprocess|os\.system|os\.popen|eval\(|exec\(|compile\(|pickle|base64|requests|urllib|socket|http\.client' .
grep -RInE 'open\(.+[wa]|write_text|write_bytes|unlink|rmtree|chmod|system\(|shell_exec|passthru|popen|<\?php|callback|webhook' .
```

判读：

- **没发现本地后门 ≠ 安全**：远程武器不需要本地后门。
- 区分「本地木马」（写本机、执行本机命令、偷本地文件）和「远程武器」（对目标发包、写目标 webshell、外带目标输出）。
- 即使没有本地后门，只要它会写 webshell、外带数据、默认高并发、关 TLS 校验，就不能随便跑。
- 不要把 payload 原文写进报告；记录能力、前置条件、检测签名即可。

### 6. lab 自证阶梯

| 级别 | 证据 | 能说明什么 |
|---|---|---|
| 0 | README 自称 | 什么都不能说明 |
| 1 | 代码里有函数/字符串 | 作者写了代码 |
| 2 | lab 里某个 key 存在 / `Armed YES` | 走到了某条路径 |
| 3 | 可重复 crash + 稳定栈 | 可能触发内存破坏 |
| 4 | ASAN/UBSAN 报 free 后重用/越界写 | 强证据 |
| 5 | 受控写/控制流劫持 + 目标版本可重复 | 完整利用 |

**只有 4/5 级才配叫「UAF 可利用」。** 第 2 级只能写「走到某条路径」；第 3 级还要排除普通 DoS/超时/worker 崩溃。

### 6.5 盲打可用性闸门（blind-usability gate）

lab 里真打出 `uid=33` 也可能是**地址辅助**的，不等于实战可用。逐项问：

| 检查 | 实战可用 | 只能 lab |
|---|---|---|
| 地址来源 | PoC 自带 in-band leak | 从 `/proc/<pid>/maps`、gdb、`nm` 读；要求 `--heap-base/--module-base/--libc-base` |
| 运行特权 | 普通网络请求 | 需要 `SYS_PTRACE`、宿主机文件、容器内 `docker exec` |
| 预置条件 | 全自动 | 需要 `seed.php` / 手工暂停 / 预置 session 文件 |
| worker | 多 worker 稳定 | 固定 **1 个 prefork worker**、靠重启对齐 ASLR |
| SAPI | 目标常见栈（FPM/nginx） | 只对 Apache prefork + mod_php；FPM/LiteSpeed 在 R1 OOM 就退出 |
| 配置 | 默认配置 | 强行 `memory_limit=4M/16M`、`USE_ZEND_ALLOC=0` |
| 后利用 | 稳定 | 触发后进程 fault，只能写个 marker |

任一项落在右列 ⇒ 判「lab 可用，实战不可用」，不要再写「pre-auth RCE」。

**最高信号是仓库自己的 `PROOF-BOUNDARY` / `Not proven` / `Limitations` 段**：作者通常已写清「没有 attacker-obtainable leak」「不支持多 worker」「不支持 FPM」。先读这段，比读 README 吹牛有用十倍。

### 7. 结论分级

| 级别 | 判据 | 建议 |
|---|---|---|
| 权威 | 厂商/项目官方 PoC，独立复现 | 可在授权 lab 验证 |
| 可参考 | 代码完整、有 lab、但无独立验证 | 只当线索/学习材料 |
| 仅 lab | 只能证明旧版本走到某路径，无 UAF/RCE 证据 | 不用于目标 |
| 不可作 CVE 验证器 | 需要 LFI/FastCGI/PEAR 前置，或 oracle 无区分度 | 不推荐 |

### 8. 报告结构

```markdown
## 结论
- 仓库性质：官方 PoC / 第三方复现 / 通用 LFI 工具箱 / 学习材料
- 它证明了什么、没证明什么
- 能不能用：可以 lab / 只能参考 / 不要用

## 元数据
- created/pushed/commits/stars/forks/release
- 与官方 advisory 的时间关系

## 声明 vs 代码
| 声明 | 代码 | 前置条件 | 证据 |

## 静态安全
- 本地后门：有/无
- 远程武器化：webshell/外带/并发/无清理

## 风险与建议
- 不要用于真实目标
- 先打补丁；临时缓解和检测点
```

交付时先一句话判词，再列证据；不要用「可能」「大概」糊过去，也不要把仓库 README 当结论复读。

## 防御映射

先打官方补丁；临时缓解按官方建议（内存/请求体限制等），再叠加：

- `open_basedir`、`allow_url_include=Off`、`allow_url_fopen=Off`（按业务）
- session 目录移出 webroot；webroot 对 PHP 不可写
- 删除不用的 PEAR；FPM 只听 Unix socket，不暴露 9000
- 不用上传进度就关 `session.upload_progress`
- 监控慢速 multipart + 异常 `PHP_SESSION_UPLOAD_PROGRESS`、LFI 指向 `sess_*`、`pearcmd.php` 的 `config-create`、`p2s_*.php` 落盘、UA 含 PHP 标签、外部直连 FPM、worker 频繁 502/重启

## Pitfalls

- **同一天创建的 CVE 仓库 = 热点传播，不是权威 PoC**：先查官方 advisory，再看仓库是否独立复现。
- **`Armed YES` / 5xx / crash 不是 UAF 证明**：没有 free 后重用、受控写入或可重复 crash 栈，就只能写「走到了某条路径」。
- **需要 LFI 的 CVE PoC 不是 CVE PoC**：它验证的是 LFI 前置暴露，不是 CVE 本体。
- **静态没发现本地后门 ≠ 仓库安全**：远程武器不需要本地后门。
- **PoC 的 `probe` 只看 Set-Cookie / HTTP 200 会把任何 PHP 站判成 vulnerable**：必须检查它有没有真正的版本/补丁 oracle。
- **老 lab + 未打补丁版本只能证明历史路径**：不能证明在真实目标、真实补丁级别上可用。
- **README 的「no AV detects」是营销，不是检测结论**：以实际文件落盘、进程行为、网络外联和日志为准。
- **「3 次 fresh-ASLR 复现」可能是地址桥**：`run.sh` 反复重启容器直到 `discover.py` 读到合适布局，`discover.py` 读 `/proc/<pid>/maps` + `nm`。这不是盲打。
- **同族仓库可能有「纠错版」**：先搜作者/研究者的 corrected findings。一条被上百仓库转发的链，可能在 `addref` 处就被判死（CVSS 0.0），真 bug 只剩 5.3 内存安全。
- **README 写 `PRIVATE / EMBARGOED` 却公开** = 泄露的禁运研究，声明按未验证处理。
- **star 数不是证据**：披露当天可出现上百个同名仓库，629★ 的可能只是最早发布。

## 参考

- `references/php2shell-2026-10.md` — php2shell 仓库审阅案例：当天新仓、AI co-author、LFI 前置、`Armed YES` 自证不足。
- `references/blind-usability-case-php2shell.md` — 三个「真 RCE」仓库的逐行反证：地址桥、`PROOF-BOUNDARY`、纠错版把链判死（2026-10-21）。
- `templates/poc-repo-review.md` — 可直接复制的审阅报告骨架。
