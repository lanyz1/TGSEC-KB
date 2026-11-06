## 九、ThinkPHP 5.x 渗透模式

### 9.1 Debug 模式利用

目标特征：HTTP 500 返回详细 ThinkPHP 错误页（含文件路径、变量类型错误）

**触发方法**：发送畸形参数导致变量类型错误
```
/?s=admin               → variable type error： array
/?s=admin/index/login   → variable type error： array  
/controller/action?invalid_param=array
```

**可利用的信息泄露**：
| 泄露内容 | 获取方式 |
|:---------|:---------|
| 框架版本 | 错误页底部 `ThinkPHP V5.0.24` |
| 文件路径 | 错误信息中的 `/application/...` 路径 |
| 数据表结构 | SQL 错误中的表名/字段名 |
| 存在但保护的目录 | `/application/admin/` → 403 (存在但不可访问) |

### 9.2 模块/控制器发现

通过错误信息判断模块是否存在：
```
/?s=admin/index/index   → 200 (页面内容)  → 路由存在
/?s=admin/index/login   → 500 (类型错误)  → 路由存在但参数错
/?s=admin               → 500 (类型错误)  → 可能加载了admin模块
/?s=nonexistent         → 404/200 (主页) → 模块不存在
```

/admin 路径的 403 (而非 404) 意味着目录存在：
```
/application/admin/  → 403 Forbidden (nginx 拦截了直接访问，但模块已安装)
```

### 9.3 固定验证码模式

ThinkPHP 重构的会员系统可能使用固定验证码值：
```
验证码输入框 value="1111"  → 固定值
/captcha 路径返回 PNG 验证码图片
checkLogin API 接受固定值验证码
```

---

