### 11.3 MBA表达式化简去混淆

#### D810-ng MBA规则系统

```python
# D810-ng DSL规则定义: MBA表达式化简
from d810.mba.dsl import Var
from d810.mba.rules import VerifiableRule

x, y = Var("x_0"), Var("x_1")

# OLLVM指令替换模式化简
class Add_OllvmRule_1(VerifiableRule):
    PATTERN = (x ^ y) + 2 * (x & y)       # OLLVM的a+b混淆形式
    REPLACEMENT = x + y
    DESCRIPTION = "Simplify OLLVM add substitution"

class Xor_HackersDelightRule_1(VerifiableRule):
    PATTERN = (x | y) - (x & y)           # Hacker's Delight恒等式
    REPLACEMENT = x ^ y
    DESCRIPTION = "Simplify (x|y)-(x&y) to x^y"

# Z3自动验证规则等价性
# verify_rule()通过Z3证明PATTERN和REPLACEMENT等价
# 如果验证失败，Z3返回反例
# 支持Z3和egglog双后端
```

#### MBA化简模式速查表

```
# OLLVM常见MBA变换及其化简:

加法:  a + b
  → (a ^ b) + 2 * (a & y)          [OLLVM标准]
  → 2 * (a | b) - (a ^ b)          [Hacker's Delight]
  → (a & b) + (a | b)              [Hacker's Delight]
  → -(-a - b)                      [双重取反]

减法:  a - b
  → (a ^ b) - 2 * (~a & b)         [OLLVM变体]
  → 2 * (a & ~b) - (a ^ b)         [Hacker's Delight]

异或:  a ^ b
  → (a | y) - (a & b)              [Hacker's Delight]
  → (a + b) - 2 * (a & b)          [OLLVM变体]
  → (~a & b) | (a & ~b)            [布尔展开]

与:    a & b
  → (a + b - (a | b))              [算术等价]
  → ~(~a | ~b)                     [德摩根]

或:    a | b
  → (a & b) + (a ^ b)              [分解]
  → ~(~a & ~b)                     [德摩根]
```

#### SiMBA++ + ML混合去混淆

```python
# 2026: ML辅助MBA模式识别
from sympy import symbols, simplify
from sklearn.ensemble import RandomForestClassifier
import numpy as np

# 步骤1: 从二进制提取MBA表达式
mba_expressions = extract_mba_from_binary("obfuscated.bin")

# 步骤2: ML分类器识别MBA模式
# 训练数据: 已知MBA变换的AST特征
clf = RandomForestClassifier(n_estimators=100)
clf.load("mba_pattern_model.pkl")  # 预训练模型

for expr in mba_expressions:
    features = extract_ast_features(expr)
    pattern_type = clf.predict([features])[0]
    
    # 步骤3: SiMBA++符号化简
    simplified = simba_simplify(expr, pattern_type)
    print(f"原始: {expr}")
    print(f"化简: {simplified}")

# 步骤4: Z3验证化简正确性
from z3 import *
for expr, simplified in zip(mba_expressions, simplified_exprs):
    x, y = BitVecs('x y', 32)
    s = Solver()
    s.add(expr != simplified)
    if s.check() == unsat:
        print("[+] 验证通过: 表达式等价")
    else:
        print("[-] 验证失败: 表达式不等价!")
```

### 11.4 OLLVM变体识别与对抗

```
2026年活跃OLLVM变体:

1. Arkari (LLVM 22.x, 2026年6月最新):
   ├── 基于Goron改进，最活跃的OLLVM变体
   ├── 间接跳转加密: -mllvm -irobf-indbr
   ├── 间接函数调用加密: -mllvm -irobf-icall
   ├── 间接全局变量引用加密: -mllvm -irobf-indgv
   ├── C字符串加密: -mllvm -irobf-cse
   ├── 整数常量加密: -mllvm -irobf-cie
   ├── 浮点常量加密: -mllvm -irobf-cfe
   └── 配置文件: -mllvm -arkari-cfg="path"

2. Pluto-Obfuscator (LLVM 12.0.1):
   ├── 增强型控制流平坦化: -mllvm -fla-ex (强烈推荐)
   ├── 全局变量加密: -mllvm -gle (强烈推荐)
   ├── 增强MBA混淆: -mllvm -mba (5系数多项式)
   ├── 随机控制流: -mllvm -rcf
   ├── 变量替换: -mllvm -vsb
   └── Trap Angr: -mllvm -trap-angr (★专门对抗angr符号执行)

3. Hikari (OLLVM扩展):
   ├── AntiClassDump: 反类转储
   ├── FunctionCallObfuscate: 函数调用混淆
   ├── FunctionWrapper: 函数包装
   ├── IndirectBranching: 间接分支
   └── StringEncryption: 字符串加密

4. 推荐组合(Pluto FullProtection):
   ./clang++ -mllvm -mba -mllvm -mba-prob=50 \
              -mllvm -fla-ex -mllvm -gle test.cpp -o test

对抗Trap Angr的策略:
  ├── 约束简化: 自定义angr exploration策略
  ├── 钩子函数: 自定义syscall/库函数行为
  ├── 路径剪枝: 提前剪枝不可达路径
  ├── 混合方法: 符号执行+具体执行混合
  └── 动态绕过: 运行时检测并patch陷阱指令
```



---
📖 本切片 2/3 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-11-ollvm-mba-03.md")`