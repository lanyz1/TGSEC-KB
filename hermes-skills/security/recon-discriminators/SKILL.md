---
name: recon-discriminators
description: "触发: 端口通但零响应/疑似dev实为停放页/批量扫出满屏200/多域名同机。侦察防误判。"
version: 1.0.0
license: MIT

---

# 侦察判读:别把「连上了」当成「打通了」

## When to Use

任一条命中就进来对照:

- 端口扫出 OPEN、TLS 也握手成功,但**一个字节的 HTTP 响应都收不到**
- 某个域名的页面看起来像开发环境/占位站,拿不准值不值得继续
- 批量扫路径结果**满屏 200**,分不清哪些是真命中
- 手上有一堆域名,不知道该算成几个目标

目标:**把「看起来有戏」和「真的是」分开**,省下的是整轮无效请求。

---

## 1. HTTP/2-only 主机:端口通、零响应(2026-09 实测)

### 症状

TCP 通、TLS 握手成功(TLSv1.3),然后:**空回复**。

| 客户端 | 表现 |
|---|---|
| `requests` | `ConnectionError` / `RemoteDisconnected: Remote end closed connection without response` |
| `curl` | RC **35**(SSL connect error)/ **52**(empty reply)/ **92**(HTTP/2 stream error) |
| 原始 socket 发 HTTP/1.0 | 收到 `b''` |

极易误判成「WAF 拦我」「源站下线」「IP 被拉黑」→ 然后白等好几轮。

### 判定:先看 ALPN,再怀疑 WAF

```bash
python3 -c "import ssl,socket;c=ssl._create_unverified_context();c.set_alpn_protocols(['h2','http/1.1']);w=c.wrap_socket(socket.create_connection(('IP',443)),server_hostname='host');print(w.selected_alpn_protocol())"
```

- 返回 **`h2`** → 服务端只收 HTTP/2。此时发 HTTP/1.1 会立刻挨 **GOAWAY**(裸字节形如 `\x00\x00\x12\x04\x00\x00\x00\x00\x00\x00\x03…`)。
- 返回 `http/1.1` 或 `None` → 不是这个原因,回去查 WAF/出口。

### 接入:换 HTTP/2 客户端

`requests` 不支持 h2;精简版 `curl` 常编进 nghttp2 之外(报 RC 92)。用 **httpx**:

```bash
pip install --break-system-packages "httpx[http2]"
python3 -c "import httpx;r=httpx.Client(http2=True,verify=False,timeout=25).get('https://host/');print(r.status_code,len(r.content))"
```

**实测:同一目标从「零响应」变成 200 + 正常页面。** 换成 h2 后一切照常,不需要任何 WAF 绕过。

> 顺序纪律:**先判 ALPN,再谈 WAF**。ALPN=h2 时折腾 HTTP/1.1 的编码混淆、分块、HPP 全是无效功。

---

## 2. 域名停放页:看着像 dev 环境,其实是广告停放

### 指纹

```html
<title>Redirecting...</title>
```
页面主体是一段内联 JS,含以下任一特征:

- `router.parklogic.com`(POST 上报)
- `adBlockingDetected` / `parameters.isIframe` / `navigator.webdriver`(反自动化探测)
- `document.write('<a id="<随机串>" href="/.<随机串>"></a>')` 然后 `.click()`
- 广告位相关类名:`ad-overlay` / `prebid-wrapper` / `.dfp-ad-container`

### 结论与动作

**这是 ParkLogic 系的域名停放/变现页,不是真站点。** 域名解析得到 IP、80/443 也开着,但内容是空地。

**立刻放弃,不要把它当 dev/staging 继续投入。** 它还会配合反自动化检测返回流重置(`StreamReset … PROTOCOL_ERROR`),让你误以为「有防护要绕」。

> 教训:我在这里先把它标成「开发环境!」,耗了数轮才看页面正文。**看到 200 就先读 title + 正文片段,再下判断。**

---

## 3. 满屏 200:catch-all 基线法

同模板多租户站、SPA 站会对**所有未知路径**返回同一个 `index.html`(状态 200)。

**判据不是状态码,而是长度:**

1. 先请求一个**保证不存在**的路径,记下字节数 = **catch-all 基线**。
2. 之后**只有长度 ≠ 基线的响应才是候选命中**。
3. 同一 host 下多个不同路径返回**完全相同的长度** → 全是兜底页。

### 这个坑有多贵(实测)

批量扫 `/admin/register`、`/.env`、`/bootstrap/cache/config.php`、`/artisan`、`/database/database.sqlite` 时,多个租户**逐路径返回完全一致的长度**(如 18108 / 10951 / 9115 / 6872 / 7939),看起来像「注册开着」「配置缓存可读」。逐条比对长度后确认:**全部是 catch-all,零命中**。

**若不设基线,会把 catch-all 的 200 写进报告当发现** —— 这是最容易自欺的一类假阳性。

> 反向利用:catch-all 的**长度差异**也是指纹。同一批同模板租户长度不同(18108 vs 6872)说明它们的构建/主题版本不同,可作为「哪个租户是异类」的线索。

---

## 4. 同 IP 多品牌归组:资产聚合必做

拿到一批 vhost/子域后,**每个都解析并按 IP 归组**:

```python
import socket
for h in HOSTS:
    try: print(h, socket.gethostbyname(h))
    except Exception: print(h, 'ERR')
```

### 实测结果(8 个域名 → 3 个 IP)

一个「目标站」背后的真实形态往往是:同一台机器上同时挂着

- 目标站 + **几十个同模板 demo 租户**
- **厂商站**(卖/部署目标那套代码的,通常弱得多)
- 邮件 + **Webmail**(Roundcube 之类)
- **支付网关 / API 网关**
- 控制台 / IDE / 发布面板
- 另一台机器:消息网关、测试站、第二个品牌的赌场

### 归组后要重算的三件事

1. **攻击面按「同机」算**:一台的 shell = 全品牌通吃;某一站加固 ≠ 整机加固。
2. **厂商站与目标同机是高价值支点**:厂商站通常弱得多,且它卖的就是目标那套代码 → 拿到平台源码 = 出厂凭据 + 0day 面。
3. **同模板租户是天然对照组**:后台注册/密码重置/调试开关在某个租户是开的,就说明模板能开 → **值得逐个横切比对**,而不是只盯目标那一个实例(只打目标站会得出「全都关着,无路可走」的错误结论)。

### 顺手把证书 SAN 读完

主域证书的 SAN 常把关键内部服务一起暴出来:`webmail.` / `api-gate.` / `gateway.` / `evo-api.` / `xagents.` / `demo-battle.` … **这些往往比主站更值得先打。**

---

## Pitfalls

1. **端口通 ≠ 服务可用**。先看 ALPN + ALPN 选中的协议,再谈 WAF。
2. **200 不等于命中**(§3)。不设 catch-all 基线就会刷出满屏假阳性。
3. **看到 200 先读 title 和正文片段**,再下「这是开发环境」这类判断(§2)。域名有 IP、端口开着、有 HTML,都不代表它是真站点。
4. **别只看主域**:证书 SAN 里的内部服务名优先打。
5. **别只打目标主站**:同机同模板租户的「开着的那个开关」才是突破点(§4)。
6. **区分「路由不存在」与「鉴权拦截」**:`404 + JSON "Route not found."` vs `401 + 业务文案`。两者混淆会让报告自相矛盾。
7. **探针脚本保持短小单一用途**,批量探测由「URL/载荷清单文件 + 几行循环」驱动,而不是把几百行塞进一个脚本。远程上传执行链路上,长脚本更脆(改一处要整份重发),且失败时难以定位。

## 关联

| 技能 | 定位 |
|---|---|
| `site-recon-bypass` | 边界/源站测绘总纲(CF/EdgeOne/WAF/JWT) |
| `space-mapping-engine-recon` | Shodan/Fofa/Censys 语法与额度 |
| `blocked-page-recovery` | 被拦/付费墙页面的回退获取 |
| `ip-ban-bypass` | IP 风控诊断与跳板换出口 |
| `vendor-doc-default-credentials` | 拿到 API 文档后的默认凭据打法 |


---

## 外部库增量（2026-10-11 分享包）

## References(本技能 `references/`)

- `vendor-vs-operator-discriminators.md` —— 厂商(卖模板的) vs 运营方(用模板的):五条判别指纹、默认端口语义、
  静态托管 ≠ API;**★ 含「从厂商前端仓反推真管理面」与「骨架仓里的凭据先判归属再谈用途」两条**(§35)。
- `decoy-page-and-deception-layer-triage.md` —— 诱饵/欺骗层(假后台登录页 + `/gotcha.html`)的三组判别矩阵、
  触发路径全表、页面解剖与处置红线(§34)。
- `size-oracle-compression-and-cf-header-traps.md` —— 体积一律取落盘 `wc -c`,优先用 md5/稳定子串(§31)。
