# UMI/webpack 构建产物深挖 + 静态加密 + 权益门闩(灰豚数据 2026-09 实战)

国内 SaaS 数据平台的完整打法实录。目标 `huitun.com`(灰豚数据),多个兄弟产品
(`dyapi/login/jjapi/orderapi/fxapi` + `cc`/`order`/`puhuo`/`statdy` 子域)。

## 1. 边界与资产(30 分钟定型)

| 资产 | 特征 |
|---|---|
| `huitun.com` / `dy.huitun.com` / `img.*` | `Server: tencent-cos` + 网宿 `X-Cache-Lookup` + `X-NWS-LOG-UUID` = **COS 静态桶 + CDN**,零应用逻辑 |
| `dyapi.huitun.com`(主 API) | 裸 nginx,**无 CDN → 源站直连**;全局登录过滤器(白名单外统一 `{"code":-200,"message":"登录状态已失效"}`) |
| `login.huitun.com`(同 IP) | 独立登录服务(Spring Boot,`/home` 回 `Hello! This is login-service!!`) |
| 同 IP 多 vhost | `dytest`/`dytest2`/`track` 与 dyapi **同一套应用**(测试环境没有更松的鉴权,别指望) |
| 兄弟产品 | `cc`(鲸投,API=`jjapi`,**与 dyapi 同机但独立应用**)、`order`(小天订单,`orderapi`)、`puhuo`(小天分销,`fxapi`) |
| 遗留 | `statdy.huitun.com` = 部署在那的 **Flask-Auth-Example 示例应用**(`/login?next=/`) |

**`robots.txt` 的 `Disallow: /actual/` 是 SPA 兜底假阳性**(返回 index.html),别当隐藏路径。

## 2. chunk 哈希映射(踩过的坑)

```python
# 主包 umi.js 里有两份 {id:"hash"} 映射(JS 一份、CSS 一份),条数相同 → 必须选对
maps = re.findall(r'\{[0-9]{1,3}:"[0-9a-f]{8}",[^}]{200,}\}', src)
hm = next(m for m in maps if parse(m).get(36) == "b1af90f8")   # 用已知能下到的 chunk 反查
url = "https://dy.huitun.com/app/%d.%s.async.js" % (cid, hm[cid])
```

选错的症状:每个 chunk 都是 **~478 B 的 `NoSuchKey` XML**(不是 404 HTML),肉眼像"下到了"。

路由→chunk:`path:"/deck/industry_overview"` 附近的 `n.e(12)`/`n.e(59)`。
实战产出:主包 2.3MB 里抠出 **1,340 条接口路径**;页级 chunk(达人详情 1.47MB)抠出
`contactWay`(联系方式筛选键)、`isContact`、`2===vipLevel?"当前为免费版/试用版会员,暂不支持导出…"`。

## 3. 静态 AES:两把硬编码密钥 + 按日期奇偶轮换

```js
Zk=["V","4","L","Q",…]  // join = "V4LQVMHF55VgGo4d"
Qk=["x","c","N","g",…]  // join = "xcNgtUIgnc8Fq9oL"
$k=e=>{let t=moment.utc(e).utcOffset(8); return t.date()%2==0?[Qk.join(''),Zk.join('')]:[Zk.join(''),Qk.join('')]}
eA=(data,key)=>JSON.parse(AES.decrypt(CipherParams.create({ciphertext:Base64.parse(data.replace(/ /g,'+'))}),
        Utf8.parse(key), {mode:ECB,padding:Pkcs7}).toString(Utf8))
```

- 触发条件:响应里 `encrypt:true`;密钥材料 = 响应的 **`t` 毫秒时间戳**(按 UTC+8 的"日期奇偶"选哪把先试)
- 候选集不止这两把 —— 把主包/页级 chunk 里**所有单字符数组(长度 16)** `\[("[^"]",){15}"[^"]"\]` 全抠出来对撞
- **零依赖解密**:`openssl enc -d -aes-128-ecb -K <hex(key)> -nopad -in ct.bin`,再按 PKCS7 去尾;判成功看明文以 `{`/`[` 开头
- 已解开的实例:首页运营配置 117KB/122KB、达人榜 52KB、店铺榜 29KB、类目库 228KB、`/sysUser/purchase/list` 价目表

**结论定性**:所谓"加密响应"只是防爬,不是安全控制 —— 拿到密钥即可离线批量解。
但**不要把"能解密密文"等同于"拿到了敏感数据"**:本例解出来的多是公开榜单/运营配置。

## 4. 权益门闩:本次真正的结论

登录(免费版)后依旧拿不到联系方式,逐层验证才定位到真实门闩:

| 层 | 证据 |
|---|---|
| 认证层 | 4 个"联系方式类"端点未登录全 `登录状态已失效`;登录后**可调**,但字段不出现 |
| 权益层 | 页级 chunk 硬编码 `vipLevel===2 → "仅限豪华版及以上用户使用"`;平台自己的未授权公告也写"联系方式仅限豪华版及以上" |
| 后端层 | 免费版调达搜/详情类接口,响应里**整个 contact 字段不存在**(不是空串/掩码)|
| 判定 | **不是"没找到接口",是"接口对当前档位不返字段"** |

等级体系(vipLevel):`2 免费版 / 3 高级版 / 4 豪华版 / 5 个人版·企业版 / 10 品牌版`;
在售商品档位与价目(接口 `/sysUser/purchase/list`,解密后按 `role × month`):
`149 个人版`(1 月 ¥149 首购"买一送二"、12 月 ¥949、24 月 ¥1699)、`5 企业版`(¥899/月)、
`7 企业版Pro`、`10 品牌版`(12 月 ¥13888)、`11 集团版`(12 月 ¥29888);`mixPurchase/list` 另给组合价。

**方法论**:先枚举平台自己的价格/权益/试用/兑换码端点(`purchase/list`、`purchase/info`、
`mixPurchase/list`、`memberStatus`、`v1/trial`、`promotion/card`、`promotion/cardActive`、`promotionCode`),
把"最便宜解锁档"问清楚再谈付费 —— 比继续猜接口参数有效得多。

## 5. 登录链(短信验证码,可直接复用)

全部在 `login.huitun.com`(cookie jar 全程携带,`JSESSIONID` 会话绑定图形码):

```
GET /bind/getVerifyCode?mobile=<手机号>        # 图形码 JPEG(会话绑定,可自行识图并用 checkVerify 自验)
GET /bind/checkVerify?mobile=&verifyCode=     # 校验图形码 code:0 = ok(图形码可能一次性)
GET /bind/captcha?mobile=                      # 发短信(实测不强制先过图形码),返回 {"status":200,"message":"ok","code":0}
GET /bind/captchaLogin?mobile=&captcha=<短信码>&verifyCode=&shareid=   # 短信码 4 位;code:-3 = 验证码错误
POST https://dyapi.huitun.com/userLogin        # body {"mobile":...,"shareid":""} → Set-Cookie SESSION(域 .huitun.com,400 天)+"登录成功!"
GET  https://dyapi.huitun.com/sysUser/currentUser   # 会话校验(返回加密体,用第 3 节密钥解)
```

口令登录另一路:`POST /weChat/userLogin {"mobile","password"}` / dyapi `POST /login`(Spring Security,空体回 500 `Bad credentials`)。

## 6. 限流信号(撞到就停)

```json
{"path":"/error","code":-100102,"message":"请求过于频繁，已被限制访问,请完成验证","roleId":2,"nextRole":0}
```

- 该响应**顺带泄露了 roleId/nextRole**,但更要紧的是:**立刻停止对业务接口的探测**,冷却期内只走
  离线/静态面(主包、页级 chunk、CDN 上的静态页),否则会把账号/IP 一起拖进更严的风控。
- 冷却期改离线仍有产出:本次正是在冷却期从 chunk 里抠出了权益拦截文案与价目端点。

## 7. 未授权面清单(供对照,均带 "登录过滤器" 白名单特征)

`/user/homePage`(117KB 加密)、`/user/webHomePage`(122KB)、`/work/reportStudy`(35 条)、
`/work/homePageGoods`、`/work/purecomList`(达人+报价比例)、`/common/shop/search?keyword=`(真实店铺列表)、
`/search/userDefault`/`shopDefault`/`hotListDefault`、`/work/notice`(164 条公告)、`/work/config`
(**内含企业微信机器人 Webhook key ×2 + 内网 `172.17.0.145:8xxx`**)、`/common/allCid`(228KB)、
`/sysUser/platforms`、`/sysUser/live`、`/accredit/code`。
`/notify`(支付回调)对 JSON/表单/XML 一律回"系统异常" ⇒ 无法伪造;`/pay/count/*/crtOrder` 是**次数**购买(¥2),
与会员购买是两套端点。
