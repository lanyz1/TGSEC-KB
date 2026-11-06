## 七、反混淆与对抗审计

### 7.1 常见混淆技术识别

```
- 字符串混淆：字符串数组 + 索引引用、Base64/hex/Unicode 编码、拼接
- 控制流平坦化（Opaque Predicate）：大量 switch + 状态变量
- 动态生成：eval/Function 构造器、动态 import、document.write
- 标识符乱化：a/b/c 单字母变量、\_0x 前缀十六进制变量
- 打包器产物：webpack/rollup bundle、压缩混淆（minified）
- 加密执行：运行时解密再 eval（外层壳 + 内层载荷）
- 语言特定：JSFuck/JJEncode（仅符号）、PyArmor、Invoke-Obfuscation、ConfuserEx
- 隐藏数据：Steganography（图片隐写）、DNS TXT 编码
```

### 7.2 静态去混淆流程

```bash
# 1. 格式化还原可读性
npx prettier --write suspect.js
npx js-beautify suspect.js -o clean.js

# 2. 识别混淆器指纹（Obfuscator.IO / js-confuser 等）
npx identify-obfuscation suspect.js   # 或手工匹配特征

# 3. AST 分析提取字符串/调用
npx esprima clean.js > ast.json
npx eslint --no-eslintrc --rule 'no-eval: error' clean.js

# 4. 手工还原字符串数组（替换索引引用）
# 5. 关键字符串提取（URL/IOC）
grep -oE "https?://[^\"']+" clean.js
```

### 7.3 动态分析与沙箱

```bash
# 本地受控 Node VM 执行（拦截 eval/网络）
node --experimental-permission --allow-fs-read=./suspect.js -e "
  const fs = require('fs');
  const src = fs.readFileSync('suspect.js', 'utf8');
  // 用 Proxy 拦截全局函数调用，观察行为而不落地执行
"

# 浏览器沙箱：jsdom 加载 + 观察 document.write/网络请求
# 恶意样本注意：cuckoo/CAPE 沙箱跑全链（检测反沙箱）

# 网络行为捕获：在隔离网段用 netcat/HTTP 服务器记录回连
nc -lvnp 8080 > http.log
```

### 7.4 AI 辅助反混淆（2025-2026 新进展）

```
- Google CASCADE（ICSE 2026）：LLM 识别 prelude 函数 + 编译器 IR 变换，生产级还原 Obfuscator.IO 混淆，替代数百条硬编码规则
- Unweaver：35+ 确定性变换 + LLM 编排的多轮去混淆工作台
- ai-code-decompile：AI+AST 还原 webpack 产物/混淆 JS
- 方法论：先确定性变换（解码/展开）剥壳，再由 LLM 语义还原，二者交替迭代
- 限制：LLM 可能"自信地改写"出与原语义不符的代码——还原结果必须做行为等价验证
```

