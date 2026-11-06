### 15.1 .NET 混淆技术全景

.NET 因元数据丰富、IL 字节码易反编译,成为混淆保护重灾区。主流混淆技术:

- **符号重命名**:将类/方法/字段名替换为零宽字符或 `a`/`b`。ConfuserEx 支持可重用名(Reusable)与不可重用名(Non-Reusable),后者逆向更难。
- **控制流混淆**:线性 IL 转为状态机或跳转表,插入垃圾指令。ConfuserEx 用 switch 扁平化,Eazfuscator.NET 用不可约循环。
- **字符串加密**:明文字符串替换为 `decryptor(int token)` 调用,运行时反射还原。ConfuserEx 用 XOR/AES,密钥与 MethodDef token 绑定。
- **防篡改/防调试**:ConfuserEx 的 Anti-Tamper 通过 MD5 校验方法体完整性;Anti-Debug 调用 `IsDebuggerPresent`、检测 `PEB.BeingDebugged`。
- **代码虚拟化**:.NET Reactor 的 Necrobit/JEOPARDY 将方法体替换为 native stub + 自定义 VM 指令,由 native 解释器执行。
- **元数据损坏**:破坏 `#Strings`/`#US` 堆偏移,使 dnSpy/ILSpy 反编译失败但 CLR 仍能加载(dnlib 需设 `MetadataFlags` 修复)。

2026 年趋势:.NET 8/9 的 NativeAOT 将 IL 直接编译为原生机器码,产出不含元数据的本地可执行,传统 dnSpy/ILSpy 完全失效,需 IDA Pro/Ghidra 配合调用约定推断。但 AOT 不支持运行时反射,商业软件仍以 CoreCLR + 混淆为主流。

| 保护器 | 符号重命名 | 控制流混淆 | 字符串加密 | 防篡改 | 代码虚拟化 | 元数据损坏 | 典型特征 |
|--------|-----------|-----------|-----------|--------|-----------|-----------|----------|
| **ConfuserEx 2.0** | 强(Unicode) | switch 扁平化 | XOR+token | MD5 校验 | 否 | 否 | 开源、`[ConfuserEx]` 属性 |
| **Eazfuscator.NET** | 强 | 不可约循环 | AES | 弱 | 否 | 否 | 商业、配置简洁 |
| **.NET Reactor** | 中 | 中 | 强 | 强 | Necrobit/JEOPARDY | 是 | license.rptc |
| **dnGuard** | 中 | 中 | 中 | 强 | native VM | 是 | native wrapper |
| **Babel.NET** | 强 | switch | XOR | 强 | 否 | 部分 | 商业 |
| **SmartAssembly** | 中 | 中 | XOR | 强 | 否 | 否 | Red Gate |

### 15.2 ConfuserEx 逆向

**de4dot 通用反混淆器**是 .NET 逆向标准起点,内置 30+ 种保护器特征识别,自动还原符号、解密字符串、简化控制流:

```bash
de4dot target.exe                  # 自动检测保护器类型,输出 target-cleaned.exe
de4dot -p confuserex target.exe    # 手动指定类型:confuser/eazfuscator/reactor/smartassembly
de4dot --symbolmap map.xml target.exe   # 生成符号映射文件,便于交叉引用
```

**字符串解密**有两条路径:de4dot 内联模拟(拷贝解密方法体模拟执行)与基于 dnlib 的手动提取(适用于 de4dot 未识别的自定义解密器):

```csharp
// dnlib 字符串解密示例:定位解密方法并内联还原
using dnlib.DotNet;
using dnlib.DotNet.Emit;

var module = ModuleDefMD.Load("target.exe",
    new ModuleCreationOptions { MetadataOptions = new MetadataOptions(false) });

// 标记疑似解密方法(特征:静态、接收 int token、返回 string)
var decryptors = module.Types.SelectMany(t => t.Methods)
    .Where(m => m.IsStatic && m.MethodSig.RetType.FullName == "System.String"
        && m.Parameters.Count == 1 && m.Parameters[0].Type.FullName == "System.Int32")
    .ToList();

foreach (var type in module.Types)
    foreach (var method in type.Methods)
        if (method.HasBody)
            foreach (var instr in method.Body.Instructions)
                if (instr.OpCode == OpCodes.Call && decryptors.Contains(instr.Operand))
                {
                    var prev = instr.Previous;
                    if (prev?.OpCode == OpCodes.Ldc_I4)
                    {
                        int token = prev.GetLdcI4Value();
                        string plain = InvokeDecryptor(instr.Operand as MethodDef, token);
                        instr.OpCode = OpCodes.Ldstr;   // 替换为明文 ldstr
                        instr.Operand = plain;
                        prev.OpCode = OpCodes.Nop;
                    }
                }
module.Write("target-decrypted.exe", new ModuleWriterOptions(module) { WritePdb = true });
```

**控制流反混淆**:ConfuserEx 的 switch 扁平化可被 de4dot 模式匹配还原(识别 `switch(num)` + 数字映射表)。**Anti-Tamper 绕过**:de4dot `--keep-types` 移除 anti-tamper 模块,或手动 patch `ModuleInitializer` 跳过校验调用。

### 15.3 .NET Reactor 代码虚拟化对抗

.NET Reactor 的 **Necrobit** 将方法体替换为 native stub,真实 IL 加密存储在资源段,运行时由 native 代码解密并交予 JIT。标准反编译器只看到空壳。

对抗路径:
1. **Reactor Slayer / devirtualizer**:开源工具针对早期版本,定位加密资源并调用内置解密器还原 IL;对 Reactor 7.x+ 效果有限。
2. **内存 dump 法**:在 dnSpy 调试器中运行,在目标方法首次被调用后(IL 已解密并交给 JIT),于 `clr.dll!compileMethod` 下断点,dump `CORINFO_METHOD_INFO` 中 ILCode 指针指向的内存。
3. **JEOPARDY 绕过**:JEOPARDY 将 IL 转为自定义虚拟指令集,需逆向解释器逻辑,建立虚拟 opcode 到 CIL 的映射表(类似 VMProtect 脚本分析),可借助 ReactorDeobfuscator 结合动态 trace。

Reactor 版本识别要点:`.rsrc` 节含 `RT_RCDATA` 资源名为 `ReactOr` 或数字 ID;导入表含 `mscoree.dll` 的 `_CorExeMain`;license 文件 `license.rptc` 可用于版本判定。对 Reactor 9.x+ 的 Necrobit,需在 `clr!JIT_MethodBarrierComp` 回调后 dump,此时 IL 已解密。



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-15-net-confuserex-eazfuscator-dng-02.md")`