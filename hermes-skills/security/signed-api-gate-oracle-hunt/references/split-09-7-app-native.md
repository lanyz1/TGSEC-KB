## 7. 客户端签名还原(App/native 侧)—— 静态优先
前面几节假设密钥拿不到。**若手上有 APK,先花 10 分钟确认「能不能纯静态拿」,再决定要不要上运行时**:
1. `readelf -sW lib*.so | grep Java_` —— `Java_<pkg>_<Class>_<method>` **明文导出**就基本赢了(加固壳常只保护 dex,不动 `.so` 符号)。
2. `objdump -d --start-address=..-stop-address=..` 看返回路径:认 `NewStringUTF`(JNIEnv 表 offset **1336 = index 167**)+ 其前的 `adrp/add` 串引用。
3. 串在 `.rodata` ⇒ **该段 VA == 文件偏移**,直接 `python3 -c "print(open(f,'rb').read()[A:B].hex())"` dump;多段短串的**拼接顺序 = append 调用顺序**。
4. 第二盐常是 **APK 签名证书 RSA 模数**(防重打包):`.so` 里常藏整份 X.509 DER 的 hex 串,或从 `META-INF/*.RSA` 用 `openssl pkcs7 -inform DER -print_certs` 取。
5. jadx 侧找签名函数:**注解名被压成单字母**(`@GET→@f` `@POST→@o` `@Headers→@k` `@Body→@y`),`grep '@GET('` 恒空;用 `grep -rhno '@f("/[^"]*"'` 拉全部路径。

典型形态:`sign = md5( md5(按 key 排序拼接的参数值 + 密钥源) + 证书模数hex )` —— **盐在哪一层很重要**:native/SP 密钥常在内层,APK 证书模数在外层(搞反则全错)。服务端只用**你发来的参数**重算 ⇒ 设备真实值(OS 版本/渠道)不重要,自造一组自洽值即可。

⚠ 未登录签名还原后,还差**一个路由该族的活宿主**才算打通;两者都拿到才是「可伪造」。**没在活 handler 上做过 A/B 对照就不要声称签名可用。**

**★ dex / Retrofit 侧(Android 原生壳)**:`.so` 静态优先之外,签名与请求契约常在 dex。① 按**类名族 grep** 锁定签名层(`*SignatureHelper` / `*Signature` / `*Interceptor` / `*ApiClient` / `*Signer`),dump 它的 `const-string` 得**头名与签名消息模板**(实测形态:`X-Timestamp`/`X-Nonce`/`X-Signature`;另有 `ACCESS-KEY`/`ACCESS-SIGN`/`ACCESS-TIMESTAMP`/`ACCESS-NONCE` 的 ts+method+path+body 族);请求头名一律以**拦截器类**为准,不扫。② Retrofit 接口方法 `code_off == 0`(无字节码)⇒ 真路径只在**注解**里,`@Body` 参数多为 `Lokhttp3/N;`(手工 RequestBody)⇒ 字段名必须 xref 调用方的 `const-string`,枚举字段名必全败(踩过一整轮)。③ 无 jadx 时用纯 Python struct 解析 DEX:见 `apk-reverse` 第 2.5 步与其 `scripts/dex_struct_extract.py`(串表是 MUTF-8 长度前缀,`strings`/行正则不可用)。

**★★ 密钥源若是「客户端自带票据里的一个声明」⇒ 伪造票据就等于自带密钥(优先于一切公式爆破)**:实测签名类从所携 token 的 **JWT claim** 读 HMAC 密钥(如 `user_secret` / `userSecret`,请求头 `Authorization: Bearer ` 里的 Bearer 亦取自该 claim),并有 `... parse fail` 风格解析文案。⇒ 一旦已握有该 token 的**签发密钥**,无需还原任何应用级公式:自铸一张 claims 里带**你自己指定的 secret** 的票,服务端便拿这个 secret 去验签,签名闸自行消失。**判据 = 同一签名类的 const-string 里同时出现 `Bearer `、claim 名与解析失败文案**。此形态下「N 种公式爆破 + 密钥字典」必然全灭(实测 144 公式全 401),别再烧轮次。

**★★ 「签的是参数值序」的签名器:GET 必须把 query 当 body 签 —— 否则整片 GET 恒失败,会被误判成「GET 面无权限」**:
客户端签名器呈 `buildSignature(map)` + `queryParamsToSignBody(query)` 形态(jadx grep `*SignatureHelper` / `queryParamsToSignBody` / `applySignatureHeaders`)时,签串 = **按 key 排序后的各参数值**以 `&` 连接,再拼 `&<秒级ts>&<小写UUID nonce>`,HMAC-SHA256(userSecret) 出 hex。GET 无 body ⇒ `queryParamsToSignBody` 把 query 转成同构 map 再签,即 **query 的值序就是签名对象**。
- **典型症状与误判**:POST 通道正常(走签名器),而**同族的全部 GET 恒回同一个 `签名验证失败-1`** ⇒ 极易被写成「GET 面无权限 / 端点未注册 / 该族封了」。真因只是把签串算成了空串。**判据 = 同一套头下 POST 通、全量 GET 同码失败 ⇒ 先改 GET 的签串构造,别判死 GET 面。**
- **空 query 的 GET 签串 ≠ 空**(仍是 `&<ts>&<nonce>` 形态),按「无参 ⇒ 空签串」想当然会命中上面那个坑。修正后同一批 GET 立即返业务数据(实测一次解锁整片资产/代理/返佣族)。
- **★ 签名对象随载体变,公式只有一套(别为加密体另创一套)**:同一签名器(`buildSignature(map)` + `applySignatureHeaders(..., encryptedFields, ...)`)下 —— GET = query 参数值;POST 明文体 = body 值;**POST 加密体 = wire 上那两个密文字段值(`{aes_key,data}`),且按它们在线上的形态(URL 编码后)取值**。差分判据:签明文值或签空体 → `签名验证失败-1`;签 urlenc 后的密文两值 → **过签名闸**。⇒ 遇到「签名恒失败」先问「我签的是哪一层载体」,再谈改算法。

> 完整配方/命令/坑位见 `references/client-sign-recovery-static.md`

**★ 服务端二进制在手 ⇒ 签名消息直接读(服务端侧还原)**:反汇编中间件的 `GenerateSignature`/`VerifySignature` —— 参数排序(`sort.Strings`+`mapIter*`)、拼接模板(`fmt.Sprintf` 格式串如 `%v&`)、算法(`hmac.New`)、输出编码(hex/base64)逐条落实,外部逐字复刻,别猜格式。同时读**密钥源函数**(如 `GetUserSecretKey`/`GetAppSecretKey` 并列出现)= 验证方支持多档密钥 ⇒ **先拿自己票据里已有的用户密钥实测,放行就整条跳过找应用密钥**。**哪档密钥生效由鉴权载体决定(实测矩阵)**:带 `Authorization: Bearer` ⇒ 验**用户密钥**;仅 `X-Api-Key`(无 Bearer)⇒ 验**应用密钥**;错配(带 Bearer 却拿应用密钥签)⇒ `签名验证失败-1`。判档 = 同端点『带票 / 不带票』各投一发;应用密钥一旦在某载体放行,即证服务端认可该 key 对。穿透判据:错误从裸 403/`access denied` 推进到下一层文案 = 上一道闸已过,**新文案即下一闸名**(缺什么头/什么载荷由它命名,逐层补)。⚠ **层序按路由而异,别拿 `Invalid AES key or data` 当签名通过证据**:要求加密信封的路由里它是**解密码头层**的直接拒态(明文体死在该层、签名层未被评审)⇒ 判签名层须用『同密文体、正确签 vs 错签』对照。配方见 `go-service-binary-dissection`「请求契约反查」。
- **★ 头名族必须从「该路由自己的验签函数」反汇编读出,不能按同服务里另一族外推**:同一服务可并存两套头名族(实测 `X-Timestamp/X-Nonce/X-Signature` 与 `clientTimestamp/clientNonce/clientSignature`),而**用错族与签错值回的是同一个错误文案** ⇒ 光看错误文本区分不了,矩阵盲扫头名还会互相污染。用法:反汇编目标 verifier(`go tool objdump -s "<pkg>.<Verifier>"`),读它自己的头名常量与取参调用;头名一律以该 verifier 为准。
- **★ 验签器读的是 `GetQueryMap()` ⇒ 业务身份参数必须放 query**:被签名/被鉴权的参数塞进加密信封体内时中间件看不到 ⇒ 恒回「参数缺失(-1)」而非签名不匹配(实测 `uid` 放加密体恒 -1,移进 query 参与签名后才推进)。**「参数缺失」先怀疑载体,不是怀疑算法**;IDOR 的身份参数同理只在 query 被采用。
- **★ 带有效票却报签名不匹配时,先枚举「票放哪个头」,再动算法**:服务端从某个特定头解析出 per-user 签名密钥,放错头 ⇒ 密钥解析失败 ⇒ 报的仍是「签名验证失败」,与「密钥/公式错」同文案(实测同一张有效票用 `token:` 头恒 -2,换 `Authorization: Bearer` 即过签名闸,而 `token:` 是 chat/OpenIM 面的正解)。判据 = 头位枚举 2–3 种 × 同一张票对照。
- **★ 「用户票打不通」先分清「用户路由」还是「App 路由」**:真票仍回 `403 access denied for user`(jwt 中间件层)⇒ 该端点族要的是 **App/应用级凭据**(ACCESS-KEY 或 app 密钥对),不是用户票 ⇒ 改投应用凭据,别继续修用户签名。
- **★ 回归排查:已知可用脚本就是基线,先逐字节 diff 自己的请求,再怀疑服务端/密钥**:同端点前一轮能读、后一轮恒拒,真因多次是**我方本轮改了请求构造**(换了头族、挪了票的头位、换了出口代理)。流程 = 原样跑一发基线脚本 → 与现脚本 diff 头集合/票头位/代理 → 只改一个变量再比。「我方构造改动」被写成「密钥错/服务端变了」会白扩整轮密钥字典。
- **★ 配方修正后,此前所有「该参数被忽略 / 该面无越权」的差分结论一律作废并重跑**:闸配方不对时(签名错、漏一个必需头、带着被判旧的版本头、body 没过信封层),中间件或软闸会用**同一响应**盖掉一切入参差异 —— 统一错误码,或**按会话身份回的默认载荷** ⇒ 目标 ID 与随机不存在 ID 逐字节一致。**那个一致性是请求被挡出来的,不是 handler 忽略参数的证据。** 实测踩过:整轮「该族 uid 一律被忽略、本平台无越权读路径」的定案,是在配方还差两个必需头时下的;配方锁定后同一 uid 差分立刻出现按 ID 分化的真实数据。⇒ 任何「参数被忽略 / 该面无越权」的判决都要写明**它是在哪个配方版本下取得的**;配方一改,旧判决降级为待复证,**别在新会话里当既成事实引用**(这类旧判决最容易被后手照着写「已排除」)。
- **★ 双原语同时错会互相掩盖(自己踩过)**:信封形态与签名基串**同时**错时,只修其中一个结果字节不变 ⇒ 极易被读成「该族无路 / 凭据不对 / 参数被忽略」并据此收线。⇒ 判「不可达」前先确认**签名基串、信封形态、头族、参数载体**四项都已按客户端源码修正,再跑一次对照;结论里写清依赖的是哪几个原语版本。
- **★ 凭据字段「存在但为空」≠ 这条路不存在**:登录/注册响应里的应用凭据成套下发(实测 `otcAppKey/otcAppSecret` 与 `kbitAppKey/kbitAppSecret` 并存),而本账号只在其一注册过 ⇒ 另一对**字段在、长度 0**。取用前先 `len()` 量一次,并去本地其他产物(代理端 bundle、落盘配置、历史响应)找同族字段真值 —— 别拿空串去签名再判「凭据无效」。

