### 15.4 dnGuard 与 x64 native 保护

**dnGuard** 将整个 .NET 程序集封装在 native loader 中(EXE 入口为机器码),运行时解密并加载到内存,CLR 通过 hosting API 启动。程序集仅在内存中以明文存在短暂时间。

对抗核心:Hook `mscorlib` 的 JIT 编译入口拦截 IL 编译,从而拿到所有方法的明文 IL:
- **Hook mscorjit.dll!compileMethod**:JIT 编译每个方法时,`ICorJitCompiler::compileMethod` 接收 IL,在此处 dump 即可获取全部 IL。
- **MegaDumper / extremeDumper / Process Hacker**:运行后扫描内存 `.NET MetaData` magic(PE 头 + `BSJB` 元数据签名),dump 出完整 assembly,再修复 PE 头与元数据偏移。

```bash
extremeDumper.exe          # GUI,选目标进程右键 dump .NET modules
MegaDumper.exe /dump:pid=1234 /out:C:\dumps
MetaFix.exe dumped.dll     # 修复 dump 后损坏的元数据偏移
```

### 15.5 实战脱壳工作流

| 步骤 | 任务 | 工具 | 关键技巧 |
|------|------|------|----------|
| 1 | 识别保护器 | Detect It Easy、PEiD | 检查 PE 节名、字符串特征、导入表 |
| 2 | 选择工具 | 依据 15.1 表格 | ConfuserEx→de4dot;Reactor→Reactor Slayer;dnGuard→MegaDumper |
| 3 | 静态反混淆 | de4dot、ConfuserEx.Protections | `de4dot -p` 指定类型,生成 cleaned 文件 |
| 4 | 动态 dump | dnSpy 调试器、MegaDumper | 在 `compileMethod` 断点或内存扫描 BSJB |
| 5 | IL 修复 | MetaFix、dnlib | 修复元数据偏移、还原 `#Strings`/`#US` 堆 |
| 6 | 反编译 | dnSpy、ILSpy、dotPeek | dnSpy 支持调试与编辑;ILSpy 命令行批量 |
| 7 | 还原符号 | de4dot symbolmap、手动 | 利用字符串引用、调用图辅助命名 |

---



---
📖 本切片 2/2 结束。 本章节结束。