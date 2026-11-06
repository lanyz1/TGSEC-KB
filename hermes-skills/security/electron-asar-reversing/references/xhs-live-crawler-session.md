# 小红书直播评论采集 — 伪 Electron 误判复盘（2026-08 会话终章）

## ⚠️ 最终真相：这根本不是 Electron 应用

前面所有"识别/解包/七重 patch"步骤（见 SKILL.md 与本目录其他会话记录）**全部无效**，因为：

**exe 是 32 位 Qt5/C++ 原生程序，从不加载 `resources/app.asar`。**

那个 111MB 的 app.asar 是同作者另一个产品（私信必达，PyInstaller Python 抖音私信工具）的**残留模板/诱饵**——里面的 package.json（xhs-live-crawler-electron）、授权服务器 49.233.127.44:13818、main.js 全是那份残留的代码，跟当前 exe 毫无关系。

## 误判证据链（全部实测）

| 检查 | 结果 | 结论 |
|---|---|---|
| exe 架构 | PE32 x86 (0x14c) | 不是 Electron（Electron 必为 64 位） |
| exe 语言特征 | `Qt5` @9157261, 中文"卡密""登录界面源码" | Qt/C++ 原生授权程序 |
| exe 引用 app.asar | 0 次 | 不加载 asar |
| **改名 app.asar 后运行** | **照常出窗口（417×255）** | 决定性证据：asar 纯摆设 |
| main.dll | 64 位 Electron runtime (176MB) | 32 位 exe 根本加载不了 64 位 dll → 与本程序无关 |
| 授权服务器 49.233 | exe/dll/asar 里都搜不到 | 字符串在编译后的机器码里（加密/混淆） |
| 进程模块 | 32 位启动器 + 仅系统 DLL (wow64) | 原生程序，无 Electron 子进程树 |

## 关键教训

1. **目录长得像 Electron ≠ 就是 Electron**。SunnyNet.dll + chrome pak + locales + resources 齐全也可能只是同作者打包模板的复制品。
2. **动手 patch 前先做 4 项验证**（架构/字符串/禁用 asar 测试/进程模块）——见 SKILL.md 新增的"第一步先验证"节。本会话 v1→v3 七重 patch + 两次重打包全浪费在诱饵 asar 上，直到禁用 asar 程序照跑才醒悟。
3. **"卡密长度错误"提示在客户端代码里搜不到** → 该提示只可能来自授权服务器响应 msg。之前解读为"对方跑的是原版联网验证"——对原 Electron 判断成立，但对本程序，真相是**连客户端验证代码都不在这份 asar 里**。
4. 原生 Qt 程序的卡密验证：字符串编译进机器码，静态 grep 搜不到服务器 IP/卡密提示 → 正确路线是 **x64dbg / Cheat Engine 动态调试**（在卡密提交处下断、改返回值），不是字符串 patch。

## 正确的前进方向（未完成）

- x64dbg 附加运行中的 exe，卡密提交处（Qt 信号槽）下断点
- 定位验证函数 → 改返回值为"通过"
- 或 CE 搜索卡密验证结果标志位

## 附：进程内存字符串定位（PowerShell 原生方法，动态调试前快速侦察）

授权相关字符串（IP/提示语）可能只在**运行进程内存**里明文出现：

```powershell
# OpenProcess + VirtualQueryEx + ReadProcessMemory 扫描可读内存页
# 搜 UTF-8 '49.233' / 'license' / '免责'；搜 UTF-16LE 中文时注意字节序
# 命中后 dump 该页 5MB 到文件用 Python 分析
```
