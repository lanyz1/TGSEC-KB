# 无双0121.vmp(2).exe — 易游(eydata.net)HTTP 验证侦察记录

Target: 易语言游戏平台辅助(09电竞/11平台/浩方/kk/sky), VMProtect 加壳, 58.7MB。
Session outcome: 加壳类型 + 验证系统(易游 eydata.net)+ 启动公告请求抓包完成; 验证请求未触发(卡密格式校验或 Frida 干扰), 30 分钟时间盒到止损。

## 加壳识别(VMProtect)
- `.text` 熵 0.00(raw size 0 = 压缩), `.rdata` 熵 0.00(vsize 0x03329dd6 ≈ 53MB 原始数据被压)
- 混淆区段名: `./_2`、`.NWh`、`.:/Z`(`.:/Z` 熵 8.00 = 加密数据)
- EntryPoint 0x49cd057 落在 `.:/Z`(VMP stub)
- ImageBase 0x400000, DllChar 0, 无 ASLR
- ASCII 字符串全 junk(VMP 混淆, `QQ`/`GetSystemTimeAsFileTime` 命中是误报)
- 静态字符串/代码分析无用 → 只能动态

## 窗口结构(易语言, 自定义类名)
- 主窗口类 `xzddg`(标题是加密串如 `2V88SJV8RBY233N03O` — 非 WTWindow!)
- 子控件: `登录卡密:` Edit / `服务器:` ComboBox / `访问方式:` ComboBox / `登录软件` Button / `选择平台`(09电竞平台 / 11/浩方/kk/sky)/ `记住卡密` / `_EL_PicBox`(图片框)
- `_EL_HideOwner`(易语言 owner 隐藏窗)— 确认易语言

## 网络验证(易游 eydata.net)
- 启动即连 `w.eydata.net:80`(HTTP), netstat 显示源 IP 172.18.0.1(TUN 适配器)
- wininet 请求: `InternetConnectA server=w.eydata.net port=80` → `HttpOpenRequestA POST /d4397ae72d53f527` → `HttpSendRequestA`(Content-Type: application/x-www-form-urlencoded, body 为空)→ `InternetReadFile` 返回 1024B 缓冲区含 `www.sina.com.cn`(公告,非验证结果)
- ws2_32 send/recv hook 抓不到(wininet 内部缓冲)— 必须 hook wininet API
- 点「登录软件」未触发新 HTTP 请求: 可能卡密格式校验(TEST1234567890 非格式)或 Frida 注入干扰(VMP 反调试)
- Frida 多次注入后程序崩溃(窗口消失, PID 无窗口)

## 易游破解路线(经典, 已发表)
- hosts 劫持 `w.eydata.net → 127.0.0.1`(域名对 HTTP 比 Frida connect 重定向更简单)
- 本地模拟易游服务器(form-urlencoded POST → 返回成功 HTML/文本)
- 或 hook HttpSendRequestA/InternetReadFile 进程内改响应
- 易游协议 = form-urlencoded POST, 响应 = HTML/明文判定(相对天盾 TCP 加密简单)

## 产物
- 脚本: D:\渗透\无双_crack\ (sniff_start.py / sniff4.py wininet hook; http_fakeserver.py; frida_http_redirect.py)
- 抓包: D:\penetration_wushuang\sniff*.log
