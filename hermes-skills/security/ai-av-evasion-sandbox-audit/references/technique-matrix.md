# 技术矩阵(值得学的部分)

来源:`scripts/loader.c`(7442 行)函数族 + 各 bypass 模块。**这些是设计思路而非可运行代码**——照抄前先修编译。

## 1 执行与隐藏
| 技术 | 函数 | 要点 |
|---|---|---|
| BYOUD 空隙 ghosting | `byoud_gap_scan_module` / `byoud_gap_ghost` | 扫已签名 DLL 代码空隙写 shellcode;需读 `.pdata` 异常表避开已覆盖 RVA(该函数字段名写错了,修好才能用) |
| VEH + gadget 间接 syscall | `veh_syscall_init/invoke/handler` | 设 VEH 在硬件断点处改 RIP 到 syscall gadget;绕过用户态 hook。**返回地址覆盖写法有 bug** |
| Heaven's Gate | `heaven_gate_*` | 32→64 WoW64 远跳扇区切换;本包整段被注释 — 思路可用 |
| 线程池回调执行 | `threadpool_exec_*` | 不用 `CreateThread` 的落地方式 |
| Module stomping | `module_stomp_*` | 盖已签名模块空区,磁盘与内存不一致 |
| 分阶段执行 | `staged_execution_init/run` | 按阶段解密/释放 |
| HWBP 链 | `hwbp_chain_init/advance` + `hwbp_stage_N` | 硬件断点串接多阶段(代码里重复定义了,修去重) |
| Nanomites | `nanomites_spawn_debugger_child` / `nanomites_child_debugger_loop` | 父进程当调试器,断点触发才填真指令 |

## 2 对抗与自适应
- **虚拟化/隔离探测**:`hvci_detect` / `vbs_enclave_detect` + `hvci_adaptive_bypass` / `vbs_enclave_bypass`(检测后切策略,这个“先探再改”的框架值得保留)
- **内核面**:`kernel_etw_disable` / `callback_double_patch` / `universal_kernel_patch`(需 driver/BYOVD)
- **PPL bypass**、**CLR hosting 执行**
- **内存取证隐藏**:`hide_dll_from_memory` / `token_manipulation`(句柄/模块表) / `mem_forensics_hide`
- **Defender 专项**:`defender_advanced_evasion`
- **执行链伪装**:`lolbin_proxy_exec`(系统自带工具代理执行)、`trusted_exec_chain`、`dll_proxy_anti_tamper`
- **反调试/反沙箱**:`jitter_sleep`(kasper_safe_sleep)、`polyglot_detect`、`atomic_execution`

## 3 国产三巨头专项(思路参考,非成品)
- 360:`360-bypass.py` — 云查阻断、内核引擎、HIPS、虚拟机探测、文件监控
- 火绒:`huorong-bypass.py` — 剑引擎、内存扫描、注册表、HIPS
- 腾讯:`tencent-bypass.py` — TAV/自保护/前台/云
- 国际:`intl-av-bypass.py` — 11 款(Bitdefender/ESET/Avast/卡巴等)策略表
- 这些模块的共同手法:**先读 AV 状态/驱动/服务/注册表路径探测(真能用),再按策略表给出规避步骤**。探测部分可直接复用。

## 4 周边可复用工具
| 模块 | 实际能力 |
|---|---|
| `pe-toolkit.py` | info / fake(时间戳·链接器·Rich头·校验和) / codecave / section / dllproxy。fake 与 dllproxy 生成可用;codecave/section 有缺陷 |
| `qvm-bypass.py` | PE 膨胀 + 资源伪造(.rc/.ico/manifest),**实测产物可运行** |
| `anti-ml.py` | 熵值分析、熵归一化(可用),头字段改写(会把段表改废) |
| `sandbox-evasion.py` | 生成 C/Go 反沙箱代码 + 18 维评分卡(模板生成器) |
| `c2-framework.py` | Malleable profile 风格流量伪装(Teams/Outlook/Azure Origin+Referer)、DoH 列表、dead-drop 概念、多语言输出(c/powershell) |
| `shellcode-obfuscate.py` | 分块 + uuid/mac/ipv4 格式编码(产物生成正常) |
| `shellcode-patch.py` | 用 capstone 做语义 patch(能跑,产出 28→29B) |
| `anti-forensics.py` | 日志清除/服务停止/文件删——**真实破坏性,只在沙箱跑** |

## 5 可用的部分汇总(实测定论)
✅ 能跑:PE fake、qvm 资源伪造、anti-ml 熵归一化、sandbox-evasion 代码生成、c2-framework 配置生成、shellcode-obfuscate/patch、apk-evasion 模板生成、各 bypass 模块的 AV 探测部分。
❌ 不可用:shellcode-encrypt 的 `--generate-c`、loader.c/android-loader.c 编译、apk-packer、apk-obfuscator 的 `--all` 与相对路径。
