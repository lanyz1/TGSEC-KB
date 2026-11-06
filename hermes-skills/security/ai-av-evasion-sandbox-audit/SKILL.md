---
name: ai-av-evasion-sandbox-audit
description: Use when 审计AI生成的免杀工具包:沙箱隔离验证与证伪。
---

# AI 生成免杀工具包的沙箱审计

TG/网盘流传的免杀包(如「思念小学生」v9.0 系列)普遍特征:**SKILL.md 吹得极满(全杀软对抗/一键免杀编译器/多语言Loader),实际代码是 LLM 逐块生成后从未编译或运行过一次**。本卡给出可复现的证伪流程与已验证的缺陷模式。

## 0 触发
用户丢来免杀/EDR绕过/AV对抗工具包 + 「沙箱运行」「学习一下」「看看真假」。

## 1 铁律
1. **先隔离再运行**:Docker + 断网 + 只用副本。包里常有 `anti-forensics.py`(`wevtutil cl` / `net stop` / 删文件)这类真破坏性代码,本机跑=自残。
2. **不信文档,只认工具输出**。SKILL.md 的版本号/功能清单为零证据。
3. **不许替它背书**:能跑通的子集 + 明确的坏点,都要报。

## 2 沙箱配方(Windows 宿主 + Docker Desktop)
见 `references/sandbox-recipe.md`(可整段复制执行)。要点:
- `docker run -d --name avsb -v <abs>/sb:/sb debian:bookworm-slim sleep infinity`
- 宿主代理会污染容器 apt → **用 http 清华源**,不要 https(容器缺 CA 直接 "certificate issuer unknown")
- apt 一个包名不存在会**整批失败**(如 `python3-androguard` 不在 bookworm)→ 先 `apt-cache policy` 查,或分开装
- 需要: `python3 mingw-w64 wine64 file xxd zip unzip`;APK 面加 `apktool default-jre-headless` + `pip3 install --break-system-packages pycryptodome pefile`
- **装完立刻断网**:`docker network disconnect bridge avsb`

## 3 三件套验证法(核心)
对每个脚本/产物做三层,别停在 --help:

**① 可运行清单**:`for f in *.py; do python3 $f --help; done` 记 rc 与 usage。缺 Python 依赖的会 import 就崩(本包 29 个脚本 27 过 / 2 崩在 `No module named 'Crypto'`)。

**② 生成物语法/语义验证**:生成器(生成 C/Java/smali)要**真编译一次**。`gcc -c` / `javac` 一跑就露馅——本包生成的 C 里带 11 对 `{{`(Python 模板残留)且数组声明在 `#include` 之前,直接编不过。

**③ round-trip 差分实验**(最有说服力):
- 构造已知输入的**真** shellcode/PE(`printf` 出 x64 指令流;PE 用 `x86_64-w64-mingw32-gcc` 编个打印标记的探针)
- 跑转换 → 编译生成的解密器 → `wine64` 里执行 → **与原字节 `cmp`**
- 关键技巧:**先修掉表层语法错(如 sed 's/{{/{/g')再跑**,才能把"语法坏"和"算法坏"两个缺陷分离证明。本包 standard 模式修语法后能编译运行,但解出 48B ≠ 原 28B,证明解密逻辑本身是桩。

**PE 侧另加**:产物用 `file`/pefile 解析段表+入口点+`z.testzip()` 校验,再在 wine 里跑一次看**功能是否保持**(打印标记是否还在)。

## 4 已证伪的典型缺陷模式(照单排查)
详见 `references/verified-defects.md`。高频模式:
1. **加密真、解密桩**:Python 侧真 AES-GCM/SM4,生成的 C 里变成 `data[i] ^= key[i%len]` 循环异或 → loader 必崩。
2. **模板残留**:`{{`/`}}`、占位符未替换、数组在 include 前。
3. **多模式共用生成器却重复定义**(`redefinition of 'encrypted_shellcode'`)。
4. **硬编码"动态"数据**:函数叫 `get_ntdll_syscall_ssn` 但注释自认模拟,实际是硬编码 SSN 表 → 换 OS build 静默调错 syscall。
5. **假检测**:`is_sandbox=True,  # Placeholder - would run actual detection`,连 indicators 都是写死的字符串。
6. **不存在的成员/方法**:`AESGCMEncryptor.generate_key()` 未定义 → 对象构造即崩。
7. **PE 改写无视段属性**:把 `.pdata/.reloc/.tls/.CRT` 当代码洞/重命名 → 产物报废。
8. **随机区间空崩**:`random.randint(2, min(8, len(remaining)))` 剩 1 字符时 `randint(2,1)` → ValueError(所以 `--all` 必崩,先试最小 flag 组合)。
9. **平台自相矛盾**:同一 TU 里既有 MSVC `__asm{}`(x64 不支持)又直接用 `ctx->Rsp`(x64 专属字段)且无 `#ifdef` → 两个目标都编不过。编译报错统计(x64 142 / i686 155 error)就是"从未编译过"的铁证。

## 5 后门审计(转发包必做)
在判定"能否用"之前先判"是否安全":grep TG bot token(`[0-9]{8,12}:[A-Za-z0-9_-]{30,}`)、私钥头、AWS key、非内网公网 IP、`socket`/`requests.post`、大量 base64 块、Startup/RunOnce 写入。
- 注意区分:模块**声明功能**里的外联(公共 DoH、example.com 占位、C2 伪装域模板)≠ 作者夹带。
- 本包结论:干净,无 token/无隐藏 C2/无外带——风险全在内容本身。

## 6 Pitfalls
- **Debian 的 pycryptodome 模块名是 `Cryptodome`**,脚本要 `Crypto` → 必须 pip 装 pycryptodome。
- `wine64` 在 Debian wine 8.0 里可能不存在 → 做 `exec /usr/bin/wine "$@"` 的 compat shim;跑 32 位 PE 还需 `dpkg --add-architecture i386` + `wine32:i386`。
- apktool 反编译真实 APK **很快**(2.4MB 约 3s),不要因为慢就放弃 APK 面验证。
- 容器里没有 `ps`(procps),排查 apt 用 `du -sb /var/cache/apt/archives/partial` 测速。
- 报告要给**精确坐标**(文件:行号)+ 原始字节,别只说"不可用"。

## 7 汇报模板
1) 沙箱是否真隔离(断网证据) 2) 可运行清单(过/崩) 3) 每个关键模块:**编译/运行/还原**三态结论 + 证据指针 4) 后门审计结论 5) 技术矩阵(值得学的部分) 6) 精确坏点清单(文件:行号) 7) 诚实总评:能学什么、不能用什么、要不要修。
