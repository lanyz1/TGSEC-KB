# 白标机队：公共资源桶 → APP 客户端 → 客户端密钥提取

从「无任何凭据」走到「用平台自己的加密协议调全 API」的一条完整链。适用于 uni-app / H5
白标博彩与担保平台机队（一个后台，几十个品牌站）。

前置：`SKILL.md` §2b 的未授权 config 端点已给出版本/租户图；本文件接手后续四步。

---

## 1 ★ 先找公共资源桶 —— 机队清单常常直接可列

品牌前端的 JS 包里几乎必然硬编码一个对象存储桶（图片 / 字体 / 公告 / APK 全在里面）：

```bash
curl -s "https://<bucket>.s3.<region>.amazonaws.com/?list-type=2&max-keys=1000"
# 有 <ListBucketResult> + <Contents> ⇒ 桶可公开列举（无需任何凭证）
```

翻页：`list-type=2` 用 `NextContinuationToken`，`list-type=1` 用 `marker=<最后一个 key>`；
两者都要循环到 `IsTruncated` 为 false（实测一桶 50,000+ 对象 / 5.4 GB 仍未到底）。

**键名布局 = 机队结构**：

```
/<tenantId>/<theme>/{avatar,public,wallet,vip,activity}/...      # 主题化前端资源
/<tenantId>/apk/<brand>.apk        /<tenantId>/apk/<brand>.mobileconfig
/<tenantId>/uploads/...            /<tenantId>/tg/...
```

- `tenantId` 前缀（`10001001` / `10001003` / `20001001` / `30001001` …）⇒ **逐个数就是租户清单**，
  比猜域名快得多。
- `.mobileconfig` 是 **iOS 全屏 webclip**：解析 plist 直接拿到品牌名 + 真实站点 URL
  （实测 `huifeng.mobileconfig` → 「汇丰娱乐」→ `https://hf666.com/`；
  `tianziu.mobileconfig` → 「天子U」→ `https://tianziu.com`）⇒ **一条 mobileconfig 一个品牌**。
- `.apk` 各租户**字节数完全相同**时，说明是同一份平台基座包 ⇒ 反编译一次覆盖全机队。
- `uploads/` 常是**设计素材**（PSD 导出、中文命名的活动图）而非用户数据 ——
  先看再下结论，别把素材目录报成数据泄露。

## 2 ★ uni-app APK → 业务逻辑全在 JS 里

```bash
aapt dump badging <apk>                     # 包名 / 权限 / 版本
unzip -l <apk> | grep -E '\.dex|lib/'
```

- 见到 `io.dcloud` / `ask.dcloud.net.cn` / `plus.` ⇒ **uni-app 混合包**：原生 dex 是壳
  （常加壳：`assets/<NAME>.dex`），**业务逻辑与硬编码常量都在**
  `assets/apps/<APPID>/www/assets/index-<hash>.js`（1~2 MB，另配 `index-legacy-*.js`，
  legacy 版通常混淆更少）。

```bash
grep -oE '/(user|agent|finance|vip|active|common|game)-api/[a-zA-Z0-9_/-]{0,50}' index-*.js | sort -u
grep -oE 'https?://[a-zA-Z0-9._:/-]{6,80}' index-*.js | sort -u
```

- 一口气拿到：**全部 API 命名空间与逐条路由**（注册 / 登录 / 代理佣金 / 财务提现 / 游戏回调）、
  硬编码后端域名（`api.<brand>.com`、`chat.<brand>.com`）、官方 TG（`t.me/<Name>` ——
  与桶名往往同源，实测桶名 `hj-hashgo` ↔ `t.me/HashGo666`）。
- `assets/supplierconfig.json` / `manifest.json` 通常为空壳，别指望它给 API 域名。
- **域名是轮换的**：翻出的 `api.<brand>.com` 可能已无解析。用法是**确认命名规律**，
  再回活着的品牌站取当前实例；不要因为域名死了就放弃这条线。

## 3 ★ 客户端加密的密钥：挂钩 WebCrypto，不要逆混淆

前端用 `window.crypto.subtle` 时，**直接挂钩三个方法**比逆混淆字符串表快一个数量级：

```js
// Page.addScriptToEvaluateOnNewDocument(source=...)  ← 必须注入在文档加载之前
const S = crypto.subtle;
const oik = S.importKey.bind(S);
S.importKey = async (fmt, keyData, alg, ext, usages) => {
  log({op:'importKey', alg:JSON.stringify(alg), keyHex: hex(keyData), keyB64: b64(keyData)});
  return oik(fmt, keyData, alg, ext, usages);
};
const oe = S.encrypt.bind(S);
S.encrypt = async (a,k,d) => { log({op:'encrypt', iv: hex(a && a.iv), plain: hex(d)}); return oe(a,k,d); };
const od = S.decrypt.bind(S);
S.decrypt = async (a,k,d) => { const r = await od(a,k,d);
  log({op:'decrypt', plainResp: new TextDecoder().decode(r)}); return r; };
```

`importKey` 交出**原始密钥**（`CryptoKey` 不可导出也没关系 —— raw keyData 已在手上），
`encrypt`/`decrypt` 交出**IV 与明文**。实测直接得到 `key396kjjfkdsflahdf9829uihha62hu`
（32 字符 = AES-256）、算法 `AES-GCM`、每请求随机 12 字节 IV。

拿到 key + IV 布局后用 Python 复刻客户端，**从此不必再开浏览器**：

```python
# iv(12) || ciphertext || tag(16)，urlsafe-b64 去 padding
def enc(o, key):
    iv = os.urandom(12)
    ct, tag = AES.new(key, AES.MODE_GCM, nonce=iv).encrypt_and_digest(
        json.dumps(o, separators=(",",":"), ensure_ascii=False).encode())
    return base64.urlsafe_b64encode(iv + ct + tag).decode().rstrip("=")
```

**同一套思路适用于任何客户端加密**：先找 `subtle` / `CryptoJS` 的调用点，挂钩而不是读混淆表。
本会话在混淆字符串表里看到的一串 16 字符「疑似密钥」全是字符串池条目，**不是 key** ——
只有挂钩拿到的 raw keyData 才算数。

## 4 ★ 请求头别猜 —— 抓 APP 自己的认证请求

自建客户端最容易卡在「token 放哪」。**不要枚举头名，抓一次真实认证流量**：

- `Network.enable` + 导航，在 `Network.requestWillBeSent` 里筛 `-api` / `callback` 路径，打印全部头。
- 实测公开接口只带 `business` / `business_code`（= 租户号）/ `source` / `language` /
  `content_language` / `timezone`；**认证头名是 `authorization_jwt`** —— 既不是 `token`
  也不是 `Authorization`。自造 `token:` 头回的是 `401 未登录`；换成正确头名后立刻变成
  `402 Token invalid` ⇒ **错误码的变化本身就是「头名正确」的证据**。
- 同时抓 body：请求体是 `{"aes_data":"<密文>"}`，用 §3 的 key 解一次就拿到明文入参
  （`{"c_key":"script_config"}`、`{"page":1,"page_size":50}` …）。

**会话节奏也是信号**：实测**注册免验证码**（`registerByAccount` 直通、返回 JWT）、
**登录要极验**（GeeTest v4：`geeCaptchaData.{lotNumber,captchaOutput,passToken,genTime}`，
缺字段依次报 `field "…" is not set`；传字符串回 `type mismatch`，即必须是 object）。
注册返回的 token 当会话 token 用会回 `402 缺少登录参数` ⇒ 把它记成
**「注册 ≠ 登录」**的结论，而不是「认证被绕过」。别把这两件事混成一条 finding。

## 5 CDP 直连（当上层浏览器封装接不上时）

系统 Chromium 直接起无头 + CDP，比依赖上层封装更稳：

```bash
chromium --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
         --remote-debugging-port=9222 --remote-allow-origins='*' \
         --user-data-dir=/tmp/chr --no-first-run
```

- **用 `terminal(background=true)` 起它**，不要 `nohup` / `&`（后台包装会被拦；交给运行时托管才拿得到 pid）。
- 起完**另发一条命令**做就绪检查：`curl -s http://127.0.0.1:9222/json/version` 取
  `webSocketDebuggerUrl`；Node 用**内置 WebSocket**（v22+ 全局可用）直连，无需依赖包。
- 三个必备 CDP 面：`Page.addScriptToEvaluateOnNewDocument`（文档加载前挂钩）、
  `Network.enable`（线上真实头/体）、`Runtime.evaluate({awaitPromise:true})`（页面内跑 async 逻辑）。
- ⚠️ **长跑的 node 脚本不要用管道接 `head` / `tail`**：上游 SIGPIPE 会在落盘前把脚本打死，
  表现为「什么都没输出」。**输出重定向到文件，再单独读文件**。
- 页面内拿 localStorage 的会话键做对照（实测键名：`tz_token` / `tz_refreshToken` /
  `tz_siteConfig` / `tz_login` / `device_id`）—— 与「前端把配置整块缓存在 localStorage」
  的习惯互证：`tz_siteConfig` 常常比接口少一次请求就给全站点配置。
