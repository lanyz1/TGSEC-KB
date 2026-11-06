# 反调试壳: dump→IAT重建→attach-patch 全管线 + 易语言 WTWindow 坑

爆金1.6(易语言抢福袋工具,自研壳 .41m/.I9o/.CKa + 反调试 + E2EE HTTP验证)第二阶段实证。
产物目录例: C:\Users\Administrator\Downloads\baojin_analysis\(unpack\*.bin, imports.json, 爆金_unpacked_RAW.exe)

## 1. 反调试壳实证规则(决定动态路线)
- **调试器从进程创建接管(加载式)→ 壳启动期检测 → 直接 Terminated**。x32dbg 加载文件跑到壳 EP 后必被杀。
- **解包完成后再 attach → 安全**(frida attach 运行中的登录界面进程全程正常,壳无周期检测)。
- 推论:要拿 OEP 必须上 ScyllaHide(或 attach-after-unpack 后靠栈/Scylla autosearch);拿不到 OEP 时,**attach 内存 patch 路线完全可行**且不依赖 OEP。

## 2. x64dbg / GUI 自动化实测
- `x32dbg.exe "target.exe" -c "bpm 0x401000, x"` 命令行参数**有效**(状态栏确认 "Memory breakpoint ... set!")。断整段 .text 执行 → 壳解包完跳 OEP 必命中。
- 系统断点→各 DLL 的 TLS 回调逐个断(x32dbg 默认),连按 F9 过;到 EP 后 F9 跑壳 → 反调试 Terminate(见 §1)。
- `headless.exe -p <pid> -c "reg"` attach 模式:刷 `[TODO] Not implemented GUI_PROCESS_EVENTS` 噪音并卡死,不可用。
- computer_use 对 x32dbg(Qt):**background 合成鼠标点击无效**(工具栏/菜单全不吃);`key` PostMessage **F9 有效**(Qt 接受,程序真的跑);菜单热键 alt+f 无效。窗口坐标每次 capture 后可能整体移动,勿用旧坐标。

## 3. 跨位数 EIP 采样(x64 python → x86 进程)
- 64 位进程 GetThreadContext 读 32 位进程上下文**静默失败/全 0**,必须 `Wow64GetThreadContext`。
- WOW64_CONTEXT 关键偏移:**Eip @ 0xB8, Esp @ 0xC4, Ebp @ 0xB4**。0xC0 是 EFlags(典型值 0x202)——用 0xC0 当 Eip 会得到恒 0x202 的假象。
- 用法:OpenThread + SuspendThread + Wow64GetThreadContext(buf 清零, ContextFlags=0x10007 @0) → 采样分类 EIP 落点。
- 拿到 ESP 后可 flat-scan 栈找返回地址链(注意深栈全是 UTF-16 宽字符假阳性,要过滤 0x40-0x7F 高字节)。

## 4. capstone skipdata — 必查的第一怀疑对象
- 2.6MB .text 默认 `Cs.disasm()` 只出 2296 条指令就停 → 误判"分页加密/诱饵"。
- `md.skipdata = True` 后同区段解出 **898,946 条指令**,整个区段连续可解码(偶发无效字节是数据插花)。
- **教训:下"代码不可解码/已加密"结论前,必须先 skipdata 复扫**。skipdata 模式下 insn.id==0 的是伪指令,访问 operands 会抛 CS_ERR_SKIPDATA,要 continue。

## 5. IAT 重建全管线(无 Scylla/pe-sieve 时手工,全程 python)
1. dump 区段:ctypes ReadProcessMemory 按内存区段表(注意 .text raw=0 但内存已解包,直接读 VA 区间)。
2. skipdata 反汇编 .text,收集 `call/jmp dword ptr [disp32]` 的 disp(本例 1794 处 → 1053 唯一槽)。
3. 槽内容 = 进程内真实 API 地址。聚簇:按连续跨度分组(988 槽主簇指向单一模块 = E2EECore.2.7.2.dll)。
4. 建模块导出 LUT:
   - `psapi.EnumProcessModulesEx`(psapi.dll,**kernel32 里没有**)、`psapi.GetModuleBaseNameA`(同,不在 kernel32)
   - 每模块读 PE 头 + 导出目录 → {imagebase+funcRVA: name}
5. 反查 1053 槽 → 1021 resolved;unknown 小簇(槽值指向模块内 .text/.41m)= 程序内部跳转表,**无需修复**(dump 后同基址仍有效)。
6. 重建 PE:保留内存 PE 头 + 只留 .text/.rdata/.data/.rsrc 区段(raw 用 dump 内容重排),删除壳区段(.41m/.I9o/.CKa);IMPORT 目录壳指向自用 3 API 需换;IAT 槽若分散则需 patch 代码引用或静态绑定——分析用途镜像(爆金_unpacked_RAW.exe)EP 占位即可进 IDA。
7. .rdata dump 里 GetProcAddress 动态调用的导出名(如 Create_HP_HttpSyncClient、rapidjson_*、e2ee_*)是**字符串**,暴露真实协议栈:HP_HttpSyncClient_OpenUrl → HTTP(S) 验证;RapidJSON → JSON 载荷。

## 6. 运行样本 patch 可靠原语
- **ctypes 三连**:`VirtualProtectEx(PAGE_EXECUTE_READWRITE)` → `WriteProcessMemory` → 读回验证 → 还原保护。比 frida 稳。
- frida `Memory.protect + writeByteArray` 在**进程刚启动不久**报 access violation(壳未 settle);等窗口出现后数秒(进程稳定)再 attach 则读/写全 OK。时序坑:同一脚本早跑失败、晚跑成功。
- patch 函数头 `B8 01 00 00 00 C3 90 90`(mov eax,1; ret; nop; nop)即"该函数恒成功"。

## 7. 易语言自绘 WTWindow UI — 控件文本是假的
- 登录窗文本框 class='Edit' 但内容在 WTWindow **内部缓冲**:
  - `SetWindowTextW` 只改显示文本,**程序读到仍空**(弹"请输入 账号");WM_SETTEXT / EM_REPLACESEL / WM_CHAR 全被忽略(仅 SetWindowTextW 改显示有效)。
  - keybd_event 真实键盘输入同样不进缓冲(焦点/输入法问题)。
- 结论:对自绘易语言 UI,**别走控件输入驱动**。定位校验回调的替代路:GBK 校验文案(请输入账号/卡号错误)运行时 xref,或 hook CreateWindowExW/信息框 + 栈回溯拿弹窗调用点返回地址 → 向上找"登录按钮被单击"子程序 → patch 本地校验 + 调验证函数。
- 验证函数本身可静态定位:GBK 文案引用(服务器连接失败/数据发送失败)→ 所在函数(本例 0x407C70,成功判定 cmp [ebp-0xc],1 / jne → NOP×6 即恒成功)。

## 8. OEP 定位死胡同(此壳,避免重复踩)
- .CKa→.text 的 jmp/push 候选(52 个)几乎全是**数据噪音**(反汇编把加密数据当指令);"不被 .text 内部调用"入度筛法失败(51/52 CANDIDATE)。
- 易语言字符串**无 imm xref**(间接文本表模型):搜 push imm、lea disp、.data 指针表全 0。
- SEH 入口模式 `55 8B EC 6A FF 68 .. 64 A1 .. 50 64 89 25` 的 18 个候选多为**带参子程序**(读 [ebp+8]),非无参进程入口;OEP 变体不同。
- 深栈扫描:最深 .text 指针全是 UTF-16 宽字符假阳性。
- 正路仍是 ScyllaHide → 内存执行断点 → OEP;或放弃 OEP 走 attach-patch(§6)。

## 9. 自释放 DLL 命名约定(一眼认技术栈)
- `E2EECore.2.7.2.dll` + 导出 `e2ee_httpserverStart/e2ee_httprequestGetHeader/e2ee_moc*` = **易语言 E2EE(HTTP 服务器/客户端框架)**;若程序导入 900+ 个 e2ee_* = 主 API 面。
- `dzHPSocket4C.dll` = HPSocket 易语言封装(HP_HttpSyncClient_*);`RapidJSON.dll` = JSON。
- 这些 DLL 常运行时自释放到 Temp/运行目录;主程序通过 GetProcAddress 动态取用,导出名以明文躺在 .rdata。

## 10. 破解推进顺序教训
先内存 patch 验证函数 → 若 UI 无反应,先查本地校验(自绘缓冲)是否拦在前面 → patch 更上层回调/校验分支。防火墙拦样本出站时,登录流程走"服务器连接失败"分支,**不会**走到深层成功判定——验证绕过时要区分"网络不可达路径"与"真实校验路径",或临时放行看真实响应。
