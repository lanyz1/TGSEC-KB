# 凭据面编排：SSH / 控制面 API / 面板登录

适用：非凭据面（未授权 / IDOR / 逻辑 / 会话 / 源码 / 公开签名面）已测满，凭据成为最后一根杠杆时。
字典必须是**运营者词表**（品牌、域名、handle、项目名、他们的数字习惯及其变形），不是 rockyou；
rockyou 级批量灌生产面板不能当主线，只当后台一条流水线，回报时一句话带过。

## 0. 开工前三问（不做就是白烧几小时）

1. **这服务到底吃不吃口令？**
   SSH：`ssh -o PreferredAuthentications=none -o BatchMode=yes -o ConnectTimeout=15 u@HOST -p PORT`
   → `Permission denied (publickey,password)` = 密码认证开着，值得喷；只回 `publickey` = 纯密钥，**别喷**。
   Web 面板：先探免鉴权策略端点（`/login-policy`、`/api/auth/policy`）看是否强制 2FA/验证码。
2. **版本有没有现成 CVE 直达？** banner 的发行版后缀就是补丁等级
   （`OpenSSH_8.9p1 Ubuntu-3ubuntu0.17` = regreSSHion 已修）。CVE 直达 > 喷口令，先花 1 分钟判。
3. **字典文件真在吗？** 启动前 `ls -la` 一遍所有 `-P/-L` 路径。
   路径写错时 hydra/脚本会**立刻退出且不留输出**，你会以为它在跑。

## 1. 吞吐：多出口 IP 轮转 + 自写客户端 > hydra

- 本机多公网出口时，**每 IP 一个 worker** 是唯一能按倍率提速的办法（限速多按源 IP 计）：
  - 裸 socket：先 `sock.bind((src_ip, 0))` 再 `connect()`
  - HTTPS：同样 bind 后 `ctx.wrap_socket(sock)`
  - SSH：`paramiko.Transport(<已 bind 的 socket>)` → `start_client()` → `auth_password()`
  - 系统 python 无 pip（PEP 668）：`python3 -m venv /tmp/v1 && /tmp/v1/bin/pip install paramiko`
- **SSH 用 paramiko，不用 hydra**，两个理由：
  1. 吞吐更高（同目标同并发实测 455 次/分 vs 271 次/分）
  2. **能区分「口令错」和「没测成」**：`paramiko.AuthenticationException` = 明确否定；
     `SSHException('Error reading SSH protocol banner')` / 超时 = 不确定，**必须重试**。
     hydra 把不确定当失败 → 静默漏口令。**漏报比慢更致命。**
- 脚本骨架：口令优先表（运营者词表放最前）→ 每个口令**遍历全部用户名**（命中面最大）→
  每 IP N 线程 → `unknown` 自动重试 2 次 → 命中写 `/tmp/<svc>_hit.txt` 并立刻 print → 每 200 次打一行速率。
- hydra 若必须用：`hydra -L users -P pass -s PORT -t 10 -o hits.txt -I HOST ssh`
  - `-R` 从 **CWD 的 `hydra.restore`** 续跑（换目录就找不到）
  - **`-o` 只写命中，STATUS 进度走 stdout** → 加 `| tail -30` 会把进度全缓冲掉、完全看不见；
    要监控就重定向到文件（`> /tmp/hydra.log 2>&1`）或 `| tee`。

## 2. 结果语义与收尾

- 下「无命中」结论前先看 `unknown/不确定` 计数：**超过 ~5% 就必须重跑不确定子集**再结案。
- 并发别超服务端 `MaxStartups` 直觉上限（SSH 默认 ~10:30:100）：单 IP 拉高并发会**随机丢连接**，
  表现跟「口令错」极像 → 用「每 IP 中等并发 + 多 IP」，不要「单 IP 高并发」。
- **控制面 API 价值高于面板登录**：VPN/WireGuard 设备注册（`/api/v1/devices`、`/api/v1/auth/login`）
  一旦进来 = 内网入口 + 全套隧道配置。这类限速多是 per-IP 个位数/分钟 →
  按 6-7 秒一发 / 每 IP 慢喷，**绝不 burst**（burst 只烧窗口、把封禁刷长）。
- 只有明确否定的失败才写 Deadends；限速未突破的面写「需更多时间/出口」，不要写成「不可利用」。

## 3. 同宿主 CPU 竞争（最容易自己坑自己）

- **bcrypt/argon2 口令喷是 CPU 密集**：对宿主机某端口开 300-400 并发登录，会把**同机**其它攻击面一起拖慢。
  实测：同机 SSH 从 455 次/分掉到 26 次/分，停掉面板高并发喷后立刻回升。
- 规则：**同一台机器上只让一个「吃 CPU」的重活当主角**。要提速 SSH/控制面，先停掉面板高并发喷，测完再决定恢复。
- 反过来用：**某服务的响应速率就是宿主机负载探针**。向量突然变慢，先怀疑自己把它压住了，再怀疑「目标死了/被封了」。
  廉价旁证：`curl -s -o /dev/null -w '%{time_total}'` 打一发健康检查，恢复正常即说明 CPU 腾出来了。

## 4. 进程与现场卫生

- **`pkill -f <pattern>` 会连自己的 shell 一起杀**（你的命令行里也含那个 pattern），表现是 exit -15、「命令莫名其妙被杀」。
  用括号技巧或更独特的串：`pkill -f "[b]rute_multi"`。
- 清进程后**数一遍残留**（`ps aux | grep -c "[h]ydra"`）再回报「已停」；
  后台进程 exit 143 / `tcsetattr: Inappropriate ioctl for device` 是无 tty 的正常现象，不是故障。
- 长喷一律后台 + 日志落盘 + 命中文件独立；用户叫停后**先确认进程数=0 且不再输出攻击进度**。
- 状态回报口径（本用户）：只报**活着哪几条、速率/ETA、命中与否**；已证伪项一句话；命中时第一行给 `user:pass`。
