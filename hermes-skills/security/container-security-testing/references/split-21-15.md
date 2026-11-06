## 三点五、实战：容器内命令执行到手后的天花板判定（15 分钟止损）

> 场景：应用层 RCE / CI hook / DB `COPY ... PROGRAM` 已经在**容器内**执行命令。
> 目标是从「容器里的命令执行」推到「宿主机 root / 整机接管」，**或者**快速证明不行、准确结案。
> 铁律：**容器内命令执行 ≠ 主机 root**，报告口径必须分开写，不许含糊成「打进去了」。

**一次跑完的能力测绘（全只读）**
```bash
id; hostname; head -3 /etc/os-release
cat /proc/1/cgroup | head -3; ls -la /.dockerenv 2>/dev/null      # 容器指纹 / 是否 host cgroup
tr '\0' ' ' < /proc/1/cmdline; echo                            # 底座：s6 / tini / dumb-init / 直接 PID1
capsh --print 2>/dev/null | grep -i current || grep CapEff /proc/self/status
mount | grep -E 'docker.sock|overlay|/host' ; ls -la /var/run/docker.sock /run/containerd/containerd.sock 2>/dev/null
cat /proc/sys/kernel/core_pattern ; ls -ld /sys/fs/cgroup ; ls /dev | head -20
ls -la /sbin/su-exec /usr/bin/su-exec /sbin/gosu 2>/dev/null   # 降权底座特征
```
对应六条判据：① `id` 是不是容器 root（**不是 root 且镜像用 `su-exec`/`gosu` 降权 ⇒ 换二进制也提不到容器 root**：
入口由 s6/tini 监督，进程仍以镜像约定 uid 跑）② `/proc/1/cgroup` 有 `/docker/` = 容器、有 `/system.slice/` = 已到宿主
③ `CapEff` 有 `cap_sys_admin` 才谈 mount/cgroup 逃逸 ④ `docker.sock`/`containerd.sock` 存在 = **最省事一条**（§2.2）
⑤ `core_pattern`/cgroup 可写 = runc CVE 与 release_agent 前提（§3.3/§4.1）⑥ 能看到 `/dev/sd*`且能 `mknod` = 特权迹象（§3.5）。

**实测常见「出不去」组合（命中就直接结案）**
- 无 `docker.sock` + 无 `CAP_SYS_ADMIN` + `core_pattern`/cgroup 只读 + 低权 uid（不能 `mknod`）
  ⇒ 容器逃逸面封死；**内核 CVE 是唯一剩路**，且需能编译/落地的执行位，性价比极低。
- 镜像用 **s6 + `su-exec`/`gosu`** 降权 ⇒ 即使换掉 `/bin/sh` 也提不了容器 root（监督进程不会以后门身份重入）。
  这条最容易被忽略，很多人在这上面耗几十分钟。
- **别把「改服务运行用户」当提权**：例如把 PHP-FPM 的 `user` 改成 root，常见结果是 **FPM 起不来（服务直接挂）**——
  既不算提权，也是对生产的中断动作。
- **出口可能在别处**：官网/前台若在 Cloudflare Pages 等托管平台（源站 `/` 上根本没有官网文件，Host 对上返 404），
  **控住源站容器也改不了客户看到的首页** —— 打之前先确认「客户看到的资产在哪」，否则最后交付口径会翻车。

**结论口径（交付必须这么写）**

| 拿到的东西 | 怎么写 |
|---|---|
| 容器内命令执行 | 「应用容器命令执行（uid=N，容器内）」，附 `id` / `/.dockerenv` 证据 |
| 容器内 root | 「容器 root」，仍**不等于**主机 root |
| 主机 root / 整机 | 需宿主侧证据：宿主 `/etc/shadow`、宿主进程、宿主机文件写入、面板（1Panel/Plesk/宝塔）接管等 |

关联：§2.2 docker.sock、§3.3 特权/release_agent、§4.1 runc 三连、§4.4 逃逸后六阶段；
DB 侧同型入口（`COPY FROM PROGRAM` 落在 PG 容器、uid=70）见 `database-host-postexploit`；
Gitea hook 容器落点看 `gitea-diffpatch-rce`；同名机多个容器 RCE 时逐个标清容器名。
**实证案例**（1Panel + Docker 源站、两条容器链、六项负面证据、收尾与交付口径照抄）：
`references/onechat-2026-09-multi-container-source.md`。

