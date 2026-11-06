# 出口节点取证与验证(从 v2rayN 取配置 → 判活 → 不误判)

用户说「出口 IP 我 v2 里面不是有吗,你复制配置自己去用就行」时,照下面走。
2026-09 实战(9v111 战线)。

## 1. 从 v2rayN 里把节点配置抠出来

不用问用户抄配置 —— 节点库就在本地 SQLite。先定位安装目录:

```bash
find /d /c/Users/Administrator /c/Program\ Files -maxdepth 4 -iname '*v2ray*' 2>/dev/null
# 典型:C:\Users\Administrator\Desktop\新v2包\v2rayN-windows-64-SelfContained\
#   guiConfigs\guiNDB.db   ← 节点库(SQLite)
#   guiConfigs\guiNConfig.json ← 本机 inbound / 当前选中节点 / RunningCoreType
#   binConfigs\            ← 生成的 xray 配置(常为空,别指望)
```

Dump 节点(字段名即 `Address` / `Port` / `Id` / `Security`):

```python
import sqlite3
p=r'<...>\guiConfigs\guiNDB.db'
c=sqlite3.connect(p); cur=c.cursor()
cur.execute("select name from sqlite_master where type='table'"); print(cur.fetchall())
# 表:ProfileItem(节点) / SubItem(订阅) / ...
for r in cur.execute("select * from ProfileItem"): print(r)
```

`guiNConfig.json` 里 `RunningCoreType`(2=Xray)、当前 `IndexId`、本地 socks 端口(`inbound`)。

## 2. ⚠️ 最大的坑:账号/密码可能是反的

**`ProfileItem.Id`(短 hex,如 `c6f8d10e`)= 密码;`ProfileItem.Security`(长串,如 `q0_...-ddcn-...`)= 账号。**
而厂商给的表格可能按别的顺序排版 —— 我第一次按表顺序填 user/pass,**四个 curl 全空**,
白判「这不是裸 SOCKS5,需要客户端」。

**一次认证失败 ≠ 协议不对。先对调 user/pass 重测,再考虑装客户端。**
判定成功:节点其实是**标准 SOCKS5**,`curl --proxy socks5h://<账号>:<密码>@<host>:<port>` 直接可用,
不需要任何客户端 —— 这比在跳板上装 xray 复刻节点省事得多。

## 3. 在跳板上用(不要用本机出口)

用户铁律:渗透流量全走跳板,含单条探测。节点配置拿到后在**跳板**上 curl:

```python
P='socks5h://<账号>:<密码>@q0_xxxx.ga6x.com:30801'
subprocess.run(['curl','-sS','-k','--max-time','35','--proxy',P,'https://api.ipify.org'],
               capture_output=True,text=True)
```

## 4. ⚠️ 判「目标不可达」的正确姿势(别被单节点抖动骗了)

**单节点会间歇性 `connection to proxy closed` / 返回 `000`,同一目标前一次 000、下一次 200 是常态。**

判死刑前必须:
1. **换第二个可用节点**重测(手上常不止一个;本案例 `14.119.66.81:30901` 稳、`q0_*.ga6x.com:30801` 抖)
2. 同一节点**重试 ≥2 次**
3. 看 `time_connect`,它区分两种情况:

| 观测 | 含义 | 动作 |
|---|---|---|
| `000` + `time_connect=0.000` | 连接压根没建立(代理侧或目标侧丢弃) | **换节点/重试**,别急着定论 |
| `000` + `time_connect>0` | TCP 通了,TLS/HTTP 层失败 → **主机是活的** | 换正确 SNI、试 `http://`、看证书 —— 别当不可达 |
| 稳定非 0 状态码 | 可达 | 继续 |

只有**多节点 × 多轮 × 80/443 全部 `time_connect=0.000`** 才能写「该主机已下线/被过滤」。
本案例 `painel.<厂商域>` 就是这样核实为真下线的(中国出口 + 美国出口 + 双节点重试全 0.000);
同期另一条线曾被单节点抖动误判成不可达,浪费一轮。

## 5. 节点稳定性记录(2026-09)

- `q0_1746307169.ga6x.com:30801` 出口 `70.39.130.220`(美国):能用但**易抖**,连续请求会 `connection to proxy closed`
- `14.119.66.81:30901`:更稳,长任务优先用它
- 两条都挂在一个出口池上,**健康检查用真实目标而不是 ipify**(国内电信节点打 ipify 常超时,ipify 空 ≠ 隧道坏)
