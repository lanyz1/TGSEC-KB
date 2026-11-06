## Cloud-verify (server-issued) verdicts — what the case studies settled
- **Server-issued model is NOT client-crackable without a success sample.** All invalid cards → byte-identical fail response; status 2B is a server-signed gate; any other plaintext status → 非法数据001.
- Fastest routes (from studied cases): (A) 买试用卡/短时卡抓成功响应,对比差异(XDGAME 案,几块钱 vs 逆向几天); (B) 若验证平台免费注册(端游外挂案),注册自建软件 + Frida 替换程序配置 + 自己卡密; (C) 有效卡密。
- **天盾(TianDun)商业版 = 付费 SaaS,免费注册自建软件不可行 → 天盾目标走 A/C。**
- **拿到有效卡密后的捕获流程(fakeserver 转发模式)**: 有卡密时最直接 = 让客户端连真实服务器,在中间转发层打印真实响应 hex。实操: ①启动 `fakeserver(forward 模式)`(监听 127.0.0.1:9001,把请求转发到真实 123.99.192.92:9001,打印 `[resp] len: hex`)②frida 注入 hook `connect` 把 sockaddr 改成 127.0.0.1(frida_redirect.py,注意默认脚本输入的是假卡密 '1234567890123456',**必须改成真实卡密再跑**)③点登陆 → fakeserver 日志出现真实响应 → 分析成功状态码/校验位/密钥流,随后即可离线伪造。注意 fakeserver 进程会被脚本误杀(`kill python` 按 CommandLine 匹配 'fakeserver' 会波及新实例)— 重启用 `terminal(background=true)` 单独管理,别复用旧 PID。
- 搜索技巧: 主流搜索引擎对本机出口 IP 全验证码 → 用 CSDN 搜索 API(`so.csdn.net/api/v3/search`) + Jina 代理(`r.jina.ai/<url>` 返回 Markdown)读被反爬文章。

