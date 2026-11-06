---
name: build-artifact-exposure
description: "Use when build zips (dist.zip) leak at the web root."
version: 1.0.0
tags: [recon, source-exposure, build-artifact, vue, uniapp, admin-bundle, cwe-540]
related_skills: [same-origin-upload-xss, spa-request-contract-extraction, admin-credential-hunt]
---

# 构建产物裸奔（部署包直挂 web root）

**一句话**：国内自研后台最常见的部署动作是「打完包把 zip 扔到站点根目录」，
于是 `/web.zip`、`/admin/dist.zip` 一次 GET 就是**整套前端 + 整套后台源码**。
性价比高于接口爆破、高于备份扫描、高于猜口令 —— 优先查它。

命中后拿到的不是「一个文件」，而是：完整 API 表、字段名、权限点、后台路由表、
懒加载 chunk 清单，有时还有写死的演示账号/内部域名/云存储桶名。

## 什么时候用

- 目标是自拼的 SPA（Vue/React）/uni-app 壳 / Go·PHP 服务的前端
- 拿到后台登录页，但接口未知、字段未知、路由不明
- 想反推后台完整功能面（而不是一页页点）
- 常规泄露面（`.env`/`.git`/备份）已空，需要另一条读源码的路

## Step 1 探路径（并发扫，别单线程）

**单线程 + 每个 404 等 6s，2000+ 路径要跑 3 小时**（实测被拖死一次）。
用 `scripts/artifact_fuzz.py`：24 线程，50 名 × 10 后缀 × 4 目录 ≈ 2280 条几分钟扫完。

```bash
python3 scripts/artifact_fuzz.py https://target
```

单站点手工最小集（快速验证）：

```bash
TARGET=https://target; OUTDIR=./artifacts; mkdir -p $OUTDIR
for p in web.zip dist.zip admin/dist.zip admin.zip static.zip src.zip www.zip \
         h5.zip app.zip pc.zip manager.zip backend.zip frontend.zip html.zip \
         build.zip release.zip latest.zip update.zip; do
  code=$(curl -sk -o /tmp/z.bin -w "%{http_code}" --max-time 10 "$TARGET/$p")
  if [ "$code" = 200 ] && head -c4 /tmp/z.bin | grep -qa 'PK'; then
    echo "[ZIP] $TARGET/$p $(stat -c%s /tmp/z.bin)"
    cp /tmp/z.bin "$OUTDIR/$(echo $p | tr / _)"
  fi
done
```

**判据只认 GET 下来的字节魔数 `PK\x03\x04`**：SPA catch-all 对 `/web.zip` 同样回 `200 text/html`（就是 index.html）。
**别用 `curl -I` 判**：HEAD 不带 body，`%{size_download}` 恒为 0，`/admin/dist.zip` 这种真包会被误判成空响应 —— 必须 GET 真字节。
附带看 `Content-Disposition: ... filename=` 与 `Last-Modified`（后者能判这个包是当次构建还是几个月前的旧包），有它基本是真文件。

**命中一个就横向扩同目录**：运维把打包扔根目录是习惯不是个案。拿到 `/web.zip` 后立刻把
`dist/h5/front/static/upload/source/src/code/go/server/backend/bin/build/release/deploy/admin/admindist/api/service/core/main/app/wwwroot/public/html`
× `.zip/.tar.gz/.tgz/.rar/.7z/.war/.jar/.sql/.gz/.bak` × `/{name}{ext}`、`/{name}/{name}{ext}`、`/static/`、`/assets/` 全扫一遍。
阴性也要写清扫了多少条（2026-10 实测 2280 条只有已知两个包，说明该目标没留后端源码包）。

**后台包通常在 `/admin/dist.zip` 而不是 `/dist.zip`** —— 两个都要打。
同为 Vue 工程，前后台两套 chunk 交叉比对才能拼出完整路由表（后台模块大量懒加载，公网包里根本没有）。

## Step 2 解包 + 定向 grep

```bash
unzip -o -q "$OUTDIR"/*.zip -d "$OUTDIR/src"
# 接口面
rg -oN --no-filename '["\x27`](/api/[a-zA-Z0-9_/{}\-.$]+)' -r '$1' "$OUTDIR/src" | sort -u > api_paths.txt
# 鉴权/存储/密钥
rg -n 'localStorage\.setItem|sessionStorage|Authorization|Bearer|secret|appSecret|accessKey|AKID' "$OUTDIR/src" | head -80
# 内网与云资产
rg -n 'http://(192\.168|10\.|172\.(1[6-9]|2[0-9]|3[01]))|s3\.|oss-|cos\.ap-|minio' "$OUTDIR/src" | head -50
```

再按模块关键词（`admin|role|permission|setting|withdraw|audit|export`）分 chunk 扫，定位后台独有入口。
有 `.map` 更好：`rg sourceMappingURL` 命中就直接下 `.js.map`，可还原原始工程目录结构。

## Step 3 把源码变成攻击面（真正的交付）

1. **接口表**：`api_paths.txt` 按模块归类 → 优先 `/admin/*`、`export`、`list`、`detail` 这类直出数据的
2. **字段表**：从表单定义/表格列定义抄字段名 —— 提交体与查询参数都不用猜
3. **权限点**：`permission`/`roles`/`hasPerm` 字符串 = 后台 RBAC 完整清单（拿去打授权不对称）
4. **二次验证形态**：grep `google|totp|otp|2fa|seed`；若后台用户列表响应模型里带 `googleSecret` 之类字段，
   说明**种子随列表接口明文返回** —— 这比猜口令省事得多
5. **版本**：`package.json` 里的框架/依赖版本 → 直接对已知 CVE
6. **写死的东西**：演示账号、测试手机号、内部域名、云桶名、地图/短信 key
7. **能力面披露**：就算进不了后台，包里每个管理页的列定义已经告诉你「后台能做什么」——
   实测：`UserList` 有「改任意用户密码」字段、`ThirdPartyConfigList` 存支付/短信/客服的 `secretKey`/`privateKey`、
   `AdminList` 明文渲染每个管理员的 `googleSecret`。这既是漏洞定级论据（泄露=这些能力暴露）也是拿票后的直接路线图
8. **★ 远端配置拉取 → API 发现文件 → 源站裸 IP（包里最贵的一行）**：前端常不硬编码 API，
   而是启动时 fetch 一个 `*ip.json` / `config.json` / `env.json`。grep `\.json["']` + `s3\.|cos\.|oss-|amazonaws`
   就能把 URL 抄出来。**那个宿主桶往往匿名可读，直接 GET**；清单里的**兜底裸 `IP:port` 才是源站**——
   实测一次 GET 就把「只能打 CDN」变成「一机 18 端口 / 多租户 / 无 WAF」。
   拿到裸 IP 后全端口扫 + 免鉴权 `/v1/home-page` 做租户指纹，链路与判读表见
   `api-contract-mining/references/build-artifact-to-origin-port-farm.md`。

## 坑

- 只认魔数：`200` + HTML 是 SPA 兜底，不是泄露（最易误报结案）
- `/admin/dist.zip` 与 `/web.zip` 是两个不同产物，只打一个会缺一半路由
- chunk 压缩过，字段名/路由名还在（字符串没混淆），但变量名没了 —— 别指望读懂逻辑，只抄名字和路径
- 部署包可能是**旧的**，接口与线上有时差，用一条无害 GET 验证再写进报告
- **★ 包会重建：盘上有副本也要回线上重下一次再 diff**。实测同一 URL 相隔数天两份包：文件数 314→330、体积 46.3MB→47.4MB，多出的 16 个文件里带 3 个**新端点**（`tax-order` 系）——只用手上旧包会漏掉整个新模块，然后把「路由不存在」写成错误结论。diff 姿势：
  `comm -13 <(cd dist_old && find . -type f|sort) <(cd dist_new && find . -type f|sort)`
  构建即使内容不变，全站 hash 也会因重打包而变 —— **按文件清单和端点集 diff，别按 hash**。
- **拿到源站裸 IP ≠ 能打源站**，先分清「端口不通」和「IP 白名单」：实测源站 TCP 通、显式 SNI 的 TLS 握手成功且拿到自签证书，但 HTTP 请求发出去**服务器零字节断开** —— 这是 **HTTP 层来源 IP 白名单**，不是服务死了。三段判据：明文 HTTP 带错 Host → `444`（nginx 无匹配 server 块，端口活着）；带对 Host → `302` 备案拦截；带 SNI 的 HTTPS → 0 字节断开 = 白名单。
  **curl 对 IP 字面量不发 SNI**（RFC 6066），必须显式给：
  `curl -sk --resolve host:37416:1.2.3.4 https://host:37416/v1/captcha -w '%{http_code} %{size_download}'`
  此时唯一出路是「让请求从白名单内发出」（目标自身 SSRF / 同网段主机），**换出口 IP 无效**。
- 拿到源码 ≠ 拿到权限：源码只降低其他攻击面成本，交付时要说清「由它派生了哪些验证」

## 交付口径

证据三件：①`/web.zip` 的 200 + 字节数 + `PK` 头 ②解包后的文件/chunk 数 ③从包里抄出的、线上验证有效的≥1 个接口或字段。
只有 ①② 写「源码泄露（高）」；补上 ③ 才写「已转化为攻击面」。

## 支持文件

- `references/rmzc-deployment-zip-walkthrough.md` — 实测：双包在根与 `/admin/` 下、解包产出的字段形态与踩坑
- `scripts/artifact_fuzz.py` — 24 线程并发扫部署包/备份（50 名 × 10 后缀 × 4 目录 ≈ 2280 条，按魔数判真伪）
