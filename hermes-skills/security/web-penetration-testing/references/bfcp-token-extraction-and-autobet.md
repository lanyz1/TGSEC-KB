# BFCP (必发彩票) Token 提取与 Auto-Bet 部署（修正版）

> 2026-07-22 ~ 2026-07-23 会话

**⚠️ 重要修正**：之前的版本声称"所有Action接受明文JSON"——这是错的。`getLotteryOpenNewestGame` 恰好接受明文，但 `getPreNumber`、`betSingle` 等需要 **gzip 压缩**。

---

## 平台识别

| 属性 | 值 |
|:-----|:-----|
| 域名 | anndgbzg-368bfcom.xyz:6524 |
| 前端 | Vue 3 + Vite + Pinia + Element Plus |
| API | POST /tools/_ajax/{Action} |
| 测试账号 | z147258369 / qwe123456 |
| siteId | **100047**（非默认值1） |
| 加密流程 | MD5(hostname + actionPath + Si(encryKey)) |

## ✅ 加密公式（已验证 = 浏览器真实请求对照确认）

### 核心公式

```python
hostname = "anndgbzg-368bfcom.xyz"      # window.location.hostname (不含端口)
action_path = "/tools/_ajax/<Action>"    # 完整路径

encryKey = str(int(time.time() * 1000)) + str(random.randint(0, 10**15 - 1))

def Si(s):
    return s.replace("2", "B").replace("7", "G")

encryValue = hashlib.md5(hostname + action_path + Si(encryKey)).hexdigest()
```

### body 压缩格式

**重要**：body 是否需要压缩取决于 endpoint：

| 类型 | 示例 Action | 需要压缩？ | 验证状态 |
|:-----|:-----------|:----------:|:--------:|
| 白名单 | getServerTimeMillisecond | ❌ 明文JSON | ✅ 已验证 |
| 数据查询 | getLotteryOpenNewestGame | ❌ 明文JSON | ✅ 已验证 |
| 预开数据 | getPreNumber | ✅ **gzip** | ✅ 浏览器cURL确认 |
| 下注 | betSingle | ✅ **gzip** | ✅ 浏览器cURL确认 |
| 撤单 | cancelBet | ✅ **gzip** | ⚠️ 推测 |

**压缩格式：gzip（不是 zlib！不是 raw deflate！）**

```python
# 压缩 body
import gzip, base64, json
body = json.dumps(request_dict, separators=(',',':'))
compressed = base64.b64encode(gzip.compress(body.encode())).decode()

# 解压响应（响应也是压缩的）
import zlib
raw = base64.b64decode(resp_str)
try:
    data = json.loads(zlib.decompress(raw, zlib.MAX_WBITS | 16))  # gzip auto-detect
except:
    data = json.loads(zlib.decompress(raw))  # zlib fallback
```

### 必需的 Cookies + Headers

| 项目 | 必须 | 来源 |
|:-----|:----:|:-----|
| Cookie: `JSESSIONID` | ✅ | 登录后服务端设置 |
| Cookie: `token` | ✅ | `localStorage.token`（JWT格式） |
| Cookie: `__uuid` | ✅ | `localStorage.__uuid` |
| Header: `user-uuid` | ✅ | 等于 `__uuid` 的值 |
| Header: `x-build-info` | ✅ | `2026-06-23T01:14:29.612Z`（页面固定值） |
| Header: `content-type` | ✅ | `application/json` |

**注意**：token 有有效期。过期后 API 返回 `code: "nologin"`。需重新从浏览器 `localStorage.token` 获取。

## 🔴 getPreNumber 真相（关键发现）

### 不能提前预测结果

`getPreNumber` **只返回4张公开牌**，第5张盖牌不在里面：

```
每玩家5张牌: [隐藏][公开][公开][公开][公开]
                           ↑          ↑
                      getPreNumber返回这4张
```

要等开奖后调 `getLotteryOpenNewestGame` 才能拿到全部5张，但那时已经封盘了。

### API数据跟网页显示的对不上

**已验证问题**：`getPreNumber` 返回的牌面数据跟网页上显示的**不完全一致**。可能原因：
- 多桌共用期号
- 数据被进一步处理
- 不同实例的牌数据不同

**结论**：不能用于预测获胜玩家。

### 不过 API 会返回赔率

`getPreNumber` 响应中还有 `odds` 字段，包含每个玩家的赔率。赔率越低说明赢面越大：

```json
"odds": [{"playCode": "SH001001001", "bonus": "1.54"},  // 玩家1(最可能赢)
         {"playCode": "SH001001002", "bonus": "13"},    // 玩家2(冷门)
         {"playCode": "SH001001003", "bonus": "3.44"},  // 玩家3
         {"playCode": "SH001001004", "bonus": "19.55"}] // 玩家4(最不可能赢)
```

但赔率是基于**公开的4张牌**计算的，跟你自己在网页上看牌分析没区别。

## 🎮 游戏代码对照

| 游戏名 | gameId | 类型 |
|:-------|:-------|:-----|
| 梭哈 | BLSH | 52张普通牌, 4牌/玩家 |
| ⭐ **百人梭哈** | **BASH** | **28张特殊牌, 5牌/玩家(4公开+1隐藏)** |
| 牛牛 | OGNN | A类 |
| 龙虎斗 | OGDT | A类 |
| 推筒子 | BLTH | A类 |
| 百家乐 | OGBJL | A类 |
| 森林舞会 | OGSLM | A类 |
| 轮盘 | OGRB | A类 |
| 1分快3 | OG1K3 | B类(数字彩票) |

## 🃏 百人梭哈(BASH) 28张牌编码（2026-07-23 实战校准版）

**⚠️ 重要修正**：之前的编码（`//4` 分组）是错的。BASH 使用**花色优先分组**，不是点数优先。每一组7张（8→A）同花色。该映射已通过 DOM 公开牌与 `roundNo` 数据交叉验证确认。

| 编码 | 牌 | 公式 |
|:----:|:---|:------|
| 1-7 | 8♦ 9♦ 10♦ J♦ Q♦ K♦ A♦ | `(n-1)//7=0→♦` |
| 8-14 | 8♣ 9♣ 10♣ J♣ Q♣ K♣ A♣ | `(n-1)//7=1→♣` |
| 15-21 | 8♥ 9♥ 10♥ J♥ Q♥ K♥ A♥ | `(n-1)//7=2→♥` |
| 22-28 | 8♠ 9♠ 10♠ J♠ Q♠ K♠ A♠ | `(n-1)//7=3→♠` |

```python
def bash_card(n):
    rank_idx = (n - 1) % 7   # 0=8,1=9,2=10,3=J,4=Q,5=K,6=A
    suit_idx = (n - 1) // 7  # 0=♦,1=♣,2=♥,3=♠
    ranks = ['8','9','10','J','Q','K','A']
    suits = ['♦','♣','♥','♠']
    return f"{ranks[rank_idx]}{suits[suit_idx]}"
```

### 校准过程

用户在下注阶段同时提供了：
1. `roundNo` 的20个DOM数字
2. 网页上实际显示的20张牌（5张/玩家×4玩家）

通过一一比对 `roundNo` 数字对应的实际牌面，确认了上述 `%7`（点数）× `//7`（花色）的编码规则。

**验证方法**：
```javascript
// 投注期间跑这个确认映射是否正确
var R=['8','9','10','J','Q','K','A'];var S=['♦','♣','♥','♠'];
var nums=Array.from(document.querySelectorAll('.roundNo li')).slice(0,20).map(function(l){return l.textContent});
for(var i=0;i<4;i++){
  var cards=nums.slice(i*5,i*5+5).map(function(n){var idx=parseInt(n)-1;return R[idx%7]+S[Math.floor(idx/7)]});
  console.log('玩家'+['一','二','三','四'][i]+': '+cards.join(' '));
}
```

### 牌型规则

**手牌**：5张/玩家（4公开+1隐藏），**preNumber只有16个数（4公开×4玩家）**

**牌型大小（从高到低）**：
```
同花顺 > 四条 > 葫芦 > 同花 > 顺子 > 三条 > 两对 > 对子 > 散牌
```

**点数大小**：A > K > Q > J > 10 > 9 > 8

**花色大小**：♠ > ♥ > ♣ > ♦（用于同分决胜）

**顺子判断**：A可作为高牌（A-8-9-10-J = J high straight）

### 👻 第5张盖牌完全不可读（2026-07-23 深入验证）

**结论：第5张牌（隐藏牌）在开奖前无法从任何客户端数据源读取。五个独立数据源全部确认无当前局的第5张牌数据。**

| 数据源 | 找到的牌数 | 说明 |
|:-------|:----------:|:-----|
| `getPreNumber` API | 16 (4/玩家) | 只有公开的4张，第5张不在响应体 |
| Vue Pinia `shNumber` | 16 (4/玩家) | 仅包含 `{issue, preNumber, odds}` 三个字段 |
| DOM `.card.back.shBack` | 0 | **空的 `<div></div>`**，连 data-* 属性都没有 |
| DOM `.roundNo li` | 40 (20×2) | **是上一局的结果**，非当前局 |
| DOM `.shuffleArea .card` | 10 | 洗牌动画随机牌，非当前局牌 |
| `getLotteryOpenNewestGame` | 20 (5/玩家) | ✅ 完整结果，但**开奖后才可用** |
| `LotteryResults` Pinia store | 20 (5/玩家) | ✅ 完整结果，但**是上一局的，非当前期** |

#### 五个独立数据源的详细验证过程

**① `getPreNumber` API** — 只返回16个数（4公开/玩家），响应中无第5张牌数据：
```json
{"code":"success","data":{"issue":"20260722410","preNumber":"10,08,06,20,...(16个数)","odds":{...}}}
```

**② Vue Pinia `shNumber`** — 与API数据完全一致，仅3个字段：
```javascript
const s = document.querySelector('#app').__vue_app__.config.globalProperties.$pinia.state.value.lottery;
Object.keys(s.shNumber)
// → ["issue", "preNumber", "odds"]
```

**③ DOM `.card.back.shBack`** — 盖牌元素完全为空：
```html
<div data-v-a5ea58ea="" class="card back shBack"></div>
```
无牌面数据，无data属性，Vue组件实例为空。

**④ DOM `.roundNo li` 陷阱**：DOM中有**40个 `<li>`**（两组相同20数）。这些数字对应的是**上一局（已开奖）的牌**。

**⑤ `LotteryResults` Pinia Store** — 存放200期历史数据，但**最新一条永远是上一期的**：
```javascript
s.LotteryResults.BASH.results.slice(0,3)
// → [{issueNo:当期-1, ...}, {issueNo:当期-2, ...}, ...]
```
每条结果结构：
- `lotteryOpen`: 20个数字（完整5张/玩家 × 4玩家）
- `cownPoint`: 各玩家牌型（如 `["对子","两对","对子","两对"]`）
- `winCownPoint`: 赢家（如 `["二"]`）
- `openTime`: 开奖时间

#### 盖牌数据流推测
```ascii
服务端(WebSocket/API推送) → 前端接收 → 更新DOM盖牌的CSS翻转状态
                                ↑
                         第5张牌数据在此刻才到达
                         （开奖瞬间，不在任何存储中预存）
```

## ⏱️ 阶段时序分析（BASH 梭哈 — 2026-07-23 高精度验证）

### 时间线（秒级精度）

```ascii
投注中(39s→0s) → 停止下注(4s→0s) → 派奖中(~8s) → 洗牌中(~2s) → 发牌中(~3s) → 投注中(39s)
   submit:✅            submit:🔒          submit:🔒       submit:🔒        submit:🔒       submit:✅
   roundNo:上一局结果    roundNo:不变        roundNo:更新     roundNo:不变      roundNo:不变     roundNo:不变
```

**关键结论**：
1. `roundNo` 的20张牌数据在 **『派奖中』阶段更新**（投注结束后~12秒）
2. 投注期间 `roundNo` 的数据是**上一局的结果**，非当前局的牌
3. `submit` 按钮在 『投注中』→『停止下注』的瞬间禁用（倒计时0秒）
4. roundNo 更新时 submit 已禁用约6~8秒

### 高精度验证方法

```javascript
(function(){
  setInterval(() => {
    const circle = document.querySelector('.circle')?.textContent || '?';
    const text = document.querySelector('.NiuText')?.textContent?.trim() || '?';
    const sb = document.querySelector('.submit');
    const sbSt = sb ? (sb.disabled ? '🔒' : '✅') : '🚫';
    const lis = document.querySelectorAll('.roundNo li');
    const rd = lis.length >= 20 ? Array.from(lis).slice(0,20).map(l=>l.textContent).join(',') : '';
    console.log(`${Date.now()} | 倒计时:${circle}s | 状态:${text} | submit:${sbSt}` + (rd ? ` | 🃏roundNo:${rd.slice(0,40)}...` : ''));
  }, 1000);
})();
```

### 多阶段数据源可用性矩阵

| 数据源 | 投注中(✅submit) | 停止下注(🔒) | 派奖中(🔒) | 洗牌/发牌(🔒) |
|:-------|:---------------:|:------------:|:----------:|:--------------:|
| `getPreNumber` (4张/家) | ✅ 可用 | ✅ 可用 | ✅ 可用 | ❌ 清空 |
| `.roundNo li` (20张) | **上一局数据** ❌ | **上一局数据** ❌ | ✅ **更新为当局数据** | ✅ 不变 |
| `LotteryResults` (20张) | **上一局数据** ❌ | **上一局数据** ❌ | **当局数据** ✅ | ✅ 不变 |
| submit 按钮 | ✅ 可用 | 🔒 禁用 | 🔒 禁用 | 🔒 禁用 |

## 💰 betSingle 正确格式（K3 1分快3 已验证）

```json
{
    "accountId": 1022198162,      // 数字！不是字符串！
    "clientTime": 1784673393892,  // 毫秒时间戳
    "gameId": "OG1K3",
    "issue": "20260722397",
    "item": ["{\"methodid\":\"K3002001001\",\"nums\":1,\"rebate\":\"0.00\",\"times\":\"1\",\"money\":1,\"mode\":1,\"issueNo\":\"20260722397\",\"codes\":\"大\",\"playId\":[\"K3002001010\"]}"]
}
```

**关键细节**：
- `accountId` 是**数字类型**
- `times` 是**字符串** `"1"`（不是数字）
- `playId` 是**数组**，必须有具体的 playId 值（不能是空数组 `[]`）
- playId 随玩法不同而变化（K3 和值-大 = `K3002001010`）
- `item` 是**JSON字符串数组**：每个元素是 JSON.stringify 的投注对象
- body 必须用 **gzip 压缩**后 base64

## ❌ 攻击方案评估

### clientTime 篡改 ❌ 无效

服务端**按期号状态判断**，不按 clientTime 判断。已封单的期号即使传截止前的时间戳也被拒（返回"本期已截止"）。

### cancelBet 竞态 ❌ 来不及

1分钟快3的周期：
```ascii
开售(0s) → ... → 封盘(54s) → 开奖(54s~60s) → 结果(60s)
                    ↑                        ↑
              不可撤单                    知道结果
```

封盘在开奖前6秒，知道结果时已封盘。撤单被拒。

### getPreNumber 预开 ❌ 数据对不上

API 返回的公开4张牌跟网页显示的不一致。可能多桌共用期号。

### WebSocket 监听 ❌ 不使用

```javascript
performance.getEntriesByType('resource').filter(r => r.initiatorType === 'websocket')
// → [] (无WebSocket连接)
```

## 💻 完整 Python 调用示例

```python
import hashlib, random, time, json, subprocess, base64, gzip, zlib

BASE_URL = "https://anndgbzg-368bfcom.xyz:6524"
PROXY = "socks5://127.0.0.1:10808"
UUID = "1e258a3145014df29489210a09abfc46"
JSESSIONID = "D7844A8C67094402A561A402EE31B3F2"

def md5(s): return hashlib.md5(s.encode()).hexdigest()
def si(s): return s.replace("2","B").replace("7","G")
def gen_ek(): return str(int(time.time()*1000)) + str(random.randint(0,10**15-1))

def call(action, params, token, compress=True):
    ek = gen_ek()
    ev = md5("anndgbzg-368bfcom.xyz" + f"/tools/_ajax/{action}" + si(ek))
    body = {"encryKey": ek, "encryValue": ev, **params}
    
    if compress:
        raw = json.dumps(body, separators=(',',':')).encode()
        data = base64.b64encode(gzip.compress(raw)).decode()
    else:
        data = json.dumps(body, separators=(',',':'))
    
    cookies = f"__uuid={UUID}; JSESSIONID={JSESSIONID}; token={token}"
    cmd = ["curl","-x",PROXY,"-k","-s","--max-time","15",
           "-X","POST",f"{BASE_URL}/tools/_ajax/{action}",
           "-H",f"cookie:{cookies}","-H","content-type:application/json",
           "-H",f"user-uuid:{UUID}","-H","x-build-info:2026-06-23T01:14:29.612Z",
           "--data-raw",data]
    
    result = subprocess.run(cmd, capture_output=True, timeout=20)
    out = result.stdout.decode('utf-8','replace').strip()
    
    try:
        parsed = json.loads(out)
        if isinstance(parsed, str):
            raw = base64.b64decode(parsed)
            try: parsed = json.loads(gzip.decompress(raw))
            except: parsed = json.loads(zlib.decompress(raw, zlib.MAX_WBITS|16))
        return parsed
    except:
        return {"error": "parse failed", "raw": out[:200]}
```

## 🪟 Windows 部署注意事项

### curl + subprocess 编码陷阱

```python
# ❌ 崩溃（GBK解码失败）
result = subprocess.run(cmd, capture_output=True, text=True)

# ✅ 正确
result = subprocess.run(cmd, capture_output=True, timeout=20)
out = result.stdout.decode('utf-8', errors='replace').strip()
```

### PowerShell 命令格式

`&&` 在 PowerShell 中报错，用**分号**替代：
```powershell
cd Desktop; python script.py
```

## 🔧 Debug 故障排除

| 错误 | 原因 | 修复 |
|:-----|:-----|:-----|
| 402 openresty | IP被CDN/网关拦截 | 从用户本地（国内IP）测试 |
| `参数格式不正确或请求不合法` | 加密格式/压缩/headers不对 | 对照浏览器Network Tab的curl |
| `本期已截止` | 期号已封单 | 下一期再试 |
| `code:nologin` | token过期 | 重新获取 `localStorage.token` |
| GBK `UnicodeDecodeError` | Windows编码 | 用 `bytes` 模式+手动解码 |
