---
name: printer-security
description: "Printer security testing — PJL command injection, PostScript exploitation, network printer discovery, fax interception. Trigger: printer, ipp, pjl, postscript, printer exploit."
---

# Printer Security

Printer security testing — PJL command injection, PostScript exploitation, network printer discovery, fax interception. Trigger: printer, ipp, pjl, postscript, printer exploit.

## 打印/文档管理服务器 → 域控沦陷(PaperCut 实战范式, 2026-08/09)

**为什么属打印机族**: 打印管理服务器(PaperCut NG/MF 等)装在**域内 Windows/Linux 服务器**上、对外开放 Web 管理面、常直连 AD 做用户认证 → 一旦 RCE,顺手的下一跳就是**域控**。这是打印生态里最值钱的一环,比打单台打印机高一个量级。

### 漏洞(2026-08 官方紧急通告, 已认定在野)
- **CVE-2026-81578 / CVE-2026-82078**(PaperCut NG/MF;补丁见官方 security-bulletin-27-aug-2026)
- 指纹: PaperCut Web 管理面(默认 :9191 管理;部分版本 :9192);`/app` 路径、页脚 `PaperCut`、`/admin` 登录框
- EOL 老版本无补丁 → 只能隔离/前置 WAF;版本命中即优先打

### 拿 shell 之后的链(2026 在野复盘,GreyNoise)
1. **RCE** 落在打印服务器(服务账号权限)
2. 域内服务器提权: **dump LSASS 内存 + 注册表 secrets** 取特权凭据 → **Pass-the-Hash** 打域控
3. 环境仍存 CVE-2021-42278 / 42287 → **noPac**(sAMAccountName 伪装 + 票据)直取域管
4. 量级: 440 实例 / 395 组织 / 48 国;12 个组织拿到域管;最快**初始访问 → 域管 5–7 分钟**

### 方法论增量(是打法形态, 不是单个漏洞)
- 该战役由**攻击者用上百个 AI agent(OpenAI Codex + DeepSeek harness)自动化**完成: agent 自建本地靶场(PaperCut + AD)先验证利用链 → 用 Netlas 生成目标清单 → 机器速度批量打;**26 秒内拿下 11 个组织**;并给 agent 下"回避某 28 国"规则(部分 agent 未遵守)
- 启示: **公开面 + 单一指纹的批量目标(打印/管理套件)是 AI 自动化首选**;我方攻击流程可借鉴"本地靶场先行验证 → 再批量",防御侧对应结论是"AI 让补丁窗口塌缩到分钟级"
- 教育行业占比最高(204/395)——学校打印服务器极普遍且补丁滞后

### 关联
- 管理与运维套件的硬编码凭据类(ASUS ACC / SmartIT)见 `rce-encyclopedia` §9b
- 打印机本体 PJL/PostScript 注入见本技能 `scripts/pjl_inject.py`、`scripts/postscript_exploit.py`

来源: BleepingComputer / The Register / GreyNoise(2026-09-10);PaperCut KB security-bulletin-27-aug-2026
