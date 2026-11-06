<!-- archived from /root/.hermes/skills/security/windows-unpacking/SKILL.md on 2026-10-21 -->

---
name: windows-unpacking
description: "Windows自定义壳/分页加密壳脱壳(易语言优先)。触发: 脱壳, unpack, Scylla, 分页加密"
---

> 归档卡：原目录 `/root/.hermes/skills/security/windows-unpacking`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/windows-unpacking/…')`，不要相对 `references/legacy/` 解析。

# Windows Unpacking — Runtime-First Methodology

对**自定义壳/VM壳/分页加密壳**(非 UPX/名牌壳)脱壳,静态硬啃区段效率低;先做运行时三连再决定 dump 策略。

## 1. 壳签名识别(静态,快速)

用 pefile/capstone 自查,命中以下组合 = 自研/VM 类壳,标准脱壳脚本无效:
- 原 `.text/.rdata/.data` 的 **raw size = 0**(文件态无数据,运行时壳填)
- **随机 3 字符区段名**(如 `.41m/.I9o/.CKa`),高熵(≈8.0)大区段 = 加密载荷;一个小低熵区段(0x1000)= 壳配置表
- EP 落在加密区段内(如 `.CKa`);无 Rich header
- 内存 PE 头的 IMPORT/IAT DataDirectory 指向壳区(壳自用仅几个 API);原始 IAT 需从代码引用重建
- VERSION 资源(FileDescription/ProductName)常**不被加密** → pefile 直接读,拿产品身份/作者
- 易语言程序:中文文本是 **GBK**,GBK 扫描才能看到业务字符串(卡密/到期/机器码);ASCII-only 扫描只会看到 KRRN 运行时错误文本

## 2. 运行时三连(脱壳前必做)

**A. 受控运行定性验证形态**(防样本向作者服务器上报本机信息):
```
netsh advfirewall set allprofiles state on
netsh advfirewall firewall add rule name="blk_xxx" dir=out program="<abs path>" action=block
```
跑起来后**枚举窗口控件文本**(pywin32):Button/Edit 是标准控件可直接 GetWindowText(登录/注册/卡密框全暴露);易语言自绘类 WTWindow 标签是 Afx 类无文本。比 OCR 精确。窗口标题流转(信息弹窗→注册→充值)直接揭示验证商业模式。

**B. 防火墙丢弃日志抓 C2 端点**(无需抓包器):
```
netsh advfirewall set currentprofile logging filename <path>
netsh advfirewall set currentprofile logging droppedconnections enable
```
样本连接被 block 后日志记录 `目标IP:端口`。配合样本运行目录**自释放 DLL**(如 RapidJSON/dzHPSocket4C=HPSocket+JSON)可推断协议栈 = custom TCP + JSON。

**C. 内存 dump 诊断解包状态**(ctypes ReadProcessMemory,不必 frida):
dump 全部区段后线性反汇编 .text:
- 能正常反汇编 + GBK 字符串可见 = 原位完整解包 → 直接重建 PE(Scylla fix)
- **只有开头几千条指令就断、区段大部分非零但不可解码、熵 6-7** = 疑似分页加密/执行后重加密,静态 dump 是诱饵 → 不能直接 dump 收工
- 实证手段:**EIP 采样**(OpenThread+SuspendThread+GetThreadContext 轮询分类落点)。大量 EIP 落在 .text 但 dump 不可解码 → 确认 paged-code 壳,需 hook 解密函数/主动转储,或走动态 patch 路线

## 3. 工具链与坑

- **x64dbg release 自带 Scylla.dll**(x32/Scylla.dll 与 x32dbg.exe 同目录自动加载),dump+IAT 重建主路径;pe-sieve 单 exe 下载常被墙,本地 Scylla 优先
- GUI 自动化:background 合成点击对 x32dbg 工具栏常无效且窗口会移动 → 坐标要每次 capture 后现取;纯脚本路线(ctypes dump + 自建 IAT)更可靠
- **frida 17 API 迁移**(旧教程全是旧 API):
  - `Module.findExportByName/getGlobalExportByName` 已废;用 `Process.getModuleByName('kernel32.dll').getExportByName('WinExec')`
  - `frida.spawn()` gating 下易卡死 → **先正常启动进程再 `frida.attach(pid)`**
  - 逐字节读用 `ptr.add(i).readU8()`;Memory.readByteArray 行为已变
- Windows OCR(pip install winsdk,Windows.Media.Ocr,需中文语言包):路径必须**反斜杠绝对路径**(正斜杠报 path invalid);ddddocr 只对验证码有效,UI 截图几乎空输出;PowerShell 5.1 WinRT 投影坏,用 winsdk Python
- **RVA→VA 算术双检**:0x400000+0x295000=0x695000(勿算成 0x4295000);"数据区没解包"假结论常来自地址算错,先验 m.base+m.size 边界

## 4. 深挖案例

易语言卡密+账号双验证软件全流程案例(签名、防火墙日志、分页加密判定、产物清单)见 references/yi-language-custom-packer-case.md
