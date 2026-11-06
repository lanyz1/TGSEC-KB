### 11.1 OLLVM 三大混淆技术原理

| 混淆技术 | 标识 | 原理 | 复杂度倍增 |
|----------|------|------|------------|
| **控制流平坦化 (FLA/CFF)** | `-mllvm -fla` | 将自然分支结构拆解为中央调度器(switch-case/if-chain状态机)路由 | 与BCF组合时x86放大4.18倍，ARM放大5.50倍 |
| **虚假控制流 (BCF)** | `-mllvm -bcf` | 插入不透明谓词(`x*(x+1)%2==0`)恒真条件分支+不可达代码 | 单独使用增加30-50%代码量 |
| **指令替换 (SUB)** | `-mllvm -sub` | 将标准算术替换为MBA表达式(`a+b → (a^b)+2*(a&b)`) | 增加指令数3-5倍 |

### 11.2 控制流平坦化去混淆

#### 方法A: 符号执行去平坦化（deflat.py / angr）

```bash
# deflat.py — 基于angr的经典去平坦化工具
# 原理: 识别调度器基本块→对每个真实基本块符号执行→求解状态变量→重建控制流
python3 deflat.py -f target_x8664_flat --addr 0x400530

# debogus.py — 移除虚假控制流
# 原理: 将不透明谓词x*(x+1)%2替换为0→恒真条件自动成立→移除假分支
python3 debogus.py -f target_x86_bogus --addr 0x80483e0

# 批量处理多函数
python3 multi.py -f target_binary --function-list funcs.txt
```

```python
# deflat.py 核心原理实现
import angr

proj = angr.Project("obfuscated.bin", auto_load_libs=False)
cfg = proj.analyses.CFGFast()

# 步骤1: 识别调度器基本块(大量条件跳转的目标)
for func in cfg.functions.values():
    if func.block_count < 50:
        continue  # 平坦化后基本块数量激增
    
    # 查找主调度器: switch-case分发模式
    dispatcher_block = None
    for block in func.blocks:
        # 调度器特征: 大量条件跳转目标
        targets = block.vex.constant_jump_targets
        if len(targets) > 10:
            dispatcher_block = block
            break
    
    if not dispatcher_block:
        continue
    
    # 步骤2: 识别状态变量(调度器比较的变量)
    state_var = identify_state_variable(dispatcher_block)
    
    # 步骤3: 对每个真实基本块执行符号执行
    real_blocks = identify_real_blocks(func, dispatcher_block)
    for rb in real_blocks:
        # 求解: 从入口到该基本块的状态变量值
        state = proj.factory.entry_state()
        simgr = proj.factory.simulation_manager(state)
        simgr.explore(find=rb.addr)
        
        if simgr.found:
            found_state = simgr.found[0]
            state_value = found_state.solver.eval(state_var)
            
            # 步骤4: 确定该基本块的后继
            successors = list(found_state.step().successors)
            for succ in successors:
                next_state = succ.solver.eval(state_var)
                # patch: 在基本块末尾直接跳转到后继(跳过调度器)
                patch_jump(rb.addr, next_block_addr)
```

#### 方法B: Miasm符号执行去平坦化（ollvm-unflattener v2.0）

```bash
# ollvm-unflattener — 基于Miasm的去平坦化(2025年v2.0)
# 支持Windows/Linux x86/x64，可生成去混淆后的可执行文件

# 单函数去混淆
python unflattener -i ./CFF.bin -o ./deob_CFF.bin -t 0x80491A0

# 跟踪所有调用进行递归去混淆(BFS遍历调用图)
python unflattener -i ./CFF_full.bin -o ./deob_CFF_full.bin -t 0x8049E00 -a

# 依赖: miasm, graphviz, keystone-engine
pip install miasm graphviz keystone-engine
```

#### 方法C: IDA Microcode去平坦化（D810-ng v0.6.6）

```python
# D810-ng配置: 专门针对OLLVM的去平坦化规则
# 配置文件: default_unflattening_ollvm.json

# D810-ng反平坦化器矩阵:
# ┌──────────────────────────┬──────────────┬──────────────────────────────┐
# │ 反平坦化器               │ 目标混淆器    │ 描述                          │
# ├──────────────────────────┼──────────────┼──────────────────────────────┤
# │ Unflattener              │ O-LLVM       │ switch/if-chain调度器+状态变量│
# │ UnflattenerSwitchCase    │ Tigress      │ Tigress m_jtbl调度器          │
# │ UnflattenerTigressIndirect│ Tigress     │ Tigress m_ijmp间接跳转         │
# │ HodurUnflattener         │ Hodur(PlugX) │ 嵌套while(1)状态机            │
# │ BadWhileLoop             │ Approov      │ while(v8!=C)状态常量0xF6xxx   │
# │ UnflattenControlFlowRule │ 通用(实验性) │ 基于路径模拟的CFG去平坦化     │
# └──────────────────────────┴──────────────┴──────────────────────────────┘

# 安装D810-ng
# pip3 install d810-ng[speedups]
# python -m d810.speedups.install
# 仅支持IDA v9+ 和 Python 3.10+
```



---
📖 本切片 1/3 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-11-ollvm-mba-02.md")`