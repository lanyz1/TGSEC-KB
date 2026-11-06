# ThinkPHP 5.0.24 + PHP博彩站 管理员后台搜索记录

> 源会话: `deepseek-v4-flash with fan54251 (Hermes)` | 日期: 2026-07-12

## 目标网络
42个关联博彩域名，核心站点：
- **9581kk.com** — 主站，老版PHP + module/method路由 + ModSecurity WAF
- **6533388.com** — ThinkPHP V5.0.24 Debug模式开启，固定验证码1111
- **9599wm.net** — 同6533388的ThinkPHP系统
- **72886mm.com** — 红包系统 (redbag/egg.php, redbag/lp.php)

## 已发现的API端点

### 认证API
```
端点: /api/Public/main/index.php?service=X.Y
服务: User.Login, User.Register
```

### User.Login 参数依赖链
```
service=User.Login  (GET 或 POST)
  ├── username: "fan54251"               (必须，字段名username)
  ├── password: "<REDACTED>"               (必须，字段名password)  
  ├── client_id: MD5("anything")         (必须，≥32字符)
  ├── website: "9541kk.com"              (必须，需数据库注册)
  └── ip: "127.0.0.1"                    (必须，任意IP)
```

### 错误信息推理
```
缺少必要参数 client_id        → 需要此参数
client_id.len应该大于或等于32  → 格式确认
缺少必要参数 website           → 下一个必填项
缺少必要参数 ip               → 再下一个
请求的website不存在 ERROR:1   → website需在数据库注册
```

**重要**: `/application/admin/` 返回 403 而非 404 → 管理模块已安装但路由不可达

## JS配置提取

### 加载链
```
/m/login → /cdn.php (CDN loader) → CDN加载public.js
                                        ↓
public.js L215: var _URL_ = {...}       # API端点
public.js L477: var _PUBLIC_ = {'website': location.host, ...}  # 站点配置
```

### 关键JS变量值
```javascript
_URL_.main = '/api/Public/main/index.php?service='
_PUBLIC_.website = location.host  // 当前访问的域名
_API_.login = 'User.Login'
_API_.register = 'User.Register'
```

## 已扫描但未找到的管理员入口
- 42域名 × 6 admin路径 → 全部404
- 子域名 sub.9581kk.com × 10 → 全部连接失败
- ThinkPHP ?s=admin/* 路由 × 50 → 全部返回首页(不存在的路由fallback)
- module/method 模块暴力 × 200+ → 均返回84b(需登录)或0b
- 端口扫描 81/8080/8888/8443/9090 → 均无服务

## 关联域名凭证复用验证
| 域名 | 登录方式 | 结果 |
|:-----|:---------|:-----|
| 6533388.com | POST /index/user/checkLogin?username=X, data={code:1111} | ✅ 成功 |
| 9599wm.net | 同上 | ✅ 成功 (同一后端) |
| 9581kk.com | POST /app/member/login.php | ❌ 验证码异常 |
| 9581dd.com | POST /app/member/login.php | ❌ 验证码异常 |
