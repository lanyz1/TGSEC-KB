## 1. AI辅助逆向工程 — 2026核心战场

2026年AI辅助逆向已从实验阶段进入生产实用阶段。LLM与反编译器的深度集成形成语义增强、代码解释和漏洞检测三大应用类别。

### 1.1 Ghidra AI插件生态

**GhidrAssist** — 将Ghidra直接连接到LLM API（OpenAI/Anthropic/Ollama本地模型），对当前选中函数进行上下文分析。核心优势：不将整个二进制反编译结果灌入提示词，而是构建聚焦查询——包含目标函数、直接调用者/被调用者、相关字符串引用。

```bash
# 安装GhidrAssist
git clone https://github.com/unkmc/GhidrAssist.git
cp -r GhidrAssist $GHIDRA_INSTALL_DIR/Extensions/Ghidra/
# 重启Ghidra → File > Install Extensions启用
```

**GEPETTO** — 最早的生产级Ghidra AI插件，专注函数解释和批量重命名。可将 `FUN_00401000` 标签转化为 `decrypt_config_buffer` 或 `parse_c2_response` 等有意义名称。对常见模式（文件I/O、网络操作、加密例程）准确率超80%。

**VulChatGPT** — 扩展GEPETTO概念，专注漏洞识别。分析反编译函数中的常见漏洞模式（缓冲区溢出、整数溢出、UAF、格式化字符串、竞态条件），生成结构化报告：漏洞类型、受影响行、严重程度估计、利用难度。分析2000个函数的二进制时，自动首轮标记50个最可疑函数可节省数天人工审查。

**PyGhidra** — 允许以Python库方式运行Ghidra分析引擎无需启动GUI，对构建自动化管道具有变革性意义：

```python
# PyGhidra自动化分析管道
import pyghidra
from pyghidra import GhidraProject

with GhidraProject.open("target_binary") as project:
    program = project.program
    fm = program.getFunctionManager()
    
    # 遍历所有函数，自动重命名
    for func in fm.getFunctions(True):
        if func.getName().startswith("FUN_"):
            decompiled = project.decompile(func)
            # 发送给LLM分析
            analysis = llm_analyze(decompiled)
            if analysis.confidence > 0.8:
                func.setName(analysis.suggested_name)
```

### 1.2 Binary Ninja Sidekick

Vector 35将AI功能直接集成到平台。Sidekick提供上下文感知的交互式聊天界面，知道当前查看的函数、当前选择的内容、已执行的分析。Binary Ninja的类型传播引擎直接馈入AI上下文，模型不仅看到原始反编译代码，还看到恢复的类型、结构和枚举值：

```python
# Binary Ninja Sidekick自动化脚本
from binaryninja import BinaryViewType
bv = BinaryViewType.get_view_of_file("/path/to/binary")
for func in bv.functions:
    if func.name.startswith("sub_"):
        analysis = bv.query_sidekick(
            f"Analyze function at {hex(func.start)} and suggest a name"
        )
        if analysis.confidence > 0.8:
            func.name = analysis.suggested_name
```

### 1.3 IDA Pro AI集成

**BinaryAI** — 使用基于嵌入的相似性搜索，将函数与已知开源代码数据库匹配。计算函数控制流图和数据流模式的向量嵌入，在索引语料库中搜索相似函数。擅长识别静态链接的库函数（zlib、OpenSSL、SQLite）。

**IDAssist** — IDA Pro插件，将LLM驱动的分析直接集成到IDA界面，支持可配置的LLM提供商、语义知识图谱、RAG文档搜索。基于Python和PySide6构建，作为可停靠面板在IDA Pro 9.0+中运行。

**DAILA** — 反编译器无关的AI交互插件，基于BinSync库LibBS抽象反编译器差异。支持IDA、Ghidra、Binja和angr-management。集成两种AI系统：OpenAI和VarBERT。

### 1.4 HELIOS — 学术前沿(NDSS 2026)

**HELIOS**（Hierarchical Graph Abstraction for Structure-Aware LLM Decompilation）提出层次化图抽象方法。第一阶段使用Ghidra无头分析器提取丰富制品：反编译器的C/C-like伪代码、控制流图、数据流信息。设计工具无关，可基于其他分析框架实现。

### 1.5 基础工具链

```python
# Capstone反汇编 + Unicorn仿真 + Keystone汇编
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from keystone import Ks, KS_ARCH_X86, KS_MODE_64

# 反汇编
CODE = b"\x55\x48\x89\xe5\x48\x83\xec\x10\x89\x7d\xfc"
md = Cs(CS_ARCH_X86, CS_MODE_64)
md.detail = True
for insn in md.disasm(CODE, 0x1000):
    print(f"0x{insn.address:x}:\t{insn.mnemonic}\t{insn.op_str}")

# Unicorn仿真执行
uc = Uc(UC_ARCH_X86, UC_MODE_64)
uc.mem_map(0x1000, 0x1000)
uc.mem_write(0x1000, CODE)
uc.emu_start(0x1000, 0x1000 + len(CODE))
```

### 1.6 AI逆向工具对比

| 工具 | 平台 | 核心能力 | LLM支持 | 适用场景 |
|---|---|---|---|---|
| GhidrAssist | Ghidra | 函数上下文分析 | OpenAI/Anthropic/Ollama | 通用逆向分析 |
| GEPETTO | Ghidra | 批量函数解释重命名 | OpenAI | 大型二进制快速标注 |
| VulChatGPT | Ghidra | 漏洞模式识别 | OpenAI | 漏洞挖掘加速 |
| Sidekick | Binary Ninja | 交互式AI对话+类型感知 | 内置 | 精细化分析 |
| BinaryAI | IDA Pro | 函数相似性搜索(嵌入) | 专有模型 | 库函数识别 |
| IDAssist | IDA Pro 9.0+ | 语义知识图谱+RAG | 多提供商 | 复杂目标分析 |
| DAILA | IDA/Ghidra/Binja/angr | 跨平台AI交互 | OpenAI/VarBERT | 多工具工作流 |
| PyGhidra | Python(无头) | 自动化管道 | 可选 | CI/CD集成 |

---

