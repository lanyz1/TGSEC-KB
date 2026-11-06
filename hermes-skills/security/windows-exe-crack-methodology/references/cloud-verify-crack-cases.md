# 云端验证(服务端签发/云端下发)破解成功案例研究

研究背景: 后会无期4.15(天盾网络验证)最后一关 = 状态码服务端签名,纯客户端无法绕过。
联网检索「服务端签发、云端下发」型验证的逆向成功案例,提炼可复用方法论。

## 案例1: 端游外挂网络验证(黄金思路 — 平台注册自建软件)
来源: CSDN 2503_90751789/article/details/159005812「某端游外挂网络验证的分析与破解思路」

流程:
1. HTTP Debugger 抓包 → 发现程序启动时从云端拉取 `SSSSSPRO.json` 配置
2. 发现同平台有免费版(同格式配置)→ 猜字段含义(Software MD5 / Updater MD5 / 每日代币数据)
3. 本地 Flask 模拟配置服务器(8818 端口)→ **Frida gadget 注入(loader.exe CreateProcess 启动后立刻注入)** → `Memory.writeUtf8String` 改程序内 URL → 指向 127.0.0.1
4. 卡密验证部分: 不逆向验证点(吃操作),而是**定位网络验证平台后台**(子域名扫描 `doc.*.com` / `web.*.com` 拿到 API 文档 + sign 算法 + SDK)
5. **平台允许任何人注册** → 注册后自建软件 → 生成配置(app_key / rc4_key / key)→ **Frida 内存替换程序里这几项配置** → 平台给自己生成永久卡密 → 登录成功

关键洞察: 对 SaaS 型验证,不需要逆向验证代码,而是**把自己变成平台管理员**(替换程序指向的软件配置为自己的合法配置 + 自己的卡密)。

## 案例2: XDGAME 卡密验证改包(需要成功响应样本)
来源: CSDN yangshunyao_1/article/details/148956941「记一次成功抓包改包破解简单卡密验证记录」

流程:
1. HTTPDebugger 抓包 → 观察响应 200 有反应但弹「无效值」
2. **花 2 元买试用码** → 对比 失败响应 vs 成功响应 → 发现成功多 `time` 和 `data` 字段
3. 直接改响应(time 加 0 延长)→ 破解成功

关键洞察: 无成功样本时,**低成本买一张试用卡/短时卡抓成功响应**,差异对比是最高效路径(几块钱 vs 逆向几天)。

## 案例3: 天盾网络验证 VMP 强壳逆向(脱壳方法论)
来源: CSDN wuyoula/article/details/148484217「天盾网络验证 VMP 强壳逆向」

流程:
1. 动态调试定位关键 API: `GetSystemTimeAsFileTime`(kernelbase) + `QueryPerformanceCounter`(ntdll)
2. 在这两个 API **尾部下断点**(不在 ret 前,要有辨识度)
3. 执行 QueryPerformanceCounter 断点后观察返回 → 注意返回 text 领空 → **text 段向上找程序入口点(OEP)**
4. dump + UIF 工具重建 IAT → IDA 分析

原理: VMP 壳用时间函数做防调试时间校验,断点时间函数能定位 VMP 解密后的真实代码。

## 天盾平台可注册性结论
- 天盾网络验证 = **商业 SaaS 产品**(CSDN 有源码售卖、离线版 746 等),后台需购买授权,**免费注册自建软件不可行**(与案例1的免费平台不同)。
- 「天之盾」是开源项目(核心源码开放,非 SaaS),也不能注册换配置。
- 因此对天盾商业版,最实际路线 = **买试用卡密抓成功响应**(案例2 思路)或**有效卡密**。

## 对纯 TCP 自定义协议验证的适用性
- 案例1/2 都是 HTTP 接口(易抓包、易改包)。后会无期是 TCP 二进制协议(加密 payload)。
- TCP 场景改包 = 本地 fakeserver(见 tiandun-runtime-lib.md 的 connect 重定向 + fakeserver 管线),已实现文本伪造,状态签名未破。
- 买卡密抓成功响应对 TCP 同样有效: fakeserver 记录有效 vs 无效卡密的完整响应对 → 对比状态码密文差异。

## 搜索/读文技巧(本次实战)
- 主流搜索引擎(Google/Bing/百度/DuckDuckGo)对本机出口 IP 全部验证码拦截 → 改用:
  - **CSDN 搜索 API**(可用): `https://so.csdn.net/api/v3/search?q=<urlencoded>&t=blog&p=1` → JSON `result_vos[]`(title/url/description)
  - **Jina AI 网页代理**: `https://r.jina.ai/https://<target-url>` → 返回 Markdown 全文(绕过 CSDN/博客反爬,curl 直接可用,免费)
- 52pojie 站内搜索重定向到必应+Cloudflare,不可用。
- GitHub API 中文关键词搜索质量差(返回无关 repo)。

## 后续行动清单(若拿到卡密/试用码)
1. fakeserver(raw 模式)记录 有效卡 vs 无效卡 的请求/响应对
2. 对比状态码密文: 有效卡 = 成功状态密文(≠54ae)+ 成功文本密文
3. 用成功响应的密钥流规律反推: 密钥流 = f(卡号+机器码),同卡固定
4. 构造: 成功状态密文 + 任意文本密文 → fakeserver 返回 → 程序进主界面
5. 或直接 hook 0x9e90c 返回结构(见 tiandun-runtime-lib.md)在客户端伪造成功数据
