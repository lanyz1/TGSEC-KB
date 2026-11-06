## 五、子域名接管检测与利用

### 5.1 接管原理（Dangling DNS/CNAME 劫持）
子域名解析（CNAME）指向已注销的第三方资源（S3 桶、Azure 应用、GitHub Pages、Heroku、Zendesk 等），攻击者注册该资源即可完全控制子域名内容，继承父域名信誉，用于钓鱼、投放恶意内容、窃取 Cookie。

**2025 典型案例：** 印尼 `.ac.id`/`.go.id` 等高校与政府域名被接管后投放在线赌博广告——信誉借壳攻击已成为主流滥用方式。

### 5.2 主流服务接管指纹（Fingerprint）
| 云服务 | CNAME/解析特征 | 错误指纹 |
|--------|---------------|---------|
| AWS S3 | `*.s3.amazonaws.com` | `NoSuchBucket` |
| Azure 应用 | `*.azurewebsites.net` | 404 页面 `Azure Web Apps` |
| Azure Blob | `*.blob.core.windows.net` | `ContainerNotFound` |
| GitHub Pages | `*.github.io` | 404 `There isn't a GitHub Pages site here` |
| CloudFront | `*.cloudfront.net` | 403 `Bad request` |
| Heroku | `*.herokuapp.com` | `no-such-app` |
| Fastly | `*.fastly.net` | 502/未知 |
| Shopify | `*.myshopify.com` | 无商店页面 |
| 腾讯云 COS | `*.cos.ap-*.myqcloud.com` | `NoSuchBucket` |
| 阿里云 OSS | `*.oss-cn-*.aliyuncs.com` | `NoSuchBucket` |

### 5.3 检测工具链
```bash
# 自动化指纹匹配（首选 nuclei 模板，签名持续更新）
subfinder -d target.com -silent | nuclei -t ~/nuclei-templates/http/takeovers/ -o takeover.txt

# 专用工具
subjack -w subs.txt -t 100 -ssl -o takeover.txt
subzy run --targets subs.txt
dnsReaper file -f subs.txt -o takeover.txt
# BadDNS（2025 新发布，自动同步 nuclei + dnsReaper 签名库）

# 半自动复核
# 对每个 CNAME 记录发起 HTTP 请求，观察指纹错误响应（见 5.2 表）
```

### 5.4 利用与影响评估
```
1. 注册被废弃资源（S3 桶名/Heroku 应用名/GitHub Pages 仓库）
2. 在接管域上托管钓鱼页/恶意 JS（继承目标信誉）
3. 窃取通过该子域名的 Cookie（父域 Cookie 范围攻击）
4. 影响评估：接管域是否用于邮件（MX 子域→邮件伪造）、是否位于 WAF 白名单
```
**注意：** 接管验证用"无害指纹探测"，实际注册资源须在授权范围与规则允许内，并提前与甲方确认。

