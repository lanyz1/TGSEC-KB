---
title: "Android-APK-Frida动态Hook手法.md"
generated: 2026-10-21
kind: consolidated-playbook
note: 由现役技能卡自动汇总；保留原卡语义，未改写攻防步骤
---

# Android-APK-Frida动态Hook手法.md

> 本页由引用该路径的现役技能卡汇总生成。原始内容与完整步骤见下方来源卡；不要把它当成独立的新打法。

## 来源卡

- `/root/.hermes/skills/security/apk-recon/SKILL.md`

## 汇总内容

### apk-recon

来源：`/root/.hermes/skills/security/apk-recon/SKILL.md`

# Skill: APK/IPA 逆向情报提取（博彩站专项）

## 适用场景

授权目标有移动端 APP 时使用。先抽情报，再按需打客户端面。

- **密钥 / 后台 / 测试域 / 签名算法** → 本卡 `apk_recon.py`（默认）
- **组件导出 / WebView / allowBackup / 手势 / 本地存储全表** → `docs/playbooks/Android客户端渗透检查清单.md`
- **Deeplink / JsBridge / 文件域 / NanoHTTPD** → Skill `webview-deeplink-bridge`
- **微信小程序 wxapkg** → Skill `wxmini-static-audit`（不是本卡）
- **UU 模拟器 + Reqable/Charles 抓包** → `docs/playbooks/MkTs-UU模拟器Reqable抓包.md`
- **证书固定 / root 检测 / Hook** → `Android-APK-Frida动态Hook手法.md`

博彩站 APP 常硬编码：
- API 签名密钥（AES/MD5 盐）→ 直接伪造任意请求
- 后台管理路径（/admin/ /operator/）→ 绕过 Cloudflare 路径保护
- 测试/预发布环境 URL → 通常无 WAF，直接打
- MQTT/WebSocket 地址 → 实时数据监听
- 运营商 API Token → 跨商户数据访问

## 工具

```
tools/ops/apk_recon.py
tools/ops/install_jadx.sh
tools/arsenal/jadx/bin/jadx (v1.5.6)
```

## 命令速查

```bash
# 快速扫描（30 秒，不反编译）
python3 tools/ops/apk_recon.py strings \
 --apk /tmp/app.apk --case 站点_日期

# 完整逆向（2-10 分钟，全面）
python3 tools/ops/apk_recon.py extract \
 --apk /tmp/app.apk --case 站点_日期

# 专项：只找签名算法
python3 tools/ops/apk_recon.py sign-algo \
 --apk /tmp/app.apk --case 站点_日期
```

## 获取 APK 的方式

```bash
# 1. 直接从目标站下载链接
curl -L https://TARGET/download/app.apk -o /tmp/app.apk

# 2. APKPure / APKCombo 搜包名
# 3. 抓包时拦截 APK 下载请求（Scrapling MCP）
# 4. 用 adb 从真机提取（需已安装）
adb shell pm list packages | grep 站点关键词
adb shell pm path com.xxx.xxx
adb pull /data/app/com.xxx.xxx/base.apk /tmp/app.apk
```

## 情报分类和后续行动

| 提取到 | 下一步 |
|--------|--------|
| API 签名密钥（AES key / MD5 salt）| 直接伪造 API 请求；接 `payment-callback-forgery` |
| 后台管理 URL `/operator/xxxxx` | 打后台弱口令；接 `cdn-origin-tracing` 找 IP |
| 测试环境 `test.xxx.com` | 直连测试环境，无 WAF 保护 |
| MQTT broker 地址 | `paho-mqtt` 订阅 `#`；接 `spring-actuator-cloud-takeover` |
| 内网 IP / 数据库连接串 | 建立隧道后直连；接 `internal-tunnel` |
| Firebase/JPush key | 推送伪造；Firebase RTDB 未鉴权探测 |
| Cognito `IdentityPoolId` | **`cognito-unauth-s3-chain`** · `cognito_s3_probe.py extract`（会解压 APK）再 `chain` |
| 签名算法实现 | 在 DeepAudit 对反编译源码做精准审计 |

## 证据落盘

```
exports/bot-recovery/<案卷>/测绘/apk/
 apk_intel.json 完整情报报告
 apk_strings_intel.json 快速字符串提取结果
 sign_algo.json 签名函数代码片段
 jadx.log 反编译日志
 decompiled/ jadx 反编译源码
```

## 真源

- 手法：`docs/playbooks/APK逆向博彩站情报提取.md`
- 动态：`docs/playbooks/Android-APK-Frida动态Hook手法.md`
- 工具：`python3 tools/ops/apk_recon.py --help`


---

## 外部库增量（2026-10-11 分享包·CJK）

## CRITICAL: 路由执行契约（必须立即执行）

读完本文件后，不允许只回复“已读/已理解”。必须按顺序执行：

1. `NOW`：跑平台原生 router（Windows `scripts/master-route.ps1`；Linux/macOS/Kali `scripts/master-route.sh`），从 `config/routing.json` 定 PRIMARY；疑难再读 `routing.md` 三轴附录。
2. `NOW`：平台原生 `case-init` 落地当前分析项目的 `work/<case>/scope.md`；**auth 未 granted 禁止对目标 ACT**。本地离线样本使用 `offline-sample` preset + explicit sample；Force 不得绕过硬门。
3. `ACT`：立即打开 PRIMARY `SKILL.md` 执行 ACTION REQUIRED。
4. `NEXT`：工具路径只认 `tool-index.md`；缺工具 → 平台原生 bootstrap（仅 manifest）。
5. 结论用 Evidence→Finding→Path。报告/journal 是 SHOULD，除非用户要交付物。

**身份**：见 `ops/IDENTITY.md`（轻量路由包 + 工具自举 + journal；**不是** Z3r0 式平台）。

如果路由无法命中，必须先联网补充方法论并提议新增 skill，禁止硬塞到不匹配模块。

## 指令语义级别（RFC 2119）

- `MUST`：必须执行，违背即任务失败。
- `MUST NOT`：禁止执行，违背即安全违规。
- `SHOULD`：原则上要做，不做必须说明原因。
- `MAY`：可选动作。

## 当前模块

| 模块 | 目录 | 适用场景 |
|------|------|---------|
| **通用逆向** | `reverse-engineering/` | GDB / Frida / angr / Unicorn / Qiling / 反分析对抗 / 全语言平台逆向 / CTF 模式库 |
| **APK 逆向** | `apk-reverse/` | Android APK 解包、jadx 反编译、smali 修改、Frida Hook、重打包签名安装 |
| **.NET / C# 逆向** | `dotnet-reverse/` | 托管 PE 逆向、dnSpyEx + de4dot 脱混淆（ConfuserEx/SmartAssembly/Babel）、IL patch、Sharp* 红队工具分析、dnSpy MCP 联动 |
| **IDA Pro 逆向** | `ida-reverse/` | IDA Pro MCP HTTP 服务器（72 个工具）：反编译、反汇编、数据流追踪、交叉引用 |
| **前端 JS 逆向** | `js-reverse/` | 浏览器端签名定位、加密参数分析、运行时采样、Node 补环境复现；优先用现有 `js-reverse_*`，需要更强的浏览器/CDP/Hook 面时接入 jshookmcp，但前提是先把该 MCP server 下载/注册并启用 |
| **radare2 分析** | `radare2/` | CLI 二进制侦察、反汇编、patch：r2 / rabin2 / rasm2 / radiff2 |
| **CTF 入口** | `ctf-sandbox/` | 单 PRIMARY；下游仍在 sidecar `../CTF-Sandbox-Orchestrator/` |
| **技术文档编写** | `docs-generator/` | 任务完成后自动生成逆向报告、渗透报告、CTF writeup、签名逆向报告 |
| **Evidence 图审查** | `case-review/` | 校验 scope、Evidence→Finding→Path 可追溯性、workitems、timeline 与 artifact hash |
| **浏览器与桌面自动化** | `browser-automation/` | 浏览器操作（Playwright）+ Windows 桌面应用操作（OpenReverse UIA/CUA）+ 网络观察 |
| **跨版本符号迁移** | `binary-diff/` | 有旧版符号迁移到新版、缺 PDB 推导、程序更新后批量迁移函数名 |
| **N-day 补丁差分→利用** | `patch-diff-exploit/` | 从厂商补丁定位漏洞点、写 PoC、N-day 武器化（与 binary-diff 分工：本 skill 偏攻击侧） |
| **RE→利用链** | `pwn-chain/` | 从逆向走到可用 exploit：栈/堆/内核 pwn、pwntools、libc-database、CTF 到真实远程的稳定化 |
| **固件渗透链** | `firmware-pentest/` | OWASP FSTM 九阶段：提取→EMBA 自动化→Firmadyne/QEMU 仿真→AFL

…（截断，全文见来源卡）
