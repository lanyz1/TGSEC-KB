# 运行时脱壳: 自定义加密壳全脚本 dump + IAT 重建(无 GUI)

来源: 爆金1.6 (易语言 + 自定义 VM/加密壳) 实测。目标形态: x86 PE32,
区段 `.text/.rdata/.data` 文件 raw=0(仅虚拟声明)、壳区段随机名(`.41m/.I9o/.CKa`)、
`.CKa` 高熵载荷(≈7.97)、`.I9o` 壳配置表(偏移表)、反调试花指令、**启动期反调试**
(x32dbg File→Open from-create 会被 Terminate; 解包完成后再 attach 不触发)。

## 阶段 0: 受控运行 + 端点捕获(验证形态未知时)
1. 防火墙隔离: `sc start mpssvc; netsh advfirewall set allprofiles state on` →
   `netsh advfirewall firewall add rule name=blk_xxx dir=out program="<abs exe path>" action=block`
   (block 规则比 disable 干净, 还能喂日志)。
2. 抓验证服务器端点(非 HTTP 自定义协议时 hosts/代理全无用):
   `netsh advfirewall set currentprofile logging filename "<abs>\fw.log"`
   `netsh advfirewall set currentprofile logging droppedconnections enable`
   运行后读 fw.log: `DROP TCP src dst-ip dst-port` 即服务器(实测 120.25.103.95:9901)。
3. 观察 UI: win32gui 枚举顶层窗口标题 + 子控件文本(Button/Edit/_EL_Label 均可 GetWindowText;
   WTWindow 自绘标签读不到文本 → 用窗口级截图 + Windows OCR)。
4. 窗口级截图 OCR(winsdk): `GetWindowRect(hwnd)` → `ImageGrab.grab(bbox)` → 存 png →
   `winsdk.windows.media.ocr.OcrEngine`(语言 zh-Hans)。**路径必须绝对反斜杠**;
   PowerShell 5.1 WinRT 投影(GetAwaiter)不可用; ddddocr 只适合验证码。

## 阶段 1: 解包完成后 dump(免调试器)
1. 让样本自然运行到 UI 出现(登录窗口 = 壳已解包)。
2. ReadProcessMemory 读 PE 头(0x400000 起)解析区段表 → 逐区段 dump 到文件
   (.text/.rdata/.data/.rsrc 必 dump; .CKa/.41m 也 dump 供壳代码分析)。
3. 先读内存 DataDirectory: 壳会把 IMPORT(rva)/IAT 指向壳区(如 0x12cf000=.I9o,
   0x13441d0=.CKa)且只有 3-4 个 API → **内存头的导入目录不可信, 必须代码引用重建**。
4. 区段内容验证: .text 头应为编译器 prologue(`33 c0 c3` / `55 8b ec`), 熵 ~6.25;
   数据区 GBK 字符串原位可扫。

## 阶段 2: IAT 槽定位(capstone skipdata — 关键!)
- **坑**: capstone 默认线性反汇编在首个无效字节即停 — 2.6MB 的 .text 只解出 2296 条,
  曾误判「分页加密/诱饵」。**`md.skipdata=True` 后全量解码 898,946 条** → 说明区段完整。
- 收集所有 `call/jmp dword ptr [disp32]`(X86_GRP_CALL/JMP + op == X86_OP_MEM)的 disp,
  去重 = IAT 槽候选。可能另有 `mov reg, [disp32]` 引函数指针(本目标未见, 遇则加)。
- 聚类(连续阈值 ~0x40): 主簇常巨大(988 槽同模块 = 一个运行时 DLL 的全部导入);
  小簇 = 各系统 DLL; 指向模块自身 .text 的簇 = 内部跳转表(不需要导入修复,
  槽值保留即可, 前提 dump 仍加载到同一 imagebase)。
- 槽内容验证: 应为代码指针(落在某已加载模块范围内)。

## 阶段 3: 导出 LUT + 槽解析(64 位 python 读 32 位进程)
- `psapi.EnumProcessModulesEx(h, mods, need, LIST_MODULES_ALL=3)` +
  `psapi.GetModuleBaseNameA` — **都在 psapi.dll**(kernel32 只有 K32* 前缀别名,
  直接用 kernel32.EnumProcessModulesEx 会 AttributeError)。
- 每模块读 PE 导出目录建 {base+funcRVA: name}; 126 模块解析 < 1s。
- 槽值 → LUT 反查 → imports.json(按模块分组)。本目标: E2EECore.2.7.2.dll 988 +
  USER32 17 + KERNEL32 9 + GDI32 4 + OLEAUT32 2 + WS2_32 1; 32 个 unknown 全是内部跳转表。

## 阶段 4: OEP 定位(免调试, 不碰反调试)
- 方法 A(栈扫): 主线程 ESP(Wow64GetThreadContext) 起向栈底(高地址)扫 4B 对齐,
  收集落在模块 .text 范围的返回地址; 最深处/最早压入者 ≈ 入口链根部(OEP→…→消息循环)。
  注意活跃帧在栈顶, 启动链的残帧在栈底方向。
- 方法 B(壳区跳转): skipdata 反汇编 dump 的壳区(.CKa), 找 `jmp 0x40xxxx` /
  `push 0x40xxxx` 候选(本目标 52 个, 需人工结合上下文筛, 不如 A 直接)。
- 线程上下文读取(32 位进程): 必须 `Wow64GetThreadContext`(64 位 GetThreadContext 恒失败)。
  **WOW64_CONTEXT 偏移: Eip@0xB8, Esp@0xC4, Ebp@0xB4, EFlags@0xC0, SegCs@0xBC,
  SegGs@0x8C**。ContextFlags=0x10007。用 0xC0 读 Eip 会恒得 0x202(=EFlags)——踩过。

## 阶段 5: 重建 PE(进行中思路)
1. 头部保留, 区段表改 4 区段(.text/.rdata/.data/.rsrc), raw 数据 = dump 内容,
   raw_off 顺序重排, raw_size=实际 dump 大小(vsize 不足部分补 0)。
2. AddressOfEntryPoint = OEP RVA。
3. 导入: 新建 .idata 区段(文件尾部)写 导入描述符 + INT(名导入) + DLL 名 + Hint/Name,
   新 IAT 连续数组; **代码中所有引用旧槽的 disp 要 patch 到新 IAT**(脚本遍历 capstone
   结果逐个改写 4 字节 disp; 数据区出现旧槽绝对地址值也需替换, 用唯一值降低误伤)。
4. 壳自释放 DLL(E2EECore.2.7.2.dll→%TEMP%、RapidJSON/dzHPSocket4C→运行目录)由主程序
   再次释放 → 无需随包; 验证时保留原运行目录。

## 运行时自释放组件识别(易语言)
- 运行目录会出现新文件: RapidJSON.dll / dzHPSocket4C.dll(HPSocket 封装) /
  E2EECore.2.7.2.dll(导出 `e2ee_*` 988 个: httpserver/request/response = E2EE 网络框架)。
- 网络技术栈 = HPSocket(TCP) + JSON 序列化 + E2EE 上层 → 自定义端口私有协议。
- guard.ini `[guard]\r\nexit=0` = 上次退出状态标志(守护自检)。
- 卡密 UI 三窗: 登录(账号/密码/记住密码/注册账号/账号充值)、注册(账号/密码/**卡密**/**超级密码**,
  用户名=小写英文数字 ≥5)、充值续费(**充值账号**+**卡密**) = 发卡网卖卡、注册耗卡、到期充卡。

## 验证壳强度的小技巧
- frida attach 运行中进程不触发反调试 → 用 frida 做内存侦察(区段 exec 范围/熵/GBK 命中页)。
- x32dbg `-c "bpm 0x401000, x"` 能在启动时设内存执行断点(免 GUI); 但 from-create 调试本身
  触发启动期反调试 → 该路只用于「确认壳检测调试器」, 真脱壳走 dump 路线。
- 易语言程序若网络验证 + 壳, 明文字符串零 URL 是常态(全加密/动态拼), 别浪费时间静态找域名。
