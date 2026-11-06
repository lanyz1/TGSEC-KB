<!-- archived from /root/.hermes/skills/security/js-deobfuscation/SKILL.md on 2026-10-21 -->

---
name: js-deobfuscation
description: "Use when target JS is heavily obfuscated (obfuscator.io)."
---

> 归档卡：原目录 `/root/.hermes/skills/security/js-deobfuscation`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/js-deobfuscation/…')`，不要相对 `references/legacy/` 解析。

# JS 反混淆(obfuscator.io 风格 bundle)

## 触发场景
- 站点主 JS 2MB+、单行、`_0x1a2b3c` 标识符满天飞,grep 业务词一无所获(字符串被拆碎/加密)
- 顶层有巨型 IIFE:`(function(A,B){ while(!![]){try{ ...checksum... } }(<arrayFn>, 0x<bignum>));`
- 数组函数 `function a0_0xXXXXXX(){var _0xYYYY=[...];...}` 返回数万元素数组;解码器 `function a0_0xZZZZZZ(...)` 内含 `['TEVoxx']===undefined` 初始化块
- Vite/Webpack 产物二次混淆(有 React/Vue 框架代码混排)

## 核心认知(实测验证,别走弯路)
1. **数组旋转**:IIFE 运行时持续 `arr.push(arr.shift())` 直到内部 checksum 等于第二参数(`0x<bignum>`)才停。数组是同一对象引用、原地旋转,闭包实时可见。
   → **不要手抄 checksum 公式到 Python 复刻**(实测漏一个负号 → 全表解错,白折腾一个多小时)。
   → **正确做法:在 Node 里执行「解码器 + 数组函数 + IIFE」三段拼接,让 JS 自己转,然后 `JSON.stringify(arrayFn())` 导出正确顺序数组。**
2. 解码 = **自定义字母表 Base64 + decodeURIComponent**(字节按 UTF-8 解码)。
   实测变体字母表:`abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789+/=`(**小写在前,非标准 atob**)。字母表写在解码器源码里,照抄。
3. checksum 用到的字符串形如 `"663790ADIHig"`(数字+字母后缀),JS `parseInt` 取前缀数字——复刻时用 parseInt 语义。
4. 一个 bundle 可能有**多套**数组/解码器对,以及二级 wrapper 链(`_0xAAA(a,b){return a0_0xDDD(b-0x333,a);}`)。**用「真执行」替代静态公式推导**,一条链自然全通。
5. 解出后的字符串可能有碎片感(如 `'ery ex'`、`'sDirec'`)——正常,它们是拼接表达式的一部分;完整 URL 靠上下文拼。

## 工作流(已验证)
### 1) 提取三件套
- 数组函数:`function <arrayFn>(){...}`(indexOf 找起点 + 平衡括号)
- 解码器:`function <decFn>(...){...}`
- 顶层 IIFE:起点 `(function(`;终点用**固定标记**:`}(<arrayFn>,0x<num>));`(含)

### 2) Node 跑 IIFE → 正确数组
```js
const data = fs.readFileSync('bundle.js','utf8');
// 用 indexOf+平衡括号 扣出 decFn/arrFn;用固定标记扣出 iife
const part = decFn + '\n' + arrFn + '\n' + iife + '\nglobalThis.__ARR = ' + arrayFn + '();';
eval(part);
fs.writeFileSync('arr_rotated.json', JSON.stringify(globalThis.__ARR));
```
执行 IIFE 即可(它自带校验,能正常 break);成功后立即 dump。

### 3) Python 复刻解码器批量解(提速 ~100×)
用 `scripts/js_decode.py`(自定义字母表 base64 + utf-8)。**批量前先与 Node 结果交叉验证 ≥200 随机样本,100% 一致才继续。**

### 4) 全量「调用求值」(反混淆杀手锏)
a. **注入函数导出桩**:用 acorn 拿每个 `FunctionDeclaration` 的精确 `end`,之后插
   `;try{globalThis.__F2=globalThis.__F2||{};globalThis.__F2["NAME"]=NAME;}catch(e){}`
   → 直接跑 `scripts/acorn_inject_exports.js`(先 `npm i acorn`)。
   **⚠️ 勿用平衡大括号找函数结尾**:解构默认参数 `({allOwnKeys:x=!0x1}={})` 会让 `{}` 计数错位,注入后直接语法定级错误(报 `Unexpected token ';'`)。
   命名过滤 `^(a0_)?_0x[0-9a-f]{6}$`。
   **⚠️ 用 `node --check` 验证注入结果时,先把 `export default ...` 剥掉**(script 模式不认 export)。
b. 整份 bundle `vm.runInThisContext`(顶层 var/function 自动进 global;先剥 export)。mock 环境要点:
   - `global.window=global; global.self=global;`
   - Node 24 等版本 `navigator` 是只读全局 → `Object.defineProperty(global,'navigator',{value:...,configurable:true})`
   - `document/fetch/XMLHttpRequest/localStorage/history` 给最小桩即可
c. **扫描全部调用点**生成求值清单:
   - 第一轮:`(a0_)?_0x[0-9a-f]{6}\(0x…,0x…\)` 纯字面量参数
   - 第二轮:对象属性参数——`a0_0xAAA={_0xbbb:0x123,...}` 定义通常即全局唯一,可建全局映射解析成字面量后重建调用再求值
   - 每个调用走 `(globalThis.__F2||{})[name]` + try/catch,统计 OK/NOFN
   - 实测:3818 个函数、两轮合计 **22777** 个唯一调用全量解出
   - 求值清单写成 `__EV(key,name,a1,a2)` 批量注入(几 MB 代码没关系)
d. **右到左一次性替换**(收集全部 (位置,替换文本),按位置倒序拼接;`json.dumps` 转义与 JS 字符串字面量兼容)。
   **别对已替换文本二次跑正则**——解出的字符串内容可能命中调用正则,二次替换会毁掉文件。
e. deobfuscated.js 里 grep:`clientapi`、`/api`、URL、密钥、`getinfo`/`inhouse` 等业务词——全部现形。这是找到目标后端接口的最快路径(往往比抓包还快)。

## Pitfalls
- **惰性模块**:函数定义在「未执行的工厂函数」里时,导出桩不会执行——实测 3820 个函数只导出 742 个。把入口调用(如 `m5()`)包 try/catch 重新执行可触发模块加载(F2 覆盖 3→742 个)。接受部分覆盖,优先解你需要的字符串,别卡在 100%。
- 二次调用入口可能第一次崩、第二次成功(初始化副作用),捕获栈信息再重试一次。
- 反调试(`debugger` 陷阱/`while(true){}` 注入)在纯 Node eval 下是 no-op 或有限次,不用特殊处理;但不要挂 `--inspect` 跑它。
- 数组元素可能不是全字符串(混数字/对象),判空与类型再解码。
- **多模块 bundle 别选错数组函数**：顶层 IIFE 可能只有 ~1KB，而其调用的数组函数远在 2MB 之外；同文件另有几十个模块级数组（quote 密度都高，容易误选）。**以 IIFE 尾标记 `}(<arrayFn>,0x<num>));` 里的名字为准**，别取「位置最近/密度最大」的。
- **Node eval 挂起 = 三件套不匹配**：错误的 decFn/arrFn 组合会让 IIFE 的 `while(!![])` checksum 永不收敛（Node 挂死，肉眼像卡住）。一律 `timeout 60 node extract.js` 跑，超时即换提取；并且**先「只跑 IIFE+数组函数」验证能 dump 出数组（长度合理）**，再加解码器——失败早、定位快。
- bundle 常在 `/static/<rand><timestamp>.js` 形式命名;重新下载比对 md5 确认服务端未动态生成(本例两次下载 md5 相同=静态)。

## Support files
- `scripts/acorn_inject_exports.js` — acorn 精确注入导出桩(可直接跑)
- `scripts/js_decode.py` — 自定义字母表 base64+URI 解码器(与 Node 交叉验证过)
- `references/case-niwsiq-obfuscatorio.md` — 完整实战案例(全部数字/命令/踩坑)
