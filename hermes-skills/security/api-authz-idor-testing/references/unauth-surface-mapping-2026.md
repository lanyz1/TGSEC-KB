# 未授权面测绘与鉴权分层判定(实战案例)

来源:qavlor.vip「Multicoin」加密盘(uni-app + ELADMIN/Spring Boot + FastJSON 1.2.70),2026-09。
价值点:在**没有任何账号**的情况下,把整个后端鉴权面打完,并从免鉴权配置里直接读到平台默认提现密码。

## 1. 从前端封装读后端白名单(最快的一步)

uni-app 的请求封装会给**每个调用点**带鉴权标记,直接 regex JS bundle:

```js
gG(e,t)=ke.post(`/v1/api/defi/exchange?amount=${e}&accountId=${t}`,{})
lG(e)=ke.post("/v1/api/defi/createDefiAddress", e, {custom:{auth:!1}})
```

`auth:!1` = 免鉴权,`auth:!0` = 需鉴权。**这把后端白名单镜像出来了**,不用盲爆路径。
实测一次正则拿到 **58 条路径**,其中 13 条 `auth:false`。

⚠️ 坑:**前端标 `auth:false` ≠ 后端真免鉴权**。实测 `/v1/api/defi/withdraw` 和 `/defi/exchange`
在前端**漏写了 auth 标记**(看着像免鉴权),但后端实际返回 401 —— 是前端疏漏,不是漏洞。
**必须用下面的方法探针实测,不能只信前端标记。**

## 2. 方法探针分类(非破坏性,一次拿全鉴权面)

对每条路径同时打 `POST {}` 和 `GET`,按响应家族归类:

| 响应 | 含义 |
|---|---|
| `{"code":401,"msg":"UNAUTHORIZED"}` / Spring `{"status":401}` | 已鉴权 |
| `400 Request method 'X' not supported` | 路由存在,方法错 → 拿到真实方法 |
| `{"code":10006,"msg":"请求参数校验异常"}` | ★ 免鉴权,已进业务逻辑 |
| `{"code":40001,"msg":"邀请码不存在"}` | ★ 免鉴权 + 暴露了业务规则 |
| `404` | 路由不存在(如 `getProxyUser/` 需带 id) |

**实测结论(58 条)**:恰好 13 条免鉴权,其余全 401。**所有资金接口
(withdraw/exchange/transfer/updateBalance/setPayPwd/submitPayment/addUserBank/createAddressByUserId)
鉴权都正确** —— 不存在免鉴权提现。

### ⚠️ 资金接口的铁律
只用**无效参数**分类:空体 / `amount=0` / 不存在的 `accountId`。
**绝不能用有效参数去"试试它要不要鉴权"** —— 可能真的发起一笔真实提现。
拿到"参数校验异常"就已经证明缺口了,不需要更进一步的证据。

## 3. 报错反推 DTO / 控制器签名

空体 POST 的 Spring 报错直接给全名与限界参数:

```
Required request body is missing: public org.springframework.http.ResponseEntity<java.lang.Object>
me.zhengjie.admin.modules.security.rest.AuthorizationController.login(me.zhengjie.admin.m...
```

→ 拿到 `AuthorizationController.login(AuthUserDto, HttpServletRequest)`,再去公开仓库
(`elunez/eladmin`, raw.githubusercontent.com)比对 DTO:

```java
public class AuthUserDto {
    @NotBlank private String username;
    @NotBlank private String password;
    private String code;  private String uuid = "";
}
```

### 字段名猜不中时的排查序
实测填满 36 个候选字段名仍报 `must not be blank` → **说明不是字段名问题**。
两个真实成因:(a) DTO 在 setter 里做 RSA 解密,明文解不出→变空→触发 `@NotBlank`;
(b) 校验发生在 request filter/`@RequestParam` 层面而非 body。
**别继续堆字段名,换去确认是不是加密/位置问题。**

## 4. 400 内部报错别判死 —— 可能只是缺请求头

`/v1/api/config/platformConfig` 长期返回 400 且回显:

```
Null key returned for cache operation (maybe you are using named params on classes without debug info?)
Builder[public java.util.List me.zhengjie.admin.modules.content.service.impl.InformationServiceImpl.getInformation...
```

看着像后端坏了。实际是**缺 `language: en` 请求头**。逐个试头:

| 试的头 | 结果 |
|---|---|
| `Accept-Language: en` / `lang=en` / `Lang=en` / `lang=en-US` / `x-lang=en` | 全 400 |
| **`language: en`(小写、裸名)** | **200 全量配置** |

→ **变体请求头清单要包含「裸名、全小写、自定义头」**,不要只试标准语义头。

## 5. 免鉴权配置接口 = 最值钱的产物(全量转存,不只看预览)

`platformConfig` 200 后返回 **5044 字节 / 122 字段**,里面直接有:

```
withdrawDefaultPassword: "591000"   ← 平台全局默认提现密码(未设支付密码的用户全用它)
withdrawOpenOut: true               withdrawalMin: 1e-07
withdrawCoin: "ETH BTC USDT USDC"   withdrawChain: "ERC20 TRC20"
sysSignCoin: "TRX"
regOpenYzm: false                   ← 验证码关闭
regOpenMail: true  regOpenYqm: true regSameIp: false
platformLogin: "https://...Multicoin-Capital-1.png"   ← 盗用真实 VC 品牌
sysDomain: "https://tradegem.top"   sysAppUrl: "https://wtafj123.cc/U8CR.app"
```

**定性证据(直接进报告)**:控盘开关
`sysOpenQuickKill`(快捷击杀)/`sysOpenOrderResult`(操控订单结果)/
`pointMin:0.8 pointMax:1.2`(控赔率)/`dataAwardMinRate:0.5 MaxRate:3.0`(虚假奖励率)
→ **该"交易所"实为控盘资金盘**。

另外 `getSymbolConfig` 也免鉴权,直接吐交易对含 `pointMin/pointMax`;`getCurrencyRate` 吐法币表
(MXN/ARS/PEN/EGP/ZAR/KZT/UAH → 反推目标市场为拉美+非洲+独联体)。

## 6. 注册口:先读开关,再动手

- `regOpenYzm:false` + `regOpenMail:true` + `regOpenYqm:true` → 邮箱注册、无验证码、**需邀请码**
- 探必填字段时返回**明确业务错误** `40001 邀请码不存在或被删除` → 确认了字段名(`yqm`)也确认了闸门
- 连续几次后 → `{"code":5109,"msg":"访问次数受限制"}` = **真实限流,立即停止重试**(别打成爆破)
- 邀请码在 TG 客服号/前端 JS/姊妹域里都**没有**公开(实测均无)→ 此路靠 OSINT 而非技术

## 7. 附带指纹

- 后端是 **ELADMIN**(包名 `me.zhengjie.admin`,定制了 `admin` 模块) → 管理端登录 `/auth/login`
  **公网可达**、`/auth/code` 返回 `{"enabled":0}`(**验证码关闭**)、密码走 **RSA 加密**
- `Authorization: Bearer <任意值>` 会触发 **500 NPE**(连 `Bearer null` 也 500)
  → 是 filter 缺陷,**不是 JWT 解析预言机**,别在这种 500 上耗时间
- FastJSON **1.2.70** 从报错原文读出(`... ; fastjson-version 1.2.70`);嵌套 `@type` 会触发
  **DNS 带外回调**(dnslog 时间戳与发送时刻精确吻合,回调源 IP 为 AWS us-east-1,与应用 UTC-5 时区吻合
  → 反推源站真实区域);顶层 `@type` 报 `autoType is not support` → **autotype 关,无 gadget,不构成 RCE**

## 8. 方法论要点(可复用)

1. **没有账号 ≠ 打不动**:前端标记 + 方法探针 = 完整鉴权面
2. **免鉴权配置接口永远是第一个要全量转存的东西**(默认口令/开关/姊妹域/第三方端点都在里面)
3. **资金接口只用无效参数分类**,这是纪律不是技巧
4. **看到"内部报错"先试请求头变体**,再判死
5. **前端标记与后端实测冲突时,以后端实测为准**
