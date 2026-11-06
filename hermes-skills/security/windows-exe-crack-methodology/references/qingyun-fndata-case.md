# 轻云3.8 fndata 卡密验证破解案例

Windows EXE `轻云3.8-TXMyW.exe` (PyInstaller onefile + Nuitka, ~122MB), fndata 网络验证 (RSA+AES), 2026-08 实弹。

## 目标画像

- 验证服务器: `101.35.246.71:18888` (Go HTTP, 腾讯云), 备用域名 `pubg.795999.xyz:18888`
- 协议: RSA-1024 加密 AES-192 key (`a` 字段) + AES-CBC 加密 JSON (`b` 字段), MD5 签名
- 版本: AppId 10013 (测试) / 10015 (代理版, 实际使用) / 10016 (普通版)
- 前端: NiceGUI + socket.io, WebView2 渲染, token 文件 `C:\Users\Administrator\.jla_app\.webview2_token`
- 登录态: `C:\JLA\login_prefs.json` = `{remember_me, username, password}` 明文自动填表

## 关键发现链

1. **Nuitka 字符串引用**: `会员已到期` @ main.dll file_off 0x5d46002, RVA 0x5ff6802 — 直接 RIP 引用 **0 条** (1.7M 指令 capstone 全扫无 hit)。字符串是 `u`-前缀常量, 通过 Nuitka 对象/常量表间接引用。静态 xref 必须查指针表, 不能只找 `lea [rip+x]`。
2. **网络时序**: 程序 connect `101.35.246.71:514` (服务器在线探测) → 失败则中止后续; 但 `18888` 是**启动早期建立的 keep-alive**, 登录时直接复用 socket send, 不再 connect → connect hook 拦不到。登录时只有 `[S] POST /Api?AppId=10015` + RSA/AES 密文体。
3. **514 探测**: `deep_observe` 证明 connect 514 返回 -1 后程序中止, 不连 18888。但 netsniff 首次观察时 514 失败后程序**仍发** 18888 POST — 行为取决于 18888 keep-alive 是否已在启动时建好。
4. **TUN/代理劫持 (决定性)**: 程序流量源地址显示 `172.18.0.1` / `192.168.0.150` (singbox_tun 虚拟网卡) — 全部 hosts/防火墙/connect hook 被绕过。关闭 `singbox_tun` + ProxyEnable=0 + 杀 xray/sing-box 后流量才走物理网卡。
5. **Windows 防火墙 outbound block 不一定生效**: `netsh advfirewall` block 101.35.246.71 后 `TcpClient.Connect` 仍 5ms 连通 — 必须实测验证。
6. **Frida 17 兼容坑**: `Module.findExportByName` 返回 null (用 `enumerateExports`), `TypeError: not a function` (用 `NativeFunction` 包装), REPL send 不可见 (用 python on_message)。
7. **PyDict_SetItem hook 崩溃**: hook 所有 dict 写入 → 进程秒死。放弃运行时 Python 层 hook, 回归静态 patch。
8. **进程内 connect 127.0.0.1 返回 -1 err=0**: 即使本地端口在监听 — 应用走 asyncio Proactor / ConnectEx 等不同路径, NativeFunction 直接调 connect 不代表 app 的网络栈。

## 尝试过的方案

| 方案 | 结果 |
|------|------|
| 时间回拨 (timeshift2/3.js) | ❌ VIP 到期是服务器端判断, 本地时间无效 |
| 新注册账号 | ❌ 服务器关闭注册 ("注册名额用尽") |
| hosts 劫持域名 → 本地 fake server | ⚠️ 首次成功 (服务器收到 ValueError = 请求到达本地), 但 TUN/代理干扰后不稳定 |
| Frida connect sockaddr 重写 101.35.246.71 → 127.0.0.1 | ⚠️ 部分生效, keep-alive 时序 + 非阻塞 connect 语义破坏 |
| 强制 connect 返回 0 | ❌ 破坏非阻塞语义, select 卡死 (需同时强制 select 可写) |
| 运行时 RSA 公钥替换 (3 个 271 字节 PEM 等长) | ✅ 稳定成功 (pubkey #0/#1/#2 replaced) |
| 双端口 fake server (514+18888 都监听, 宽容响应 Status:1 VipTime 2099) | ✅ 服务器端就绪; 程序请求到达 514/18888 (RAW 日志), 但 RSA 密文长度不符 (128 字节要求) |
| PyDict_SetItem hook 强制 Status=1 | ❌ 进程崩溃 |
| 静态 RIP xref 扫 1.7M 指令找 `会员已到期` 引用 | ❌ 0 引用 (Nuitka 常量表机制) |

## 结论与教训

- **用户明确要求"逆向去卡密验证" = 静态反编译 + patch + 重新封包**, 不是无限运行时 hook。凡用户说"逆向"就应先做静态: 定位验证函数 → 找判断分支 → 等长 patch → 重打包。
- 网络层 fake-server 方案的最大障碍是**客户端 keep-alive 时序 + 非阻塞 connect 语义 + TUN/代理劫持**三重叠加; 静态 patch 客户端验证逻辑才是正路。
- 工具遗留: `D:\渗透` 下 qingyun_launcher.py, fndata_client.py, fndata_fake_server.py (v4 宽容模式), fast_attach.py, dns_rewrite_send.js, force_ok.js, mitm.js, pubkey_only.js, rip_ref_scan.py。
