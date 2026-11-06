---
name: kvm-vhost-csum-host-read
description: >-
  Use when 已拿 KVM/QEMU 虚机 guest root，要打宿主内核：vhost-net CHECKSUM_PARTIAL 的 IHL 改写
  (0x45→0x4f) 让宿主在 60B 头后写入 12B 越界，泄露 32B 宿主内存（CVE-2026-99999 / PwnEscape）。
  含 6 变体、双字节 fold 调参、宿主侧取证三件套、修复版本表。
---

# PwnEscape：vhost-net IHL 改写 → 宿主内存泄露（CVE-2026-99999）

实战来源：内网 KVM 台架（嵌套 KVM，宿主内核 5.15.0-112 未修），guest root → 宿主 32B 读。

## When to Use

- 已控 **KVM/QEMU 虚机内 root**，想从 guest 打到宿主内核
- 宿主开了 `vhost-net`（多数云主机默认）+ 网卡 checksum offload
- 有 `CAP_NET_RAW`（root 自带）能发原始以太帧
- 明确的「越权边界」证明需求（guest 读宿主内存 = 硬边界突破）

## 机制（一句话版）

1. guest 发伪造 `CHECKSUM_PARTIAL` 的以太帧，IP `ihl` 声明 0x45（20B 头）但实际塞 60B 数据
2. 宿主按 0x45 校验/路由，延迟校验和交给 `skb_checksum_help()`
3. **双字节暴力调参**让 fold 后高字节 = `0x4f` → 把 IHL 从 5 改成 **15（60B 头）**
4. 宿主认为头长 60B，把「头后 12B」写进 `skb->data` 之后 —— 落到下一个 skb 的宿主内存
5. 分片重装后 32B 宿主内存随回包/观测点抓包带出

## 台架验证（有人跑过才算数）

- 4.4 内核：写入 `0x45→0x4f` / IHL=60 / 三片全带改写头 / `options=[8B guard][32B 宿主内存]` 全成立
- 6.8 + conntrack：全链打通（ReasmOKs/FragOKs/写入实证），**F2 必须同为 `flags=1`**
- 嵌套 KVM：宿主 5.15.0-112（未修）完成 0x45→0x4f + 32B 泄露，宿主双方向抓包 + guest 内联捕获双证

## 操作顺序（PoC 脚本）

```bash
python3 pwnescape_poc.py selftest        # 离线自检：构造/调参/判别全链，不触网，先跑这个
python3 pwnescape_poc.py recon           # 接口/网关/虚拟化/MTU 侦察
python3 pwnescape_poc.py fire            # 实弹：6 变体 × dst(自身+HK+观测点)，1 轮
python3 pwnescape_poc.py fire 10.0.0.1,1.2.3.4 3   # 指定 dst + 3 轮
python3 pwnescape_poc.py analyze cap.pcap          # 观测点侧脱机分析
```

- **判据**：guest 侧收到带 12B 尾巴的包 **且** 观测点 pcap 里 `IHL=15`、`options` 区段非零
- 三个证据缺一不可：guest 内联捕获 / 宿主侧 tcpdump（同接口双向）/ 内核计数（`ReasmOKs` 增长）

## 修复版本（宿主侧，2026-10）

commit `6785011f8b16`（`ip_check_csum_start`，5 个消费点），已回补：
`5.10.272` / `5.15.223` / `6.1.190` / `6.6.159` / `6.12.113` / `6.18.57` / `7.2.11` / `7.3-rc7`

- 判宿主是否修：`uname -r` 比对上面分支，或看 `skb_checksum_help` 是否走 `ip_check_csum_start`
- 云厂商常滞后大版本号（如 `5.15.0-112` 属未修区间），按实际 patch 而非大版本判断

## 坑

1. 没开 checksum offload（`ethtool -k eth0 | grep tx-checksum`）→ 宿主不接管校验，链路断
2. `virtio-net` 走 vhost 才在宿主处理；纯用户态 QEMU 后端不命中
3. 分片必须**全部**带改写头，一片漏了重装失败
4. 32B 泄露是**小口子**：要反复打、按偏移拼宿主内存（页表/cred 结构各占不同偏移）
5. 宿主侧取证要在**桥接口**抓（`br0`/`vnet*`），guest 内抓不到改写后的头

## 相关卡

- `linux-privilege-escalation` — 拿到 guest/userland 之后
- `crio-checkpoint-escape-cve-2026-92574` — 容器侧同族越界
- `hypervisor-appliance-pentest` — ESXi/NAS 面板面
