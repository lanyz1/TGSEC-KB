### 20.1 符号执行原理与挑战

符号执行 vs 具体执行: 具体执行单一输入产生单一路径,符号执行用符号变量表示输入,通过路径约束(path constraint)探索所有可行路径,核心挑战是路径爆炸(path explosion)——分支数随输入位宽指数增长。

静态符号执行(如KLEE早期)从入口纯符号探索;动态符号执行(concolic execution,如SAGE/DART)先具体执行一条路径,再翻转分支约束求解新输入,缓解路径爆炸。约束求解器: Z3(SMT,微软)、STP、Boolector、CVC5,性能差异显著,Z3最通用。2026年挑战与进展: 路径爆炸缓解采用状态合并(state merging,用λ表达式合并分支)、冗余路径剪枝(verbatim技术避免重复探索等价路径);预计算约束缓存(constraint caching);增量求解(incremental solving)复用求解器状态。混合执行(concolic + fuzzing)成为主流,符号执行仅处理模糊测试难以突破的复杂约束。

### 20.2 angr符号执行框架

angr是Python符号执行框架,核心概念: Project(二进制加载与架构)、State(执行状态,含寄存器/内存/约束)、SimEngine(执行引擎)、SimulationManager(状态集合管理)。

```python
import angr

proj = angr.Project("./target", auto_load_libs=False)
state = proj.factory.entry_state()
simgr = proj.factory.simulation_manager(state)

# 探索到达特定地址的路径
simgr.explore(find=0x400800, avoid=0x400900)

if simgr.found:
    found = simgr.found[0]
    # 求解输入
    solution = found.posix.dumps(0)  # stdin
    print(f"Solution: {solution}")
```

管理器操作: `step()`推进一个基本块,`explore(find, avoid)`自动探索至目标,`prune()`剪除不可满足状态,`merge()`合并等价状态。Hook函数简化分析: `proj.hook_symbol('strcmp', angr.SIM_PROCEDURES['libc']['strcmp']())`用SimProcedure替代复杂库函数;自定义hook返回固定值(如`strcmp`恒返回0)绕过校验。约束求解: `state.solver.eval(expr)`求解符号表达式,`state.solver.BVV`构造位向量,`state.solver.If`构造条件表达式。angr的`Claripy`后端可切换Z3/STP。实战技巧: 用`state.options.add(angr.options.LAZY_SOLVES)`延迟求解提升性能,`Veritesting`模式自动合并路径缓解爆炸。

### 20.3 KLEE — LLVM符号执行

KLEE基于LLVM bitcode执行符号分析,需先用clang将源码编译为LLVM IR: `clang -emit-llvm -c target.c -o target.bc`。KLEE对IR做符号执行,生成KTest测试用例。

```bash
# KLEE符号执行
klee -libc=uclibc -posix-runtime target.bc
# 输出test*.ktest用例
ktest-tool klee-last/test000001.ktest
```

KTest文件包含触发各路径的输入数据,可直接作为AFL种子。KLEE的`klee_make_symbolic`标记符号变量,`klee_assume`添加路径约束。2026年KLEE对LLVM 15+支持完善,新增对新LLVM IR特性的符号语义。与AFL配合: KLEE探索深度路径生成高质量种子 → AFL变异扩展,形成KLEE-AFL混合fuzzing,显著提升覆盖率与漏洞发现率。KLEE-Net模块支持网络协议符号执行。

### 20.4 Manticore — 多范式符号执行

Manticore支持多目标: x86/x64/ARM二进制符号执行、EVM字节码符号执行(智能合约漏洞挖掘)。其优势是统一的符号执行API跨平台。

```python
from manticore.eth import ManticoreEVM

m = ManticoreEVM()
with open('contract.sol') as f:
    source_code = f.read()

user_account = m.create_account(balance=1000)
contract_account = m.solidity_create_contract(source_code, owner=user_account)

# 符号执行所有公开函数
symbolic_data = m.make_symbolic_buffer(320)
contract_account.fallback(data=symbolic_data)

# 检测整数溢出/重入漏洞
for state in m.running_states:
    # 检查balance异常状态
    pass

m.finalize()  # 生成报告
```

Manticore for smart contracts自动检测整数溢出、重入攻击、未授权访问。二进制分析模式下,`manticore ./binary`自动探索路径并生成触发各分支的输入。Manticore的插件系统支持自定义检测器(detector)。

### 20.5 Triton — 动态符号执行与污点分析

Triton结合DBI(基于Pin)的具体执行与符号执行,实现concolic analysis,适合分析混淆代码与自动求解约束。

```python
from triton import TritonContext, ARCH, Instruction

ctx = TritonContext()
ctx.setArchitecture(ARCH.X86_64)

# 设置符号变量
ctx.setConcreteRegisterValue(ctx.registers.rax, 0x41414141)
ctx.symbolizeRegister(ctx.registers.rax, 'input')

# 执行指令并追踪污点
inst = Instruction(b"\x48\x01\xc0")  # add rax, rax
ctx.processing(inst)

# 获取符号表达式
rax_sym = ctx.getSymbolicExpressionFromId(ctx.getSymbolicRegisterId(ctx.registers.rax))
print(f"RAX = {rax_sym.getAst()}")
# 输出: RAX = (input_0 + input_0)
```

Triton的污点传播引擎自动追踪符号变量在寄存器与内存间的流动,`getTaintedRegister`/`isMemoryTainted`查询污点状态。应用: 自动化绕过license check——标记用户输入为符号,执行license校验例程,在比较指令处收集路径约束,用Z3求解满足"校验通过"的输入;反混淆VMProtect时追踪VM handler的数据流,还原虚拟化指令语义。Triton支持AST快照与SMT简化,降低求解开销。

### 20.6 QSYM — 混合模糊测试

QSYM = 符号执行 + 模糊测试,符号执行仅用于求解模糊测试难以突破的复杂约束(如magic number比较、checksum校验),避免纯符号执行的路径爆炸。

```bash
# Symcc编译: 在编译时插入符号执行指令
symcc --stat-syms ./target.c -o target_sym

# 配合AFL运行: concolic execution辅助fuzzing
afl-fuzz -i input/ -o output/ -- ./target_sym @@
```

QSYM采用乐观求解(optimistic solving)与约束切片(constraint slicing)仅保留关键约束,大幅提升求解速度。与AFL配合: QSYM作为AFL的辅助引擎,当AFL卡在magic number时触发符号执行求解。2026年进展: SymCm——在LLVM编译器级插桩,性能比传统DBI方式提升10x,符号执行开销接近零;SyME将符号执行并行化,多核扩展求解。Symcc编译的二进制在运行时自动记录路径约束并生成新种子,与AFL++的`-c symcc`集成。



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-20-angr-klee-manticore-triton-qsy-02.md")`