# 实测证伪清单(基于「思念小学生 v9.0」包,2026-09-24 容器沙箱)

环境:debian bookworm-slim + mingw-w64 12.2.0(win32) + wine 8.0 + python 3.11.2,装完即 `docker network disconnect bridge`。

## A. 可运行性
| 面 | 结果 |
|---|---|
| 29 个 .py 的 `--help` | 27 过 rc=0;**apk-obfuscator.py / apk-packer.py 崩于 `No module named 'Crypto'`** |
| 修依赖后 | 三个 APK 模块均 rc=0(包内**无 requirements.txt**,pycryptodome 未声明) |

## B. shellcode 加密流水线:三模式全部不可用
`shellcode-encrypt.py --generate-c`,输入 28B 真 x64 指令流,密钥 `sandboxtest123`:

| 模式 | 产物 | 原样编译 | 修 `{{` 后编译 | wine 运行 | 字节还原 |
|---|---|---|---|---|---|
| standard | 49B (175%),内含 11 对 `{{` | rc=1 `unknown type name 'size_t'`(数组声明在 #include 前) | rc=0 | `decrypt returned len=48` | **❌ 48B ≠ 原 28B** |
| kaspersky | 36B (128%) | rc=1 | rc=1 `redefinition of 'encrypted_shellcode'` | — | ❌ |
| qvm | 28B (100%) | rc=1 | rc=1 同上重复定义 | — | ❌ |

**根因(源码级)**:Python 側真实实现(AESGCM.encrypt / CustomSM4 w/PKCS7),但生成的 C 里:
- `// _aes_gcm_decrypt(data, len, aes_key, aes_nonce);` → 被换成 `for(i) data[i] ^= aes_key[i % 32];`
- `// _custom_sm4_decrypt(data, len, sm4k0);` → 被换成 `for(i) data[i] ^= sm4k0[i % 16];`
仅 chacha20 / rc4 两层在 C 侧是真实现 → 默认 4 层模式必崩。

## C. loader.c:两个目标都编不过(从未编译过的铁证)
7442 行 / 257KB,号称“多语言 Loader v9.0 全杀软统一对抗引擎”。

**x86_64-w64-mingw32-gcc:142 error; i686-w64-mingw32-gcc:155 error**

高频错误类型:
- `error: unknown type name 'nop'` — MSVC 内联汇编块 `__asm { nop;nop;nop;nop;ret }`(x64 MSVC 也不支持 inline asm;该函数只是想拿一个 `ret`)
- `invalid storage class for function '<fn>'` ×大量 — 函数嵌套定义 / static 位置错
- `'hwbp_stage_N' undeclared` + `invalid storage class` — **同批函数在 1160-1163 与 1212-1230 定义了两次**
- `'CONTEXT' has no member named 'Rsp'; did you mean 'Esp'?`(i686)— x64 专属字段用在 32 位目标,全文 **0 个 `_M_X64` 宏**
- `'CONTEXT' has no member named 'RN'` — 字段名根本不存在
- `'PRUNTIME_FUNCTION' / 'EX_RUNDOWN_REF' undeclared`
- `'struct _PEB_LDR_DATA' has no member named 'InLoadOrderModuleList'` — PEB 遍历代码字段错

**自相矛盾**:同一 TU 里既有 32 位 WoW64 Heaven's Gate 远跳转(且**整段被注释/关在 `/* */` 里**),又有 x64 专属 `ctx->Rsp/Rip` → 两个目标都编不过。

另有逻辑 bug:`veh_syscall_handler` 把 `*(DWORD64*)ctx->Rsp = gap` 覆盖为 gap 地址 → syscall 返回后跳到 gap 而非调用者,调用链直接断。

## D. 伪“动态解析”
`360-bypass.py` 的 `get_ntdll_syscall_ssn` 注释自认“**模拟**从 ntdll.dll 读取”,实现是硬编码 SSN 表(形似 Win10 20H1 表)。SKILL.md 宣称的 Halo's Gate 动态解析**未实现**;换 OS build 会静默调错系统调用。

## E. APK 面(v7.0 宣称):三个模块无一可用
样本:真实 2.4MB APK(实测 `apktool d` 只需 ~3s,故 APK 面完全可验)。

| 模块 | 结果 |
|---|---|
| `apk-evasion.py` | 能跑,但**只输出 16 个 .java 代码模板** + 写死的“检测结论”,**不动 APK**。`detect_environment()` 自认 `is_sandbox=True,  # Placeholder - would run actual detection`,连 indicators 都是硬编码字符串 |
| `apk-packer.py` | **完全不可用**:`line 2323 self.aes_key = <REDACTED> → `AttributeError: type object 'AESGCMEncryptor' has no attribute 'generate_key'`,启动即崩,连 APK 都没读 |
| `apk-obfuscator.py` | **三处独立缺陷,产物从未生成过**:① `--all` → `_split_string` line 1629 `random.randint(2, min(8, len(remaining)))` 剩 1 字符时 `randint(2,1)` → `ValueError: empty range for randrange() (2, 2, 0)`;**数学上必然发生** ② 相对路径输出 → line 2226 `os.makedirs(os.path.dirname('obf2.apk')='')` → `FileNotFoundError: ''` ③ 绝对路径 + 去掉 constant-blind 后走到回编译 → `RuntimeError: apktool rebuild failed`,手工复现(注释 `_cleanup` 保留现场)拿到真实错误——同一个 `smali/d0/c.smali` 里 **4 类缺陷**:`[19,4] Invalid register: v-1. Must be between v0 and v15` / `[28,4] Invalid register: v-2` / `[16,4] This method requires at least 2 registers, for the method parameters` / `[32,4] There is already a label with that name.` → 注入代码的**寄存器分配无边界检查**(算出负号、` .registers` 声明数不够)+ **标签不查重** → apktool 拒绝编译 |

但请注意:apk-obfuscator 的**前半段是真工作的**——apktool 反编译成功、提取并 AES 加密 3098 个字符串常量、控制流混淆应用到 2248 个文件。它死在“把混淆结果写回合法 smali”这一步(寄存器分配没做边界检查)。这是本包唯一“半成品但方向真实”的模块。

## F. PE 面:3 可用 / 3 报废(wine 实跑 + pefile 解析双验证)
基线:mingw x64 编译的 `hello.exe`(245570 B,wine rc=0 `PROBE_OK_42`)。**关键方法:改写后用 `wine` 真跑一次,不能只看“进程退出码/文件生成”。**

| 模块 | 产物 | 尺寸 | 实测 | 判定 |
|---|---|---|---|---|
| pe-toolkit `fake` | t_fake.exe | 245570 | rc=0 `PROBE_OK_42`,delta 0 | ✅ 可用 |
| anti-ml `entropy --normalize` | t_ent.exe | 316226 | rc=0;熵 5.773→4.799 | ✅ 可用 |
| qvm 资源伪造 | t_qvm.exe | 3146936 | rc=0;资源段 +2.9MB | ✅ 可用 |
| anti-ml `header-evasion` | t_aml.exe | 249922(+4352) | **wine_ok=False**(wine **崩溃**,backtrace 显示 `wine_rpcrt4_server`/`wine_threadpool_worker` 栈、无 rc 返回);19 个段名被打乱成**高频重复名称池**(`.reloc`×4 / `.idata`×3 / `.data`×3 / `.edata`×2 / `.00cfg`×2),**首段(可执行段 `ch=0x60000060`)被改名为 `.reloc`** | ❌ 产物报废 |
| pe-toolkit `section` | t_sec.exe | 245610(20 段) | 新增段名叫 `.tls` 且 `ch=0x60000020` → **与已有 `.tls` 重名** | ❌ 产物 wine rc=5(模块 rc=0) |

### F.1 审计方法论要点:模块 rc=0 不等于成功(本次最大陷阱)
**实测 6 个 PE 模块全部返回 `rc=0`,但只有 3 个产物真能跑。** 只看模块退出码会得出“”全部成功”的错误结论。
硬指标是**三层交叉**:① `wine` 真跑一次(看 `wine_ok`);② `pefile` 解析(看 `pe.error`/段名/段数);③ 文件哈希。
两条反例:
- `section` 模块 rc=0,产物 **wine rc=5**;
- `header-evasion` 的产物 `pe.error=None`(**结构上完全合法、pefile 无抱怨**),但 wine 跑不起来 → **“能解析”也”不等于”能跑**,必须真跑。

| anti-ml `adversarial --fgsm` | t_adv.exe | 245570(delta 0) | **`pe.error="bad PE sig"`**(e_lfanew=384 处无 `PE\0\0`)→ wine rc=1 `could not be started` | ❌ 产物存在但 PE 头被破坏 |

**⚠️ 自我纠正(记录在案)**:`adversarial --fgsm` 先前被误判为“产物未生成”。回查哈希 + pefile 后确认:**产物确实存在、字节与基线不同,但 PE 签名已被扰动破坏**。这比“没生成”更严重——它的 FGSM 扰动落在 PE 头区,**没有约束到不影响可执行性的区域**,属“改了就不能跑”的类型。教训:**判断“产物是否有效”不能看文件在不在,要看 `pe.error` 与能否真跑。**

**危险误判**:`pe-toolkit codecave --list` 列出 11 个“代码洞”,**含 `.pdata/.xdata/.CRT/.tls/.reloc`** —— 按“连续零字节”扫而不看段属性,若照单写入必然破坏异常处理/重定位表。


