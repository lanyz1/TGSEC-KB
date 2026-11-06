---
name: pfsense-virtualbox-leftovers
description: "Use when 打 pfSense CE/Plus MIM 或 VirtualBox 7.2.20：39 条插值、九条 MIM 残留、SAS1068 guest→host 覆盖。"
---

# pfSense / VirtualBox 残留（2026-10）

## 一、pfSense CE 2.9.0-DEVELOPMENT：39 条残留插值
- 前提纠正：WebGUI「管理员本来就有 root」只对 `Diagnostics: Command` 成立；**只授予单页权限的受限 GUI 用户**不成立。
- 权限模型：`page-diagnostics-command` 带 `standard-warning-root`，`diag_command.php` 直接 `exec` —— 只要能把用户推到这一页就等于命令执行。
- 面：公开 master `9363ac5` 上 39 处**未被转义就插进 shell/命令串**的字段（是前面 5 个已公开 shell 的续集）。
- 打法：先找一个能写配置字段的低权页面（别名/描述/网关名/证书字段），把 `$()` 或反引号塞进去，再触发消费该字段的诊断页或定时任务。

## 二、pfSense Plus Nexus MIM（Netgate/pfsense-api `b4acd7c`）：九条可叠加残留
面在 `:8443` 的 MIM 控制器 REST。九条分别是：
1. 注册样例里带着可用凭据；
2. **unix socket** 暴露（本地提权链第一跳）；
3. `GET` 导出**私钥**；
4. ACME 配置整包 dump；
5. **fleet JWT** 可预测/可复用；
6. ACB userkey 泄露；
7. Snort 路径拼接（`../`）；
8. 官方样例把 **TLS 校验关掉**（`verify=False`）；
9. 以上可组合：样例凭据 → 读私钥 → 解 JWT → 打 fleet。
注：Plus 二进制未实测，全部是 OpenAPI/生成客户端层面的代码审计结论。

## 三、VirtualBox OSS 7.2.20（`f2792cf44`，svn r175154）：guest→host
- 目标类：guest 读写**hypervisor 进程内存**（VMSVGA/PCnet 时代最值钱的那一类）。
- 主洞：**SAS1068 MPT CONFIG 的 SCSI-SPI 页覆盖 `SasPages` 主机指针** → CONFIG 页可越界到 host 指针数组。
- 旁边五条：五个 High 解析器 + confused deputy（guest 触发、host 进程代跑）。
- 现实约束：拿 full host-user 还需要 Windows **restricted token** 上的第二条残留。
- 定位：源码 harness 实验室结论，尚无 CVE；版本钉在 2026-09 CPU（7.2.18，CVE-2026-87267..87285）之后，说明 CPU 没修到这块。
- 利用入口：`VBoxManage` 挂载/热插 MPT 控制器 → guest 侧发 CONFIG 页（CDB 走 SCSI pass-through）。

## 打法小结
| 目标 | 第一跳 | 关键动作 |
|---|---|---|
| pfSense CE | 低权 GUI 用户 | 找可写配置字段 → 插值 → 触发 `diag_command.php` 类消费点 |
| pfSense Plus MIM | `:8443` REST | 样例凭据/unix socket → 私钥导出 → fleet JWT |
| VirtualBox 7.2.20 | guest 内提权到 host 进程 | MPT CONFIG 页覆盖 `SasPages` |

## 出处
`abraxaslabs.tech/research/pfsense-ce-leftovers`、`/pfsense-api-nexus-mim`、`/virtualbox-7-2-20-leftovers`；PoC 仓同名。
相关卡：`opnsense-pfsense-vuln-matrix`、`virtualbox-vuln-matrix`、`hypervisor-appliance-pentest`、`selfhosted-panel-exploitation`。
