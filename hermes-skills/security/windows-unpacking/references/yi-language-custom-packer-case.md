# 案例: 爆金1.6.zip — 易语言卡密+账号双验证软件脱壳侦察

2026-09 实战记录。样本: 爆金.exe(易语言主程序,自定义壳)+ RSCProject.dll(易语言支持库,加壳)+ lc_guard.exe(进程守护,无壳)。

## 三文件定性(VERSION 资源 + 导入/导出表,全部静态可拿)

| 文件 | 身份来源 | 保护 |
|---|---|---|
| 爆金.exe | VERSION: FileDescription=易语言程序 / LegalCopyright 作者版权所有…; manifest name=E.App + (http://www.eyuyan.com) | 自定义壳(.41m/.I9o/.CKa) |
| RSCProject.dll | VERSION: "C++程序开发库(curl,v8引擎,json,线程池…)"; 导出 Api_V8New/Run/Import + Api_StorageGet/Set | 加壳(空区段名,全高熵) |
| lc_guard.exe | VERSION: ProductName=进程守护 | 无壳 |

易语言静态编译程序特征: PE32 x86, 链接 KRRN 静态库(GBK 错误文本 "无效的密码文本/运行时出错!" 可见), manifest E.App。

## 壳解剖(爆金.exe)

文件态区段表:
- .text/.rdata/.data raw=0(fake), .41m vsize 0xd7f71e raw=0, .I9o vsize 0x98 raw=0x1000(壳配置表), .CKa vsize 0x1537567 raw=0x1538000(加密主体,熵7.97), .rsrc 正常(资源未加密!)
- EP RVA 0x1414d8d = 落在 .CKa 内; 无 Rich header

运行态内存(壳解包完成后, frida/ctypes 验证):
- .text 在声明的 RVA 原位可执行(头部 33 c0 c3 90 55 8b ec = 标准编译器 prologue), .rdata/.data 原位含 GBK 业务字符串
- IMPORT DataDirectory → .CKa 解密区(0x13441d0), 描述符 FirstThunk 全部指向 .I9o(0x12cf000,+8 递增, 仅 3 个 API = 壳自用最小 IAT)
- 结论: 壳解包后原始镜像"看起来原位完整", 但 .text 线性反汇编 ~2296 条后中断、非零 87% 不可解码 → 判分页加密/执行后重加密, 静态 dump 不可直接收工(下一招 = EIP 采样或 hook 解密函数)

## 受控运行三连(实测命令)

1. 网络隔离 + 出站阻止:
```
sc start mpssvc; netsh advfirewall set allprofiles state on
netsh advfirewall firewall add rule name="blk_x" dir=out program="<abs exe>" action=block
```
2. 窗口控件枚举(pywin32)替代 OCR:
- 类名: WTWindow=自绘顶层窗(标题可读); Afx:400000:b:10003:900015:0=易语言自绘标签(GetWindowText 空, 布局靠截屏); _EL_Label=有文本标签; Button/Edit=标准控件, 直接读出登录/注册/充值全部字段
- 抓到的验证 UI 流转: 主窗「爆金 - 1.6」→「信息:」MessageBox →「爆金 - 注册」→「爆金 - 充值续费」
- 注册窗 4 Edit: 账号/密码/卡密/超级密码; 充值窗 2 Edit: 充值账号/卡密 → 卡密+账号双验证(发卡网卖卡密商业模式)
- 校验文案: "用户名必须为小写英文+数字组成,长度不得少于5个字符"
3. 防火墙丢弃日志抓服务器:
```
netsh advfirewall set currentprofile logging filename C:\...\fw.log
netsh advfirewall set currentprofile logging droppedconnections enable
```
样本登录被 block 后日志行:
`2026-09-09 06:21:48 DROP TCP 192.168.1.29 120.25.103.95 51116 9901 0 - ... pid 23836`
→ 验证服务器 120.25.103.95(阿里云):9901 私有端口。

4. 运行目录观察自释放组件(时间戳新出现文件):
- RapidJSON.dll(JSON)、dzHPSocket4C.dll(HPSocket 易语言封装)、guard.ini `[guard] exit=0`
- 协议栈推断: custom TCP(HPSocket)+ JSON(RapidJSON),非 HTTP —— 对应 9901 非标准端口

## 工具链实测要点

- frida 17.15: 32位进程 attach 正常(x64 python), `Module.findExportByName`→`TypeError: not a function`; 正解 `Process.getModuleByName('kernel32.dll').getExportByName('WinExec')`。`Module.getGlobalExportByName('kernel32.dll')` 报 unable to find global export 'kernel32.dll'(参数语义不同)。spawn gating 卡死 → Popen 启动后 attach。
- x32dbg GUI 自动化坑: computer_use background 合成点击工具栏常无效;窗口会整体移动导致旧坐标失效;每次 action 后重新 capture 取最新 bounds。
- 本机工具位置: D:\penetration_hwq\x64dbg_latest\release\x32\x32dbg.exe + Scylla.dll; scylla.zip/pe-sieve 下载产物是 "Not Found" 9字节(被墙)。
- zip 中文文件名乱码修复: 文件名.encode('cp437').decode('gbk')。
- OCR 链: winsdk Windows.Media.Ocr(中文语言包已装)→ StorageFile.get_file_from_path_async 必须反斜杠绝对路径; PowerShell 5.1 直接 WinRT 报 GetAwaiter 不存在; ddddocr 对 UI 截屏基本空输出, 只适合验证码。

## 代码配方

GBK 业务字符串扫描(易语言): 直接对文件 bytes 用 gbk 解码区段找关键词(卡密/到期/机器码/账号), 命中在加密流里 = 巧合(上下文乱码), 命中在明文数据区 = 真信号。lc_guard.exe 只命中 KRRN 运行时文本 → 无自定义业务文案。

内存 dump(ctypes ReadProcessMemory): OpenProcess(PROCESS_VM_READ|PROCESS_QUERY_INFORMATION) → 读 PE 头区段表 → 按 (ImageBase+VirtualAddress, VirtualSize) 逐段 ReadProcessMemory → 存 .text/.rdata/.data/.rsrc(.CKa/.41m 可留作壳引擎取证)。

EIP 采样(诊断分页加密, 本案例设计但未跑完):
- Toolhelp32 Snapshot 枚举线程 → OpenThread(THREAD_ALL_ACCESS) → SuspendThread → GetThreadContext(CONTEXT 结构 x86 布局: ContextFlags+Dr0-7+FloatSave 112B+Seg 4B×4+EDI..EIP..SS, Eip 偏移 0xB8)
- 300 次采样按 EIP 落点分类(fake.text/.CKa/system-dll)统计; 若大量 EIP 在 .text 且 dump 不可解码 = paged-code 实证。
