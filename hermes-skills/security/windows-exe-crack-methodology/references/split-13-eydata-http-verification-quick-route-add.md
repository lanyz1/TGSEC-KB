## EYData (易游) HTTP verification — quick route (adds to the cloud-verify routes)
- 易游/eydata 类域名型验证: **hosts 劫持优先**(`w.eydata.net → 127.0.0.1` + flushdns),应用进程解析走 hosts(nslookup 绕过,用 Python socket 验证)。比 Frida connect hook 简单且无注入崩溃风险。
- 请求: `POST /<software-path>` form-urlencoded body `SingleCode=<card>&Ver=<ver>&Mac=<32hex machine>`;公告请求(无 body)与验证请求路径不同,按 body 含 `SingleCode=` 区分,只 fake 验证请求。
- 响应 = 纯文本状态码: 黑盒测状态码最快(改 fakeserver 返回值 + 枚举窗口抓易语言信息框 `信息：` 子控件文本)。
- 实测状态码: `-401`=单码卡密错误, `0`=服务器连接失败, `1`=单码卡密错误, `2`=操作成功(弹框)但**不跳功能界面**(成功响应带更多字段,格式未破;`2|timestamp` 猜测失败 → 需有效卡密抓真实成功响应)。
- VMProtect 壳下: 静态字符串全加密;Frida hook wininet(HttpSendRequestA/InternetReadFile)可抓协议,但多次注入会崩 VMP 程序,hosts+fakeserver 免注入更优。
- `references/wushuang-eydata-case.md` — 无双0121.vmp VMProtect+易游(eydata.net)HTTP 验证侦察: VMP 区段识别、wininet hook 管线、启动公告 vs 登录请求区分、易游 hosts-hijack 破解路线。

