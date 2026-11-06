# SPA 配置解码与 CDN 回源恢复

本文件是 SKILL.md 第 6 步的展开：当 CDN/WAF 把应用层路径全部 301 掉，如何从「静态资源」和「SPA 内联配置」里把 API 契约、站点编号、访客 token 捞出来。

## 1. 判定回源模式

请求任意应用路径（`/api/...`、`/assets/...`、`/hall/...`），观察 301 的 `Location`：

```
HTTP/1.1 301 Redirect
Location: https://153.43.231.188:18027/?cid=939108/api/system/status
```

含义：CDN 把「路径」塞进了回源请求的 `cid` query 里。回源服务按 `cid` 的第一段做站点路由、剩余部分当静态路径。

## 2. 两种拼法都试

| 拼法 | 结果 |
|---|---|
| `https://<origin>:<port>/?cid=<siteCode>/<path>` | 多数返回 SPA（路径被当路由） |
| `https://<origin>:<port>/<path>?cid=<siteCode>` | **静态资源 200**（JS / manifest / 图片） |

实测：`/assets/theme-0/index.XXXX.js?cid=939108` 返回 200 的入口 JS，而 `/?cid=939108/assets/...` 返回整张 SPA。

## 3. manifest → 全量 chunk

入口 JS 内容形如：

```js
window.__MANIFEST_ASSETS = 'assets/theme-0/manifest.8e3fa8ac.json';
import"./commonChunk.AUoCIbzg.js";import"./vendorChunk.CxNzOamF.js";
```

取 `manifest.<hash>.json` 得到 `preload` 数组（全部 chunk 与 CSS 路径），再按同样拼法逐个下载。主 chunk 常有 1–2 MB，业务逻辑、API 路径、错误文案都在里面。

## 4. 双层编码的站点配置

SPA HTML 里：

```js
window.LOBBY_SITE_CONFIG = JSON.parse(M)
```

`M` 来自 `decodeURIComponent(window.atob("..."))`，且 base64 尾部常带 `@<uuid>` 干扰串。正确解两层：

```python
import base64, urllib.parse, json

s = open('spa.html', encoding='utf-8', errors='ignore').read()
j = s.find('UGF0aCUyMi')            # 配置 blob 的 base64 头部特征，或直接搜 'window.atob('
a = s.rfind('"', 0, j); b = s.find('"', j)
raw = s[a+1:b].split('@')[0]        # 去掉 @uuid
txt = base64.b64decode(urllib.parse.unquote(raw)).decode('utf-8', 'ignore')
txt = urllib.parse.unquote(txt)      # 第二层 URL 解码
cfg = json.loads(txt)
```

顺序要点：**base64 解码得到的仍是 URL 编码文本，必须再 unquote 一次**。只解一层会看到 `%7B%22...`（`{"` 的编码）而误判「解码失败」——这是最常踩的坑。若 `base64.b64decode` 报 padding 错，先 `urllib.parse.unquote` 再解。

## 5. 配置里值得优先看的键

```
INJECT_DATA.<apiGetXxx>      SSR 预取的 API 响应快照（等于免鉴权数据）
  .apiGetSystemStatus        → homeGetSysInfo.token（访客 token）
                             → fingerprintJS.publicKey / geetest_captcha_id
  .apiGetSiteInfo            → siteCode / parentSiteCode / deployEnv / skinId
  .apiGetAppDownloadInfo     → APK 直链、备用下载域名
  .apiGetMessageAll          → 公告 / 站内信
siteinfos                    → ossBaseUrl（存储桶前缀）
INJECT_DATA.apiGetSystemStatus.data.data.promoteGetSocialmedia
                             → Telegram 频道、客服 QQ/微信/WhatsApp 链接
```

`siteCode` 是包网 SaaS 的客户编号，`parentSiteCode` 是总站编号——这两个值能把同平台的不同客户站点串起来。

## 6. 存储桶从配置里冒出来

配置里的图片 URL 常直接泄露桶域名：

```
https://<bucket>.oss-accelerate.aliyuncs.com/siteadmin/...
https://<bucket>.s3.ap-east-1.amazonaws.com/cocos/...
```

`oss-accelerate` 是加速域名，列桶/取对象要用真实 region endpoint；region 打错时阿里云 403 XML 会回 `<Endpoint>` 字段，直接照抄即可。

## 7. 失败信号（出现即停）

- 所有 `/hall/api/*`、`/api/*` 都 301 到同一个静态回源 → WAF 规则写死；换同平台的其他客户站试，别在同一站反复换编码。
- XFF / X-Real-IP / True-Client-IP / Forwarded 全部无效 → WAF 不信任这些头，停止绕过尝试。
- 回源端口对任意 `Host` 都返回同一张 SPA → 回源服务只服务静态，API 不在这个端口。
- `Host:` 改成 `admin.` / `api.` 返回 530 → 该子域无 vhost，不存在。
