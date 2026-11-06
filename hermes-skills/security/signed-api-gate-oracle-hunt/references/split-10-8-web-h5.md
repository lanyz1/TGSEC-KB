## 8. Web/H5 前端签名还原 —— 密钥通常是**明牌**,先找再算
App/native 之外,同一网关的 H5/网页端常把整套签名体面地写在 bundle 里。**顺序:先抠 bundle 找密钥与签法,再考虑任何爆破/枚举。**
1. **定位业务包** — 读 `index.html` 拿 `main.<hash>.js`;`runtime.<hash>.js` 里的分片清单才是权威。3MB 级 `scripts.*.js` / `vendors.js` 是第三方库(plotly/mapbox/ckeditor),其字符串里带 `/activiti-explorer/`、`/warning` 这类看似真路由的**诱饵**,拿去探测会白烧一轮 —— **只信业务 `main.*.js`**。同一 SPA 可能有多份构建(`:11443` 与 `:13443` 上的 `main.*.js` 不同 hash),以当前实际加载的那份为准。
2. **找签名函数** — 搜 `sign-data` / `signKey` / `appKey` / `app-key` / `MD5` / `hmac` / `signature` 的**调用点**,以及被多处引用的常量对象(密钥表通常就是一个 `{环境: {appKey, signKey}}` 字面量)。
3. **典型形态(门户网关族)**:
   ```js
   要签串 = accessToken + url + JSON.stringify(body) + signKey
   headers = { "sign-version":"1.0.0", "app-key":appKey, "timestamp":<ms>,
               "access-token":accessToken, "sign-data": MD5(要签串).toUpperCase() }
   ```
   **复现必须用 JavaScript 原生的 `JSON.stringify` 语义**(成员间逗号后无空格、转义规则一致)。用 Python `json.dumps` 默认参数(带空格)算出来的签串**永远不对** —— 这是自签失败最常见的原因。
4. **★ 看签串里有没有「可空字段」** — `accessToken` 取自身份 cookie(`APIGW-ACCESS-TOKEN` 一类),**缺失即为空串 ⇒ 签串前缀为空 ⇒ 无 token 也能造成服务端认可的签名**。这条比脱壳/解密取 token 便宜一个数量级,应当**先测**。
5. **密钥是矩阵不是单值** — 租户(品牌/机构代号) × 环境(test1/test2/prod)各一套 `appKey`/`signKey`,外加一个 `Basic`(常见 id=secret 弱模式,同一个 Basic 也用于 `/oauth/token` 的 client 认证)⇒ 视为「密钥已握有,N 组候选」,**不要再去枚举头名/字段名组合**:字段名是固定的(`sign-data`,不是 `sign`)、值就在包里,这类枚举是纯无效功。
6. **与章节 3 互补** — 预言机拿不到时自签是同一闸的另一条路;两条都不通,缺口就不是签名,转章节 5(缺实例 ID)。资源名同样从 bundle 里抠(如 `/api-gw-asset/{nwd-loan,nwd-loan-wap,loan-picture,open-gateway}`),别靠猜。
7. **★ 抠 bundle 要抠「请求拦截器」,不是只抠签名函数** — 决定闸门开不开的常是拦截器产物而非算法:① 默认头(如 `{api-version:"1", sign:"false"}` = 一个版本轴开关 + 客户端可主动声明免签);② **认证头注入规则**(`Authorization: "Bearer "+token`、自定义 `Token:` / `Kbit-Token:`,以及 localStorage 键名如 `token` / `user_secret_key`);③ 构造配置(baseUrl / walletUrl / **urlPrefix**,如 `urlPrefix:"/api/v1"` ⇒ 真前缀与 `^/v1/` 不同)。
   **实测价值:按拦截器逐字复刻后,恒回「请升级客户端」的路由立刻返业务数据(ErrCode:0)⇒ 那句文案是「你没按我的头来」,不是版本不够。**
   **★ 版本类闸先做「头消融」A/B,别升版本号**:这类「请升级客户端 / 版本过低」闸常由**客户端自报版本的那个头**(如 `Terminal-Version`)触发 —— 实测**整条头去掉后闸消失、同一路由直达业务层**,而升版本值/扫版本头名全部无效。判决序 = ① 逐头隔离(一次去掉一个头)找出触发头 ② 去掉它 ③ 才谈版本值。**「客户端版本太低」几乎从不是服务端的真判定,而是你自己带上去的自证。**
   **头名/字段名一律以客户端源码为准,不扫**:只有客户端也留空的**值**(版本号、AppType 取值)才值得枚举;一整轮 header 名/值矩阵(十几个 AppType 值 + 十来个版本头名 + sign 开关 + Origin + body/query 的 apiVersion)零变化是无效功的典型。
8. **★ 同 host「已知可用路由」做对照,先定性「按路由」还是「按连接」** — 同一套头、同一加密体下 A 路 `ErrCode:0`、B 路回神秘闸门文案 ⇒ 闸门**按路由**:同一 api-version 值下 A 已通过即证**版本值轴不是闸门**,立刻停止版本扫射(实测 17 个版本值全无效)。之后只剩:找 B 路由自己的真实调用形态(必填参数 / 加密开关 / 它其实属于另一个服务),或换读链族。

