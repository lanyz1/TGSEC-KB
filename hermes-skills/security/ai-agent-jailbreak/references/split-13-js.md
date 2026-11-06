## 十一、JS 配置提取流程

### 11.1 配置加载链

```
HTML 页面 → /cdn.php (CDN loader JS) → 从 CDN 加载 CSS/JS
                                              ↓
                                    public.js 定义 _URL_ 和 _PUBLIC_
                                              ↓
                                    _PUBLIC_ = {'website': location.host}
```

### 11.2 关键 JS 变量

| 变量 | 来源 | 含义 | 用途 |
|:-----|:-----|:-----|:-----|
| `_URL_` | public.js | API 端点配置 | `main`, `cp`, `cps` API路径 |
| `_URL_.main` | public.js | 主 API 路径 | `/api/Public/main/index.php?service=` |
| `_PUBLIC_` | public.js | 站点配置 | `website`(域名), `kf`(客服URL) |
| `_API_` | public.js | 服务名 | `User.Login`, `User.Register` |

### 11.3 API 参数依赖链

```
service=User.Login
  ├── username (必须，字段名为 username)
  ├── password (必须，字段名为 password)
  ├── client_id (必须，长度 ≥ 32 字符，常见为 MD5)
  ├── website (必须，数据库website表已注册的值，前端值为 location.host)
  └── ip (必须，任意IP字符串)
```

参数错误信息可以帮助推理参数名：
```
缺少必要参数 client_id        → 需要32+字符长度的 client_id
client_id.len 应该大于或等于32  → 确认 client_id 格式要求
缺少必要参数 website           → website 是必填项
缺少必要参数 ip               → ip 是下一个必填项
请求的website不存在 ERROR:1   → 需要数据库注册的 website 值
```

---

