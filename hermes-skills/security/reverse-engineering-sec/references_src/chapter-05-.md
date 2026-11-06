## 5. 反混淆与反反调试

### 5.1 WASM反混淆工具链

BlackHat Asia 2025发表的系统性方法，将LLVM工具链用于WebAssembly反混淆：

**混淆工具识别**:
| 混淆器 | 特征技术 |
|---|---|
| O-LLVM | 指令替换、控制流平坦化、虚假控制流 |
| Hikari | 函数调用混淆、函数包装、字符串加密 |
| Polaris | 别名访问、间接调用、线性MBA |
| Wasmixer | WebAssembly专用混淆 |

**反混淆工具链**:

```bash
# Squanchy — 自动化WASM反混淆
# 将Wasm提升到LLVM IR → 优化 → 提取干净模块
git clone https://github.com/pgarba/Squanchy.git
cd Squanchy
python3 squanchy.py --input obfuscated.wasm --output clean.wasm

# SiMBA++ — 简化MBA表达式
python3 simba.py --input obfuscated.ll --output simplified.ll

# GAMBA — 非线性MBA求解
python3 gamba.py --input simplified.ll --output solved.ll

# SOUPER — 超级优化器(解析不透明谓词)
souper -z3solver input.ll -o output.ll
```

**实际案例**: hCaptcha的中型混淆函数可在<1-2分钟内简化，展开控制流并内联函数。

### 5.2 传统二进制反混淆

```python
# 使用angr进行控制流反平坦化
import angr

proj = angr.Project("obfuscated.bin", auto_load_libs=False)
cfg = proj.analyses.CFGFast()

# 识别控制流平坦化的调度器
for func in cfg.functions.values():
    if func.block_count > 50:  # 平坦化后基本块数量激增
        # 分析调度器模式: switch-case分发
        blocks = list(func.blocks)
        # 查找分发器基本块(大量条件跳转)
        for block in blocks:
            if len(block.vex.constant_jump_targets) > 10:
                print(f"[+] Likely dispatcher at {hex(block.addr)}")
                # 使用符号执行重建原始控制流
```

### 5.3 反反调试技术

```python
# 绕过ptrace反调试(Linux)
import ctypes
libc = ctypes.CDLL('libc.so.6')

# 方法1: LD_PRELOAD覆盖ptrace
# preload.c
"""
long ptrace(int request, int pid, void *addr, void *data) {
    return 0;  // 始终返回成功
}
"""
# gcc -shared -fPIC -o anti_anti_debug.so preload.c
# LD_PRELOAD=./anti_anti_debug.so ./target

# 方法2: Frida Hook ptrace
# frida脚本
Interceptor.attach(Module.findExportByName(null, 'ptrace'), {
    onEnter: function(args) {
        console.log('[+] ptrace called, faking success');
    },
    onLeave: function(retval) {
        retval.replace(0);  // 返回0(成功)
    }
});

# 方法3: 修改/proc/self/status
# Frida脚本: 覆盖TracerPid
Interceptor.attach(Module.findExportByName(null, 'fopen'), {
    onLeave: function(retval) {
        // 重写/proc/self/status内容
    }
});
```

### 5.4 动态密钥捕获

针对运行时生成AES密钥链的动态密钥混淆：

```javascript
// Frida: 捕获运行时AES密钥
Java.perform(function() {
    var SecretKeySpec = Java.use('javax.crypto.spec.SecretKeySpec');
    SecretKeySpec.$init.overload('[B', 'java.lang.String').implementation = function(key, algo) {
        if (algo === 'AES') {
            console.log('[+] AES Key captured: ' + bytesToHex(key));
        }
        return this.$init(key, algo);
    };
    
    // 捕获动态密钥生成
    var KeyGenerator = Java.use('javax.crypto.KeyGenerator');
    KeyGenerator.generateKey.implementation = function() {
        var key = this.generateKey();
        var encoded = key.getEncoded();
        console.log('[+] Dynamic key generated: ' + bytesToHex(encoded));
        return key;
    };
});
```

---

