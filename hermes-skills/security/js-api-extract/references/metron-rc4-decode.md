# Metron 风格 JS RC4+base64 混淆解码模板

适用于 `_0xd79e` 数组 + `_0x2f23` 解码器的 obfuscated JS。

## 识别信号

- JS 文件开头: `var vip='Metron',vip_=function(){return['\u202Evip'],_0xd79e=[...]}`
- 调用模式: `_0x2f23('\u202eXXX', 'key')`
- 解码算法: atob + %XX encode + decodeURIComponent + RC4 (256-byte S-box)

## Node.js 解码模板

```javascript
// decode_template.js — 按需修改 BODY_PATH 和 decodeList
const fs = require('fs');

const BODY_PATH = '/path/to/auth.js.body';  // 已下载的 JS 文件
const body = fs.readFileSync(BODY_PATH, 'utf8');

// Mock window 环境
var window = global;
window.location = { pathname: '/', protocol: 'http:', host: 'localhost' };

// 截取基础设施：找到数组和 decode 函数的定义，到 "var auth=" 之前
const infra = body.substring(0, body.indexOf('var auth='));
// 如果 auth 不存在, 到 'jQuery(document)' 之前
const altIdx = body.indexOf('jQuery(document)');
const infraCode = infra || (altIdx > 0 ? body.substring(0, altIdx) : body);

// 加载基础设施
eval(infraCode);

// 指定要解码的 (index_hex, key, label)
const decodeList = [
    ['37c', 'eSY7', 'login_submit_url'],     // 示例：在JS中搜索 _0x2f23('\\u202e37c','eSY7') 获得
    ['2d6', 'QGh3', 'register_url'],
    ['435', 'Wd9!', 'poll_check_url'],
];

for (const [hex, key, label] of decodeList) {
    try {
        const val = _0x2f23('\u202e' + hex, key);
        console.log(`DECODE[${label}]: ${val}`);
    } catch(e) {
        console.log(`FAIL[${label}]: ${e.message}`);
    }
}

// 批量扫描所有索引 + 常见 key（从JS的第二参数中提取）
const keysToTry = ['eSY7', 'Wd9!', 'g0Ti', 'iP#7', 'QGh3', 'boAI', '3dZi', 
                   'PwY2', '!5r9', 'ANb^', 'NKcv', 'f(Q4', 'R1ES', 'T#o*', '5K83'];

for (const key of keysToTry) {
    for (let i = 0; i < Math.min(_0xd79e.length, 1178); i++) {
        try {
            const hex = ('000' + i.toString(16)).slice(-3);
            const val = _0x2f23('\u202e' + hex, key);
            if (val && val.length > 2 && val.length < 80 && 
                /^[\w\/\-.:@+=\[\]{}$!%]+$/.test(val)) {
                if (val.includes('/') || val.startsWith('http')) {
                    console.log(`URL[0x${hex} key=${key}]: ${val}`);
                }
            }
        } catch(e) {}
    }
}

console.log('DONE');
```

## 快速判断是否为该混淆类型

```bash
# 在目标 JS 中检查典型特征
head -c 500 target.js | grep -o 'vip_.*_0xd79e=\|_0x2f23.*\u202e\|McOiWg10\|KMOFW8KCwq8'
# 有输出 → 这是 Metron 风格混淆，用本模板

# 或检查《0xd79e.length`（通常几百到一千多）
head -c 2000 target.js | grep -oP '_0xd79e=\[([^]]+)\]' | tr -cd ',' | wc -c
```

## 边界定位标记

找到基础设施 vs UI 代码的分界：

| 标记字符串 | 含义 |
|---|---|
| `var auth=function` | 认证逻辑开始（前面的都是基础设施） |
| `jQuery(document)` | UI 初始化开始 |
| `var _0x5c218b=function` | 登录相关函数（前面是 _0x2f23 定义+初始化） |
| `_0x2f23['mrvVwW']` | decode 函数的自检初始化标记（确认 _0x2f23 已完整） |

## 常见错误与修复

| 错误 | 原因 | 修复 |
|---|---|---|
| `Cannot read properties of undefined (reading 'pathname')` | window.location 未 mock | 在 eval 前添加 mock 代码 |
| `_0xd79e is not defined` | eval 顺序不对，基础代码未先执行 | 把 decode 调用放在 infra eval 之后 |
| `... is not a function` | 缺少初始化 IIFE | 扩大截取范围，包含 `vip_=function` 和 IIFE |
| 全部输出 `{$/` 等碎片 | key 不对或索引偏移 | 换用该 decode 调用实际的第二参数 |
| output 全为 null/undefined | _0xd79e 数组还没初始化 | 包含初始化代码: `(function(_0x4c0c41,_0x8347ce...` IIFE 部分 |

## 替代方案（当 Node 不可用）

如果无法使用 Node.js，可在浏览器开发者控制台运行：

```javascript
// 在页面中注入 auth.js（如果它已经加载了）
// 然后在控制台直接调用 _0x2f23
var hex = '37c';
var key = 'eSY7';
console.log(_0x2f23('\\u202e' + hex, key));

// 或者直接在页面 Sources 面板的 auth.js 文件末尾
// 添加 console.log 断点，在调用 _0x2f23 时查看返回值
```
