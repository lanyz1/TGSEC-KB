---
name: fake-auth-server-redirect
description: Redirect app network verification to a local fake server.
version: 1.0.0
license: MIT
platforms: [windows]

---

# Fake Auth Server Redirect

把 Windows 程序(卡密/登录/VIP 到期)的**网络验证流量重定向到本地模拟服务器**:程序用自己的公钥加密请求 → 本地假服务器用我们私钥解密 → 伪造"成功 + VipTime=未来"响应 → 程序放行。核心是"让程序真的连到 127.0.0.1",而这一步会栽在三个隐形环境杀手(TUN 网卡 / 系统代理 / keep-alive 连接)上。

## When to Use

- 目标程序连验证服务器(RSA+AES 加密请求,服务器端判断到期/卡密)
- 需要伪造"登录成功 / VIP 未到期"而不用逆向 patch 二进制
- 本地模拟服务器已能解密请求并返回正确加密响应,但程序请求"到不了"本地

## Prerequisites

- Python3 + `pycryptodome`(AES/RSA)+ `frida`(公钥运行时替换、连接观察)
- 目标视为已授权资产
- 已通过 RSA 公钥等长替换(219 字节)让程序用你的公钥加密 → 假服务器用你私钥解密

## 排查顺序(流量到不了本地的三大杀手)

按此顺序排查,每步都先确认上一步:

1. **TUN 虚拟网卡透明接管(最阴,最先查)**
   - 症状:程序发了请求但本地服务器收不到;`netstat -ano` 里目标连接源地址是 `172.18.0.1` / `192.168.0.150` 等虚拟网卡 IP,不是 127.0.0.1。
   - 检查:`Get-NetAdapter | Where-Object {$_.InterfaceDescription -match 'TUN|TAP|WireGuard'}`
   - 处理:`Disable-NetAdapter -Name <tun名> -Confirm:$false`(可逆),然后**重启目标程序**。
2. **系统代理(ProxyEnable=1)**
   - 症状:`send` 返回正常字节数(如 375)但本地服务器日志空 —— 数据发给了代理。
   - 检查:`Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings' | Select ProxyEnable,ProxyServer`
   - 处理:`Set-ItemProperty ... -Name ProxyEnable -Value 0`,重启程序。
3. **keep-alive 连接复用(connect hook 永远拦不到)**
   - 症状:程序登录时直接 `send` POST,不出现新 `connect` 调用(用 Frida hook connect 验证)。
   - 原因:验证连接在程序**启动早期**已建立,登录复用 socket。
   - 处理:用 fast-attach(启动后 0.2s 轮询子进程,出现瞬间注入 hook),让 hook 在连接建立前生效;运行中挂 hook 无效,必须重启。

## 快速验证程序到底连了哪

```bash
# Frida hook send + getpeername,打印 POST 请求的真实对端
# 关键输出形如: [SEND] sock=6176 peer=127.0.0.1:514 data=POST http://101.35.246.71:18888/Api
# peer 是实际连接地址,URL 是程序字符串——两者可能不一致(代理/TUN/重定向导致)
```
如果 peer 已经是 127.0.0.1 但服务器没收到 → 看下面的"双端口兜底 + python -u"。

## 服务器侧两个必踩的坑

- **双端口兜底**:程序可能把 POST 发到探测端口(如 514)**或** API 端口(如 18888)。本地服务器直接监听两个端口,日志按 `port=` 区分:
  ```bash
  python3 -u fake_server_dual.py 514 18888
  ```
- **必须 `python3 -u`(或 print flush=True)**:重定向到文件时 print 全缓冲,`tail` 看不到日志会误判"程序没连上",实际请求已到。这是排查时最浪费时间的假阴性。

## 探测端口语义(为什么防火墙会让程序放弃)

程序登录前常先 `connect 验证IP:<探测端口>` 当"服务器在线"检查:
- 真实服务器探测端口关闭 → **ECONNREFUSED → 程序照样继续发 API 请求**(不是硬前置)
- **防火墙 block 出站 → 超时/无响应 → 程序认为服务器不可达,放弃整个登录**
- 结论:别用防火墙 block 验证 IP 来"逼 fallback";要让探测得到"拒绝"或重定向到本地监听成功。若程序有备用域名,hosts 劫持域名到 127.0.0.1 有效,但前提是 IP 线路失败方式是拒绝而非超时。

## Frida hook 内置 Python C API 的崩溃坑

Nuitka 编译程序内部是 `python310.dll`。**不要 hook `PyDict_SetItem`/`PyObject_Call` 想改 Status=1** —— 解释器热路径被高频调用,hook 里再调 NativeFunction(`PyUnicode_AsUTF8`)会立即崩溃(attach 后进程 DEAD)。要改登录判断就走静态逆向(patch 机器码)或响应层伪造,别动解释器内部。

## 工作流偏好:动态 hook 走不通就转静态逆向

用户明确要求:**网络模拟/Frida 绕圈超过时限(约 10 分钟)还走不通,就直接"整个逆向 + 去掉验证 + 重新封包"**(反编译 → patch 验证分支 → PyInstaller 重新打包),不要无限期在运行时 hook 上打转。动态调试只是侦察手段,静态逆向产物才是交付物。

## Pitfalls

- `frida-trace -i "send"` 会 hook 到 WSOCK32.dll(旧库)→ 必须 `-i "WS2_32.dll!send"`
- Frida `Module.findExportByName` 报 "not a function" → 用 `Process.findModuleByName(...).getExportByName(...)`;拿不到时用 `module.enumerateExports()` 遍历找
- 程序解析 IP 时 hook `getaddrinfo` 重写结果,注意 x64 参数:`getaddrinfo(host, service, hints, ppResult)` 第 4 参是 `args[3]` 不是 `args[4]`
- 改 hosts / 防火墙 / 重定向后**必须重启目标程序**才生效;运行中改环境多数无效
- 浏览器操作 NiceGUI 页面点登录无网络活动 → 可能程序已缓存失败状态或 WebSocket 断,重启程序再试

## Verification

- [ ] `netstat` 无虚拟网卡源地址连接(排除 TUN)
- [ ] `ProxyEnable=0`(排除系统代理)
- [ ] Frida 看到程序 connect 到 127.0.0.1 且本地服务器日志出现 `[REQ]`
- [ ] 程序接受伪造响应进入主界面

## References

- `references/qingyun-fndata-case.md` — 轻云3.8 + fndata 平台完整实战:验证系统画像、协议细节、三连坑(TUN/代理/keep-alive)证据、各 Frida/Python 工具文件用途。做同类 fndata 网络验证目标时先读这份。
