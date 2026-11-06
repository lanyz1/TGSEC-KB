## 顺手把跳板机本身当情报源(拿到就先读一遍,别只当出口用)

作业机/跳板机是**别人(或你上一轮)打过的现场**。在打目标之前先把它读一遍,常能省掉整轮盲猜:

- **`known_hosts` 反解出它真正连过哪些主机**。Ubuntu 默认 `HashKnownHosts yes`,条目是哈希的,肉眼读不出:
  ```bash
  for i in $(seq 1 254); do
    ip="<段前缀>.$i"
    ssh-keygen -F "$ip" -f /root/.ssh/known_hosts >/dev/null 2>&1 && echo "KNOWN $ip"
  done
  ```
  ⚠ **`known_hosts` 只证明“TCP 连上并完成了密钥交换”** —— SSH 在认证**之前**就下发 host key,
  所以它是“重点关注名单”而**不是**“已拿下清单”。在报告里别把两者混为一谈。
- **`/tmp` 与 `~` 下前序会话的脚本与输出**往往比目标本身更有信息量(目标清单、已穷尽路径、已试过的凭据),
  但也可能**混着完全不同的项目** —— 先按目标指纹筛,别把别的项目的战果算进来。
- `~/.ssh/` 找私钥与 `authorized_keys`;`.bash_history` 按目标关键词 grep。
- **没有 paramiko 时用 `sshpass` 走原生 `ssh`**(作业机常已装 `sshpass`):
  ```bash
  sshpass -p "$p" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null \
    -o ConnectTimeout=6 -o PreferredAuthentications=password -o PubkeyAuthentication=no \
    "$u@$ip" 'id; hostname'
  ```
  比装 paramiko 快,也绕开 PEP668 装包限制。
- **从跳板机测目标常能绕过“本机 IP 被封”**:同一台目标本机打回 `Error reading SSH protocol banner`
  (连接被重置),换跳板机源 IP 就能正常完成密钥交换 ⇒ **“打不通”先怀疑源 IP 被封,不是目标没开 SSH**。
- **非默认端口的服务也要从跳板机复测一遍**:IP 白名单常只放行同段/同机房出口,
  本机与跳板机回的错误不同(如 MySQL 的 `Host '<ip>' is not allowed` 直接点名被拒的出口)。

