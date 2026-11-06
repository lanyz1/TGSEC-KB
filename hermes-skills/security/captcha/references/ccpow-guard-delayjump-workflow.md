# ccpow Guard WAF — delay_jump 策略（多策略架构）

bsncdn.ai "ccpow" 人机校验 WAF。多策略架构：同一 `_guard` 后端部署 rotate/slide/click/delay_jump 四类策略，按请求画像分配。本 reference 覆盖 delay_jump（JS PoW + 延时）策略 + 多策略判定。

## 多策略架构（关键）

- 同一 `_guard` 后端共享 `guard/guardret/_okN_/_err` 状态机
- 策略端点：`/_guard/rotate.png`（旋转拼图，680x250 8-bit PNG）、`/_guard/slide.png`（滑块）、`/_guard/click.png`（点选）、`/_guard/html.js?js=delay_jump_html`（延时）
- 通关 token 不同：rotate=`_ok8_`，delay_jump=`_ok2_`（版本号不同）
- 页面注入 `window.__ccpow = {s, c, b, t}`：s=会话token、c=挑战nonce、b=PoW难度位、t=Worker数/倒计时

## guardret 提交加密（RC4，与 rotate 同源但 payload 不同）

- `guard = <8B key><12B 含10位时间戳><9B nonce>`
- key = guard 前 8 字符（每次会话轮换）
- delay_jump payload = `str(int(guard[22:])*2+15)` ← 与 rotate 的 `str(angle)` 不同
- `guardret = b64(RC4(payload, key))`
- b64 填充符用 `'A'` 而非 `'='`（非标准；服务端宽松解码，两种填充均过）
- KSA/PRGA 标准 RC4

## guardpow 工作量证明（SHA-256 PoW，delay_jump 特有）

- 输入 s、c、b 来自 `__ccpow`
- 搜索 nonce ∈ [0, 50_000_000)
- 条件：`sha256_hex(s+c+str(nonce))` 前导 `'0'` 字符数 ≥ b（b=5 → 20 bit，平均 ~100 万次哈希）
- 提交：`guardpow = c + "." + nonce`
- 浏览器 10 个 Web Worker（stride=10，start=0..9 分片）；纯 HTTP 串行 stride=1 语义一致

## 双证明校验（缺一不可）

- 缺 guardpow → `_err=pow`
- 缺 guardret → `_err=guardok-8|delay-4`
- 错误码前缀 = 服务端校验流水线阶段名（用错误码反推校验链）

## 通关与消费语义

- 成功 = 200 + origin 页面 + `_ok2_`（Max-Age=604800 7 天）+ 挑战 cookie（guard/guardret/guardpow/guardword/guarddata）全部 Max-Age=0 清空
- 失败 = 200 挑战页 + guard 轮换（不消耗挑战，可连续重试；本目标无 IP 级 TCP 封禁）
- `_ok2_` 单独复用不放行（origin 只在通关响应下发一次）

## 混淆器字符串表（obfuscator.io + RC4）

- delay_jump.js（29KB gzip / 70KB 明文）字符串表用 RC4 加密，与 guardret 提交链路**同源**（厂商在混淆层与协议层复用同一密码原语）
- 反调试：无限递归 + `setInterval(..., 2000)` + self-defending 正则自检

## 纯协议交付

- 流程：GET /dashboard/login → 解析 `__ccpow`{s,c,b} + guard cookie → 解 PoW(nonce) → 算 guardret → sleep(t+2) → 带 guard+guardpow+guardret 提交 → 200 + _ok2_
- 零行为检测：无轨迹/无指纹/无 TLS 指纹校验，纯 HTTP(curl/Python) 即可通关，不需浏览器
