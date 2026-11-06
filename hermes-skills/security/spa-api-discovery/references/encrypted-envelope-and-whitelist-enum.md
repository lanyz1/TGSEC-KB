# 加密信封逆向 + "全局登录过滤器/白名单"枚举(2026-09 灰豚数据实战)

适用:目标 API 返回体带 `encrypt:true` + `data` 是 base64 长串;或全站接口统一回同一个"请登录"信封。
本文件是**方法级**沉淀,目标侧细节见 `references/` 内案例。

## 1. 加密响应:先在 JS 里找解密例程,别急着猜算法

模式识别(命中即走本节):

```
{"status":200,...,"data":"y5vF92OZ6f/9zbkXa0VpQr7DuoVzqw/qQ4HcofLDSH...","t":1789302592407,"encrypt":true}
```

- `t` = 毫秒时间戳,且**常被当作密钥派生输入**(不是装饰);
- 前端一定有解密函数 —— 搜**调用点**,不是 crypto 库内部:

```bash
grep -o '.\{240\}Base64\.parse.\{320\}' app.js     # 解密例程所在
grep -o '.\{200\}AES\.decrypt.\{200\}' app.js
```

灰豚实测例程(可直接照抄逻辑):

```js
$k = e => {                                   // e = 信封里的 t
  let t = moment.utc(e).utcOffset(8);         // 北京时间
  let n = t.date() % 2 == 0;                  // 日期奇偶决定用哪把
  return [ n ? KeyB : KeyA, n ? KeyA : KeyB ]; };
eA = (data, key) => AES.decrypt(Base64.parse(data.replace(/ /g,'+')), Utf8.parse(key),
                                {mode: ECB, padding: Pkcs7});   // → JSON.parse(...)
```

- 密钥是**打包进前端的 16 字符常量**,打包器会把它拆成**单字符数组**,形如
  `["V","4","L","Q","V","M","H","F","5","5","V","g","G","o","4","d"]` ⇒ `join('')` 还原。
  捞法(见 `scripts/crack_encrypted_envelope.py`):
  `` \[((?:\s*`[A-Za-z0-9]`\s*,){15}\s*`[A-Za-z0-9]`\s*)\] ``
  灰豚一次捞 91 个"16 字符"命中,靠**随机串形状**筛出 5 把真密钥。
- 密钥**按日期轮换**是常见设计 ⇒ 同一发请求里两把都试即可,不用管奇偶。
- 裸 AES 库里的 `Yk.default`/`CryptoJS` 命中不是线索,**调用点参数才是**。

### 零依赖解密(纯净跳板机没有 pycryptodome)

不要为解密去 pip 装包。base64 → 落盘 → openssl 原生解:

```bash
openssl enc -d -aes-128-ecb -K $(printf %s 'V4LQVMHF55VgGo4d' | xxd -p) -nopad -in ct.bin -out pt.bin
# 然后手工去 PKCS7 尾:p = pt[-1]; 1<=p<=16 and pt[-p:]==bytes([p])*p → pt[:-p]
```

(ECB 无 IV;CBC 加 `-iv <hex>`。JDK/前端多为 PKCS7。)

**密钥不止一套**:灰豚在 umi.js 与 home chunk 里各有密钥数组。解不开时**先回 JS 再捞**,不要换算法。

## 2. "全局登录过滤器 + 白名单"枚举:三分法 + 分类即情报

许多国产 SaaS 用**入口级全局过滤器**判登录,白名单放宽到"首页/公开数据"接口。逐条无参 GET,按 body 三分:

| 分类 | 判据(body 碎片) | 含义 |
|---|---|---|
| `LOGINF` | `登录状态已失效` / `"code":-200` | 受保护,**立刻跳过别浪费请求** |
| `SYSERR` | `系统异常` / `"code":500` | ★**已过鉴权、控制器抛异常(缺参数)**=该路径在**白名单内**,配好参数就能打 |
| `OTHER` | 其余 | **真数据** 或 **业务错误**(必须读 body 自己判) |

坑与变体:

- 支付类服务常用另一句 `用户登录状态不可用` / `"code":-1001` = **需要登录**,别误判成未授权;
- 响应体可能是**两段拼接**(网关错误 + 业务信封),按**出现过的任一判据**归类;
- 有的路径回 **HTTP 404 + Spring 时间戳信封**(`+0000`)⇒ 是**另一个 app/端口**在处理该 Host,顺线索找兄弟服务;
- Tomcat 对 URL 里的**中文字节直接 400**,参数必须 URL-encode(否则把可达端点误判成死);
- 节奏:1300 条 × 0.3s ≈ 7 分钟,后台跑 + 结果落 TSV + **按已完成集合断点续跑**。

## 3. 白名单里最常漏的是"配置/凭据类"接口

灰豚未授权可读(全部实测):`/user/homePage`(117KB)、`/user/webHomePage`(122KB)、
`/search/userDefault`(**达人库 total=10001**,粉丝数/GMV/带货指数)、`/search/shopDefault`(店铺 GMV/DSR)、
`/work/config`(**系统配置表**,含退款 uid、签到币值)、`/work/notice`(164 条公告)、
`/accredit/code`(**泄露第三方开放平台 client_key**)、`/actual/commerce/info`(平台大盘)、
`/sysUser/platforms`、`/common/area`。

⇒ 别只盯"数据接口"。**`*/config`、`*/platforms`、`*/code`、`*/sign` 这类配置与凭据类接口**经常也在白名单。

## 4. 一个前端包 = 一串兄弟产品 API 域

主 SPA chunk 只挖出 25 个接口时,别急着猜路径 —— 去找**其它前端入口**:

- 静态首页(往往是 COS/OSS + CDN 的纯静态桶)只挂主 SPA;
  **`/app/`、`/pro/`、`/admin/`、`/login`、`/h5/` 各有自己的 bundle**;
- 灰豚 `dy.huitun.com/app/` 的 **UMI 包(`umi.*.js`,2.3MB)一次给出 1340 条路径**,而主 SPA 只给 25 条;
- JS 里 grep 出的域名清单 = **产品矩阵**:`jjapi`/`orderapi`/`fxapi`/`login`(兄弟 API)+
  第三方(1688 授权、抖店开放平台);
- Actuator 索引会把**真实后端真身**回显出来(灰豚:`_links.self.href = https://api.supsaas.com:9080`),
  拿这个 host:port 再判断它是否只在内网(从跳板打 `code=000` = 内部端口);
- 同 IP 多 vhost(如 `dyapi`/`dytest`/`dytest2`/`track` 同机):用 `Host:` 头轮换横扫,
  测试环境常与生产**同码同数据**;
- 兄弟产品**共用一套前端模板**时,同一个枚举脚本换 `--base` 即可复用(把 JS 产物一次性保存在跳板上)。

## Pitfalls(本类任务专属)

- 解密失败先怀疑**密钥集合不完整**,回 JS 再捞;不要改算法也不要放弃
- curl 取 base64 载荷:`+` 会变空格、`=` 可能被剥,**解码前先补 `replace(' ','+')` + 补 padding**
- 静态桶的 `/?prefix=`、`/?list-type=2` 若返回 **SPA 兜底 HTML**,说明该 Host 不是桶端点(假阳性,别当"可列举")
- 真正的桶要拿 COS/OSS 原始域名试:`<bucket>-<appid>.cos.<region>.myqcloud.com`(403 AccessDenied 也算"存在"),
  `*.oss-<region>.aliyuncs.com` 报"must be addressed using the specified endpoint" ⇒ 桶存在、换 region 继续试
- 后台长跑脚本务必 `setsid nohup ... >> log 2>&1 < /dev/null &`,否则调用方读 channel 会挂住(见
  `ip-ban-bypass/references/jump-server-exec-notes.md`)
