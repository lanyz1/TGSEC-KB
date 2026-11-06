## 信封闸(请求体加密):三档错误码判据 + 自实现坑

管理后台/资金后端常见「请求体整体 AES 加密、AES key 再用服务端公钥 RSA 包一层」。这类闸的正确性判据**不是响应体像不像，而是错误码停在哪一档**:

| 档 | 响应形态 | 含义 |
|---|---|---|
| 闸层 | 框架/网关**统一码**(如 `4044`) | 明文体死在这层，**信封根本没被解** |
| **模型绑定层** | `.NET 400` / `Unexpected character encountered while parsing value: P` / `The <Field> field is required.` | **信封已解开**，服务端把解密后的 JSON 交给了模型绑定器 ⇒ 加密闸专属过渡态 |
| 业务层 | 业务错误码(如 `4009 User is not registered`) | 全链通，进 oracle 阶段 |

- **吃到模型绑定层 = 信封格式对的直接证据**，而且它**免费给出内层字段名与类型**(比回 bundle 反查快一轮)⇒ 先用空体/半体把绑定错误读全，再去 bundle 复核嵌套结构。
- **层序按路由而异，别外推**:要求加密信封的路由里，明文/错签都先死在信封层的 `Invalid AES key or data` —— 那是**解密码头层的直接拒态**，签名层根本没被评审 ⇒ 判签名层必须用「同密文体 + 正确签 vs 错签」对照。
- **自实现信封的两个本机坑(不是算法猜错，别回去重逆 bundle)**:① Python `cryptography` 的 CBC **不自动补 PKCS7**，不补就报 `The length of the provided data is not a multiple of the block length`；② 解响应时**先剥 padding 再 `json.loads`**，残留控制字符会报 `JSONDecodeError: Extra data`，看着像「信封不对」。
- **公钥从免鉴权端点现取**:`GetRsaPublicKey` / `getConfig` 类回 `{KeyId, PublicKey}` ⇒ 信封构造器就在**自己的 bundle 里**(搜该端点名的调用点，紧跟的 2–3 个短函数 = 生成 key/iv、组装信封、解响应)，不要盲扫头矩阵；`X-Skip-Encrypt: 1` 类**调试旁路头先试一发**，命中就省掉整条实现。
- **IP 白名单类闸与信封闸的分读**:`IP未授权访问：<ip>` 里 `<ip>` **等于你送的头值** ⇒ 该头被信任已成立，但「被信任」≠「能过白名单」(环回/内网段常不在名单)⇒ 结论写「需猜白名单内容」+ 按 ELB/NAT 出口与同机房段枚举，**不要写成「信任头无效」**；且 IP 闸常只罩部分路由(同 API 下有路由回 IP 未授权、有路由回登录失败)⇒ 先按路由分类再决定 oracle 读哪个码。

> ⚙ 信封/解密自实现（RSA 包 AES，含 padding 与响应解码坑）可直接跑验证：`scripts/envelope_rsa_aes.py`（`python3 envelope_rsa_aes.py --selftest` 先离线自证，再 `get_pubkey()` → `build_envelope()` → `strip_meta()` → `decode_response()`）。新建信封族时**先跑 selftest**，把本机实现排除掉，剩下的差异才可能是算法。

