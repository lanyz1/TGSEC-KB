# 加密信封 API 逆向（前端硬编码密钥 → 可编程客户端）

**何时用**：目标请求/响应是密文（`data=<base64>`、`{"enc":"..."}`、`sign=<hex>`），或你只能看到密文流量、想写探针却没签名公式。中文白标游戏/钱包/支付站实现几乎同构。

## 1. 先找明文密钥，不要先逆混淆

- 抓入口 HTML → 登录/注册页的 `<script>` → `grep -E 'AES_KEY|SIGN_KEY|API_SIGN|SECRET|secret_key|md5\('`。
- 实测：`login_webapp.html` 里 `API_SIGN_KEY` 与 `AES_KEY` **明文硬编码**，929 字节就结束战斗。
- 找不到就扩大范围：全部 JS chunk、`window.__CONFIG__` 内联配置、sourcemap。

## 2. 判形状（三个正则足够）

- 加密：`CryptoJS.AES.encrypt(json, key, {iv, mode: CBC})` → **AES-CBC；随机 16B IV 常前置拼进密文再整体 base64**（`b64(iv‖ct)`）→ 解密时先切前 16 字节。
- 签名：两种主流，都要试：
  - `md5(JSON.stringify(payload) + SIGN_KEY)`（拼接式，键序敏感）
  - `md5(sortedQuery + '&key=' + SIGN_KEY)`（参数排序式）
- **编码外层别漏**：`btoa()` / base64 / urlencode 常包一层。真实教训：TG initData 前端发的是 `btoa(initData)`，不扒这层会把「编码错」误判成「校验不过」。

## 3. 用 Python 复刻（一次跑通，永久可用）

- `uv pip install pycryptodome`；`AES.new(key, AES.MODE_CBC, iv)` + PKCS#7 pad/unpad。
- **先只发一个已知合法请求验证信封**（能解出业务明文即通），再批量上探针。
- 封成模块（如 `tm_api.py` 只暴露 `enc()`/`sign()`/`call()`），后续所有脚本 import 它，别每次重写。

## 4. 错误文案差分 = 免费合约预言机

- 逐类造错，按回包文案分辨真实闸门：
  - **缺 token** → `token 参数缺失` ⇒ **该方法真实存在**（与「方法不存在」是两回事，别混）
  - **未知方法名** → 另一套文案（或 `code=None`，见 §6）
  - **缺参数** → 直接点出参数名
- 把得到的「方法名 ↔ 参数名 ↔ 错误文案」写成表，就是闸门顺序图的骨架。

## 5. 方法库存来自 grep，而非字典

- 盲打方法名字典实测只命中 **4/50**；grep 单包 `method:"..."` 一次拿全。
- 前端里的**参数名也一并抽出**（`LoginWebUsername`/`LoginWebPassword` 这类驼峰名就是真字段），比猜字段快一个量级。
- 注意：某些「登录」方法（`web_login`/`web_reg`）参数是**独立于前端会话的另一套认证面**（代理/商户后台）→ 单列一条攻击线，别当成同一个登录。

## 6. 判死纪律

- **`code=None` / 整批同形空响应 = 限速或 WAF 摘要，不是「方法不存在」。** 换出口（Tor 轮换）用小样本重测再下结论；把限速误读成「无此功能」会白白关掉一条真攻击面。
- 高频探针后**直连全站 502（CF 错误页）而换出口 200** = 自己的出口 IP 被拉黑，不是目标挂了：`curl --socks5-hostname 127.0.0.1:9050 --proxy-user t$RANDOM:1`（每次随机 user = 独立电路）。Python 用 `socks5h://` 需 `pysocks`（系统 python 常缺 → 换 venv 解释器）。

## 7. 工程细节

- `pkill -f <脚本名>` 会匹配到自己的命令行 → SIGTERM 自杀；用收紧模式 `pkill -f "python3 .*<name>"` 或直接记 PID。
- 长批次一律 `terminal(background=true)` + `python3 -u`。

## 已验样本

- 提米钱包 `tm.mymygame.me` / `timi.nimingkj.com`（`/api.php`，AES-CBC(iv 前置)+MD5(API_SIGN_KEY)）= 完整走通：密钥→信封→登录→50 方法。案例细节见 `tg-miniapp-wallet-pentest` 的 `references/anonykj-white-label-family-2026-09.md`。
