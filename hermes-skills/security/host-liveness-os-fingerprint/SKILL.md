---
name: host-liveness-os-fingerprint
description: "Use when ping 通但端口连不上/要判主机死活或猜系统。TTL+IP ID+MAC 四件套定性。"
version: 1.0.0
tags: [recon, liveness, ttl, ip-id, os-fingerprint, ssh-unreachable, filtered, proxy-arp]
---

# 主机存活判定与 OS 指纹（TTL / IP ID / MAC）

「这台机器还活着吗 / 为什么连不上 / 它是什么系统」——在没有开放端口、拿不到 banner 时，
**TTL、IP ID 序列、MAC 绑定关系**这三样就是唯一的证据源。
本卡给出固定判定树和一张判读表，避免把「ping 通」当成「主机在」、把「全端口 filtered」当成「服务下线」。

## When to Use

- 「这个 IP 为什么 ssh 连不进来 / 端口连不上 / 是不是被封了」
- ping 通但所有端口 `filtered`，需要判**死机 / 网关代答 / 活着但没服务**
- 扫不出版本，需要猜 OS（Windows vs Linux）来选打法（RDP/SMB vs sshd/nginx）
- 自有机器/客户机器掉线，要定性是欠费停机、系统重装，还是 IP 被回收换主
- 怀疑云平台 SDN 网关在**代理应答 ARP/ICMP**，制造「主机在线」的假象

## 0. 判定树（照顺序走，别跳步）

```bash
ip route get <IP>                              # ① 是否同 /24 二层直连
ip neigh show | grep <IP>                      # ② MAC 绑定
ping -c 4 <IP>                                 # ③ 通不通 + ttl
nmap -Pn -n -p- --min-rate 5000 --reason <IP>  # ④ 全端口状态 + no-response 明细
```

```
① 同网段(二层直连)?
   ├─ 是 → TTL 不经路由衰减 = 原值可用作 OS 指纹
   └─ 否 → 先 traceroute 数跳数，TTL 只能给上限（64/128 − hop），别硬判
② MAC
   ├─ 一号一 IP           → 独立 VM
   └─ 多个 IP 共用一个 MAC → 一台机器绑多个 IP（正常商业做法，**不是**代答）
③ ping
   ├─ 不通 + 全端口 filtered → 关机/停机/被墙（结合 ② 判是否代答）
   └─ 通 → 看 ttl：64=Linux / 128=Windows / 254=网络设备
④ 全端口
   ├─ 有 open            → 直接打，不用再猜
   ├─ 有 closed(回 RST)  → **主机活着铁证**，该端口无监听
   └─ 全 filtered(0 RST) → 入站被静默 DROP，**不是**「服务不存在」
```

## 1. 四件套：TTL / IP ID / MAC / 换机交叉

### ① TTL —— 同网段才准

二层直连不收路由衰减，TTL 是原始值：

| ttl | 判决 |
|---|---|
| 64 | Linux / Unix / 路由器上的 Linux |
| 128 | **Windows** |
| 254 / 255 | 网络设备（华为/思科等） |

> 跨路由时每跳 −1，只能反推「初始 TTL ≥ 观测值」。**先 `ip route get` 确认同网段再用这条。**

### ② IP ID 序列 —— 区分 Windows 与 Linux

连发 5 个 ping，读每个 reply 的 IP 头 `id` 字段：

| 序列 | 判决 |
|---|---|
| `57629,57630,57631,57632,57633` 严格 +1 | **Windows** 全局计数器 |
| `64995,65016,65041` 跳跃/被打乱 | **Linux** per-destination 计数 |
| 全 0 | 部分 Linux 内核（也可作弱指纹） |

> ⚠️ **单看 IP ID 会误判**：云平台 SDN 网关代答的设备同样是严格 +1（它空闲，只服务你的 ping）。
> 必须和 MAC 唯一性、换机交叉、TCP 栈行为**三条同向**才落槌。

### ③ MAC 绑定 —— 最容易读错的一条

```bash
nmap -sn -n 10.0.0.0/24 | awk '/Nmap scan report/{ip=$NF} /MAC Address/{print ip" "$3}'
```

- **一台机器绑多个 IP（共用同一 MAC）是正常商业做法**：客户买 4 个 IP 挂 4 个站。
  实测同一 /24 里 `.3/.4/.7/.9` 共用 `…:2F`，`.8/.39/.184/.201/.241` 共用 `…:58`。
- **真正判代答**要看：这些 IP 是否**同 TTL、同 IP ID 计数器、且完全没有 TCP 栈反应**。
- 云商按 VM 分配 MAC（如 `24:bc:16:00:00:xx` 连号池），一 VM 一个 MAC。
  这类前缀在标准 OUI 表里**查不到**，别因为「厂商未知」就认定是网关。

### ④ 换机交叉 —— 排除源 IP 白名单

从同段/另一台自有机器再测一次目标：

- **两台都连不上** → 排除「只封我的源 IP」，问题在目标侧
- **只有我连不上** → 是源地址白名单/风控，换出口即可（见 `ip-ban-bypass`）

## 2. 判读表：把「连不上」拆成四种完全不同的病

| 观测组合 | 结论 | 处置 |
|---|---|---|
| 全端口 filtered + ICMP 通 + ttl=128 + IP ID 严格+1 | **主机活着，Windows，没有 SSH 服务端**；Defender 防火墙默认静默 DROP 一切未放行入站 | 只能走云控制台 VNC；要 ssh 得先装 OpenSSH Server（见 §4）|
| 全端口 filtered + ICMP 通 + ttl=64 | 主机活着，iptables/安全组 DROP | 控制台进去改规则，或从允许的源打 |
| 全端口 filtered + ping 不通 + MAC 多 IP 共享 | 疑似网关代答 / 机器关机 | **不要报「主机在线」**；去面板核状态 |
| 22 closed(回 RST) 但连不上 | 主机活着，sshd 没监听/没装 | 换端口扫一遍，或换协议（RDP/SMB/HTTP）|
| 全端口 filtered + 只有我连不上 | 源 IP 被封/白名单 | 换出口，不要动目标 |

## 3. 杀手锏：翻 auth.log 定性「它到底有没有 sshd」

```bash
grep -a "<IP>" /var/log/auth.log* | grep -aE 'Accepted|Failed'
```

- 只有 `Accepted password for root from <IP> port N` ⇒ **它是客户端，登录过我们**
  ⇒ 这台机器**只装过 ssh 客户端，从来没跑过 sshd**。
  「ssh 连不进来」最反直觉、也最常见的答案就是这个。
- 同时看时间线（`head -1` / `tail -1`）：最后一笔之后就没动静 = 部署脚本停了 / 机器换主 / 被重装。

> 归因纪律：同网段自有 fleet 的 IP，**先按「老板自己的服务器」处理**，
> 结论只写客观事实（`<IP>` 在 `<时刻>` 用 root 登录并把进程拉起），把「是不是监控/部署器」交给老板认领，
> 不要抢着定性成入侵或后门。

## 4. 落地处置：Windows 机器怎么才能连进去

3389/22 全被 DROP 时，**唯一入口是云控制台 VNC / 远程控制台**。进去后按需放行：

```powershell
# 开 RDP
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections -Value 0
Enable-NetFirewallRule -DisplayGroup "远程桌面"

# 装 OpenSSH Server 并放行
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd; Set-Service -Name sshd -StartupType Automatic
New-NetFirewallRule -Name sshd -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22
```

Linux 侧对照（ufw 全 DROP 的典型误配）：

```bash
ufw status verbose; iptables -S INPUT | head -20   # 先看是不是 default deny 没放行 22
```

## 5. 工具

- `scripts/fingerprint_ttl_ipid.py` —— scapy 一把梭：TTL + IP ID 序列 + TCP 22/3389 状态 + ICMP addr-mask/timestamp + UDP unreachable，支持 `--ctrl` 挂对照组。
  实测可直接区分「真 Linux / 真 Windows / 代答设备」。
- 安装（本机无 pip3、PEP668 受限时）：
  ```bash
  uv venv /root/.venv_scapy
  uv pip install --python /root/.venv_scapy/bin/python scapy
  /root/.venv_scapy/bin/python scripts/fingerprint_ttl_ipid.py <IP> --ctrl <已知Linux机>
  ```
- 完整实战案例与数字对照表：`references/ssh-unreachable-ttl-ipid.md`

## Pitfalls

1. **ping 通 ≠ 主机在**。云 SDN 会代答 ARP/ICMP，制造在线假象。
2. **全端口 filtered ≠ 服务下线**。返回 RST 才是「主机活着 + 端口没开」；零响应是防火墙 DROP。
3. **多 IP 共 MAC 不是代答**，先想「一台机器绑多 IP」。
4. **ttl=128 不一定 Windows**：改过 `ip_default_ttl` 的 Linux 也会。要 IP ID 同向才落槌。
5. **别在公网跨路由场景用 TTL 判 OS**，跳数未知时会判错。
6. **同一个 /24 里 ttl=128 的机器占一成是正常的**（Windows 客户群），别把「一堆 128」当成异常代答。
7. **出结论前必须换机交叉一次**，否则分不清「目标死了」和「我被封了」。
8. **别把「我连不上」写成「服务已下线」**——报告措辞按 §2 判读表走。

## 关联

| 技能 | 定位 |
|---|---|
| `host-reachability-verification` | 探针可信度 / filtered-closed 语义 / 中间层撒谎识别（本卡的上级总纲，user-owned）|
| `recon-discriminators` | 端口通但零响应、停放页、满屏 200 的误判防护 |
| `ip-ban-bypass` | 确认是源 IP 被封之后的换出口 |
| `linux-host-hardening` | 目标侧加固：sshd/ufw/fail2ban |
| `rdp-*` / `windows-*` | 确认是 Windows 之后的打法分诊 |
