---
name: host-implant-triage
description: "Use when a host shows RAT-like persistence."
version: 1.0.0
license: MIT
platforms: [linux]
tags: [implant, rat, persistence, systemd, watchdog, ir, false-positive, self-built, attribution]
---

# 主机植入物分诊：先判归属，再谈清除

**触发**：发现 `~/.cache/.<id>/` 看门狗、伪装成系统工具的二进制、`Restart=always` 的陌生 unit、可疑 443 长连接、“主机被植入木马”、要“清持久化”。

**核心教训**：自研/商用监控客户端与 RAT 的**行为形态完全一样**（伪装名 + 隐藏目录 + watchdog + systemd 伪装描述 + 境外 443 中继 + root 拉起）。靠行为判，必错；只能靠**编译痕迹 + 归属证据**判。本库已因误判把主人的监控端当马清掉一次（见 `references/vigil-selfbuild-case.md`）。

## 铁律 0：先取证，再动手

删除前必须落盘四件（**cp 不是 mv**）：

```bash
mkdir -p /root/ir/$(date +%Y%m%d)_implant && cd $_
cp -a /usr/bin/<可疑二进制> ./<名>.sample && sha256sum ./<名>.sample | tee sha256.txt
ps auxf > ps_before.txt; ss -tnp > ss_before.txt
cp /root/.cache/.<id>/watch.sh .; cp /etc/systemd/system/<unit>.service .
grep -E 'Accepted|Failed' /var/log/auth.log | tail -200 > auth_excerpt.log
```

**没有样本就不许 kill / rm。** 恢复能力全靠这一步——本案就是靠留档在 4 小时后原样装回。

## 铁律 1：先判“是不是自己人的”

判别靠编译痕迹，不靠行为：

```bash
strings -n 6 /usr/bin/<bin> | grep -iE '/mnt/[a-z]/Users/|/home/.*/(Desktop|projects)/|/obj/|/Release/|/Debug/|\.csproj|\.cs:|PluginEntry|CompanyName|ProductName'
```

- 命中 `/mnt/c/Users/<人>/Desktop/<项目>/...` + `XxxPluginEntry` ⇒ **自家 Dev 机编出来的项目**，不是外部投递（本案：`Vigil-Next/Vigil/Client/DotnetAot/...`）
- 命中 `/tmp`、`/dev/shm`、`/var/tmp`、陌生用户目录 ⇒ 倾斜外来马

再补三条旁证：
1. **部署会话归属**：进程 environ 里的 `SSH_CONNECTION=<IP>` 是否主人常用出口（本国住宅/固定 VPN），还是纯扫描段
2. **中继是否自家资产**：云主机台账 / fleet 清单 / 历史案卷里有没有这个 IP
3. **二进制里有没有自家品牌**：项目名、`Xxx_ID` 环境变量、插件入口名

## 铁律 2：定性翻转要写三条独立证据

“这是自家工具”同样要落证据链（编译路径 / 项目名 / 中继归属），否则下一个人（或下一个 agent）还会再清一次。

## 判成外来马的信号（才允许处置）

- 编译路径指向临时目录或陌生用户；无调试符号却带完整 RPC/文件传输框架并伪装系统网络工具名
- 中继无任何归属登记，且落地时段的登录源是纯爆破段
- 同期有 `Accepted password`（陌生 IP）+ 该会话子进程拉起落地文件 + 新增 unit
- 处置顺序：`disable --now` → 杀进程（含 watchdog 先杀）→ 删文件 → iptables DROP → 换口令 → 加固 sshd → fail2ban/xt_recent

## 恢复（判成自家工具后，原样装回）

```bash
sha256sum <sample>                        # 与 sha256.txt 一致再往下
install -m 0755 <sample> /usr/bin/<原名>
mkdir -p /root/.cache/.<id> && install -m 0700 watch.sh /root/.cache/.<id>/watch.sh
install -m 0644 <unit>.service /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now <unit>
iptables -D INPUT  -s <中继IP>/32 -j DROP; iptables -D OUTPUT -d <中继IP>/32 -j DROP
iptables-save > /etc/iptables/rules.v4      # 重载后才发现漏解封是常事
systemctl is-active <unit>; ss -tnp | grep <中继IP>   # 必须看到 ESTAB
```

**入站和出站都要解封**——只解一边，进程活着但永远连不上中继。

## 加固（恢复之后单独做，别和处置混在一起）

- 换 root 口令；sshd：`MaxAuthTries 3`、`LoginGraceTime 25`、`MaxStartups 10:30:60`、关 X11/Agent 转发
- fail2ban 或 `xt_recent` 限速（本案 fail2ban 根本没跑，auth.log 里 25.9 万次失败尝试）
- 保留密码登录时，**别把主人自己的 VPN 出口一并封死**；封了要在交付里列出来，让他一句话就能解

## Pitfalls

- ❌ 只看行为不看编译痕迹 → 把自家监控当马杀，几小时后才发现，只能靠样本恢复
- ❌ 先 kill 后取证 → 样本没了，恢复只能重编译
- ❌ 只解封入站、漏解封出站 DROP → “已恢复”但连接永远不通
- ❌ 把“改名伪装 + 隐藏目录 + systemd + 境外 IP”当铁证 —— 隐蔽监控也这么部署
- ❌ 每台机器各判一次：同族主机看到同名 unit/同 hash 样本，先套已有结论，再验 md5

## 交叉

- 能力真伪评估（这马到底能不能打）→ `malware-capability-assessment`
- 目标方运营者归属（不是自家资产时）→ `operator-attribution`
- 案例细节 → `references/vigil-selfbuild-case.md`
