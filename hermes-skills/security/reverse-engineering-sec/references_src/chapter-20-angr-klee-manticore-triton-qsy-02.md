### 20.7 符号执行实战场景

自动化CTF flag求解: angr解决简单crackme——标记输入为符号,`explore(find=打印"Correct"地址, avoid=打印"Wrong"地址)`,求解到达成功分支的输入。适用于校验逻辑简单的逆向题,对复杂VM或魔改加密仍需手动分析。

漏洞利用自动生成: 求解触发crash的输入——将网络输入标记为符号,在crash点收集路径约束与内存约束,用Z3求解满足缓冲区溢出条件的输入。angr的`explore(find=crash_addr)`配合`state.solver`可自动生成PoC。

协议fuzzing: 符号执行生成协议测试用例——对协议解析器符号执行,在状态机分支处求解满足各分支的协议数据,生成覆盖所有解析路径的fuzzing种子,显著优于纯随机变异。

反混淆: 符号执行还原OLLVM控制流平坦化——识别dispatcher(分发器)基本块,对每个真实basic block标记符号执行上下文,通过约束求解恢复原始控制流图;angr的`Veritesting`与DDG(数据依赖图)辅助还原。Triton的污点追踪可识别opaque predicate(恒真/恒假条件)并化简,还原混淆逻辑。对VMProtect虚拟化,符号执行配合污点分析可自动推导VM handler语义,重建原始指令。

---



---
📖 本切片 2/2 结束。 本章节结束。