# CTF 靶场: 0Pages 静态托管 Lab — ZIP 上传穿越 + 符号链接 + 限流处理

来源: 2026-08 会话 (38.60.125.120:30018, Vue3+Vuetify 前端 + Express 后端, "0Pages - Static Hosting", 60 分钟 CTF)
状态: 未拿 flag (进行中被限流打断), 但攻击面侦察完整, 方法可复用

## 靶场画像

- 静态托管平台: 注册 → 登录 → 上传 **ZIP** → 部署站点 → `/preview/{site_id}/` 访问
- Vue3 + Vuetify SPA; 后端 **Express** (`X-Powered-By: Express`)
- 认证 = **会话 Cookie** (无 JWT); 未登录访问 API 返回 `{"status":"error","message":"You must be logged in."}`
- 前端 bundle `/assets/index-C5rBFlsM.js` (721KB) 暴露全部 API

## API 清单 (从 bundle 尾部 axios 实例挖出)

```javascript
// 文件尾部: v=T.create({baseURL:"/api",timeout:3e4,withCredentials:!0,...})
// 导出映射: {fs as a, ds as b, cs as c, ls as g, as as l, us as t} = {transactions, sites, me, balance, login, transfer?}
POST /api/auth/register  {username, password, confirm_password}   // 注意: 必须带 confirm_password!
POST /api/auth/login     {username, password}
POST /api/auth/logout
GET  /api/sites                        // 我的站点列表
POST /api/sites                        // multipart: archive=<zip>  部署
DELETE /api/sites/{site_id}            // 删站点
GET  /api/sites/{site_id}              // 下载部署包 (实测会挂起/超时, 可能 404 或 bug)
GET  /api/sites/template               // 下载模板 zip
```

**注册字段坑**: 只发 `{username,password}` 报 `"Please fill all fields."` —— 前端验证规则是
`username 必须字母数字 /^[a-zA-Z0-9]+$/`、`password ≥4 字符`、`confirm_password === password`。
用户名强校验字母数字 → **注册口 SQLi/注入被封死**。

## 登录 SQLi 测试结果 (参考: 防注入的写法)

- `admin' OR '1'='1` / `' OR 1=1--` / UNION 注入 → 全部 `"Invalid username or password."` (参数化, 防注入)
- `admin" OR "1"="1` → **"Internal server error."** (双引号触发 500 = 报错信息泄露, 可当盲注 oracle)
- `admin` 注册冲突 → `"Username already exists."` 确认 admin 账号存在

## ZIP 上传攻击面 (核心)

部署: `curl -b cookies -X POST /api/sites -F "archive=@x.zip;type=application/zip"`
返回: `{"status":"success","data":{"site_id":"<uuid>","webroot":"webroot",...}}`

**webroot 固定为 zip 内 `webroot/` 目录**——zip 根放 index.html 或 public/ 部署后**无内容可服务**
(preview 全部 SPA fallback)。必须 `webroot/index.html` 结构。

### 路径穿越 (ZIP Slip) 实测结论
```python
# zip 内条目: webroot/../../pwned.txt
with zipfile.ZipFile('t.zip','w') as z: z.writestr('webroot/../../pwned.txt','DATA')
```
- 上传成功, 但**文件写到 webroot 上一级** (站点沙箱内), preview 读不到
- `/preview/{site}/../xxx` → **"Site not found."** (区别于 SPA fallback 的 HTML) ——
  证明服务器**保留 `..` 语义**在解析, 但被限制在站点沙箱内
- 深度穿越 `webroot/../../../../../tmp/x` 上传 → 请求**挂起/超时** (可能是 zip 解压路径被拒或慢)
- **"Site not found." vs SPA-fallback-HTML 是区分"路径被处理 vs 路径不存在"的诊断信号**

### 符号链接 (symlink) 实测结论
```python
zi = zipfile.ZipInfo('webroot/link_passwd'); zi.create_system = 3  # Unix
zi.external_attr = (0xA1FF << 16)  # S_IFLNK | perms
z.writestr(zi, '/etc/passwd')      # 链接目标
```
- symlink 条目**被保留** (部署成功, 列表里存在), 但 preview **不跟随解析**——
  返回链接目标字符串本身 (`/etc/passwd`), 不是目标内容
- 结论: 该平台解压不创建真实 symlink (或静态服务禁用 follow), symlink 攻击无效

### 其他
- 上传可部署任意 HTML → **存储型 XSS** 潜在 (若有 admin bot 访问 preview)
- Express SPA fallback: 任意未注册路径返回 200 + index.html (带 Last-Modified/ETag 静态头) —
  目录枚举 /api/flag /admin 全 200 是 fallback, 别误判为存在

## ⚠️ 限流教训 (本会话翻车点)

**高频请求触发服务器限流: 连续 ~30+ 个请求后, 所有请求返回 "Empty reply from server" (连接被重置, exit 52)**, 包括正常登录。等待 45s+ 仍被封。对策:
- **CTF 靶场请求间隔 ≥2-3 秒**, 别用 for 循环狂发
- 每次 curl 加 `--max-time` 防挂起
- 被封后**停止探测, 等待数分钟**, 期间只做静态分析 (读 JS/构造 payload)
- 分阶段: 侦察(慢) → 关键攻击(慢) → 验证(慢), 中间穿插本地分析

## 未竟方向 (若继续)
1. 找 admin 的 site_id (UUID 不可枚举, 看有无 IDOR/遍历接口)
2. ZIP 穿越写文件到应用目录 (需先探明解压基路径 = 应用根还是 data/sites/)
3. 存储型 XSS → admin bot 偷会话 (若有 bot)
4. 下载接口 GET /api/sites/{id} 挂起原因 (可能路径遍历读任意文件的前置)
