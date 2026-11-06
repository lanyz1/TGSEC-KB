# Tampermonkey 用户脚本 SPA 路由适配

## 问题背景

中文赌博平台的 SPA（Vue/React）使用两种路由模式：

| 路由模式 | URL 示例 | getType() 匹配方式 |
|:---------|:---------|:------------------|
| **Hash 模式** | `/#/NN/OG1NN` | `location.hash` |
| **Pathname 模式** | `/lottery/K3/OG1K3` | `location.pathname` |

大多数现成的用户脚本（如 BFCP AutoBet）只检查 `location.hash`，无法在 pathname 模式的路由下工作。

## 修正方法

### 核心修改：getType() 函数同时检查 hash 和 pathname

```javascript
function getType() {
    var h = location.hash;
    var p = location.pathname;
    var u = location.href.toLowerCase();
    function m(re) { return re.test(h) || re.test(p); }
    
    // 游戏类型匹配（同时支持 hash 和 pathname）
    if (m(/\/SH\//) || m(/三公/) || m(/sangong/)) return 'SH';
    if (m(/\/TH\//)) return 'TH';
    if (m(/\/SLM\//)) return 'SLM';
    if (m(/\/NN\//) || m(/牛牛/) || m(/niuniu/)) return 'NN';
    if (m(/\/DT\//)) return 'DT';
    if (m(/\/RB\//)) return 'RB';
    if (m(/\/BJL\//) || m(/百家乐/) || m(/baccarat/)) return 'BJL';
    if (m(/\/GF\//)) return 'GF';
    if (m(/\/K3\//) || m(/快三/)) return 'K3';
    if (m(/\/SSC\//) || m(/\/FFC\//)) return 'SSC';
    if (m(/\/BSC\//) || m(/\/PK10\//)) return 'PK10';
    
    // Fallback: 如果 URL 含 game/lottery/play 但未识别具体类型
    if (m(/game/) || m(/lottery/) || m(/play/) || m(/pg\//)) return 'K3';
    
    return p === '/home' || p === '/' ? 'HOME' : '?';
}
```

### 额外需修改的地方（针对 Canvas 游戏）

**1. API 拦截增强** — Canvas 游戏通常使用 WebSocket 而非 fetch()：

```javascript
// 原始: 只拦截 fetch() 中的 getPreNumber/getLotteryOpen
// 补充: 拦截 WebSocket 消息
// ⚠️ 必须保留原始 WebSocket 原型链，否则 Canvas 游戏断网！
var _WS = window.WebSocket;
if (_WS) {
    var OrigWS = _WS;
    window.WebSocket = function(url, protocols) {
        // 保留原始构造参数传递方式
        var ws = arguments.length === 2 ? new OrigWS(url, protocols) : new OrigWS(url);
        try {
            ws.addEventListener('message', function(e) {
                try {
                    var txt = typeof e.data === 'string' ? e.data : '';
                    if (!txt) return;
                    if (txt.indexOf('preNumber') > 0 || txt.indexOf('lotteryOpen') > 0 || 
                        txt.indexOf('openResult') > 0) {
                        var data = JSON.parse(txt);
                        if (data.preNumber) onPreNum(data);
                        if (data.lotteryOpen || data.openResult) onResult(data);
                        setUI({apiCount: UI.apiCount + 1});
                    }
                } catch(_) {}
            });
        } catch(_) {}
        // ⚠️ CRITICAL: 必须复制原型链属性，否则 Canvas 游戏 WebSocket 连接失败
        window.WebSocket.prototype = OrigWS.prototype;
        window.WebSocket.CONNECTING = OrigWS.CONNECTING;
        window.WebSocket.OPEN = OrigWS.OPEN;
        window.WebSocket.CLOSING = OrigWS.CLOSING;
        window.WebSocket.CLOSED = OrigWS.CLOSED;
        return ws;
    };
}
```

**2. fetch() 拦截条件放宽**：

```javascript
// 原始: 只匹配精确的 API 名称
var isPN = reqUrl.indexOf('getPreNumber') >= 0;

// 放宽: 也匹配部分名称
var isPN = reqUrl.indexOf('getPreNumber') >= 0 || reqUrl.indexOf('preNumber') >= 0;
var isRO = reqUrl.indexOf('getLotteryOpen') >= 0 || reqUrl.indexOf('lotteryOpen') >= 0 || reqUrl.indexOf('openResult') >= 0;
```

### Chrome Tampermonkey 安装问题

当 Chrome 提示 "Apps, extensions and user scripts cannot be added from this website" 时：

**方法1：Tampermonkey 仪表盘导入（最可靠）**
1. 点 Tampermonkey 图标 → "添加新脚本"
2. 删除默认代码 → 从 .user.js 文件复制粘贴内容
3. Ctrl+S 保存

**方法2：HTTP 服务器分发**
```bash
# 启动临时 HTTP 服务器
python3 -m http.server 9999
# 在 Chrome 中打开
# http://localhost:9999/bfcp.user.js
```

**方法3：直接编辑 Chrome Preferences 启用扩展**
当扩展文件存在但 Chrome 未注册时（常见于手动复制的配置）：
```python
import json
with open('Chrome/Default/Preferences', 'r') as f:
    d = json.load(f)
exts = d.setdefault('extensions', {}).setdefault('settings', {})
exts['dhdgffkkebhmkfjojejmpbldmpobfkfo'] = {
    'state': 1,
    'toolbar_pin': 'true',
    'location': 1,
    'ack_external': True
}
with open('Chrome/Default/Preferences', 'w') as f:
    json.dump(d, f, indent=2)
```

### 已知支持的 URL 模式

| 平台 | URL 模式示例 | 路由模式 | 游戏类型 |
|:-----|:------------|:---------|:---------|
| 新葡京娱乐城 | `/#/NN/OG1NN` | Hash | NN |
| 新葡京娱乐城 | `/lottery/K3/OG1K3` | Pathname | K3 |
| 天能棋牌 | `/pg/?token=...` | Pathname | 需检测 |
| 通用 | `/?game=NN&room=...` | Query | 需适配 getType |

### Canvas 游戏检测

赌博游戏常使用 `<canvas>` 渲染（Unity/WebGL），此时 DOM 中无卡牌/按钮元素可点击。BFCP 脚本的 `clickBet()` 通过 textContent 找按钮会失败。

**检测方法**：
```javascript
// 查看页面是否用 Canvas 渲染游戏
if (document.querySelector('canvas#GameCanvas')) {
    console.log('Canvas game detected — DOM-based clickBet will not work');
}
```

**对 Canvas 游戏的局限性**：
1. 卡牌数据不在 DOM 中 — 无法用 `querySelector` 读取
2. 按钮是 Canvas 上绘制的 — 无法通过 textContent 定位点击
3. 游戏数据通过 WebSocket 二进制协议传输 — 需要协议逆向
4. 某些 Canvas 游戏 SDK 自行管理 WebSocket 连接 — 包装 WebSocket 可能收不到消息

### 多 getType() 函数残留清理

多次 patching 后文件内容会残留多份 getType() 函数（新旧重叠），导致括号不平衡：

```javascript
// 症状: 面板不显示 (JS 语法错误)
// 检测: 数花括号
//   旧: getType() { ... }        ← 一个函数
//   新: getType() { ... }        ← 另一个函数（重叠未替换干净）
//        // Pathname-based ...   ← 旧函数残留代码
//        if (/\/pg\//.test(p))   ← 函数体外代码导致语法错误

// 修复: 删除整个旧函数残留块，只保留最新的 getType()
// 方法: 从最近的 function getType() 到下一个 var isA 之间的所有内容
```

**验证**：用 `grep "function getType" file.js | wc -l` 确认只有一个 getType() 定义。用 `opens - closes` 检查括号平衡。
