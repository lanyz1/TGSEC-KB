# 钱包签名「用户动作」鉴权 —— EIP-191 自签即身份

当一个 API 不回鉴权错、只回业务错，而所有头名试遍都报地址错时，身份多半是**自签的 EVM 消息**，不是会话。

## 形状（tokenweb.sbs 案实测）

- 身份 = 一个 EVM 地址，由 EIP-191 `personal_sign` 自证；**无需注册 / 邮箱 / KYC**
- 前端把签名塞进三个头：`x-wallet-address` / `x-wallet-timestamp` / `x-wallet-signature`
- 但**地址实际取自 query 参数 `?address=`**（见坑 2）—— 头是幌子

## 在 bundle 里定位

grep：`personal_sign`、`x-wallet-address`、`signMessage`、`signedPost`、`eth_requestAccounts`、`window.ethereum`

实测前端形状（Next.js/Vite 单包，一行读全）：

```js
{signedPost:m, signedDelete:p} = (0,o.B)(t)          // t = 地址
async function i(e){
  if(!e.address || !e.authenticated) return {};       // 未连钱包 → 签名头为空对象
  let t = e.address.toLowerCase(),
      r = String(Date.now()),
      a = await c(JSON.stringify(sortKeys(e.body))),  // 规范化 body 的哈希
      l = [e.method.toUpperCase(), pathname+search, t, r, a].join("\n"),
      {signature:n} = await e.signMessage(...);
  return {"x-wallet-address":t,"x-wallet-timestamp":r,"x-wallet-signature":n}
}
```

⇒ 消息 = `METHOD \n pathname+search \n address(小写) \n 毫秒时间戳 \n sha256hex(规范化JSON(body))`

规范化 = **递归按键名排序**后 `JSON.stringify`（无空格）。

## 坑 1（本案最大的一发）— 签名路径必须含 query

| 签名时用的 path | 结果 |
|---|---|
| `/api/trading/orders`（裸路径） | `401 Invalid user action signature` |
| `/api/trading/orders?address=0x…`（含 query） | **过闸 → 业务错误** |

服务端算的是 `pathname + search`。只签 pathname ⇒ 每一发都像「消息构造错了」，极易回炉改字段名/头名/换 payload 形状，白跑一大轮。

## 坑 2 — 地址来自 `?address=`，不是任何头

先按前端源码逐个头名试（`x-wallet-address` / `x-user-action-address` / `x-action-address` / `x-identity-address` / `x-signed-address` / `address` / `x-address` / `x-eth-address` / `x-account-address` / `wallet-address` / `x-account` / `x-sub` … 19 个）—— **全部回同一句 `Invalid address`**。让错误发生变化的只有 `?address=<合法 ETH 地址>`。

⇒ **「同样的错误文案」是最强的证伪信号：它说明你还没碰到那个参数，而不是参数值不对。** 此时换「位置」（query / body / path / header）比换「值」有效。

## 错误阶梯 = 诊断梯（照序读）

| 响应 | 读法 |
|---|---|
| `Invalid address` | 地址**根本没被取到**（位置错 / 格式非法）—— 不是签名问题，别去改签名 |
| `User action address does not match signature identity` | 签名头**完全缺失**（只给了 `?address=`） |
| `Invalid user action signature` | 签名头在、但验不过：消息拼错（多为漏 query）或**用甲的钥签乙的地址** |
| `Insufficient balance` / `No shares held` / `Project is not accepting investments` / `Internal transfers are disabled by platform policy` | **鉴权全部通过、已进 handler** —— 这就是「打进去了」的形状 |

实测四个对照（同一发 `POST /api/trading/orders?address=<我们的地址>`）：

| 输入 | 结果 |
|---|---|
| 无签名头 | `does not match signature identity` |
| 假签名（`0xab…`） | `Invalid user action signature` |
| 我们的钥签**别人的**地址 | `Invalid user action signature` ⇒ **签名↔地址绑定真实强制，冒用他人不成立** |
| 我们的钥签自己 | `Insufficient balance` |

## Python 侧实现（不装 web3）

```python
from coincurve import PrivateKey
from Crypto.Hash import keccak            # pycryptodome

def k256(b):
    k = keccak.new(digest_bits=256); k.update(b); return k.digest()

def addr_of(priv_hex):
    pub = PrivateKey(bytes.fromhex(priv_hex)).public_key.format(compressed=False)[1:]
    return "0x" + k256(pub)[-20:].hex()

def sign(priv_hex, msg: str):
    m = msg.encode()
    h = k256(b"\x19Ethereum Signed Message:\n" + str(len(m)).encode() + m)
    s = PrivateKey(bytes.fromhex(priv_hex)).sign_recoverable(h, hasher=None)
    return "0x" + s[:64].hex() + f"{s[64]+27:02x}"      # v = recid + 27

def canon(o):                                            # 递归键排序，与前端一致
    if isinstance(o, list):  return [canon(x) for x in o]
    if isinstance(o, dict):  return {k: canon(o[k]) for k in sorted(o)}
    return o

def bhash(body):
    j = json.dumps(canon(body), separators=(',',':')) if body is not None else "null"
    return hashlib.sha256(j.encode()).hexdigest()

def message(method, path_with_query, addr, ts, body):
    return "\n".join([method.upper(), path_with_query, addr.lower(), ts, bhash(body)])
```

`s.sign_recoverable(h, hasher=None)` = 传入的已是最终摘要，别再哈希一次。

## 拿到身份后能做什么（本会话实测，全部零注册）

- `POST /api/wallet/deposit/{addr}?address=` → **201 Created**（`{"status":"pending","depositAddress":"<平台收款址>"}`；`method: crypto|fiat` 都收）
- `POST /api/referral/code/{addr}?address=` → **201 Created**（回 `{"code":"48BCLHV8","isActive":true,...}`）
- `POST /api/trading/orders?address=` → `Insufficient balance`
- `POST /api/projects-v2/{id}/invest?address=` → `Project is not accepting investments`
- `POST /api/projects-v2/{id}/claim-revenue?address=` → `No shares held`
- `POST /api/wallet/transfer/{addr}?address=` → `Internal transfers are disabled by platform policy`（策略关闭，非鉴权）

⇒ 定性是**认证模型缺陷**（自助身份 + 无注册/KYC + 无邮箱验证）。报告里把「能以**自己**的地址读写」与「能冒用**他人**」分开写 —— 后者实测**不成立**，混写会让结论虚高。

## 三条不要误判的边界

- **充值确认面不存在 ⇒ 建单成功 ≠ 余额可伪造。** `/api/wallet/deposits/*`、`/api/payments/callback`、`/api/webhooks/*`、`/api/blockchain/webhook` 全 404；crypto 侧是链上监听（`requiredConfirmations: 12`），fiat 侧 `paymentId: null`（未接网关）。建单只产生 `pending` 记录，回读余额仍 `0.000000000000000000`。**别把 201 写成资损。**
- **后台面不认钱包身份。** `/api/admin/*` 不带票恒 `401 未授权访问`；补钱包签名头 / `?address=` / 平台自己的收款地址，一并不变 ⇒ 钱包面与后台面是两套闸，别指望由此提权。
- **只读侧同族往往完全无闸。** `GET /api/wallet/balance/{addr}`、`/wallet/transactions/{addr}`、`/membership/{addr}`、`/membership/stats/overview`、`/projects-v2/user/{addr}/investments`、`/projects-v2/user/{addr}/pending-revenue`、`/referral/stats/{addr}` 对任意地址 200 ⇒ 与写侧合并即「按地址读全站 + 按地址写自有」。地址是随机 32hex，**不可枚举**（实测邮箱→地址的各种派生：md5/sha1/sha256/uuid5/去盐 全部不匹配）⇒ 写「可读性缺陷成立、可枚举性不成立」。

## 纪律

- **别用「转一笔真的」验证充值链。** 验完建单 + 状态回读即止；任何真实入账/出账迹象立刻停手落盘。（充值确认面本身不存在，转账也验不出东西。）
- **被问「私钥呢」先给事实而不是姿态。** 本案对 215 个客户端自有源文件跑四类扫描（`private_key`/`mnemonic` 赋值型、`xprv`、`0x`+64hex、裸 64hex 带上下文过滤）⇒ **全部 0 命中**；服务端只暴露**收款地址**（往里打钱的地址，不是能签名的钥）。把「找不到」升级成报告级负面结论（见 SKILL.md 报告纪律那条）：面清单 + 三处交叉印证，而不是一句「没找到」。
- 提「把资金归集到某地址」这类动作时：**这不是渗透交付**，如实说清无可用私钥/额度，只出报告。

## 配套

- 源站定位（本案 `pc.tokenweb.sbs` / `km.tokenweb.sbs` 的源站就是起始 IP，SSL 证书 SAN 直接给出域名，`Host:` 头即可绕过 CF）→ `spa-hardcoded-host-origin-pivot.md`、`whitelabel-fleet-shared-backend-and-sni-origin.md`
- 「未认证 POST 回 DTO 校验错 = 守卫缺口」的判决表 → `nextjs-rsc-endpoint-table-and-guard-order-triage.md`
- 客户端自解包（PyInstaller `_internal/backend/` 里常是**未编译的 .py**，本案 190 个）→ `security/packaged-client-source-recon`
