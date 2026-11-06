### 23.1 恶意软件分析方法论

恶意软件分析是逆向工程的重要分支,目标是提取 IoC、还原行为逻辑、生成检测规则。方法论上分为三类:
- **静态分析**:不执行样本,分析 PE 结构(节区、导入表、资源)、字符串提取(URL、API、互斥体名)、YARA 规则匹配、熵值计算判断是否加壳、反汇编关键函数。优点安全快速,缺点被加壳/混淆样本难以穿透。
- **动态分析**:在隔离沙箱中执行样本,监控 API 调用、文件/注册表/网络行为。优点能穿透简单混淆,缺点触发率有限(样本可能有反沙箱逻辑)。
- **混合分析**:符号执行 + 动态执行,用符号执行探索路径约束,动态执行覆盖具体行为,如 Driller、QSYM。适合分析有复杂条件分支的恶意逻辑。

**分析流程**:样本优先级排序(基于来源、文件类型、沙箱初筛结果)→ 静态特征提取(PE 信息、字符串、YARA)→ 动态行为监控(沙箱 + API hook)→ 行为报告(文件/注册表/网络/进程操作时间线)→ 检测规则产出(YARA/Sigma/Snort)。

### 23.2 沙箱环境搭建

Cuckoo Sandbox 是最经典的开源恶意软件分析沙箱,基于虚拟机 + agent 模式。

```bash
# Cuckoo安装与配置
pip install cuckoo
cuckoo init
# 配置virtualbox隔离网络
# 配置分析agent (Windows VM中的agent.py)

# 提交样本分析
cuckoo submit sample.exe
# 提交URL分析
cuckoo submit --url http://malicious.com
```

Cuckoo 的工作流:主机调度 → 启动干净 VM 快照 → VM 内 agent.py 接收样本并执行 → 行为监控(基于 API hook 注入分析 DLL)→ 网络流量通过 inetsim/fakenet 转发 → 分析完成回滚快照 → 生成 JSON 行为报告与 PCAP。Cuckoo 已基本停更,2026 年主流替代方案:

- **DRAKVUF**:基于 Xen 的硬件级沙箱,无需 VM 内 agent,通过 Xen altp2m 内存事件实现无侵入式 API 监控,隐蔽性极高,可检测反 agent 类恶意软件。
- **Joe Sandbox**:商业沙箱,云端分析,支持多平台(Windows/Linux/macOS/Android),报告详尽。
- **Any.run**:交互式云沙箱,支持分析师手动操作样本(点击、输入),大幅提高触发率,适合分析需要用户交互的恶意软件。

### 23.3 API监控与行为分析

动态分析的核心是 API 监控,通过 hook 关键 API 还原恶意行为。常用工具:**API Monitor**(Windows GUI 工具,实时监控 API 调用与参数)、**Process Monitor**(文件/注册表/进程/网络活动监控)、**Wireshark + FakeNet**(网络流量捕获与模拟 DNS/HTTP 响应)。

关键 API 监控列表:

| API类别 | 关键API | 恶意行为 |
|---------|---------|----------|
| 进程注入 | CreateRemoteThread, NtMapViewOfSection, QueueUserAPC | 进程空洞化、APC 注入、反射式 DLL 注入 |
| 文件操作 | CreateFile, WriteFile, MoveFile | 勒索软件批量加密、文件释放 |
| 注册表 | RegSetValue, RegCreateKey | 持久化(Run 键)、配置存储 |
| 网络 | WSAStartup, connect, InternetOpen, WinHttpSendRequest | C2 通信、数据回传 |
| 加密 | CryptEncrypt, BCryptEncrypt, CryptGenKey | 勒索加密、C2 流量加密 |
| 内存 | VirtualAllocEx, WriteProcessMemory, CreateRemoteThread | 跨进程代码注入 |
| 服务 | CreateService, StartService | 服务持久化、提权 |
| 计划任务 | NetScheduleJobAdd, ITaskService | 计划任务持久化 |

监控时应同时记录调用栈,便于关联 API 调用到具体代码模块。

### 23.4 沙箱对抗技术与绕过

恶意软件广泛使用沙箱检测以规避自动分析。常见检测手段:
- **硬件指纹**:CPU 核心数 < 4、内存 < 4GB、硬盘 < 60GB 视为虚拟机;检查 `CPUID` 的 hypervisor bit;检查 BIOS 字符串中的 `VMware`/`VirtualBox`/`QEMU`。
- **用户交互检测**:启动后等待鼠标移动、剪贴板变化、窗口焦点切换,长时间无交互则判定为沙箱。
- **时间延迟**:`Sleep(大数值)`(如 600 秒)等待沙箱超时退出;`GetTickCount` 反 timing 检测;`rdtsc` 测量指令间隔判断是否被插桩。
- **进程检测**:遍历进程查找 `vmtoolsd.exe`、`vboxservice.exe`、`xenservice.exe`、`cuckoo.exe`、`python.exe`(Cuckoo agent)。
- **MAC 地址**:`08:00:27`(VirtualBox OUI)、`00:05:69`/`00:0C:29`/`00:50:56`(VMware OUI)、`00:15:5D`(Hyper-V)。
- **时间戳**:检查 PE 编译时间与当前运行时间差值,异常大可能为沙箱重置环境。

绕过技术(分析侧):
- 修改沙箱配置使其更真实:增加 CPU 核心、安装常用软件(Office、浏览器)、注入真实用户活动模拟(鼠标抖动脚本)。
- Hook `Sleep` 函数加速执行(Cuckoo 的 `sleep_skipper` 模块),将 `Sleep(N)` 直接返回。
- 使用 DRAKVUF(无 agent)避免进程检测,因 Xen 事件监控不注入任何分析模块。
- NVIDIA GPU 指纹模拟(2026):某些高级样本检测 GPU 型号,沙箱需模拟真实 GPU EDID。

### 23.5 YARA规则编写

YARA 是恶意软件特征匹配的事实标准,规则由 meta、strings、condition 三段构成。

```yara
rule Ransomware_2026_Generic {
    meta:
        description = "Generic 2026 ransomware detection"
        author = "analyst"
        date = "2026-07"
    
    strings:
        // 加密相关API
        $api1 = "BCryptEncrypt" ascii
        $api2 = "CryptGenKey" ascii
        // 持久化注册表键
        $reg1 = "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Run" ascii
        // C2通信特征
        $c2 = { 63 6f 6e 6e 65 63 74 00 ?? ?? ?? ?? 68 74 74 70 }
        // 勒索信特征
        $note = "YOUR FILES ARE ENCRYPTED" nocase
        
    condition:
        // PE文件且匹配多个特征
        uint16(0) == 0x5A4D and
        ($api1 or $api2) and
        $reg1 and
        ($c2 or $note) and
        filesize < 5MB
}

// 2026: AI生成YARA规则
// 使用LLM从恶意软件分析报告中自动提取IoC并生成YARA规则
// 工具: YaraForge, Loki (YARA-based IOC scanner)
```

YARA 规则编写要点:strings 段善用 `ascii`、`wide`(UTF-16,Windows 常用)、`nocase`、`xor`(变异字符串)、hex 与 regex;condition 段合理组合,避免过松(误报)或过紧(漏报),推荐用 `and` 串联多类特征(文件类型 + 行为特征 + 字符串)。`filesize` 限制可加速扫描并排除大文件误报。

2026 年趋势:LLM 辅助 YARA 生成。YaraForge 从 ThreatFox、MalwareBazaar 等威胁情报源自动提取 IoC 生成规则;Loki 基于 YARA 的 IOC 扫描器集成社区规则库;部分团队用 GPT-4/Claude 阅读分析报告自动产出候选 YARA 规则,人工审校后入库。



---
📖 本切片 1/2 结束。 续篇: `skill_view(name="reverse-engineering", file_path="references/chapter-23-api-yara-02.md")`