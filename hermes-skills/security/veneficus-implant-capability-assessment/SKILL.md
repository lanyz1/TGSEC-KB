---
name: veneficus-implant-capability-assessment
description: "Use when 评估 Veneficus/abraxas 类全链植入物真实能力，或要按它的架构搭同类 C2 栈：BYOVD 池、AMSI/ETW 补丁、栈欺骗、持久化三选。"
---

# Veneficus Mini v3.0 —— 全链植入物的能力判定与可复用件

## 一句话
Abraxas Labs 公开的 Windows 10/11 x64 全链 kit：**PowerShell 落地 → Rust PE → Cloudflare Worker 中继 → Telegram 出数据**。它自称 “Full kill-chain malware 0day”，但作者自己放出的 `VENEFICUS_MINI_v3_DEEP_ANALYSIS.md` 逐文件标了「真代码 / stub / 编译不过」。**结论：控制面骨架和几个用户态件是真的，内核面（BYOVD/DKOM/栈欺骗）基本全是空壳，IOCTL 常量大多抄错。**「拿它当真能用的 implant」= 误判；「从里面拆零件」= 有价值。

## 架构（原文）
```
受害机
  loader.ps1   AMSI 静默 → GET /beacon 拉 PE → %TEMP%\MicrosoftEdgeUpdate.exe
    └── veneficus_mini.exe
          ├─ 环境评分（沙箱/虚拟机/分析痕迹）→ 高分自删 / 中分只指纹 / 低分跑全栈
          ├─ 隐蔽：syscall bypass 链、lacuna 栈欺骗、DKOM、AMSI/ETW 补丁
          ├─ BYOVD：结束 EDR 进程（K7RKScan / ThrottleStop / BdApi / TrueSight / wsftprm / RTCore64）
          ├─ 窃取：凭据、cookie、LSASS dump、设备指纹
          ├─ 持久化：WMI / 计划任务 / 注册表 三路回退
          ├─ SOCKS5 127.0.0.1:1080
          ├─ HVNC 127.0.0.1:5900
          ├─ Clipper：BTC/ETH/LTC/XMR/DOGE/SOL/XRP/BNB/USDT 地址替换
          └─ C2：AES-GCM 加密轮询 10±3s（safe mode 60±18s）走 HTTPS
Cloudflare Worker
  /beacon 下载  /exfil 收密文转 TG  /commands 一次性命令队列  /config 配置
  /admin /register /unregister /listing /set_config  ← 全部要 X-Admin-Key
Telegram Bot  收密文+nonce+HMAC，运营端离线解密
```

## 真实能力对照（自己别被 README 忽悠）
| 模块 | 文件 | 真实状态 |
|---|---|---|
| 主流程 / 沙箱评分 | `main.rs` | **真**（有完整控制流） |
| AES-GCM + HMAC | `c2.rs`/`crypto.rs` | **真** |
| Worker 路由形状 | `relay/` | **真**（但 `/beacon` 根本不发 payload、`/exfil` 不存全量） |
| Chromium 窃取 | `payload/steal.rs` | 半真：拷 SQLite，但用 DPAPI 解 login blob —— **Chrome v80+ 是 `v10` + AES-GCM，密钥在 `Local State`，这套解不开** |
| Firefox | 同上 | 只捞到 `logins.json` 密文（`NSS_ENC:`），没解 |
| LSASS dump | `payload/lsass.rs` | 调 `MiniDumpWriteDump` 真，但现代 Windows 有 **PPL**，基本被挡 |
| AMSI 补丁 | `stealth/stomp.rs` | 字节真：`mov eax,0x80070057; ret`；但**原生 EXE 里 `amsi.dll` 常常没加载**，打了等于没打 |
| ETW 补丁 | 同上 | 字节真：`xor eax,eax; ret`（3 字节），ntdll 必在，这条能生效 |
| Tartarus/Halo's Gate/ntdll unhook/间接 syscall | `stealth/syscalls.rs` | **全 stub**：init 全 `return true`，allocator 返 null，且没人调用 |
| 栈欺骗 lacuna | `stealth/lacuna.rs` | 包装器在，**从未用于发系统调用**；`CallGhost` 在 Cargo.toml 里但没 import |
| DKOM | `stealth/dkom.rs` | 全 `return false`（需要内核 R/W，而 BYOVD 那条路没导出） |
| 持久化 | `persistence.rs` | **真**：WMI / schtask / HKLM Run 三条 `cmd`/`powershell` 一行 |
| SOCKS5 | `proxy.rs` | 真但只 CONNECT、只本机、要 `/proxy_on` |
| HVNC | `backdoor/hvnc.rs` | 只做 RFB 3.8 握手，**没有隐藏桌面、没有帧缓冲** |
| Clipper | `payload/clipper.rs` | 真剪贴板循环，正则引擎可用，无 C2 配置时空转 |
| PrinterBug/PetitPotam | `lateral/ntlm.rs` | **stub + 未被调用** |
| CVE-2025-33073 横向 | `lateral/ntlm.rs` | 注释写成 “Windows EFS 提权”，还在 Windows 植入物里 `python3 CVE-2025-33073.py` —— 子系统错、主机错、模块没接 |

## BYOVD 驱动池（这张表才是真东西）
| 驱动 | CVE | 真实原语 | 本 kit 用的 IOCTL | 对不对 |
|---|---|---|---|---|
| ThrottleStop.sys | **CVE-2025-7771**（CVSS4 8.7，`AV:L/AC:H/PR:H`，Kaspersky 报过在野 “ThrottleBlood.sys”） | **物理内存 R/W**（`MmMapIoSpace`，无访问控制）→ 打内核 | `0x80002044` 只传 PID 字节 | **错**：缺 VA→PA 转换 |
| K7RKScan.sys | **CVE-2025-1055** / **CVE-2025-52915** | 内核进程终止 IOCTL（老版本几乎无调用者校验=直接 LPE） | `0x830020C4` + PID(LE) | 与公开 PoC 的 `0x222018` 不同，需实测 |
| Safetica ProcessMonitorDriver.sys | **CVE-2025-70795** | 进程终止 IOCTL（11.34.5.0 移除） | `0x22E084`，和 TrueSight/wsftprm 共用（复制粘贴） | **错**：公开值是 `0xB822200C` |
| RTCore64.sys | 无 CVE 串（MSI Afterburner，常年被滥用） | 任意内核 R/W | `0xAA013044` | 结构体写法在 `&[&dyn]` 数组里，**大概率编译不过** |
| capcom.sys | 无（已被微软 blocklist） | 内核执行用户函数 | 同 RTCore64 | IOCTL 语义就不对，不是 PID-kill |
| BdApiUtil64 / TrueSight / wsftprm | 无 | 历史 BYOVD 进程结束 | `0x9C402440` / `0x22E084` | 文件缺失 / 常量复用 |

**判定口径**：这套东西的内核面 = 名字齐、实现散。真要用 BYOVD，回到公开 PoC 的 IOCTL 值 + 自己算 VA→PA（`MmGetPhysicalAddress` 语义），别用这份源码。

## C2 设计（可抄的部分）+ 它自己的 OPSEC 漏洞
- 设计：Worker 只做中继**不解密**，密文直接转 Telegram；`/admin` 系列全部 `X-Admin-Key`；命令队列**一次性**消费。
- 漏洞 1：**AES-256-GCM 通道密钥由编译期 agent id 派生且不加盐** → 拿到二进制就等于拿到密钥。
- 漏洞 2：`/beacon` 路由**根本不存在**，stager 拉不到 payload（拿它当基础设施模板会直接断链）。
- 漏洞 3：命令以明文在 Worker 里排队。
- 漏洞 4：持久化三条全是 `cmd`/`powershell` 一行，日志痕迹重（`wevtutil` 清日志只会更显眼）。

## 能直接拆去用的件
1. **AMSI/ETW 补丁字节**（上面两条）—— 只要目标进程加载了 `amsi.dll`/`ntdll` 就能用。
2. **三路持久化回退**：`WMI __EventFilter/CommandLineEventConsumer`、`schtasks /create /sc onlogon`、`HKCU\...\Run` —— 换成更隐蔽的载体（COM hijack / 计划任务伪装系统目录）再上。
3. **Sandbox 评分思路**：CPU 核数/内存/磁盘型号/进程名/用户名/最近文件 —— 自己写判定表比抄它的权重靠谱。
4. **Clipper 正则族**（BTC/ETH/TRON 地址格式）—— 地址替换前先校验链上前缀与 checksum，否则替换出来的地址无效。
5. **Chromium 正确解法**：`Local State` → `os_crypt.encrypted_key` → DPAPI 解 → AES-256-GCM 解 `v10` blob（key 前缀 `DPAPI`）。它的 `steal.rs` 是反面教材。

## 怎么用这张卡
- 遇到这类 kit 的样本/仓库 → 先跑「真/stub 对照」再评级，别拿 README 当能力声明。
- 要搭同类栈 → 抄 C2 拓扑（Worker 中继 + TG 出数据 + Admin-Key 控制面），别抄内核面。
- 蓝队侧：Worker 域名 + `X-Admin-Key` 头 + `/listing` 路由是强指纹；`%TEMP%\MicrosoftEdgeUpdate.exe` 落地名也是。

## 出处
`github.com/abraxas/veneficus`（含 `VENEFICUS_MINI_v3_DEEP_ANALYSIS.md`）、`github.com/abraxas/veneficus-implant-public`（`.pseudo` 大纲）、`abraxaslabs.tech/research/veneficus`。
相关卡：`windows-av-evasion`、`windows-privilege-escalation`、`windows-lateral-movement`、`c2-family-infra-mapping`、`malware-capability-assessment`。
