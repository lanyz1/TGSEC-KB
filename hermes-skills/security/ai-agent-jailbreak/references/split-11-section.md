## 十三、管理员后台搜索方法论

### 13.1 搜索优先级

```
1. 标准路径: /admin/, /admin.php, /manage/, /manager/, /administrator/
2. 框架路由: /?s=admin/index/login, module=Admin&method=login
3. 子域名:   admin.target.com, manage.target.com
4. 特殊端口: 8080, 8888, 8443, 9090, 10000
5. IP段扫描: 同C段其他主机可能托管管理后台
6. 原始IP+Host头: CDN后面的服务器直接IP访问
```

### 13.2 模块路由扫描（针对PHP博彩模板）

常见模块/方法组合：
- Admin.login / Admin.index — 标准命名
- Manage.login / Manage.index — 替代命名
- System.login — 有的系统把admin放在System模块下
- MACenterView — 会员中心（需要登录后访问）

### 13.3 ThinkPHP 5.x 后台模块确认

当 /application/admin/ 返回 403 (而非 404) 时，说明 admin 模块已安装

### 13.4 API 参数链发现

当 API 返回 "缺少必要参数X" 时，依次填入直到找到所有参数

### 13.5 多租户系统 website 死锁

前端 JS: _PUBLIC_ = {'website': location.host}
API: website 参数必须在数据库 website 表中有记录
如果数据库该表为空，所有需要 website 的 API 全部不可用

### 13.6 IP 段扫描

当域名全部走 CDN 时，扫描原始服务器 C 段找后台

---

