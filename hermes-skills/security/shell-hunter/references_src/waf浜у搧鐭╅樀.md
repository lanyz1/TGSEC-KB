# WAF 产品级绕过矩阵

> 通用 WAF 绕过见 `waf-bypass.md`；本文件是**识别出具体 WAF 产品后**的产品级绕过。先指纹、后按厂商打。所有绕过均为授权测试场景验证手法。

## 0. WAF 识别速查

| 特征 | 产品 |
|------|------|
| `cf-ray` 头 / `Server: cloudflare` / `__cfduid` cookie | Cloudflare |
| `x-amzn-*` 头 / `AWS WAF` 拦截页 / `awswaf` cookie | AWS WAF |
| `ModSecurity` 头 / `OWASP CRS` 拦截详情 / 405 带规则号 | ModSecurity + CRS |
| `AkamaiGHost` 服务 / `X-Akamai-*` 头 / 403 带参考号 | Akamai |
| `X-Iinfo` 头 / `incapsula` 头 | Imperva |
| `BIGipServer*` cookie / F5 拦截页 | F5 BIG-IP ASM |
| `X-Sucuri-ID` / `Sucuri/Cloudproxy` 头 | Sucuri |
| 阿里云：`X-WAF-*`/`aliyun` 特征、拦截页「阿里云 Web 应用防火墙」 | 阿里云 WAF |
| 腾讯云：`waf.tencent-cloud.com` 拦截页/`TencentWAF` 特征 | 腾讯云 WAF |
| 百度云/安全宝/加速乐/创宇盾：各拦截页文案 | 国产 WAF |

## 1. Cloudflare

| 类别 | 手法 |
|------|------|
| Unicode 归一化差异 | 全角 `＜script＞` 通过 CF 但在后端渲染为 `<script>` |
| 分块传输 | payload 跨 chunk 拆分，CF 可能不重组即放行 |
| SQLi 变异 | `/*!50000UniOn*/SeLeCt`（MySQL 版本注释绕过关键字匹配） |
| XSS 变异 | `<svg/onload=alert&#40;1&#41;>`、`<details open ontoggle=alert(1)>` |
| 源站直连 | 历史 DNS/Shodan `ssl.cert.subject.cn:target.com`/邮件头找源站真实 IP 绕 WAF |
| JSON body | form-urlencoded 换 JSON，不同解析器规则更弱 |
| 超长参数名 | 参数名 >128 字符可能跳过检测 |
| 模式差异 | Managed Rules vs OWASP CRS 不同绕过面；免费版规则少 |
| 注意 | Browser Integrity Check / Bot Management ≠ WAF，别混为一谈 |

## 2. AWS WAF

- **规则组差异**：托管规则组（AWSManagedRules）与自定义规则绕过面不同；先试失真 variant
- **JSON 规范**：AWS 用 JSON 路径匹配 → 嵌套/编码逃逸常见
- **ACL 范围**：CloudFront 前置 vs ALB 前置绕过不同（ALB 可直连源？）
- **大小写/编码**：UTF-8 覆盖字符、双重 URL 编码（一次解码差异）

## 3. ModSecurity + OWASP CRS

- **注释混淆**：`SEL/**/ECT`（randomcomments）
- **版本注释**：`/*!50000...*/`（modsecurityversioned tamper）
- **参数污染**：CRS 对重复参数取第一个/第二个差异（HPP）
- **规则编号认知**：403 带规则号 → 对症绕过（如 942 系 SQLi 规则 -> 换编码）
- **multipart 混淆**：畸形 multipart boundary 让 ModSec 解析与后端不一致

## 4. Akamai

- **指纹验证严**：先看 `X-Akamai-*`，Akamai 依赖 TLS 指纹 + 行为分析
- **请求频率**：限速绕过用 IP 轮换/分布式低频
- **边缘计算**：Akamai EdgeWorkers 可被缓存键碰撞（见 web-cache）
- **已知绕过**：块级数值溢出类 payload、畸形 Content-Type 的解析差异

## 5. Imperva / Incapsula

- **`X-Iinfo` 头**：内容可泄露 WAF 决策细节 → 读它调整 payload
- **页面缓存**：Incapsula 有缓存面 → 缓存投毒绕过即时检测
- **常见绕法**：`\u` 转义序列、JSFuck 类编码在部分规则集下放行

## 6. F5 BIG-IP ASM

- **学习模式**：ASM 有学习周期，全新 payload 可能未被策略覆盖
- **编码链**：`%u` 编码、双重编码、chunked + gzip 压缩组合
- **BIGip cookie 解密**：`BIGipServer...` cookie 解出后端 IP（信息泄露辅助）

## 7. 国产 WAF（阿里云/腾讯云/百度云/创宇盾）

- **脏数据填充**：payload 前后插大量无害字符（长度/正则状态机逃逸）
- **Unicode 变体**：全角/半角混写、`∕`/`⁄` 斜杠变体
- **大小写+注释混合**：`sEl/**/EcT` 多级组合
- **编码叠加**：URL 编码 → HTML 实体 → JSON unicode 三层
- **协议面**：畸形 Content-Type/分块/HTTP/2 降级（见 `http-smuggling` 变体）
- **源站旁路**：子域/测试环境/邮件头/证书历史找真实 IP（结合 CDN 溯源）

## 8. 快速对照表（遇 WAF 先试这几枪）

| 场景 | 第一枪 | 第二枪 | 第三枪 |
|------|--------|--------|--------|
| SQLi 被拦 | `/*!50000*/` 版本注释 | JSON body 重放 | 分块传输 |
| XSS 被拦 | 全角/HTML 实体 | `<svg/onload>` 变异 | 长度填充 |
| 关键字被拦 | 大小写混写 | 注释插入 | 编码叠加 |
| 频率被限 | 换 IP/缩短 payload | 参数名超长 | 低速分布 |
| 全部被拦 | 找源站直接打 | 找子域旁路 | 请求走私 |

## 9. 纪律
- 绕过先有判断再动手：确认 WAF 产品与拦截面，不盲目堆 payload
- 用不超过 5 组精心构造的 payload 验证，不是海量爆破
- 绕过的最终证据仍是业务差分（注入出数据/脚本执行），不是「WAF 没拦截」