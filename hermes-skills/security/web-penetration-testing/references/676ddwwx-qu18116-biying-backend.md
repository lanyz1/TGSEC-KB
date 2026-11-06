# 676ddwwx.cn → qu18116.cn → ag.61995q.com:7777 多架构赌博平台

## 架构总览

```
676ddwwx.cn (ASP.NET 网关层)
  ├─ /ZRhVA?token=xxx          → 302 → /GE/CC/VALIDATOR
  ├─ /GE/CC/VALIDATOR?key=...  → Token签名验证 (MD5.MD5.timestamp)
  └─ after validation → iframe → qu18116.cn

qu18116.cn (ASP.NET 应用层)
  ├─ /Main/ShowPortal?t=token  → 校验密码页
  ├─ /Main/Login               → POST: t=token, password=pwd → 0/-1/-2
  ├─ /Main/Stage               → 游戏主界面 (340KB, pwd参数非必需)
  ├─ /Main/GetLuZiData         → 历史开奖数据
  ├─ /Main/ShowDesign          → 旅游伪装模板
  └─ /Main/ShowModifyPwdPage   → 修改密码

ag.61995q.com:7777 (PHP BIYING 管理后台)
  └─ /cl/index.php?module=System&method=xxx

api8890.com (WebSocket 实时通信)
```

## 技术栈

| 层 | 技术 | 识别方式 |
|:--|:-----|:---------|
| 网关 | ASP.NET MVC 4.0 / IIS 10.0 | X-Aspnetmvc-Version: 4.0, Server: Microsoft-IIS/10.0 |
| 前端 | layuiAdmin + jQuery + 混淆JS | /Scripts/layuiAdmin/layuiadmin/layui/css/layui.css |
| 游戏前端 | index.js (420KB ` ` 重度混淆) | Unicode escape + XOR数字 + 字符串反转 |
| 通信 | WebSocket | wss_domain = 'api8890.com' |
| 后端管理 | PHP + BIYING模板 | Apache + frameset布局 + module=System路由 |
| 服务器 | Google Cloud | IP: 34.96.197.130, 34.80.211.95 |
| CDN | MJCDN + Cloudflare + 多CDN | teytest2.mjcdn.com, nxy.ycybbx.com, mca.klssy.com |

## 游戏参数

- 游戏: 澳洲幸运5前四(5分钟)
- gametype: 11 (ao5)
- 内部账号: robot = 'jxx5208', memberid = 'wxid_6UkgKKTJZ2'
- WebSocket: api8890.com
- 内部服务器: server_domain = 'ff98-8200'

## BIYING 后台访问

后台主入口: `https://ag.61995q.com:7777/cl/index.php`

| module | method | 说明 |
|--------|--------|------|
| System | login | 登录页 |
| System | first | 管理首页(框架) |
| System | all | 全局配置? |
| Member | index | 会员管理 |
| Admin | index | 管理员 |
| Agent | index | 代理管理 |

后台页面使用 frameset 布局:
```html
<frameset rows="*,0,0,0">
  <frame name="mem_index" src="cl/index.php?module=System&method=first">
  <frame name="act" src="">
  <frame name="upupMsg" src="/cl/upupFlash.php">
  <frame name="refresh" src="refresh.php">
</frameset>
```

## BitBrowser API 获取浏览器ID

当 BitBrowser API 的 `/browser/list` 返回 totalNum>0 但 list=[] 时：

```python
import sqlite3
# BitBrowser 数据库路径
db_path = "~/AppData/Roaming/BitBrowser/db.sqlite"
conn = sqlite3.connect(os.path.expanduser(db_path))
cursor = conn.cursor()

# 查询浏览器窗口表
cursor.execute("SELECT * FROM browser_persistent_data")
columns = [c[1] for c in cursor.execute("PRAGMA table_info(browser_persistent_data)")]
for row in cursor.fetchall():
    print(dict(zip(columns, row)))
    # browser_id 字段即 BitBrowser 环境ID

# 浏览器临时数据（含IP信息）
cursor.execute("SELECT * FROM browser_temp_data")
for row in cursor.fetchall():
    print(row)
```

## CDN 源站 IP 发现 (Cloudflare DNS)

```bash
# 递归 DNS 查询穿透多层 CDN
curl -s "https://cloudflare-dns.com/dns-query?name=target.com&type=A" \
  -H "Accept: application/dns-json" | python3 -c "
import sys,json
d=json.load(sys.stdin)
for a in d.get('Answer',[]):
    print(f'{a[\"name\"]} → {a[\"data\"]}')
"

# 实战案例: qu18116.cn 的 CNAME 链
# qu18116.cn → teytest2.mjcdn.com → dljpjq1.322220.xyz → 194.147.100.xx
```

## CDP WebSocket 连接到 BitBrowser Chrome

BitBrowser 打开浏览器环境后返回:
```json
{
  "ws": "ws://127.0.0.1:51741/devtools/browser/59c139fb-...",
  "http": "127.0.0.1:51741",
  "driver": "chromedriver.exe"
}
```

但 WebSocket 连接可能被 Origin 限制:
```
Rejected... Use --remote-allow-origins=*
```

Python 原始 socket 握手法 (需正确掩码处理):
```python
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("127.0.0.1", 51741))
# 发送 WebSocket 握手请求...
# 注意: 客户端帧需要 XOR 掩码 (client-to-server masking)
```
