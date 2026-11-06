## 七、API配置安全

### 7.1 CORS高级绕过
```http
# 检测：任意Origin反射+Credentials
Origin: https://attacker.com
Access-Control-Allow-Origin: https://attacker.com
Access-Control-Allow-Credentials: true

# 反射绕过变体：
Origin: null                          # iframe sandbox
Origin: https://target.com.attacker.com
Origin: https://attacker.comtarget.com
Origin: https://target.com.evil.com
Origin: https://<EMAIL-REDACTED>
# 前缀/后缀匹配缺陷逐一测试

# CORS+CSRF组合：先跨域读Token再带Token发请求
# 不预检的简单请求利用（POST form text/plain）
```

### 7.2 HTTP安全头与缓存
```http
# 敏感API的缓存投毒/泄露：
# 响应无 Cache-Control: no-store → CDN/浏览器缓存含个人数据
# 通过 ?cb= 时间戳参数生成可预测缓存键 → 撞缓存拿他人数据
# 验证：Vary头缺失、s-maxage、CDN缓存键只含部分参数

# 缺失安全头检查：
Strict-Transport-Security / X-Content-Type-Options
X-Frame-Options / Content-Security-Policy
# 注意 X-API-Version / X-RateLimit-* 暴露限速与版本信息
```

### 7.3 API版本与影子API
```
# 影子API发现：
# 版本漂移：/api/v1 vs /api/v2 行为/鉴权差异
# 测试环境：staging./beta./test./dev.子域
# 内部端点：/internal /admin /migrate /legacy
# 未注销的旧端点：/api/users_old /api/userlist
# 方法差异：v1用POST v2用GET（权限检查位置不同）
```

### 7.4 调试/诊断端点
```
/actuator/health /env /mappings /beans /jolokia /heapdump /logfile /trace /shutdown
/debug/pprof /debug/vars /debug/pprof/cmdline   (Go pprof泄露)
/swagger-ui /graphiql /console
/_cat/indices /_plugin/head                     (Elasticsearch)
/console/weblogic/ (WebLogic)
/#/healthz /readyz (K8s探针泄露Pod信息)
# heapdump下载后用Eclipse MAT/JProfile搜密码/AK/SK/JWT密钥
```

