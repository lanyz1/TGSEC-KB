---
name: encrypted-js-shell-decoding
description: "Use when JS 整文件包壳需还原 API 契约与登录算法。"
version: 1.0.0
license: MIT
tags: [包壳JS, 加密JS, 自定义解码器, Node vm, JSON-RPC, 参数反推, 白标平台, 跳板页]
---

# 包壳 JS 平台的 API 契约还原

适用：站点静态 JS 不是明文，也不是 webpack/Vite 产物，而是**整文件包成一行**：
```js
a4vjeuue("<base64 巨串>")        // 或任意自定名函数，一文件一行
```
典型于国产白标平台（博彩/发卡/棋牌）。目标：拿到完整 API 方法表 + 登录算法 + 参数名，
不靠猜、不靠字典。

**分工**：国密/js-websocket/webpackChunk 走 `spa-protocol-reverse`；
MD5/HMAC 签名与 bundle 里 VITE 密钥走 `gambling-api-crypto-reversal`；
本卡只管「整文件包壳 + 跳板页配置 + 错误码驱动」这一段。

## 1. 先判定是哪一种「看不懂的 JS」

| 形貌 | 归属 |
|---|---|
| 单行 `f("base64")`，无 `webpackChunk`、无 sourcemap | **本卡** |
| 正常 IIFE + 变量名短 | 普通压缩，直接读 |
| `webpackChunk` 运行时装模块 | `spa-protocol-reverse` |
| JSVMP / WASM / Worker 里算签名 | `js-reverse` |

判据：`grep -c 'eval(' file.js` 与文件行数。整文件 1～3 行且含 `eval(` → 本卡。

## 2. 核心：跑它自己的解码器，不要静态逆

解码器**通常在 HTML 内联脚本里，不在 JS 文件里**：
```js
function a4vjeuue(t){ eval(dpc94kc2.h9842z2mnny2(t)) }
var dpc94kc2 = function(){ /* ... */ }
```

做法：
1. `curl` 入口 HTML，定位 `var <解码器名> = function` 整块直到 `};`，抠出来存 `decoder.js`。
2. Node + `vm` 起沙箱加载它（它一般只用 atob/unescape/charCodeAt，缺的对象补空）：
```js
const vm = require('vm'), fs = require('fs');
const ctx = {window:{}, document:{}, navigator:{}, console, atob, unescape, Uint8Array};
vm.createContext(ctx);
vm.runInContext(fs.readFileSync('decoder.js','utf8'), ctx);
vm.runInContext('this.__dec = dpc94kc2.h9842z2mnny2', ctx);
// 逐文件：剥掉 f(" 与 ") 外壳 → 取 base64 → ctx.__dec(b64) → 明文落盘
```
3. 实测膨胀率约 **1.5×**（146KB→241KB / 126KB→222KB），全量成功。
4. **先解 `manifest.js`**（它同样包壳），从里面拿真实 chunk 清单，再逐个下；不要去猜 chunk 名。

## 3. 跳板页：配置都在根域，不在站点

根域常常不是站点，而是「域名路由表 + 跳转器」：
```
GET /                 → 几 KB，<meta name="Generator" content="<厂商>">，打印同平台全部域名
GET /<厂商配置路径>    → 十几 KB 总配置（AES key、版本、API 域名组、皮肤版本映射）
GET /<厂商>/stat.do?pv=ajax&pa=host.info&domain=<域>
                      → {sn, webPath, name, cdnPath, isBlock, fromIp}
```

**SPA 静态路径**由「版本映射 + 皮肤 id」推出来，不用爆破目录：
```
${cdnPath}/${pc|m}/${skin_versions[webPath].v}/static/js/{manifest,vendor,common,<skin>}.js
```

`host.info` 类接口会回显 **你自己的出口 IP**（`fromIp`）—— 这是判断「是否被列入白名单」
最快的对照，比盲试快一个数量级。

> 伪值识别：`serverIp` 若出现 `172.272.1.428` / `204.304.1.396` 这类**超出 255 的段**，
> 说明运营方自己填的假数据 —— 该站大概率是演练/靶场，别把它的账号体系当真盘口结论。

## 4. 错误码即参数链（本卡最高效的一招）

别猜字段名。**从最小的 body 开始，让报错逐个吐出缺哪个字段**，一次只补一个：
```
{}                        → "loginId 参数不能为空"      ⇒ 字段名是 loginId
{loginId}                 → "saltedPassword 参数不能为空" ⇒ 下一个参数
{loginId,saltedPassword}  → "验证码不正确"               ⇒ 协议已通，只剩 captcha
全参数 + 好码              → "用户名或密码错误"            ⇒ ★协议 100% 正确，只剩账号
```

判读纪律：
- **「用户名或密码错误」= 成功信号**，不是死路。回头改算法是最常见的时间浪费。
- 区分**参数层**报错（缺字段/类型）、**门禁层**报错（验证码/限流/白名单）、**业务层**报错（账号错）。
  只有门禁层值得重试；参数层/业务层必须停下来改结构。
- 参数真名从**解壳后的 JS 字符串常量**里拿，不要从压缩后的函数签名猜。

## 5. 前端密码摘要的常见形

```js
// A. 加盐双 SHA1（实测 saltedPassword）
salt = Date.now();  token = SHA1(SHA1(pw) + salt)
// B. 固定盐 MD5
md5(pw + SALT)
// C. RSA 公钥封装（JSEncrypt / node-forge，公钥就在解壳后的 JS 里）
```
先 grep `SHA1|SHA256|md5|JSEncrypt|encrypt(` 定位，再用**一个错误响应**验证盐值类型：
毫秒时间戳的盐每次请求都变，固定盐不变。

## 6. 出口 / 白名单

- 白名单常**按租户（sn）绑定**，不按节点：同节点 A 站拒、B 站过，先换 sn 再换 IP。
- 受阻时用**自有可控主机**当出口：本地只算签名/加密，远端只发包，目标侧不装依赖。
```bash
cat > /tmp/req.curl <<'EOF'
url = "https://<host>/path"
header = "Content-Type: application/json"
header = "Referer: https://<域名>/"
data = "{\"k\":\"v\"}"
EOF
scp -P <port> -i <key> /tmp/req.curl root@<srv>:/tmp/
ssh -p <port> -i <key> root@<srv> "curl -sS -K /tmp/req.curl -m 20"
```
**`curl -K` 配置文件 > 内联 `-H '...'`**：header 带 `"` `{}` 时内联必然被 shell 吃坏。
- 批量探测：一次几十并发就会被限速（403 + `code=000`），**分批 + 降速**，每条响应落盘再核。

## 7. 拼图/滑块验证码：模板匹配在渐变背景上会失效

4 位纯数字码 → `ddddocr` 限定字符集，实测从 ~90% 提到**连续 15/15**。

**拼图缺口定位**：服务端通常给 `pieceY`（滑块的 y），只需要 x。
背景是渐变/带纹理时 `cv2.matchTemplate` 会撞重复纹理（实测算出 184/89/20 全错）。
改用**缺口白边**：
```python
a = np.array(Image.open(bg).convert('L'))
ys, xs = np.where(a > 220)          # 缺口白边是最亮的那簇
x = int(xs.min())                   # 左边界 = 滑动距离
# y 直接信服务端的 pieceY，不要自己求
```
实测 3/3 命中。**先验一下**：`pieceY` 是否落在白边簇的 y 范围里 —— 落在里面才说明找对了簇。

## 8. 交付纪律

- 解壳明文、方法表、算法都**落盘到案卷**再写报告；报告只引用可复跑的文件路径。
- 方法表按业务分组（认证/资金/游戏/代理），**资金面（充值/提现/转账/KYC）单列** ——
  那是这类平台的价值面，别混在长清单里被忽略。
- 遇到死路（自研字节码、无 DNS 的 CDN、纯静态加密）**明确写「此路不通」并写理由**，下一轮不重踩。

## 9. 附件

- `references/zts-zb-cloud-protocol.md` — ZTS/zb-cloud 族（bg789/mega888 白标）完整实测：
  跳板页结构、8/8 解壳结果、`?pa=` JSON-RPC、45+ 方法表、登录错误码链、`bgluares` 死路。

## Pitfalls recap

- 不要在包壳 JS 上做静态 base64 解码 —— 外层还套了一层自定义编码，必须跑它自己的解码器。
- 不要把「用户名或密码错误」当失败；那是协议验证通过的唯一证据。
- 不要把 `db-schema config not found` 当节点选择问题死磕 —— 那是该租户独立部署的信号。
- 不要看到验证码就上新工具；先测「只查格式」（固定码 `1234` 能进业务层 = 直接跳过 OCR）。
