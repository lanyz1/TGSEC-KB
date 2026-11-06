---
name: evasion
description: >-
 测绘引擎·Skill: 对抗规避（Evasion）
---

# Skill: 对抗规避（Evasion）

## 适用场景

授权目标遭遇以下情况时使用本 Skill：
- WAF / CDN 拦截 payload（403/406/444/503）
- 扫描器被封 IP / rate-limit（**换出口**先读 `本机IP被封换出口代理.md`，不要 SSH 用户主机）
- 怀疑目标是蜜罐/沙箱
- 需要伪装 UA / 请求头绕过指纹检测
- Tsecbench 对抗规避题型

## 工具

```
tools/evasion-kit/evasion.py
```

## 快速命令

```bash
# 生成随机 UA 池
python3 tools/evasion-kit/evasion.py ua-pool --count 5

# payload 编码变体（cloudflare/aliyun/safedog/safeline/generic）
python3 tools/evasion-kit/evasion.py encode \
 --payload "<payload>" --waf cloudflare

# 在授权目标逐一测试哪些变体能过 WAF
python3 tools/evasion-kit/evasion.py matrix \
 --url https://TARGET/search \
 --payload "' OR 1=1--" \
 --param q --waf cloudflare \
 --case CASE --delay-ms 800

# 蜜罐/沙箱检测
python3 tools/evasion-kit/evasion.py sandbox-detect \
 --url https://TARGET --case CASE
```

## 决策树

```
WAF 拦截
 │
 ├─ cloudflare (cf-ray 头)？ → --waf cloudflare + chunked/dots 变体
 ├─ 阿里云盾 (ali-swift 头)？ → --waf aliyun，unicode %u0027
 ├─ SafeLine？ → --waf safeline，multipart Content-Type
 ├─ 通用签名拦截？ → double-url-encode / newline-inject
 └─ 全部被拦？ → 换慢速时序 --delay-ms 3000 + UA 轮换

蜜罐怀疑（sandbox-detect）
 ├─ verdict: suspicious → 降低侦察烈度，收窄发包频率
 └─ verdict: clean → 正常推进
```

## 编码矩阵说明

| 变体标签 | 原理 | 典型绕过 WAF |
|---------|------|-------------|
| url-encode | `%27` | 基础 |
| double-url-encode | `%2527` | 二次解码 WAF |
| url-encode-upper | `%27` 大写 | 大小写不敏感签名 |
| fullwidth | `＇` | 语义匹配型 WAF |
| comment-insert | `se/**/lect` | MySQL 注入 |
| newline-inject | `%0a` 替换空格 | 正则换行盲点 |
| case-mix | `SeLeCt` | 大小写不敏感签名 |
| html-entity/decimal/hex | `&#60;` | XSS WAF |
| cf-chunk-header | chunked 分块 | Cloudflare |
| aliyun-unicode | `%u0027` | 阿里云盾 |

## 与其他 Skill 联动

- bypass 命中 → 用变体进 `sqlmap-tamper-kit` 或 `payment-callback-forgery`
- sandbox 检测 → 若 suspicious 先整理 triage，降优先级
- WAF 类型先用 `waf-detector` Skill 识别，再来本 Skill 选变体

## 证据落盘

```
exports/bot-recovery/<案卷>/测绘/evasion/
 bypass_matrix.json
 sandbox_detect.json
```

## 真源

- 手法：`docs/playbooks/对抗规避手册.md`
- 工具：`python3 tools/evasion-kit/evasion.py --help`
- 主机免杀 / 特征清理（不是 WAF）→ `docs/playbooks/免杀与特征清理手法.md` · `sig_cleanup_scan.py`


---

## 外部库增量（2026-10-11 分享包）

## Scripts

- `scripts/packer.py` -- XOR/AES/gzip/b64 layered payload packing + stub generation
- `scripts/obfuscator.py` -- Python/PS code obfuscation, string splitting
- `scripts/amsi_bypass.py` -- AMSI/ETW bypass techniques (PS/C#/memory patch)

## 打法: 打 EDR 自身(免杀/提权新角度)

落地 Windows 主机遇 EDR,除"绕过"外可审计 **EDR 自身特权功能当提权/防御关闭跳板**。2026-09 匿名研究员 Nightmare Eclipse 批量放出 EDR/杀软 0day LPE:
- **FalconFlank**(CrowdStrike Falcon,未分配 CVE): 滥用 Falcon 的 Office 恶意宏清除功能(File Suspicious Macro Removal)→ 在最新 Win11 25H2/Server 2025 + Falcon 上直接起 SYSTEM cmd;官方缓解 = 关该策略
- 同批: **HardBreacher**(Kaspersky Endpoint)、**PrettyPrague**(GenDigital Avast) LPE;Kevin Beaumont 已确认可用
- **坑**: 官方出 PoC 后 EDR 厂商会立刻加检测——自测要么加白名单、要么**混淆 PoC + 换 dll load 手法**
- 通用检查面: 目标机 EDR 的宏清除/隔离/回滚/修复类"补救"功能常以高权限(甚至 SYSTEM)执行用户可控输入 → 先查这些功能的策略开关与 DLL 加载路径,再看目标二进制
- 来源: https://www.bleepingcomputer.com/news/security/new-crowdstrike-falconflank-zero-day-grants-system-privileges/

## 浏览器 Cookie/密码提取的免杀链路(密钥-数据-解密三分离)
内网个人主机(运维浏览器里存着堡垒机/云平台/OA/企业面板凭据)是常规目标,但直接跑 Chromium 凭据提取器基本被 EDR(360/火绒/深信服)拦。2026-09 实战方案 BrowserDataOut(FreeBuf/国家网络空间安全云社区,作者 AabyssZG)把链路拆成 3 个可独立过杀软的 Go 工具:

1. **BrowserKeysDump(取密钥)** — 用户数据目录 `Local State` 的 `os_crypt` 字段:
   - `v10` → `encrypted_key`,去 `DPAPI` 前缀 → `CryptUnprotectData` → 32B AES-256 主密钥
   - `v20`(Chrome/Edge 127+,App-Bound Encryption) → `app_bound_encrypted_key`(前缀 `APPB`);先 **SYSTEM 身份 DPAPI** 解一层(entropy = chrome.exe 路径哈希,由 Google Update 提升服务做),再当前用户 DPAPI → 尾部 `[安装路径][flag][12B IV][密文][16B tag]`,flag=1 AES-256-GCM(key 硬编码在 `elevation_service.exe`)/ flag=2 ChaCha20
   - **坑**: v20 必须在浏览器进程内走 IElevator COM(反射式注入)→ 免杀最易被点名的环节;目标只有 v20 时优先"注入 + 混淆",或改走 v10 老版本/其他 Chromium 分支(360/QQ 浏览器)
2. **BrowserDataCopy(取数据)** — 运行中浏览器对 `Cookies`/`Login Data`(SQLite)加独占锁 → **复制文件而非读库**(句柄/卷影类手法),避免 open+read 触发 EDR 文件访问规则
3. **BrowserDataRestore(离线解)** — 只需 keys.json,在**分析机**解 `v10‖12B nonce‖密文+16B tag`(AES-256-GCM) → 分类 JSON

- 可迁移设计要点: **密钥与数据分离采集、解密异地完成** —— 目标机上只表现"读两个文件",全程不出现解密/明文凭据行为,EDR 行为链与落盘取证都难有落点;前提是 DPAPI 只绑"机器+用户"**不区分同用户下的进程**(任何同身份程序都能解主密钥)
- 实战口径: 密码侧有 2FA 时 Cookie 是唯一活路(拿 Cookie 绕 2FA);提取后建议先本地验证 session 有效性再用
- 来源: https://www.freebuf.com/articles/endpoint/500407.html
