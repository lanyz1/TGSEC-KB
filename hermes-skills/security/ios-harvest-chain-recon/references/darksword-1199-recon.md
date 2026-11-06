# 1199.wmqddnhmx.top (DarkSword) 侦查档案

## 结构
- Node server.js 端口 3001（nginx 反代到 1199 域名），后台 admin/[REDACTED]!
- assets/ 51 个 JS：exploit_registry.js 35 个 exploit 注册项覆盖 iOS13-26
- 核心文件：rce_loader.js（版本路由）、rce_module/worker/sbx0/sbx1/kernel_priv 分版本
- profiles/ 20 个版本 profile（ios_13_7.json ... ios_26_3.json），含 offsets/dyld/symbols/gadgets

## 版本→CVE→模块映射（exploit_registry.js 实锤）
| iOS | RCE | 沙箱逃逸 | 提权 |
|---|---|---|---|
| 13.0-13.4 | CVE-2020-3887 | CVE-2020-3840 | CVE-2019-8605 |
| 13.5-13.7 | CVE-2020-9951/9860 | CVE-2020-3840 | CVE-2019-8605 |
| 14.0-14.8 | CVE-2021-30858 | CVE-2021-30807 | CVE-2021-30883 |
| 15.0-15.6 | CVE-2022-32893 | CVE-2022-32894 | CVE-2022-32917 |
| 16.x | CVE-2023-23531/32439/37450 | CVE-2023-41062 | 共用18链 |
| 17.0-18.4.1 | CVE-2025-43529 UAF | CVE-2026-20700/24201 | CVE-2025-43510/43520 |
| 18.6-18.7.2 | CVE-2025-43529-18.6 | CVE-2026-20700 | CVE-2025-43510/43520 |
| 26.0-26.9 | CVE-2025-43529-26 | CVE-2026-20700-26 | CVE-2025-43510-26/43520-26 |

## 真伪判定结论
- 代码真实：rce_module_13_14.js 224 个 hex 偏移 + addrof/fakeobj 原语；rce_module_15.js 139 个偏移；kernel_priv 66 个内核偏移；文件大小 40KB-530KB 非空壳
- 26 链纸面级：rce_module_26.js 注释明说"22F76、22G81 等不同 build 必须分别生成"，无真机实锤
- uploads/device_log 全假：3065 张"照片"全是 64×64 PNG 占位图（179字节）、通讯录全带星号掩码、server.js 有 fakeUploadCount/isFake/fallbackProgress 伪造机制、备份名 _realism/_keepfirst_random
- 18.x 链最成熟（真机实锤记录）；13-17 公开 PoC 移植可运行但老版本实战价值小

## 与 3939 对比
- 3939 只有 18.4-18.6.2 子集（SYZB 系列），1199 是完整版
- 两套 exploit 代码同源（3939 的 SYZB2025/2027 与 1199 的 rce_module/rce_worker 内容对应）
