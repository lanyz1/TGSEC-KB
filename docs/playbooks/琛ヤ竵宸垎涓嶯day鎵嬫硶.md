---
title: "补丁差分与Nday手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# 补丁差分与Nday手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/patch-diff-exploit/SKILL.md`

## 汇总内容

### patch-diff-exploit

来源：`/root/.hermes/skills/security/patch-diff-exploit/SKILL.md`

## ACTION REQUIRED（读完后立刻执行）

1. `NOW`: 确认本次任务目标是用户明确提供的授权目标（RoE）；未授权目标立即停止，不执行
2. `NOW`: 确认当前任务是否命中本 skill 的适用范围
3. `NEXT`: 用 shell 检查工具可用性（`which`/`where`），缺工具用 `pip install` 或系统包管理器安装，不猜路径
4. `NEXT`: 缺工具时调用 bootstrap，不要猜路径
5. `ACT`: 进入"工作流"第一步并执行，不要停在确认状态

# N-day 补丁差分到利用 (Patch Diff Exploit)

## 本仓探针

```bash
python3 tools/ops/binary_diff_probe.py drive --old 旧 --new 新 --case <案>
```

L2=哈希不同。证据进案卷 `测绘/`。

只做跨版本符号迁移、不反推洞 → `binary-diff`。已经有 CVE 编号要打授权站 → `1day-nuclei-kit` + `nday_route.py`，禁止只扫 CVE 结案。

## 适用范围

当任务属于以下场景时使用本 skill：

1. **已知 CVE 但无公开 PoC** — 厂商公告写了"修复了 XX 组件的越界写"但没放 PoC，需要从补丁反推
2. **SRC / 红队打 N-day** — 目标资产未及时更新，需要把刚发布的补丁差成可用的 1-day 利用
3. **Patch Tuesday 跟进** — 每月第二个周二微软放补丁，需要快速锁定高价值漏洞（Kernel / Win32k / AFD / CLFS）
4. **Linux LTS 补丁分析** — 主线 fix 已合并，但旁支或某发行版 backport 不全，找未修补面
5. **驱动 / 服务的安全补丁还原** — 显卡驱动、AV 引擎、虚拟化组件等闭源软件的补丁分析

### 与其他 skill 的分工

| 场景 | 用什么 |
|------|--------|
| 有旧版符号，迁移到新版本帮助分析 | `binary-diff/` |
| **从补丁找漏洞、写 PoC 打补丁前版本** | **本 skill** |
| 写出完整利用链（堆喷、ROP、提权） | `pwn-chain/` |
| 把 1-day 武器化部署到目标网络 | `pentest-tools/network-attack-defense/` |
| 从零逆向一个二进制 | `ida-reverse/` / `radare2/` |

差别的关键：`binary-diff` 的目标是**让新版可分析**（把旧符号搬过来），本 skill 的目标是**找出补丁修了什么 bug 然后打补丁前的版本**。前者服务防御侧 / 研究侧分析，后者服务攻击侧武器化。

## 核心原理

```text
patched 二进制 (after) unpatched 二进制 (before)
 ↓ ↓
 导入 IDA/Ghidra 导入 IDA/Ghidra
 ↓ ↓
 └──────── BinDiff / ghidriff ──────┘
 ↓
 函数级 diff（matched / unmatched / changed）
 ↓
 聚焦 match score 中等的函数（0.5 - 0.9）
 ↓
 看新增了什么：边界检查 / 锁 / 字段清零 / 整数溢出检查
 ↓
 反推 bug class：OOB / Race / Info Leak / UAF / Integer Overflow
 ↓
 在 unpatched 版本上写 PoC 触发
 ↓
 验证：unpatched 崩 / patched 不崩 → 漏洞确认
```

补丁修复模式 → 漏洞类型反查：

| 新增内容 | 大概率的 bug class |
|---------|------------------|
| `if (a + b < a)` / `__builtin_add_overflow` | 整数溢出 |
| `KeAcquireSpinLock` / `mutex_lock` | 竞争条件 (TOCTOU / double-free) |
| `if (idx >= MAX)` / `if (len > buf_size)` | 越界读 / 越界写 |
| `RtlZeroMemory` / `memset(struct, 0, ...)` | 未初始化内存信息泄漏 |
| `InterlockedDecrement` + refcount 检查 | UAF / 引用计数错误 |
| `ProbeForRead` / `ProbeForWrite` | 用户态指针未校验 |
| `SeAccessCheck` / capability 校验 | 权限校验缺失 |
| 删除 / 收紧 `IOCTL` code | 暴露面收敛（看老接口怎么打） |

## 工作流

### 5 步完整流程

```text
Step 1: 拿 before / after 二进制
 - Windows: Microsoft Update Catalog 下 MSU/MSP，用 expand.exe / dism 解包
 - Linux: 从发行版 USN/RHSA 拉 .deb/.rpm，用 dpkg-deb / rpm2cpio 解包
 - 第三方软件: 官网取 N-1 和 N 版本安装包

Step 2: 对齐符号
 - 有 PDB 直接吃，没 PDB 时用 binary-diff skill 把 N-1 版本的符号搬到 N 版本
 - Linux 内核取对应版本的 vmlinux + System.map / debuginfo

Step 3: 二进制 diff
 - BinDiff: 直接给两个 IDB，看函数级匹配结果
 - ghidriff: pip 一键安装，CLI 输出 markdown 报告
 - Diaphora: IDA 内插件，老牌但需要 IDA Pro

Step 4: 定位变更
 - 过滤 match score 0.5-0.95 的函数（完全相同的不看，完全不同的多半是新加 / 重命名）
 - 重点看：新增的 if / 新增的循环边界 / 删除的代码块（删了什么也是线索）
 - 用 LLM 看 before/after 伪代码反推 bug class（见 references/root-cause-and-poc.md）

Step 5: 写 PoC
 - 整数溢出：构造边界值（INT_MAX-1、0xFFFFFFFF）
 - 竞争：多线程 hammer，open/close + ioctl 高频并发
 - UAF：spray → free → reuse pattern
 - OOB：精确控制 len / index 越过边界
 - 验证 patched 版本不再崩，unpatched 版本稳定崩 → bug 复现成功
```

### 工具调用顺序

```text
下补丁 → 解包 → 加载到 IDA/Ghidra → BinDiff/ghidriff → 看 unmatched/low-match 函数
 → LLM 反推 bug class → 写 PoC → 在 unpatched 跑 → 崩 → 收工
```

## 典型场景示例

### 场景 1：Windows Patch Tuesday — Kernel CVE 复现

```text
背景：2025 年 11 月 Patch Tuesday，MSRC 公告 CVE-2025-62215
 Windows Kernel race condition 导致 double free，CVSS 7.0，本地提权
 微软只放了补丁，没放细节，没有公开 PoC

目标：复现 PoC，验证未打补丁的 Windows 11 22H2 / 23H2 可提权

步骤：
1. Microsoft Update Catalog 搜 "2025-11" + KB 号，下两个版本：
 - 22H2 build 22621.xxxx (unpatched)
 - 22H2 build 22621.yyyy (patched 后)
 命令:
 expand.exe Windows-KB5052000-x64.msu -F:* C:\out\patched\
 expand.exe C:\out\patched\Windows-KB5052000-x64.cab -F:* C:\out\patched\
 提取 ntoskrnl.exe / win32k.sys / win32kfull.sys / afd.sys

2. 两个版本都吃 PDB (微软符号服务器):
 symchk /v /r ntoskrnl.exe /s SRV*C:\sym*https://msdl.microsoft.com/download/symbols

3. 跑 BinDiff:
 bindiff old.BinExport new.BinExport
 或 ghidriff:
 ghidriff ntoskrnl_old.exe ntoskrnl_new.exe -o diff_out/

4. 看报告，过滤 similarity 0.6-0.95 的函数。
 假设定位到 NtXxxIoctl 类函数新增了一段:
 KeAcquireSpinLockRaiseToDpc(&obj->Lock);
 if (obj->RefCount == 0) { ... goto cleanup; }
 → 新增了锁 + 引用计数检查 → race + double free，符合公告描述

5. 写 PoC：用户态多线程同时调 NtClose + 触发同一对象的 IOCTL，
 制造 close 释放与 IOCTL 还在用之间的竞争窗口
 崩在 ntoskrnl 的 ObfDereferenceObject 后续 free 路径上

6. 验证：
 - unpatched 22621.xxxx 上跑 PoC，~30 秒内 BSOD (BAD_POOL_HEADER 或 DOUBLE_FREE)
 - patched 22621.yyyy 上跑同 PoC，无任何异常
 → 复现成功
```

### 场景 2：Linux 内核 LTS 分支补丁找未修的旁支

```text
背景：主线 6.x 已修某 net subsystem 的 OO

…（截断，全文见来源卡）
