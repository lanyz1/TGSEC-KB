# 网关必填参数链 oracle 与微服务未授权面测绘

实战:央选信息/灰豚族(chaoyongbushou.com / yangxuan.net / chaoyongmao.com / supsaas.com / sviptrader.com),2026-09-16。
出口:跳板机 sh 8.133.234.161(本地机器不出网)。

---

## 1. 核心技巧:让报错当探针,逐字走完必填参数链

**现象**:国产自研 API 网关把校验写成"逐项检查必填参数,缺哪个就把它的名字报出来":

```
{"code":1600003,"message":"Ct不能为空"}   → 补上 → {"message":"Ts不能为空"}
→ 补上 → {"message":"Si不能为空"} → 补上 → {"message":"Vn不能为空"} → 补上 → "非法时间戳"
```

**报错 = 参数名 oracle**。不要猜,写个循环照着报错补参数即可走完整条链:

```python
d = {"ct": "h5", "ts": str(int(time.time()))}
for _ in range(12):
    r = call(path, qs=list(d.items()))
    m = re.search(r'"message":"([A-Za-z]+)不能为空"', r)
    if not m: break                 # 链走完,进入值校验/路由
    d[m.group(1).lower()] = "1"     # ★ 必须小写!见下
```

### 三条必须记住的坑

1. **报错里的大小写 ≠ 真实参数名。** oracle 报 `Si` / `Ts`,实际只认小写 `si` / `ts`(PHP `$_GET` 大小写敏感)。
   大小写传错的表现极具迷惑性:传 `Ts=1` 永远回 "Ts不能为空";传 `ts=1` 立刻前进到下一项。
   **规则:oracle 给名字,自己按 lower() 试一遍,再看是否会前进。**
2. **报错文案会撒谎。** `Ts=1`(存在的值)报 "Ts不能为空";13 位毫秒报 "非法时间戳"。
   文案只能当"哪一项"的线索,不能当"为什么"的结论 —— 换一个变量重跑一次才下结论。
3. **同一条链上一个参数只改一个变量做差分。** 我曾把 `//`(双斜杠)返回的"页面未找到"误判成"两道校验已通过",
   实际是**路由未命中、中间件根本没跑**。看到"通过"先怀疑路径,再看校验。

### 该案例的最终契约(值校验阶段)

| 参数 | 合法值 | 说明 |
|---|---|---|
| `ct` | `h5` / `pc` / `ios` / `android` / `wx` | 客户端类型;非法值报"不支持的客户端类型" |
| `ts` | **10 位秒级**时间戳 | 13 位毫秒 → "非法时间戳" |
| `si` | **任意 8 字符** | 只校验长度(len==8),不校验内容 ⇒ 认证形同虚设 |
| `vn` | 任意非空 | 版本号,不校验 |

⇒ 整条"认证"降级为参数存在性 + 长度检查。**没有任何密钥参与**。
(注意:正确的参数名靠 oracle 走链 + 小写重试拿到,不要照抄上表去猜别的站。)

---

## 2. 网关/服务两层路径 oracle(判"存在"不靠猜)

同一套微服务架构里通常有两层 404,语义完全不同,**必须分开记账**:

| 响应 | 出自哪一层 | 含义 |
|---|---|---|
| `{"error_msg":"404 Route Not Found"}` | **网关** | 服务前缀不存在(Spring Cloud Gateway 没这条路由) |
| `{"code":"10404","message":"未找到该路径"}` | **微服务自身** | 前缀对、服务内路径不存在 |
| `{"code":401,"message":"暂未登录或token已经过期"}` | 微服务 | 路径存在,**要 token** |
| `{"code":422,"message":"参数缺失"}` / `"xxx不能为空"` | 微服务 | 路径存在且**免登录**,只缺参数 ★ |
| `405 Method Not Allowed` | 微服务 | 路径存在,**换方法**(GET↔POST) |
| `{"code":400,"message":"请求方式不正确"}` | 微服务(自研鉴权) | 同上,换方法 |

**扫描判据:422/"参数缺失" = 未授权可达面**(不是 401)。这条判据把"哪些服务整个没鉴权"一次性定位出来。
本案例服务清单(靠上面的 404 差分钉死,非猜测):
`micro-user-center` / `micro-auth` / `domain-shop` / `micro-creation-publish` / `clever-agent`。

同一轮里发现:
- `POST /clever-agent/wechat-customer/get-jsapi-ticket` → **200 返回真实 WeChat JSAPI ticket**(未授权)
- `micro-creation-publish` 整个服务 **免登录**:`share-info/getMaterialVideoDetail` 只校验 `id`,
  `content-publish-plan-record/publish-detail|claim|h5-publish` 同样免登录
- 只有 `micro-user-center/system/mangerUser/get-user` 是 401(管理员接口,需 token)

---

## 3. 端点级参数名 oracle(拿到参数名 → 再枚举 ID)

同一个思路往下用一层:参数名猜错 → "xxx不能为空";猜对但值无效 → "xxx不存在"。

```
getMaterialVideoDetail?shareId=1  → "分享链接id不能为空"   (名字错)
getMaterialVideoDetail?id=1       → "分享数据不存在"       (名字对!值无效) ★
```

一次小集合试探(≤10 个名字)就能锁定参数名,且**报错的措辞会告诉你字段的语义**
("分享链接id不能为空" → 这是个 share link id;`claim`/`h5-publish` 的 `id` 命中后 message 为 null)。
参数名确定后才谈 ID 枚举/越权。

同法确认的其它契约:
- `send-sms-code` 必填 `scene`,非法值直接**回显合法枚举**:`必须在指定范围 [1,2,3,4,5,6,21,22,31,41,51,60,61,70]`
  → `scene=1/2`(登录/找回类)对不存在的号回 **"手机号不存在"** = **手机号存在性 oracle**
- 注册接口在补 `Referer` 后才继续:见 §5

---

## 4. 从前端 bundle 抽"请求头契约 + 配置"(离线,零目标流量)

正确入口路径带 `/assets/`:`/h5-creator/assets/index-<hash>.js`。
**坑:少写 `/assets/` 会拿到一个 394 字节的错误页而不是 JS**,grep 全空,极易误判断"包里没有"。

把 chunk 全量下到跳板机后离线榨取(快、不产生目标日志):

```bash
grep -ohE 'url:"[^"]+"' *.js | sort -u        # 全部接口路径(本案例 23 条)
grep -oE 'applicationId[^,;]{0,40}' *.js      # 自定义头
grep -oE 'interceptors\.request\.use[^;]{0,400}' *.js   # 请求拦截器 = 头契约
grep -oE '(bucket|region)[^,;]{0,60}' *.js    # OSS/COS 配置
```

本案例从 `request-<hash>.js` 拦截器拿到**完整头契约**:

```js
e.headers["Custom-Cookie"]          = `token=${Ie.getToken()}`;
e.headers["creation-authorization"] = `Bearer ${...}`;
e.headers.applicationId             = "3";      // ★ 缺它报"请求头缺少applicationid参数"
```

以及基址选择逻辑:命中某模式走 `seller-api.<域名>`、否则走 `api.<域名>` —— **这类三元表达式是发现"第二套 API"的捷径**。
配置类常量同样明文:`bucket=yx-aicontent-creation` / `region=oss-cn-hangzhou` /
key 前缀 `` `aicreate/prod/${tenantId}/${yyyy_MM_dd}/` ``(tenantId 取自 localStorage,默认 "h5")/ 企业微信 corpId。

**自检**:拿到头契约后,若目标开始报"缺少 xxx 头/参数",说明契约读对了 —— 顺着补,不要回头再猜。

---

## 5. 两个"看似玄学"的门:Referer 与验证码

- **同一接口从 500 变业务错误,往往差一个 Referer。**
  `POST /micro-user-center/system/auth/register` 一直回 `{"code":500,"message":"登录地址异常"}`;
  加上 `Referer: https://h5.sviptrader.com/` 立即变成 `{"code":400,"message":"验证码"}` —— 第一道门是**来源校验**。
  国产 H5/小程序 API 遇到"地址异常/来源非法/签名错误"这类含糊 500 → **先补客户端 Referer / Origin / MicroMessenger UA 再谈别的**。
- **验证码门如何判"能不能绕"**(三个测试就够,别猜):
  - 不传 → "验证码不合法";传旧值 → "验证码不正确";传空 → 不合法 ⇒ **强制、不可跳过**
  - 报错差分 = **用户名存在性 oracle**:`验证码不正确` → `密码错误` 说明该账号存在(本案例确认 `admin` 存在)
  - 密码位有**格式前置校验**(`密码不合法`,6–12 位)⇒ 长度不合规时注入根本到不了 DB,别据此判"无 SQLi"
  - 固定测试码(0000/123456/8888/111111)全否定(`验证码不存在`)⇒ 码存在服务端存储里(Redis 类),不是硬编码

## 6. 边界与自律(本案例留下的硬规定)

- **`send-sms-code` 会真的给真人发短信。** 它同时是手机号存在性 oracle,但**每探一次就骚扰一个真人**
  ⇒ 只做 1–2 次确认,绝不批量枚举手机号;报告里写清楚"未做批量枚举"及原因。
- **`//` 之类假通过、`Referer` 门、报错文案撒谎** —— 全部按"一次改一个变量、看是否前进"处理,不堆叠假设。
- 同一 IP 上"PHP 运营后台"与"Java 微服务"常共存(本案例 121.196.214.43 上同时有 PHP `/admin/login/` 和 seller-api),
  **别用一个技术栈的结论去否定另一个**。
