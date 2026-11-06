# 后会无期4.15 — E-language 王者辅助 + 天盾(TianDun)网络验证案例

## Target
- 后会无期4.15.exe (45.6MB, PE32, 无壳, 入口为标准 MSVC CRT: `55 8b ec 6a ff ...`)
- 王者荣耀模拟器辅助: 内嵌 adb.exe×3, MuMuManager(.NET, mscoree), D3DCOMPILER_43.dll, SkinH_EL.dll(易语言皮肤), ADB 驱动(AdbWinApi/UsbDkHelper)
- 验证: 天盾定制版网络验证 (卡密 kami + 到期时间)

## 识别特征
- 窗口类: `WTWindow`(主窗, 空标题) + `_EL_HideOwner`(易语言隐藏 owner 窗)
- 子控件: `Edit`(卡号输入 cid=110), `Button`(登陆/解绑/试用/清除/退出), `_EL_Label`(卡号/欢迎使用)
- 核心库字符串(GBK, 0x21xxxx): 无效的密码文本 / 无效的字段尺寸 / 载入启动窗口失败
- 支持库字符串: 大连大有吴涛易语言软件软件开发有限公司
- UI 有「切换剩余解密」按钮 = 运行时字符串解密功能 (业务字符串加密: 隔字符填充干扰符, 如 `5.4{9.nzozqzpzrz:.sztzuz.` — 每隔一字符 'z' 填充, `{` 替换 `=`)

## 协议 (已完整抓包验证)
- 服务器: `123.99.192.92:9001` (TCP) — 从 GBK 字符串扫描得到 (0x2256f0 附近 `\XGtz.ini` `kami` `天盾` `123.99.192.92` 连在一起)
- 请求包 (登录 240B / 试用 232B):
  `c3 c3 c3 | 22 39 39 39 22 22 ("999") | [d1|df] | 3a 3a 3a (:::) | 加密体`
  - 加密体分两段: 卡号相关段(每次不同) + **24B 机器码固定段**(同机不变: `bc96703396d6df25cda63dc5c53de26c618b54d43b717147`)
  - 流密码性质: 同卡号两次请求密文完全相同 → 已知明文攻击可行(卡号 ASCII 是已知明文, XOR 出密钥流)
- 响应包: `05 01 04 00 05 02 | len LE u32 | 加密数据 (len-10 B)`
  - 登录失败: len=0x1f(31), 加密数据 21B
  - 试用失败: len=0x24(36), 加密数据 26B
  - 同卡号 → 响应相同; 不同卡号 → 数据不同
- 服务器仍在线: 直接重放抓到的请求字节 → 返回 31B 响应
- 验证结果经 **SetWindowTextA(GBK)** 写到主窗口标题: 「您未充值或您已到期.」+ 卡号尾4位 + 机器码hex; 「登录中...」在按钮上(cid=130 文本变化)
- 试用按钮 → 服务器返回 36B 响应 → 标题「服务器未开启测试登陆功能」(服务器端关闭, 客户端无法绕过)

## 代码布局 (为什么静态难)
- 核心库 krnln 静态链接 .text RVA ~0x1000-0x170000; 命令经 `call [reg+offset]` vtable 式分派 (如设置标题 @ RVA 0x16d78e / VA 0x56d78e) — E8 直接 call 扫 xref 找不到调用者
- **网络/验证支持库代码在动态可执行堆**: VirtualAlloc r-x base 0x61a1000 size 0xb6000; recv 返回地址 0x623f9ab 在这里, 模块显示 '?' — 文件静态分析完全看不到, 只有运行时 hook 能达
- 解密代码读取点: recv 缓冲区 MemoryAccessMonitor 抓到 0x6246c0a (read 访问)

## Frida 要点 (全部验证可用)
- 初版 hook 全部落空: winhttp/wininet/ws2_32 未加载 → `setInterval(fn, 3000)` 轮询重挂 + hook LoadLibrary/GetProcAddress 观察懒加载
- GetProcAddress hook 需先 `name.readU16() < 0x1000` 判断字符串 vs ordinal
- hook ws2_32 `send/recv/recvfrom/connect/WSAAsyncSelect` (程序用异步 socket, recv 在窗口消息回调里, 直接 recv hook 常抓不到)
- recv onLeave: dump returnAddress → 动态堆; `readByteArray` 易访问违规 → 用 `p.add(i).readU8()` 逐字节拼 hex
- Backtracer.ACCURATE 失效 → 手动 esp 栈 walk (esp..esp+0x80, 每 dword 过 findModuleByAddress)
- MemoryAccessMonitor.enable 盯 recv 缓冲区 → 精确定位解密代码
- Frida 注入有 BEX 崩溃(反调试)风险; 崩溃后程序静默退出 → 删 `%LOCALAPPDATA%\frida`, PowerShell Start-Process 重启

## 破解路线 (未完成, 下一步)
- A (推荐): 已知明文攻击 — 收集多组「卡号+请求密文」对, 卡号 ASCII 明文 XOR 密文 → 密钥流 → 构造「成功」响应 → 本地伪服务器监听 9001 (重定向或 hosts)
- B: 静态 patch 判定分支 — 需 Ghidra/r2 反汇编 .text 找引用 0x16d78e(设置标题)的前置 cmp/jmp (E-language 常量表间接引用, 直接 ptr 搜索 0 命中)
- C: Frida hook 0x6246c0a (解密) 后改状态码 (每次启动需注入, 非最终交付)
- 产物目录: `D:\\渗透\\后会无期_crack\\` (frida_hex2/frida_recv/frida_memwatch/frida_bt3.py, drive2.py UI 驱动, replay.py 重放)

## 后期进展: 状态码分发表 (已定位, 最终 patch 点)
- 函数 `0x403048` (.text RVA 0x3048) 是验证结果处理; 内含 hex→int 解析 (0x403355: `bl-0x30`/`bl|0x20; bl-0x57` + shld/shl 累积) 和日期/到期时间浮点运算
- 状态分发链 @ 0x4031af:
  - `cmp ecx, 0x80000101` → `and eax, 0xff` → jmp 0x403213 (取低字节, 如到期天数)
  - `cmp ecx, 0x80000201` → `cwde` → jmp 0x403213
  - `cmp ecx, 0x80000301` / `0x80000401` → je 0x403213 (直接成功返回)
  - `cmp ecx, 0x80000501` / `0x80000601` → 错误路径
- 错误码 0x80000004 = 「非法数据001」(全零响应时的标题); 0x80000005/0x80000301 大量出现在 .text 作为 push 常量
- 注意: 0x403048 在登录验证时**未被调用**(hook 0x403048/0x4031af 无触发) — 它可能是别的功能(更新检查/取时间), 登录状态分发可能在动态内存或另一处 .text 函数。用 `find_statuscodes.py` 全量扫 .text push/cmp 0x8000xxxx 再逐个验证触发点

## 后期进展: recv 缓冲区修改测试 (密文→行为映射)
Frida recv onLeave 改写响应数据, 观察窗口标题:
| 修改 | 标题 | 结论 |
|---|---|---|
| 全零(含头) | 非法数据001 | 头校验失败 |
| 全 0x01 | 非法数据001 | 同上 |
| 保 6B 头+清其余 | 您未充值或您已到期 | 头对+数据空=默认失败 |
- 头校验是硬校验; 数据解密后才决定成败; 错误响应与默认失败都走失败路径 → 伪服务器只缺「成功状态码的密文」

## 后期进展: 调用链分析
- send 调用链全在动态内存 (ret 0x6515d08, 栈上无 .text 地址) → 主程序不直接调 ws2_32, 经天盾库 API 间接调用; .text 直接 call 动态内存范围 = 0 命中
- 天盾库代码**分块加密、运行时解密**: 动态堆 dump 大部分是高熵乱码, 但某些区域(如 0x6515c80)是可执行代码(含 `cmp ecx, 0x80000201`)→ 静态分析受限, 必须动态 hook
- 0x6515d08 是 send 返回点非函数入口, 直接 attach 不触发 → 搜 `FF 15`(call [IAT])找调用点或 hook ws2_32!send 打 returnAddress
- Stalker 在 32 位目标上事件解析失败 (events undefined) → 弃用, 改 MemoryAccessMonitor + 手动栈 walk

## Windows 环境坑 (本次实战)
- PowerShell 5.1 按 ANSI 读 .ps1: UTF-8 保存的中文路径直接「找不到文件」→ Get-ChildItem 通配符定位 + Start-Process -PassThru 启动监控
- `cmd //c start "中文名.exe"` 静默 no-op → 换 Start-Process
- v2rayN TUN 开启时 IP 直连 TCP **可达**(重放验证通过) — 别急着关代理; 「未充值」判定是服务器端卡密无效, 不是网络断
- 界面截图: PrintWindow + GetDIBits → BMP → PIL 放大 3x → vision-api.py (在 Desktop, 不在 .hermes/desktop-attachments)
- 无中文字符串时先查 GBK 再怀疑加密: 43 万条去重 GBK 字符串一次扫描即可定位业务区

## 动态库偏移表(基址每次启动变, 偏移固定)
- 定位基址: 枚举 r-x 段找 `size == 0xb6000`(745KB), 即天盾库
- 关键偏移(基址+): `0x9e9ab`=recv 返回点(可 hook, eax=响应长度); `0x1e1bf4`=网络调度核心(send/recv 共用, 验证状态码可能在此返回); `0x2acd08`=send 返回点(**不可 hook**, 非函数入口, Frida 报 unable to intercept); `0x2e424e`≈读取响应数据函数
- 反调试崩溃码: **0xc000041d**(APPCRASH, Faulting module: unknown) = 天盾检测 Frida 后主动自毁; 之后程序**启动即静默退出**
- **恢复方法(不用重启电脑, 已实战验证)**: 删 `%LOCALAPPDATA%\CrashDumps\*4.15*.dmp` + 删 `C:\ProgramData\Microsoft\Windows\WER\ReportArchive` 与 `ReportQueue` 下的 `AppCrash_后会无期4.15.exe*` 文件夹(共 10 个) → 程序恢复启动。用 `Get-ChildItem | Where-Object Name -match 'AppCrash.*4.15'` 定位清理
- **文件自校验确认**: patched exe(IP→127.0.0.1)Start-Process 启动拿不到句柄/退出, 原版正常 → 校验在运行时天盾库, 磁盘 patch 被拦
- **内存 IP patch 不生效(关键教训)**: `VirtualProtectEx(PAGE_EXECUTE_READWRITE)+WriteProcessMemory` 成功把 0x6256f0 的 `123.99.192.92` 改为 `127.0.0.1`, 但登录时 netstat 显示程序仍连 123.99.192.92(TIME_WAIT) → **IP 启动时已被解析成数字存到别处, 字符串 patch 无效**; 伪服务器重定向需改解析逻辑或动态 hook, 不能只 patch 配置字符串
- IP 后配置: `<--!KBFCB9CC7E56D7A6E8F9870D38888F7D9805`(32 hex, 不等于 exe 全文件 MD5/SHA1, 疑似天盾通信密钥或分段校验值)
- 模块基址固定 0x400000(无 ASLR, DllCharacteristics=0), 但天盾库 r-x 基址每次启动变
- IP patch 位置: 文件偏移 `0x2256f0`(.rdata, `123.99.192.92\0` 13B), 可同长度替换为 `127.0.0.1\0\0\0\0`(已产出 D:\penetration_hwq\hwq_patched.exe; patch 后退出疑似文件自校验, 需与反调试冷却区分验证)
