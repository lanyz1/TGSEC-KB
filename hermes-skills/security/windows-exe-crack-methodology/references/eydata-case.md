# 易游网络验证 (eydata.net) crack campaign — 无双0121.vmp 实战

Target: `无双0121.vmp(2).exe`(58.7MB, VMProtect 加壳, 易语言, 游戏平台辅助 09电竞/11/浩方/kk/sky)。
Outcome: 验证协议完整破解(请求/响应格式 + 状态码语义);hosts 劫持 + 本地 fakeserver 方案搭建完成;
卡点: 成功响应完整格式未知(仅知 `2` = 操作成功弹框,但无法进入功能界面),需有效卡密抓真实成功响应。

## 识别特征
- 文件名含 `.vmp`;PE 区段 `.text`/`.rdata` 熵 0(raw=0 压缩), `./_2`/`.NWh`/`.:/Z` 高熵 = VMProtect 3.x。
- 易语言: 窗口类 `xzddg`(非标准 WTWindow,自定义类名)+ `_EL_PicBox` + `_EL_HideOwner`。
- 登录 UI: `登录卡密:` Edit + `服务器:` ComboBox + `访问方式:` ComboBox + `登录软件` Button + `选择平台`(09电竞/11浩方kk sky)+ `记住卡密`。
- 启动即连 `125.77.163.15:80`(HTTP,非天盾 TCP)。域名 `w.eydata.net` 解析到 45.248.9.242/45.248.9.53/125.77.163.15。

## 验证协议(完全破解)
- 公告请求(启动时): `POST /d4397ae72d53f527`(Content-Length: 0, 无 body)→ 真实响应 `www.sina.com.cn`(15B 纯文本)。
- **验证请求(点登录)**: `POST /5a32d9d8353dbfcb`(路径与公告不同!)
  body: `SingleCode=<卡密>&Ver=5.1&Mac=<32hex机器码>`(Content-Type: application/x-www-form-urlencoded)
- 响应: **纯文本状态码**(Content-Type: text/plain; charset=utf-8, Server: yhui-cloud/20.10.14.1.2)

### 状态码语义(黑盒验证)
| 响应值 | 程序行为(消息框) |
|---|---|
| `-401` | 单码卡密错误(真实服务器对无效卡) |
| `0` | 服务器连接失败 |
| `1` | 单码卡密错误 |
| `2` | **操作成功**(弹「操作成功」框,但功能界面未跳转) |
| `2\|20991231`(带管道符) | 服务器连接失败(格式错误!成功格式非此) |
| `3` | 无消息框(未知,疑似成功路径但无跳转) |

## 破解管线(已验证可用)
1. **hosts 劫持(域名验证首选,比 Frida 简单)**: `127.0.0.1 w.eydata.net` 写入 hosts + `ipconfig /flushdns`。nslookup 会绕过 hosts(显示真实 IP),但应用进程 `socket.gethostbyname` 返回 127.0.0.1 ✓。验证: `python -c "import socket; print(socket.gethostbyname('w.eydata.net'))"`。
2. **本地 HTTP fakeserver 监听 :80**: 区分登录请求(含 `SingleCode=`)→ fake 返回;其他(公告)→ 转发真实服务器(REAL_IPS 列表逐个尝试)。
3. 程序启动 → 公告转发 → 点登录 → SingleCode 请求被 fake。
4. 消息框抓取: 枚举窗口找标题含「信息/提示/错误」→ 读子控件 Static 文本(易语言信息框默认标题 `信息：`,OK 按钮)。

## 抓包方法(VMProtect 下)
- 静态字符串全 VMP 加密(无效)。
- Frida hook `wininet.dll`(易语言 HTTP 用 wininet): `InternetConnectA`(server:port)、`HttpOpenRequestA`(verb+path)、`HttpSendRequestA`(hdr + body args[3]/args[4])、`InternetReadFile`(响应)。
- 程序用 `HttpSendRequestA`(ANSI);响应读取用 `InternetReadFile`(1024B 缓冲,内容是纯文本)。
- Frida 注入 VMP 程序不稳定(多次注入后程序崩溃/窗口消失),但单次快速注入可工作。
- **比 Frida 更好的**: hosts 劫持 + 本地 fakeserver 直接看请求/响应(完全无注入风险)。

## 卡点 & 下一步
- `2` = 操作成功(弹框)但**不跳转功能界面** → 程序本地逻辑需要成功响应的**更多字段**(到期时间/用户数据?),格式未破(`2|xxx` 试错失败)。
- 需要: 有效卡密(天卡几块钱)→ fakeserver 记录真实成功响应 → 对比格式 → 完整伪造。
- 或逆向 VMProtect 后的本地跳转逻辑(难)。

## 复用要点
- 域名型验证(eydata.net): **hosts 劫持优先**(无需注入/无崩溃风险)。
- HTTP 纯文本状态码验证: 黑盒测状态码最快(改 fakeserver 返回值 + 抓消息框)。
- 公告/验证请求区分: 按 body 特征(SingleCode=)分流,fake 只改验证。
- VMP + 易语言: 窗口类可能自定义(xzddg),用 GetClassNameW 动态确认,别假设 WTWindow。
