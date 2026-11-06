---
name: js-api-extract
description: "JavaScript 静态分析提取隐藏 API 端点。当目标是 SPA/前后端分离架构、页面使用 Vue/React/Angular、或常规目录扫描收效甚微时使用。通过分析 JS bundle 提取 API 路径、密钥、内部域名、WebSocket 端点。是 API 渗透的信息收集阶段。发现端点后 → api-fuzz 进行语义化 fuzz"
metadata:
  tags: "js,javascript,api,extract,spa,vue,react,angular,webpack,bundle,endpoint,前端分析"
  category: "recon"
---

# JavaScript API 端点提取方法论

前后端分离架构中，JS bundle 是 API 端点的**最大信息源**——比目录扫描高效 10 倍。

## ⛔ 深入参考（必读）

- JS 分析正则库 + 提取脚本 → [references/js-extract-patterns.md](references/js-extract-patterns.md)

---

## Phase 1: JS 文件收集

### 1.1 从页面 HTML 收集
```bash
# 抓取页面中所有 JS 引用
curl -s "$TARGET" | grep -oE '(src|href)="[^"]*\.js[^"]*"' | sed 's/.*="\(.*\)"/\1/'

# 递归抓取（含 iframe/动态加载）
curl -s "$TARGET" | grep -oP '(?:src|href|url)\s*[=:]\s*["\x27]([^"\x27]*\.js[^"\x27]*)["\x27]' | sort -u
```

### 1.2 从 Source Map 恢复
```bash
# 检查 JS 文件末尾的 sourceMappingURL
curl -s "$TARGET/static/js/app.xxx.js" | tail -1
# 如果有 //# sourceMappingURL=app.xxx.js.map
curl -s "$TARGET/static/js/app.xxx.js.map" -o sourcemap.json

# Source Map 暴露完整源码——等于拿到了前端源码
```

### 1.3 从 Webpack 清单收集
```bash
# 常见 chunk 清单文件
/static/js/manifest.json
/asset-manifest.json
/webpack-manifest.json
/build/asset-manifest.json
/static/js/runtime~main.xxx.js  # runtime chunk 包含所有 chunk 映射
```

### 1.4 历史版本
```bash
# Wayback Machine 获取旧版 JS（可能包含已删除但未下线的 API）
curl -s "https://web.archive.org/cdx/search/cdx?url=$DOMAIN/*.js&output=text&fl=original" | sort -u
```

## Phase 2: API 端点提取

### 2.1 路径模式提取
```bash
# 从 JS 内容中提取 API 路径（最核心的一步）
curl -s "$JS_URL" | grep -oP '["'"'"'](/(?:api|v[0-9]|rest|service|graphql|ws|internal|admin|auth|user|public)[^\s"'"'"']*?)["'"'"']' | sort -u

# 拼接路径提取（前端常见写法：baseURL + path）
curl -s "$JS_URL" | grep -oP '(?:baseURL|BASE_URL|API_URL|apiPrefix|apiBase)\s*[=:]\s*["'"'"']([^"'"'"']+)["'"'"']'

# 通用路径提取（含相对路径）
curl -s "$JS_URL" | grep -oP '["'"'"'](/[a-zA-Z][a-zA-Z0-9_/\-]{2,}(?:\?[^"'"'"']*)?)["'"'"']' | sort -u | grep -v '\.\(js\|css\|png\|jpg\|svg\|ico\|woff\|ttf\)'
```

### 2.2 完整 URL 提取
```bash
# 提取完整的 HTTP(S) URL
curl -s "$JS_URL" | grep -oP 'https?://[^\s"'"'"'<>]+' | sort -u

# 提取内部域名/子域名
curl -s "$JS_URL" | grep -oP 'https?://[a-zA-Z0-9._-]+\.DOMAIN\.com[^\s"'"'"']*' | sort -u
```

### 2.3 关键信息提取
```bash
# API Key / Secret / Token
curl -s "$JS_URL" | grep -oiP '(?:api[_-]?key|secret|token|auth|password|credential)\s*[=:]\s*["'"'"']([^"'"'"']{8,})["'"'"']'

# WebSocket 端点
curl -s "$JS_URL" | grep -oP 'wss?://[^\s"'"'"']+' | sort -u

# 内部 IP/域名
curl -s "$JS_URL" | grep -oP '(?:10|172\.(?:1[6-9]|2\d|3[01])|192\.168)\.\d+\.\d+' | sort -u
```

## Phase 3: 处理混淆/打包的 JS（常见于 Metron 系后台）

当标准 grep 提取发现 JS 中只有 `_0xd79e` 数组和 `_0x2f23` 解码器（或类似 packed array），
没有任何可见的 API 路径，说明字符串被 RC4/base64 编码了。**不要跳过这一步——这正是 API 端点被藏起来的地方。**

### 3a 识别混淆结构

典型特征（最常见于 Metron 主题的中文管理系统后台）：

```javascript
var vip='Metron',vip_=function(){return['\u202Evip'],_0xd79e=[vip,'McOiWg10',...]};
// 后面跟着 _0x2f23 解码函数
// 使用 _0x2f23('\u202eXXX', 'key') 调用
```

其他变体（`_0x...` 数组 + base64 + XOR/RC4 是 JSFuck/JJEncode 家族的变体）：
- `_0x4e3b = ['base64...','...']` + 一个自执行函数初始化
- `_0x3a7c = [...], _0x1f2a = function(i, k) { ... }` 类似模式

### 3b 提取基础设施

1. 找到数组（`_0xd79e=[...]`）和 decode 函数（`_0x2f23=function(...)`）
2. 找函数的执行依赖——通常有 `atob` polyfill 和 RC4 实现内嵌
3. 截取干净的 JS 片段（数组定义 + 初始化 IIFE + decode 函数），不含后续的 UI/DOM 代码
4. 在 Node.js 中运行前 mock `window` 为 `global`：

```javascript
var window = global;
window.location = { pathname: '/', protocol: 'http:', host: 'localhost' };
```

### 3c 核心解密算法（代码提取版，非手动实现）

用 Node.js 跑原始 JS 调用 `_0x2f23`。不要手写 Python RC4 —— JS 的 `decodeURIComponent` + 256 字节 S-box 与标准 RC4 有微小差异，原生跑最准。

**流水线：**
```javascript
// 1. 获取 raw JS 文件（前面 Phase 1 已下载）
// 2. 截取基础设施代码（到 `var auth=` 或 `jQuery(document)` 之前）
// 3. 拼接 Node.js mock 头 + decode 调用
// 4. 跑 node 解码

// 解码指定索引的调用示例：
var hex = ('000' + index.toString(16)).slice(-3);
var decoded = _0x2f23('\u202e' + hex, key);  // key 取自代码中该调用的第二参数
```

### 3d 扫描 API 端点

用 Node.js 批量遍历所有数组索引 + 常见 key：

```javascript
var keysToTry = ['key1', 'key2', ...];  // 从代码中提取使用的 key 参数
for (var k = 0; k < keysToTry.length; k++) {
    for (var i = 0; i < _0xd79e.length; i++) {
        var hex = ('000' + i.toString(16)).slice(-3);
        var val = _0x2f23('\u202e' + hex, keysToTry[k]);
        if (val && val.match(/^[\w\/\-.:@]+$/)) {
            console.log("URL[0x" + hex + " key=" + keysToTry[k] + "]: " + val);
        }
    }
}
```

扫描结果过滤模式（关注有 API 特征的结果）：
- 包含 `/api`, `/auth`, `/login`, `/register`, `/user`, `/admin`, `/reset`, `/upload`
- `http://` 或 `https://` 开头
- 纯 ASCII 字母数字路径（排除二进制噪声）

### 3e 修复常见问题

- **`Cannot read properties of undefined (reading 'pathname')`** → mock `window.location`
- **`_0xd79e is not defined`** → 解码调用放在了基础设施代码之前
- **只有 `{$/` 等碎片输出** → key 参数的字符集导致 RC4 输出偏 ASCII 表层，换个 key 重试
- **`TypeError: ... is not a function`** → 截取范围太窄，缺失了自执行初始化函数（搜索 `vip_=function` 和 `_0x2f23['mrvVwW']` 做包含标记）

### 3f 后续使用

提取出的端点清单应输入 Phase 4 做批量验证。确认活性的端点按 Phase 3 优先级表分类后进入攻击计划。

## Phase 4: 端点分类与优先级（同原）

提取完后按安全价值分类：

| 优先级 | 特征 | 说明 |
|--------|------|------|
| 🔴 高 | `/admin/`, `/internal/`, `/debug/`, `/manage/` | 管理功能，可能缺乏认证 |
| 🔴 高 | `/upload`, `/import`, `/export`, `/download` | 文件操作，可能有路径穿越/任意读写 |
| 🔴 高 | `/user/`, `/account/`, `/profile/`, `/order/` | 用户数据操作，IDOR 高发区 |
| 🟡 中 | `/auth/`, `/login/`, `/register/`, `/reset/` | 认证流程，可能有逻辑绕过 |
| 🟡 中 | `/search`, `/query`, `/filter` | 查询接口，SQL 注入高发区 |
| 🟢 低 | `/static/`, `/public/`, `/health`, `/status` | 静态资源/健康检查 |

## Phase 4: 批量验证

```bash
# 对提取的端点逐一验证存活
for path in $(cat extracted_paths.txt); do
    code=$(curl -s -o /dev/null -w "%{http_code}" "$TARGET$path" --connect-timeout 5 -m 10)
    echo "$code $path"
done | grep -v "^404 " | sort
```

**关键看点**：
- `200` → 直接可访问，检查响应内容
- `401/403` → 存在但需认证，尝试绕过
- `405` → 端点存在但方法不对，尝试 POST/PUT/DELETE
- `500` → 后端报错，可能有注入点
- `301/302` → 跟踪重定向目标

## 输出要求

提取结束后输出：
1. **JS 文件清单** — 分析了哪些 JS
2. **发现的 API 端点列表** — 按优先级排序
3. **暴露的敏感信息** — API Key、内部域名、Token
4. **推荐的下一步测试** — 哪些端点应该优先 fuzz
