## 21. 二进制差分与补丁分析 — Diaphora/BinDiff/DarunGrim

### 21.1 二进制差分技术原理

二进制差分(Binary Diffing)是逆向工程中用于对比两个二进制文件差异的核心技术,其根本目标是在剥离符号表、经历编译器优化与地址重排后,仍然能够识别出"逻辑等价"或"高度相似"的代码块。差分的结果常用于补丁逆向(定位 CVE 修复点)、恶意软件变种溯源、固件版本对比以及漏洞 1day 分析。

- **Basic Block Matching(基本块匹配)**:基本块是差分的最小单元,匹配策略包含三层。第一层是 hash 匹配,对基本块内指令字节序列(或归一化后的助记符序列)计算哈希,如 MD5/SHA-1/FNV,哈希相同则视为同构;第二层是结构匹配,在哈希失效时比较指令数量、操作数类型、跳转目标数等拓扑特征;第三层是松弛匹配,允许少量指令差异(如立即数变化),用于检测补丁修改的微小变化。
- **Function Matching(函数匹配)**:在基本块匹配之上进行函数级对齐。CFG 同构是比较两个函数的控制流图是否同构(忽略节点地址);名称匹配利用导出表、PDB 残留符号、RTTI 类名进行精确匹配;调用图匹配(Call Graph Matching)将函数作为节点、调用关系作为边,在全局调用图上做近似同构匹配,从而定位"调用结构相似但内部略有改动"的函数。
- **Algorithm categories**:graph isomorphism(图同构,BinDiff 采用的 Bellman-Ford 变种与 Hungarian 算法组合)、hash-based(DarunGrim 的指令指纹)、symbolic execution-based(对基本块做符号执行后比较约束求解结果,精度高但开销大)。业界主流工具多以图同构 + 哈希混合策略,在精度与速度间取得平衡。
- **应用场景**:补丁差异分析(Patch Tuesday 逆向还原 CVE)、恶意软件变种分析(同族不同版本的 C2 协议演变)、固件版本对比(IoT 路由器固件差异定位新漏洞)、1day 漏洞利用开发(已知 CVE 但无 PoC 时,通过差分还原漏洞触发路径)。

### 21.2 工具对比矩阵

| 工具 | IDA集成 | 跨平台 | 算法 | 免费开源 | 2026维护状态 |
|------|---------|--------|------|----------|--------------|
| BinDiff (Google→Zynamics) | 原生插件 | Linux/macOS/Windows | Graph isomorphism + Hungarian | 非开源(免费) | 活跃,Ghidra/Binary Ninja 支持 |
| Diaphora | IDA 脚本 | 全平台(依赖 IDA) | 多算法混合(Best/Partial/Unreliable) | 开源(GPLv3) | 活跃,社区驱动 |
| DarunGrim | IDA 插件 | Windows 优先 | 指纹哈希 + CFG | 开源 | 维护缓慢 |
| TurboDiff | IDA 插件 | Windows | Corelan 团队,匹配策略偏补丁 | 免费 | 基本停更 |
| BinSlayer | 独立 | Linux | 基于 NetworkX 图匹配 | 开源 | 学术原型 |
| BinDiff 2 (Ghidra fork) | Ghidra | 全平台 | 同 BinDiff 内核 | 开源 | 2026 社区维护 |

选型建议:常规补丁逆向首选 BinDiff(精度高、IDA 集成好);需要自动化批处理或自定义匹配策略时选 Diaphora;学术研究或定制图算法可用 BinSlayer;纯 Ghidra 工作流可考虑 BinDiff 2 社区版。

### 21.3 BinDiff实战 — 补丁差异分析

```bash
# BinDiff命令行使用
bindiff --primary=original.exe --secondary=patched.exe --output_dir=results/

# BinDiff导出: 比较结果可视化
# 在IDA Pro中:
# 1. File → BinDiff → Diff Database
# 2. 选择原始二进制和补丁二进制
# 3. 查看匹配/不匹配的函数
# 4. 重点分析 "unreliable match" 和 "no match" 的函数
```

BinDiff 的工作流是"先建库再比对"。对每个二进制先用 `binexport` 工具(或 IDA 插件)导出 `.BinExport` 数据库,包含函数、基本块、指令、调用图结构;再用 `bindiff` 比较两个数据库,生成 `.BinDiff` 结果文件。比较结果分为四类:**Matched**(高可信同构)、**Reliable Match**(部分指令差异)、**Unreliable Match**(仅结构相似)、**No Match**(新增/删除函数)。

分析补丁时的核心策略:先按相似度排序,跳过完全匹配的函数(占 90% 以上),聚焦 Unreliable Match 与 No Match 函数。在 IDA 中双击结果项可同步显示两个版本的 CFG 并排视图,修改的基本块会高亮。**从补丁还原漏洞的关键逻辑**:补丁通常只修改漏洞触发路径上的少量代码,因此差分定位的修改点即为漏洞点;通过对比修改前后的边界检查、长度校验、指针运算,可推断出原始漏洞类型(越界读写、整数溢出、UAF 等)。

2026 年趋势:Microsoft Patch Tuesday 逆向已高度自动化,开源项目(如 PatchDiffFlow、DiffDump)结合 BinDiff 结果与 LLM 自动生成漏洞类型推测报告,将单个 CVE 的逆向时间从数小时压缩到分钟级。

### 21.4 Diaphora实战

Diaphora 是目前最活跃的开源差分工具,以 IDA Python 脚本形式分发,支持 SQLite 数据库导出与多种匹配策略。

```bash
# IDA中执行Diaphora脚本
# 1. 打开original.exe, 执行Diaphora → Export Database
# 2. 打开patched.exe, 执行Diaphora → Export Database  
# 3. 执行Diaphora → Diff Database 选择两个.dsqlite文件
# 4. 查看Best Match/Partial Match/Unreliable Match/No Match
```

匹配结果分类与含义:
- **Best Match**:高可信度匹配,通常名称、CFG、调用关系三者一致,可视为完全相同的函数,跳过即可。
- **Partial Match**:CFG 相似但非同构,存在指令增删或基本块重排,需人工核对差异指令,这类函数往往是补丁修改的目标。
- **Unreliable Match**:仅调用结构或粗粒度特征相似,可信度低,需结合上下文判断是否为对应函数。
- **No Match**:新增或删除的函数,是补丁引入新功能或删除旧逻辑的关键证据。

Diaphora 支持导出 JSON/CSV 结果,便于自动化分析。典型脚本流程:批量导出多个补丁版本的 `.dsqlite`,用 Python 脚本循环比对,提取所有 Partial/No Match 函数名,生成差异清单。对于无符号二进制,Diaphora 的"Best Match by MD Index"能基于函数调用图拓扑指纹进行匹配,有效缓解符号缺失问题。

### 21.5 恶意软件变种分析

同族恶意软件不同版本间的差分是威胁情报生产的核心手段。典型流程:收集同族样本(按 YARA 族规则或家族名聚类)→ 对核心模块逐版本差分 → 提取功能变化。重点关注四类变化:**核心功能变化**(如新增勒索加密模块、删除传播模块)、**反检测代码新增**(如新增沙箱检测、反调试、反 hook)、**C2 通信协议演变**(如加密算法升级、协议字段调整、域名生成算法 DGA 变更)、**持久化机制调整**(如注册表键变更、计划任务格式变化)。

自动化批处理示例:用 Diaphora 导出每个版本的数据库,编写脚本两两比对,生成"功能演进时间线",可直观看到某家族从简单 RAT 逐步加入挖矿、勒索、横向移动模块的演化路径。对于加壳样本,需先脱壳(Unicorn 模拟脱壳或 dump 内存)再进行差分,否则哈希与 CFG 会被混淆层破坏。

### 21.6 2026趋势: AI辅助二进制差分

- **CodeBERT/CodeT5 用于函数语义相似度比较**:将反编译伪代码视为自然语言,用预训练代码模型编码函数语义向量,计算余弦相似度,弥补纯图匹配在变量重命名、循环展开等变换下的失效。
- **Gemini/Claude 用于差异代码片段的自然语言解释**:将差分定位的修改基本块反编译后送入 LLM,自动生成"该修改将缓冲区长度检查从 `len > 256` 改为 `len >= 256`,修复了 off-by-one 越界写"等自然语言说明。
- **自动 CVE 映射**:差分结果与已知漏洞模式库(如 CVE 描述向量化)匹配,自动推测补丁对应的 CVE 编号,实现"给两个二进制,输出候选 CVE 列表"。

---

