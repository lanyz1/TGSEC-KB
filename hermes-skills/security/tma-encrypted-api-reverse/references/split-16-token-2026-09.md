## ★★★ 签名分隔符以「差分矩阵」定案 · 响应体密文 · token 闸门在握手（2026-09 增补）

- ★★★ **签名不符（40703）不要读源码猜，直接跑「分隔符 × 签名对象 × URL 变体」差分矩阵**：实测一发命中 —— **bundle 静态写 `.join('\\r\\n')`（CRLF），部署服务端只认 `'\\n'`（LF）** ⇒ **现场 > 静态源码**；连读两轮源码改签名（改 CRLF、改顺序、改紧凑 JSON）全失败，矩阵一次定案。同批另两处须同时对齐：**BODY 必须紧凑 JSON**（对齐 `JSON.stringify` 无空格）、**GET 的签名 URL 不含 query**（客户端用 `params` 传参）。
- ★★ **响应体也是密文信封**：签名不符时回**明文**错误 JSON；一旦签名通过立刻变成 **AES-GCM 信封 `{"iv":"…","data":"…"}`** ⇒ 客户端必须内置解密，**所有判读都在解密之后**（用业务码 `40671`/`40705` 判断，别拿密文长度/md5 判同异）。
- ★★★ **token 闸门在 `handshake`，会话与 token 绑定**：同一铸造流程，`start_param` 填**假串** ⇒ `handshake 200`（服务端不对未知串校验）；填**真实但已失效的 token** ⇒ `handshake 400 40704 请求已失效` ⇒ **token 确实被查库**。⇒ 要进 `detail/open` 必须持**新鲜 token**；拿不到新鲜 token 时本面**无 oracle**，别再堆探针。
- ★★ **解锁 token 形态可判活性、绝不可枚举**：实测 `rpl_` + base64url(18B)，**前 6 字节为 0 ⇒ 序列化 ID**。ID 空间疑似连续，但**枚举 token = 抢他人红包 = 第三方资金红线**，一律不做；正路 = **只读监听官方频道新推送**捞新鲜 token。
- ★ **错误码谱系补全**：`40701` 无效/缺 · `40702` 已过期 · `40703` 签名/信封不符 · **`40704` 请求已失效（两义：initData 已被握手消费 / `start_param` token 已死）** · `40705` 会话已失效 · **`40671` 解锁链接无效（业务层，且排在 body 校验之前）**。
- ★★ **解锁类命名空间要枚举到闭合**：实测仅 `GET rp/detail?token=` + `POST rp/open|verify-segment|claim` 四条，其余 400+ 词全 `404 18B`(Go 原生) ⇒ 才有资格写「该命名空间仅 4 端点」。另：`verify-segment`/`claim` 的 `session_id` 是**包会话**（非 ECDH `X-Session-Id`），乱填回 `40705`。
- ★ **同一 bot 可挂多个用户名**：`t.me/<别名>?start=…` 的别名经 `ResolveUsername` 可能解析回**同一个 bot id**（实测 `@myqb` == `@MYPay`）⇒ 别据别名判定「第二个 bot / 第二套后端」；而 `short_name`（`InputBotAppShortName`）必须填**真实 app 短名**，填别名一律 `BOT_APP_INVALID`。

