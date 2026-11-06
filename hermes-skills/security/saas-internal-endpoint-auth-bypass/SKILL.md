---
name: saas-internal-endpoint-auth-bypass
description: "SaaS内部RPC命名空间漏配鉴权+preAuthSign免密接管链。"
---

# SaaS 内部接口鉴权绕过家族

一套可横向替换的攻击面族:**「鉴权按路径前缀配 → 内部命名空间整片裸奔」×「免密签名由未授权接口白送」×「网关前缀 = 任意微服务路径」**。
适用于任何 Spring Cloud Gateway + 多租户 SaaS + 自研"微服务前缀"路由的目标。

## 何时用
- 多租户 SaaS,网关按 `/micro-xxx/**` 前缀转发到微服务
- 抓到任一微服务的 Swagger/OpenAPI(常整片泄露 `docs_*.json`),里面有 600KB 级路径契约
- 前端 bundle 里出现 `login-conform` / `pre-login` / `pre-sms-login` 这类**免 token 白名单**

## 核心判据(先钉死这 3 条,否则全是假阳性)

1. **`@Valid` 早于 auth 切面** ⇒ `422 参数缺失` / `405` / `400 请求方式不正确` **不等于**"无鉴权";只有**全合法 body** 打进去返回 401 才算有防护。
   - 反过来:**返业务错(500 / 400 业务码 / 409)= 已过鉴权** ⇒ 真越权。
2. **输入无关的统一响应 = 接口级熔断/下线**,不是你的参数错。
   差分法:打一个**确定不存在**的 ID(如 `userId=99999`)。若与"存在"的 ID 响应**完全一致** ⇒ 接口被熔断/风控,不是权限问题。
3. **数据真实性必须交叉验证**:同一实体用两条独立链路取(如 `talent-search` 的 `anchorUid` vs `anchorLiveInfo` 的 `user_id`),一致才算真数据。

## 步骤

### 1. 枚举内部命名空间(最容易裸奔的一批)
把 Swagger 全部 path 按前缀聚类,重点试这些**内部 RPC 命名空间**:
```
/rpc/**       /fegin/**   (故意拼错,常是另一套路由)   /feign/**
/opend/**     /inner/**   /internal/**   /open/**     /data-screen/*WithoutAuth
```
对照打**正常业务命名空间**(`/ranking/**` `/team-achievement/**` `/anchor-crm/**`):若它们 401 而上面那批 200/业务错 ⇒ **鉴权按前缀漏配**已坐实。
> 方法名带 `WithoutAuth`、`*NoAuth`、`Open*` 的接口是设计即开放,优先打。

### 2. 免密接管链(preAuthSign)
```
GET  /<prefix>/system/auth/list-tenants?userId=<N>          <- 免鉴权
     -> {tenantInfoList:[{userId, tenantId, nickname, roleList:[超级管理员],
                          preAuthSign:"<32hex>"}]}           <- 签名白送=漏洞本体
POST /<prefix>/system/auth/login-conform
     {tenantId, userId, preAuthSign, loginCreation:1, applicationId:<app>}
     -> {"accessToken":"...","refreshToken":"...","expiresTime":"2058-..."}
```
- `preAuthSign` **固定不变** ⇒ 等价永久后门
- 缺 `userId` 时:找 `tenant/user/list`、`mangerUser/page`、`mangerUser/belong-user-list`、任何带 `userId` 字段的导出/排行接口(`*_export`)
- 出口被 IP 白名单挡(`IP受限，不在可访问名单内`)⇒ 换跳板机出口重试

### 3. 网关前缀穿透微服务自身 actuator
```
GET /<service-prefix>/actuator            -> _links(常泄露内网端口,如 :9080)
GET /<service-prefix>/actuator/env | beans | heapdump | jolokia
```
每个微服务前缀都试一遍。只暴露 `health/threadPool` ⇒ 低可利用;**一旦 `env`/`heapdump` 出来 = 直接拿配置与内存凭据**。
> 注意:网关**根部** `/actuator` 常被自定义 404 处理器挡掉(那不代表服务没暴露),必须带服务前缀打。

### 4. 鉴权态回收(拿到 token 后必做)
把之前 401 的清单用 token 重打一遍:
- `401 -> 422/业务错` 即证明**鉴权墙已塌**
- 优先回收:用户/员工 `page`(常带 `mobile`)、菜单树 `list-menus`、部门 `dept/list`、角色 `role/list`、字典 `dict-data/list-all-simple`、协议 `protocol/list-show`

### 5. 分页参数名陷阱(极易误判"拉不全")
服务端**静默忽略**错误参数名,每页都返回同一批。**判别法:看响应里的 `pageIndex` 是否等于你请求的值**。
逐个试:`pageIndex` -> `pageNo` -> `current` -> `pageNum` -> `page`/`limit` -> `offset`/`limit`。
不生效的典型假象:`itemTotal=62` 但连拉 4 页都是同一批 20 条。
> 同名接口不同参数风格并存很常见:`auth-list` 用 `pageNo/pageSize`,`tenant/page` 用 `pageIndex/pageSize`。

### 8. STS 带 ListBuckets 型(账号级越权,比 oss-sign 更狠)

**特征**:边车/工具服务提供 `POST /<svc>/oss/sts`(常**零鉴权**,body 可为 `{}`),返回 `accessKeyId/accessKeySecret/securityToken/expiration`。
**判据与放大步骤**(必做,别只测已知桶名):
```python
auth = oss2.StsAuth(ak, sk, token)
for b in oss2.Service(auth).list_buckets().buckets:   # ★ 关键一步
    print(b.name, b.location)
```
拿到账号内全部桶后再逐个 `Bucket(auth, ep, name).list_objects_v2(prefix=...)`。
**经验**:这类 STS 往往给到整个账号的读权限 —— 实战中曾一次枚举出 21 个桶(素材桶/部署代码桶/SQL 转储/订单归档/DBS 全库备份/私有镜像仓库)。
**优先逛哪些桶**:`*-deploy*`/`*wockerspace*`/`*op-*`(部署代码 tar = 源码+凭据)、`*sql-dump*`/`*order-archiving*`(原始 SQL)、`dbs-backup-*`(表级备份,含 `admin_user`)、`cri-*-registry`(私有镜像)。
**常见路径模板**:`app-deployment/<app>/<subdomain>/<branch>/code/<branch>/<ts>/<name>.tar`。
**必须先测写权限再谈利用**:`put_object` 一个随机 marker → `head_object` 复核 → `delete_object` → 再 `head_object` 确认 404(零残留)。可写 ≠ 应该写:替换生产部署包是破坏性操作,须显式授权。

### 9. 源码 → token 伪造型(硬编码密钥 + 无签名 token)

**这是"零凭据拿后台超管"的最短路径**,命中条件三件套:
1. 拿到后端源码(见第 8 节部署桶);
2. token 生成函数用**对称加密且密钥硬编码**(`openssl_encrypt($plain,'AES-128-CBC',$key,...)`);
3. 解析函数**只解 payload、不校验有效期、无 HMAC**(常见 `parseToken()` 只 `substr` 取 userId)。

**实战模式(PHP/Yii2)**:
```php
$_aesKey = '<硬编码16字节>';
genToken($uid) = bin2hex(openssl_encrypt(sprintf('%09s',b62($uid)).sprintf('%06s',b62(time())),
                 'AES-128-CBC', $key, RAW, substr(md5($key),8,16)));
parseToken($t){ user_id = b62To10(substr($t,0,9)); }   // ← 无时间校验
```
**复刻要点**:
- `sprintf('%09s', …)` 在 PHP 里是**空格左填充**(不是 0 填充),照抄数字会算错;
- Base62 表要照抄源码(`0123456789a-zA-Z` 顺序);
- IV 常是 `substr(md5($key),8,16)` 这种可推导值;
- **多版本密钥都试**(master 与最新 test 版的 key 常不同;线上可能用新版 build)。
**验证三步差分**(不要只看状态码):
1. 带伪造 token 打开**已登录才可见的页** → 期待 200 + 尺寸远大于登录页;
2. 带伪造 token 打开 `/login` 路由 → 期待 **302**(已登录被踢走);
3. **不带 token** 同路径 → 期待 302/登录页。三者同时成立才算绕过。
**别忘了**:拿到后台后先扒菜单 HTML 的 `href` 列表 —— 真实路由与源码里的控制器名常常对不上,菜单才是权威路由表。

### 10. 什么时候必须停手(负面结论要写进报告)

- 后台无用户文件上传处理器(源码级 `grep move_uploaded_file|UploadedFile|->saveAs(` 只有第三方编辑器)/ 编辑器扩展名白名单不含 php → 别硬吹"可 getshell";
- MySQL/RDS 端口从出口超时(白名单) → 明确写"凭据已获取但未建立连接",不得暗示已拖库;
- 部署桶可写 → 只做"可写性验证 + 立即复原",不做替换生产制品的破坏性动作。

### 7. 跨应用 token 复用 + 后端路径 oracle(2026-09 央选/随心推实战)

**特征**:同一集团多个独立后端(Java 网关 + 独立 JSON 网关),token 由统一认证服务签发 →
A 网关的 token 被 B 后端直接采信。判据三步差分:

| 请求 | 响应 | 判读 |
|---|---|---|
| 无 token | `{"code":2000001,"message":"登录态已失效"}` | 被拦 |
| 带 token(任意应用) | `{"code":500,"message":"系统开小差了"}` | **鉴权层通过**,业务层异常 |
| 带 token + 正确应用头/签名 | 同上(无变化) | token 有效但缺业务档案 |

- **路径 oracle**:统一网关对**不存在的路由**返自定义 404 体(如 `code:404 页面未找到。`),对**存在但无权限**的路由返鉴权码(2000001)。
  用这两档差分即可测绘后端完整路由表 —— **无需鉴权**。此法在"所有响应同码"的网关上无效,须先取一真一假两路径校准。
- **`sg` 签名常不校验**:复刻客户端签名后对比"带签名/不带签名"响应,若一致 → 服务端根本没验签(只验 token)。
- **前端 bundle 硬编码签名密钥是常态**(实测 `API_SECRET="123456"`)。取法:`strings`/正则搜 `API_SECRET|SECRET=|sign=`,`getSign=` 附近必伴密钥。
- **JS 签名语义复刻要点**:key 排序后按 `key+String(value)` 拼接;对象→`[object Object]`、数组→逗号连接、bool→`true/false`、null→`null`。POST 把 `sg`+系统参数放 **query**,body 原样。
- **失败模式**:token 通过认证后业务层恒定 500 = 缺 seller/partner 档案上下文 → **需真实业务账号才能取数,不要谎称已越权**。

**陷阱**:不要在"所有路径都返同一错误码"的网关上声称枚举到了路由;必须先校准真假路径两档。:前端直取云 STS(策略常等于 `*`)
**特征**:后端边车把云存储签名发给前端直传,响应体里直接有 `accessKeyId/accessKeySecret/securityToken/expiration/bucket/region`。
**判据**:别只看返回体,**用官方 SDK 实际列桶**;手写 OSS V1 签名极易 `SignatureDoesNotMatch`。
```python
import oss2
auth = oss2.StsAuth(AK, SK, ST)
b = oss2.Bucket(auth, "oss-cn-hangzhou.aliyuncs.com", bucket)
sum(1 for _ in oss2.ObjectIteratorV2(b, max_keys=1000))   # 真实对象数
```
**为何是重漏洞**:签发方几乎从不按租户收窄 Resource ⇒ 把**全平台共用桶**的钥匙给了任意租户用户(实测单桶 84 万对象 / 5.28 TB,且可写可删)。
**写权限验证必须闭环可复原**:`PUT 探针 → GET 回读 → DELETE → HEAD 确认 404`,key 用 `pentest-probe/delete-me-<日期>.txt` 这类自说明路径。
**审计坑**:
- 客户端作用域探测(`ListBuckets`、跨区桶)权限不足时触发 SDK 退避重试,能把脚本卡死 ⇒ **先干掉正事(写验证/清单),再探作用域**;脚本加 `python3 -u` + 分页进度打点。
- `pip3 install` 被 PEP668 拦 ⇒ `--break-system-packages` 或 venv。
- 交付**完整对象清单**(`ObjectIteratorV2` 落盘 path+size),不要下载 TB 级内容。

## Pitfalls
- **别把"统一 400/403"当权限拒绝** —— 先做不存在 ID 的差分。
- **别把 `422`/`405` 当免鉴权** —— `@Valid` 与 HTTP method 校验都在 auth 切面前。
- **`code:0` + `data:null` 是空壳假阳性** —— 必须差分(用未注册号/不存在 ID)验证。
- **自增 ID 枚举接口(如 `?businessId=N`)通常无频控** —— 一次能拉几百条,但注意别把频率推到熔断。
- **`docs`/`api-docs`/`swagger-resources` 泄露是情报金矿** —— 优先离线全量拉,再在线打;比盲扫有效 10 倍。
- **写接口探测必须零副作用**(空数组/不存在的 ID),且**如实交代无法自证的部分**,别声称"无残留"。

## 交付物
- 客户/租户清单 -> CSV(公司/账号/手机/套餐/到期)
- 资产库 -> CSV(第三方账号 + 粉丝/播放等指标)
- 接管凭证 -> JSON(标注来源 userId/tenantId 与有效期)
- 报告需写明:哪条链路**已验证成功但有时间戳**(接口可能事后熔断),哪条是**当前不可复现**。
