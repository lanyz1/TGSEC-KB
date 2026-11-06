## 6. WebAssembly逆向

### 6.1 WASM二进制分析特性

WebAssembly二进制格式是结构化、可验证的栈式虚拟机表示——在可分析性上显著优于原生机器码。每个WASM模块暴露类型化的导入/导出表、声明的函数计数、可读的数据段。

### 6.2 WASM工具链

| 工具 | 功能 |
|---|---|
| WABT (WebAssembly Binary Toolkit) | 标准二进制工具包(wasm2wat/wat2wasm/wasm-objdump) |
| wasm-tools | 现代Wasm工具集 |
| Ghidra (Wasm插件) | 查看反编译的Wasm |
| JEB Pro | 商业Wasm分析工具 |
| wasm2c | 将Wasm提升到C(有良好定义的运行时) |
| WAMRC | WebAssembly Micro Runtime AOT编译器 |
| SeeWasm | WASM符号执行工具 |

```bash
# WASM逆向基础流程
# 1. 提取WASM模块
wasm-objdump -x module.wasm        # 查看节信息
wasm2wat module.wasm -o module.wat # 转换为WAT文本格式

# 2. 导出函数分析
wasm-objdump -x module.wasm | grep "Export"
# 查看导出函数名和类型签名

# 3. 使用wasm2c提升到C
wasm2c module.wasm -o module.c
# 生成的C代码可读性更好，便于分析

# 4. 使用SeeWasm符号执行
seewasm -m module.wasm -func export_function_name
```

### 6.3 WASM逆向军备竞赛(2026)

到2026年，主要反机器人平台的Wasm逻辑已被安全研究社区完整记录：

| 平台 | 逆向状态 | 影响 |
|---|---|---|
| Cloudflare Turnstile | token生成逻辑已完整文档化 | 存在生成有效token的Python库 |
| DataDome | sensor data格式已知 | 可伪造有效请求 |
| Akamai BotManager | cookie生成已被复制 | 绕过反机器人检测 |
| Solver-as-a-service | 每次收费<$0.00 | 自动化绕过即服务 |

---

