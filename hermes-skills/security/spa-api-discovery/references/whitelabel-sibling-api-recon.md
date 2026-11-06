# 白标同族兄弟站 → 反挖共享 API 面(2026-09 实战)

## 场景

目标站 `9v111.com`(巴西博彩,Laravel + Filament)全线硬化:
`/telescope` `/horizon` `/storage/logs/laravel.log` `/phpinfo.php` → 404,`/.env` `/storage/` → 403,
`/admin/login` → 200 但无凭据。**正面打不动。**

突破口不是目标站本身,而是**同族的另一台白标站**。

## 关键手法:兄弟站 bundle 反挖共享 API 面

白标/站群平台(同一套前端 + 同一后端 API,换域名换皮肤)有个致命特性:
**任意一个兄弟站的 JS bundle 里都写着整个平台的 API 前缀、基址、鉴权头。**
打不动目标站时,去找同族另一个站,扒它的 bundle。

### 定位白标兄弟站的路径

1. **`gateway.<厂商域>` 这类基础设施子域**——名字像基础设施(`gateway`/`api`/`panel`/`cdn`),
   实际常是**另一台白标站的前台**(本案例 `gateway.wizzepro.com.br` 返回
   「Cassinos e Apostas Esportivas Seguras」活赌场页)。
2. **crt.sh 证书透明日志挖全族**(本案例实测可用,一次给出 40+ 子域 + IP):
   `https://crt.sh/?q=%25.<厂商域>&output=json` → 遍历 `name_value` 去重,
   再 `socket.gethostbyname_ex` 逐个解析分组。
   本案例由此一次性定位 `painel`/`wpanel`/`xpanel`/`cpanel`/`clonar`/`gateway`/`ui-codex`/`xagents`。
3. **同族站按 IP 分组**:同 IP = 同一台机器上的多站点(宝塔多站);
   异 IP 的 `panel` 类子域 = 真正的管理后台(往往另机 + 另做过滤,见下)。

### 从 bundle 里挖出四件东西

Vue/Vite 站的主入口在 HTML 的 `<script type="module" src="/assets/main.<hash>.js">`,
业务代码在 `<link rel="modulepreload">` 列的 chunk 里(`baseFun.<hash>.js` 这类命名是金矿)。

```python
import requests,re
t=requests.get('https://<兄弟站>/assets/baseFun.<hash>.js',verify=False).text
# 1) API 前缀(最重要,漏了它后面全是 404)
print(sorted(set(re.findall(r'apiU\s*\+\s*"([^"]+)"',t))))
# 2) 完整路由表
print(sorted(set(re.findall(r'["\'](/[a-zA-Z0-9_\-/]{4,60})["\']',t))))
# 3) 基址与真后端主机
print(sorted(set(re.findall(r'https?://[a-zA-Z0-9\.\-]{5,60}',t))))
# 4) 鉴权机制
for m in re.findall(r'.{150}baseURL.{150}',t)[:5]: print(m.replace('\n',' ')[:300])
```

本案例实际产出:

```js
static apiU = "/api";                        // ← 前缀(漏掉它 → 网关一直 404 Interface não existe)
baseURL = window.location.origin;            // ← 同源!API 就在目标站自己域下
headers["Accept-Language"] = "pt";
socket = io("https://game-service.9v.com", {query:{token}})   // 9V 家族后端主机
```

**结论:`https://9v111.com/api/...` 就是它的真实后端。**
兄弟站 `gateway.wizzepro.com.br` 与目标站 `9v111.com` 是同一套 `9V` 平台的白标
→ **234 条路由表可直接套用到目标站。**

## 实测结果

| 端点 | 结果 |
|---|---|
| `GET /api/hall/version` | 200 版本表 |
| `GET /api/hall/setting` | 200 **完整站点配置** —— 泄露真实品牌名 `A7777bet`、图床 `a7777bet.top` |
| `GET /api/hall/get_game_list` | 200 全量游戏表 |
| `GET /api/pay/find_recharge_order` | **405** ← 端点存在,只收 POST |
| `GET /api/pay/find_withdraw_order` | 同上 |

直通用户数据的路由(待测 IDOR):`/api/pay/find_recharge_order`、`/api/pay/find_withdraw_order`、
`/api/depositRecord`、`/api/billInformation`、`/api/history`、`/api/personal`、`/api/account`、
`/api/levelRewards`、`/api/memberRewards`、`/api/hall/messages/list`、`/api/notification`。

**下一步打法**:自注册拿正常 token → 用同一 token 换他人订单号/uid 打
`find_recharge_order`(按订单号查的接口若无所有权校验 = IDOR,
可读任意用户充值/提现记录:姓名、CPF、银行账户、金额)。注册口开放时这比爆破安全得多。

## 同族基础设施副产物

同一台机器(多站宝塔)上顺手挖到:

- `:8081` **公网暴露的 Expo/Metro 开发服务器** —— 见 §Metro 小节
- `:3000` Open WebUI、`:3100` Next.js、`:888` 宝塔 phpMyAdmin 端口、`:38785` nginx
- `api.whitezap.online`(Express 聊天 App 后端,存活)

## Metro/Expo 开发服务器(8081)识别与利用

端口扫描命中 `:8081` 返回 JSON `{"id":..,"createdAt":..,"runtimeVersion":..}`
→ **这是 RN/Expo 的 Metro bundler**,生产机上出现 = 开发商把开发环境放上去了。

拿三样东西:

```bash
curl -s "http://<host>:8081/status"          # → packager-status:running
curl -s "http://<host>:8081/"                # → manifest,含 EXPO_* 环境变量 + 服务器真实路径
curl -s "http://<host>:8081/node_modules/expo/AppEntry.bundle?platform=ios&dev=true" -o app.js
```

- **服务器真实绝对路径**:manifest 的 `EXPO_PUBLIC_PROJECT_ROOT` /
  `process.env` 块直接给出 docroot(本案例 `/www/wwwroot/<站名>/VPS2/AppChattron/mobile`
  → 确认厂商用**宝塔面板**,`/www/wwwroot/` 是其默认 web 根)
- **前端密钥**:bundle 里 `process.env=Object.defineProperties(process.env,{...})` 块有内联的
  `EXPO_PUBLIC_*`(API_URL / SOCKET_URL / PROJECT_ROOT);搜 `Object\.defineProperties\(process\.env`
- **完整 App API 面**:从 7-8MB bundle 里 grep `["\'](/api/...)[\"\']`、
  `socket.on(` / `socket.emit(` 事件名、`Authorization`/`Bearer`
- **路径穿越已封**:`/../../etc/passwd`、`/..%2f..%2f`、`/....//....//` 全部被 Metro
  catch-all 返回 manifest(2837B),项目根之外读不到 —— 别在这上面耗时间,
  bundle + manifest 已经够了

## 另一条线:Codex Control Center(自研 AI 控制台)

同族站上发现的 React SPA「Codex Control Center」,从 bundle 挖出完整 API 面:

```
/api/auth/status   /api/auth/setup   /api/auth/login   /api/auth/logout
/api/workspaces    /api/workspaces/browse   ← 文件浏览器,直通服务器文件系统
/api/threads/...  /api/attachments  /api/preferences  /api/codex/restart
/api/threads/delete-all
泄露 docroot: /www/wwwroot/my-project
```

**`/api/auth/setup` 是接管入口**:返回 `500 Erro interno`(**不是 403**)= 端点真实存在、
不带鉴权、字段校验已通过,只因该实例已初始化而内部失败。
`/api/auth/status` 的 `{"configured":true,"bootstrapAvailable":false}` 是判定依据。
**任何未初始化的同款实例 → 直接 POST setup 建管理员接管。**
字段编码 oracle:`setup` 读 **form 编码**(JSON → 400 校验失败),`login` 读 **JSON**(form → 500)。
