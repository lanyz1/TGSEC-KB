# 路由面与请求契约的直取(strings 先行,反汇编后置)

适用:拿到 Go/GoFrame 系(GoFrame、gin 等)线上服务二进制或它的 `strings` 全量 dump,
要在**不反汇编**的前提下拿到权威路由表、字段名、列名、校验文案。

## 1. 全量路由表

框架把 OpenAPI/路由元数据编译进二进制,`strings` 即可正则出来:

```bash
grep -oE 'path:"[^"]{2,60}"[[:space:]]*method:"[a-z]+"' all_strings.txt | sort -u
# → path:"/user/thirdPartyUserTokenRefresh" method:"post" summary:"" tags:""
```

判定与坑:

- 数量级可达数百条,一次拿全(含内部/管理路由),免去按业务词猜端点。
- **元数据路径 ≠ 线上 HTTP 路径**:元数据常写 `/user/x`,线上真实是 `/v1/user/x`。
  前缀用**已知可用调用**定(客户端脚本 BASE 常量/一次 200 的请求),不要猜。
- 路由带方法:同一路径 GET/POST 可能只有一种存在 —— 用错方法会拿到 `Not Found`
  而不是「被拒」,别把它读成面被封。
- 同一 dump 里还有请求/响应结构名(`*v1.ThirdPartyUserTokenRefreshReq`)与
  `json:"…" orm:"…" dc:"…"` tag —— 见下。

## 2. 字段名 / 列名 / 校验文案

```bash
grep -oE 'json:"[a-zA-Z_]+"[^|]{0,60}' all_strings.txt   # 字段名 + 邻近校验标签
grep -oE 'orm:"[a-z_]+"' all_strings.txt                  # 表列名
grep -n '不能为空\|invalid\|not found' all_strings.txt     # 校验文案 ↔ 同段 tag
```

- GoFrame 风格 `Field json:"fieldName" v:"required#错误文案"`:字段名与它被拒时的文案写在
  同一 tag 里,黑盒收到哪句文案就能反推字段名。
- `json:"x" orm:"col"` 成对出现 = ORM 模型的字段↔列映射(建表/查询语义一次看懂)。
- **字段名与取值格式逐字照抄**(大小写、驼峰、数字还是字符串)。用自己觉得顺眼的写法替换 = 白跑一轮。
- 服务端落盘配置里的键名同属权威:`xxx.appID/appSecret/appSecretPn` 这类前缀键
  一次暴露「有几套凭据族、各叫什么」。

## 2.5 源码路径串:模块全集 + 「合并体」识别 + 文件模块指纹

Go 编译产物保留源文件路径串 ⇒ **不反汇编就能拿到项目的模块全集**:

```bash
grep -oE '/internal/controller/[A-Za-z0-9_/-]+\.go' all_strings.txt | sort -u
grep -oE '/internal/(model|service|logic|dao|middleware|consts|cmd)/[A-Za-z0-9_/-]+\.go' all_strings.txt | sort -u
```

- controller 文件全集(实测单服务 262 个)比路由表**更全**:含**未注册 / 内部 / 管理**路由的模块名,
  是「这个进程到底有哪些业务能力」的权威清单。按业务词过滤即得目标面(如 `*file_upload*`)。
- 同一 dump 里 `*Req`/`*Res` 结构名 + `api/<模块>/v1.XXX` 串 = 模块 ↔ 契约对应关系。

**合并体识别(高价值)**:自研服务二进制里出现**另一套全家桶的源文件名** ⇒ 两套代码被编译进
**同一个进程**(实测:自研钱包二进制里混有 gin-vue-admin 的 `exa_file_upload_and_downloads.go` /
`exa_files.go` / `casbin_rule.go`)⇒ 三条推论:

1. **管理域名死了 ≠ 管理面死了**:管理路由仍在这个业务进程里,拿业务域名解析出的 IP ×
   `{80,443,8080,8888}` × `Host: admin.<域>`(也试业务 Host 自己)打同一批管理 API。
2. 已掌握的该框架接管链(泄露的 `jwt.signing-key` → 伪造超管票 → 系统配置写 / 上传写)可直接复用,
   别因为「管理域名不通」就把它归为死路。
3. 框架自带**上传 / 导出模块**就是现成的任意写原语(如 `local.path`),先去路由元数据里找它的路由名。

**文件 / 上传模块指纹串**(有其一即存在文件管理能力):

```
<h1>Index of %s</h1>            # 目录列举(能列任意目录)
os.Create failed for name "%s"  /  Write data to file "%s" failed
os.Remove failed for path "%s"  /  io.Copy failed from "%s" to "%s"
```

把它当**静态搜索目标**:先用这些串确认能力存在,再用路由元数据里的 `*file*` / `*upload*` 路径定位入口。

## 3. 路由面 sweep(授权目标上)

拿全表之后批量打一遍,按**业务错误码**分类,而不是按 HTTP 状态码:

| 响应 | 含义 | 动作 |
|---|---|---|
| `ErrCode 0` + ResData | 通(可能未鉴权) | 重点看数据面 |
| `ErrCode 403 access denied` | 路由存在,鉴权/权限不足 | 找该端点要的凭据族 |
| `ErrCode 65 Not Found` | **路由不存在** | 先回查拼写与 HTTP 前缀,再判死 |
| Need Login / 401 | 需要用户票 | 补票重打 |

direct-origin(裸 IP + Host 头)通常没有 CDN/WAF 限速,适合这种几十~几百发的一次性 sweep;
但 **HTTP 状态码会骗人**(框架把业务错统一成 200),分类必须读 body 里的业务码。

## 4. 声明「该面已封」之前的自检(三条缺一不可)

1. **路径逐字来自产物**(二进制元数据 / JS bundle / OpenAPI),不是英文直觉 ——
   真实产品存在拼写错误的路由,例如 `/asstes/getMemberAssetSummary`(`assets` 拼成 `asstes`)。
   按正确英文探测得到 404,会把活路记成死路,而且这个结论会被后续所有轮次继承。
2. **参数名与取值格式逐字来自 tag**,并且试过产物里出现的每一种形态
   (数字 id / 字符串前缀 id / 大小写变体)。
3. **该端点要求的凭据族自己是否已持有**:应用级(appId/appSecret)与用户级
   (token/secretKey)是两套闸门;注册/登录响应里常直接下发 `appKey`/`appSecret`
   (形如 `kbitAppKey: kbappSys`),而服务端落盘配置里另有 `xxx.appID/appSecret` 一套 ——
   两处都找,别只看客户端。

> 「四路全封」这类结论如果建立在 404 与猜测拼写之上,要重新自检一遍再向用户陈述;
> 把「路由不存在」误报成「漏洞面不存在」是最贵的一类错。
