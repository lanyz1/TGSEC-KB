---
name: auth-server-emulation
description: Fake an auth server by swapping the client RSA key.
version: 1.0.0
license: MIT
platforms: [windows, linux, macos]

---

# 验证服务器模拟绕过(客户端公钥替换 + 本地假服务器)

当目标程序用**内置 RSA 公钥**加密请求、连远程验证服务器(卡密/登录/VIP 到期),且**服务器端**校验拒绝(如 `Vip已到期`、`注册名额用尽`),本地时间回拨无效时,用本方法**完整接管验证**。已在轻云3.8(fndata 平台,RSA+AES-192-CBC)实战验证。

## When to Use

- 登录/心跳被**服务器端**拒绝(返回错误状态码,不是本地判断)——时间回拨、patch 本地判断都无效
- 程序内置 RSA 公钥(字符串表里有 `-----BEGIN PUBLIC KEY-----`)
- 想伪造"登录成功 + VIP 永不过期 + 任意卡密/积分"而不依赖真实服务器
- 服务端关闭了注册(`注册名额用尽`)或免费试用期已过

## Prerequisites

- Python3 + `pycryptodome` + `frida`(Windows 上)
- 目标程序的 main DLL/二进制可读、可写(先杀进程解锁,改前备份)
- 掌握目标的请求加密格式(见下方 fndata 示例;其他平台先抓包还原)

## 核心原理

```
客户端请求:  {"a": RSA公钥加密(随机AES密钥), "b": AES-CBC加密(JSON请求体)}
服务器响应:  {"a": AES加密(JSON响应), "b": MD5(明文响应)}

攻击:
  1. 生成自己的 RSA 密钥对
  2. 把程序内置的公钥等长替换成自己的公钥(1024位 PEM body 恰好 219 字节)
  3. 本地起 Flask 假服务器,用私钥解出 AES 密钥 → 解出请求体 → 按 fnobj 返回伪造成功响应
  4. Frida hook connect/WSAConnect 把目标服务器 IP:PORT 改写到 127.0.0.1
```

## 流程

### 1. 生成密钥对(必须等长!)

```python
from Crypto.PublicKey import RSA
key = RSA.generate(1024)
pub = key.publickey().export_key(format='PEM')
body = pub.split(b'-----BEGIN PUBLIC KEY-----\n')[1].split(b'\n-----END PUBLIC KEY-----')[0]
assert len(body) == 219, f'length mismatch: {len(body)}'  # 必须等于原公钥 body 长度
open('my_priv.pem','wb').write(key.export_key(format='PEM'))
open('my_pub.pem','wb').write(pub)
```

1024 位 RSA 公钥 PEM body 固定 219 字节 —— 等长替换不需要改任何指针/段大小。若目标是 2048 位(body 392 字节),同样等长替换即可。

### 2. 替换程序内全部公钥

```bash
# 参考 scripts/patch_pubkey.py:正则找所有 PUBLIC KEY 块,校验等长后逐块替换,写 .bak 备份
# 注意:先从后往前替换保持偏移有效;文件被运行中进程锁定时先杀进程
```

### 3. 启动本地模拟服务器

```bash
# scripts/fndata_fake_server.py —— fndata 平台专用,监听 0.0.0.0:18888
# 用私钥 RSA 解密 a → AES 密钥 → 解 b → JSON 请求 → 按 fnobj 返回伪造响应
python3 fndata_fake_server.py
```

登录成功响应最小字段(fndata):`Status:1, Msg:"登录成功", User, Key, LoginIp, LoginTime, OutUser, RegisterTime, UserClassMark:1, UserClassName, VipNumber, VipTime:<2099>, NewAppUser, Token`。**HeartBeat / GetAppUserInfo / GetAppGongGao / LogOut 也要按 fnobj 返回**,否则登录后功能异常或心跳踢下线。

### 4. Frida 重定向连接

```bash
# scripts/fndata_redirect.js —— hook ws2_32 connect + WSAConnect
# 目标 sockaddr 是 101.35.246.71:18888 时改写成 127.0.0.1:18888
frida -p <主进程PID> -l fndata_redirect.js
```

### 5. 验证接管

触发登录(浏览器带 webview2 token 操作 UI,或程序内点登录),假服务器日志出现 `[REQ] ... fnobj=UserLogin` 即接管成功。UI 可能仍需点一次登录按钮;若请求到了但没跳转,检查响应字段是否缺前置接口(如 GetToken)。

## Pitfalls

- **⚠️ PyInstaller onefile 父子进程:hook 挂对进程!** PyInstaller onefile = 父进程解压器 + **子进程**才是主程序(main.dll、网络逻辑全在子进程)。`frida -p <父PID>` 挂上去 connect hook 全静默、main.dll 也扫不到公钥(轮询 120 次超时)。必须 attach **子进程**(psutil/`Get-CimInstance` 按 ParentProcessId 找),或**快速轮询 attach**:启动 exe 后每 0.2s `dev.enumerate_processes()` 找刚出现的子进程立即注入(见 `scripts/fast_attach.py`)。⚠️ **不要用 spawn gating**:`dev.enable_spawn_gating()` / `dev.enable_child_gating()` 在 Windows 上抛 `frida.NotSupportedError: not yet supported on this OS`。症状:脚本 ready 但 `pubkey not found` + 无 REDIRECT
- **⚠️ 启动期 keep-alive 连接:hook 晚了就拦不到 connect**。程序常在启动时就建好到验证服务器的 TCP 连接(keep-alive),登录时直接复用 `send`,不会再有新 `connect` 调用 → 后挂的 connect hook 永远看不到。诊断:netsniff 只见 `[send] POST /Api...Host: <IP>:<port>` 却无对应 connect。解法:**重启程序后在子进程刚出现、连接建立前立即 attach**(或 spawn + child-gating)
- **⚠️ 前置探测端口(如 514):探测失败就中断登录流**。程序可能先 connect 一个"服务器在线"探测端口(轻云是 514),失败即放弃后续 18888 请求(日志只有 `[connect] IP:514 -> ret=0xffffffff` 就停了)。此时要么本地监听 514 并回数据,要么 Frida 对探测端口也重定向;但**不要对非阻塞 connect 强制返回成功**(`retval.replace(0)` 会让程序以为 socket 已连上,实际不可用,流程更乱)。先观察 connect 序列再决定
- **⚠️ 磁盘 patch 公钥每次重启失效**:PyInstaller onefile 每次启动都重新解压,磁盘上 patch 的 main.dll 是临时解压产物,重启即还原。**持久做法是 Frida 运行时内存替换**(扫描 `-----BEGIN PUBLIC KEY` → `Memory.protect rwx` → 写等长新公钥),挂在子进程上,每次启动重新挂即可
- **等长是硬约束**:替换公钥必须字节数完全一致;不一致宁可重新生成密钥对(1024→1024,2048→2048),不要硬塞
- **先杀进程再改文件**:运行中的 main.dll 被锁,PermissionError;改前一定备份
- **从后往前替换**:多个公钥时从最后一个开始替换,避免偏移失效
- **本地时间回拨救不了服务器端判断**:登录直接返回 `Vip已到期` 是服务器拒的,先确认是本地还是服务器端再选方案
- **假服务器要覆盖全部接口**:登录成功只是开始,HeartBeat 不返回会让程序心跳失败自动退出
- **系统代理会干扰**:程序走 v2rayN/xray 代理时,连接重定向 hook 可能看不到目标 IP;必要时关代理重启程序再挂 hook
- **响应加密细节**:AES-192-CBC + PKCS7,IV=key[:16];MD5 用明文响应大写 hex
- **⚠️ 归因验证(血的教训)**:假服务器日志出现请求 ≠ 程序连上了!你自己用 `requests.post` 测试假服务器时也会产生 `[REQ]` 日志。必须核对**源地址/源 PID**:程序请求应来自目标进程、源 IP 通常是 127.0.0.1 或目标机内网 IP;如果日志里请求源是 Docker 网段(172.x)或你自己测试用的 IP,那就是你自己的流量,不是目标程序。**验证接管前先确认归属,否则会把"自己测试通了"误报成"程序被接管了"**——用户最恨这种未经证实的乐观结论
- **frida CLI 交互模式不打印 send() 消息**:`frida -p PID -l script.js` 进 REPL 后,脚本里 `send()` 的输出**不会**实时打印(除非按回车或加 `-q` 非交互)。诊断"hook 没触发"时,先把脚本改成 `console.log` 或直接看假服务器日志,别因为看不到 send 就误判 hook 失效
- **Python asyncio 在 Windows 用 ConnectEx 不是 connect**:若程序用 aiohttp/asyncio(ProactorEventLoop),普通 `connect`/`WSAConnect` hook 永远抓不到连接——它走 `ConnectEx`(IOCP 异步),函数指针通过 `WSAIoctl(SIO_GET_EXTENSION_FUNCTION_POINTER)` 运行时获取。hook `WSAIoctl` 拦截返回指针再 `Interceptor.attach` 那个地址,或用 `scripts/fndata_redirect.js` 的 ConnectEx 分支。症状:getaddrinfo 触发了但 connect 无输出
- **端口被旧进程占着**:重复重启假服务器时,旧 python.exe 可能仍 LISTENING 18888(新实例绑定失败但日志显示"监听"误导)。改文件/重启前先 `netstat -ano | grep 18888` 确认 PID 并杀干净,否则连的是僵尸进程
- **请求没发出先查前端**:点登录后假服务器无请求、Frida 也无网络调用,可能是页面 WebSocket 断了导致点击没到后端——重新 navigate 页面再点,别急着改服务器

## Verification

- [ ] 假服务器日志出现目标 fnobj 请求(接管成功)
- [ ] 登录返回 Status:1 且界面进入主界面
- [ ] 心跳/用户信息接口正常,程序不自动退出
- [ ] 重启程序 + 重新挂 hook 后仍可复现

## 支持文件

- `scripts/patch_pubkey.py` — 等长替换二进制内全部 RSA 公钥
- `scripts/fndata_fake_server.py` — fndata 假验证服务器(登录/心跳/公告/用户信息)
- `scripts/fndata_redirect.js` — Frida 连接重定向(目标 IP → 127.0.0.1,含 ConnectEx 分支)
- `scripts/netsniff_connectex.js` — 诊断脚本:打印 ALL connect/WSAConnect/ConnectEx 目标 + WSAIoctl 捕获 ConnectEx 指针(普通 hook 抓不到连接时先用它定位连接方式)
- `scripts/fast_attach.py` — 启动 exe + 轮询找子进程立即注入 hook(Windows 替代 spawn gating 的可靠方案)
- `references/qingyun-38-case.md` — 轻云3.8 完整实战:最终可行链路、514 前置探测坑、归因验证教训、未完成点
