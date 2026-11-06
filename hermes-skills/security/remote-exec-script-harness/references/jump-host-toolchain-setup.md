# 跳板机侧工具链安装与任务纪律

跳板机(ubuntu 24.04 云机)上装东西/跑长任务的固定做法与坑。

## 1. 装 Python 包(PEP668)

```bash
python3 -m pip install --break-system-packages -i https://pypi.tuna.tsinghua.edu.cn/simple <pkg>
```

- 不加 `--break-system-packages` 会以 `externally-managed-environment` 直接失败。
- aliyun 镜像缺 wheel 时换 **tuna**;`curl_cffi`、`playwright` 走 tuna 秒装。
- 安装失败时**打印完整 pip 输出**(别只 `tail -3`),否则看不到真实原因。

## 2. 真浏览器(过质询 / 渲染 JS 用)

- `python3 -m playwright install chromium` 在 CN 出口常**长时间零进展**:官方 CDN 慢,`cdn.npmmirror.com/binaries/playwright/` 与 `registry.npmmirror.com` 的 chromium 快照路径都 404。
- **可靠替代:** 直接用系统 Chrome,不需要 `playwright install`:

```bash
curl -sL -m 900 -o /root/chrome.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends /root/chrome.deb
/usr/bin/google-chrome --version
```

- Playwright 侧用 `chromium.launch(channel="chrome", headless=False)` 驱动它;headless 易被反自动化识别,过质询一律 headful。
- **无显示环境自动套 xvfb**(让一条 rex2 命令就能跑完,不用在远端手搓两层命令):

```python
import os, sys
if not os.environ.get("DISPLAY"):
    os.execvp("xvfb-run", ["xvfb-run", "-a", "--server-args=-screen 0 1366x900x24",
                           sys.executable] + sys.argv)
```

- 清理卡死的安装进程:driver 的真实命令行是 node 跑 `cli.js install ...`,所以 `pkill -f "playwright install"` **匹配不到**;用 `pkill -f "cli.js install"` + `pkill -f "oopBrowserDownload"`,否则残留进程一直占 `__dirlock`,后续安装永远起不来。
- 判断安装到底有没有动:`ls -la /root/.cache/ms-playwright` + `du -sh`(缓存目录长期 16K = 根本没下载)。

## 3. 长跑任务与日志

- rex2 只在远端命令**结束后**才打印 ⇒ 本机日志 0 字节 **不等于** 失败(见 SKILL.md §3)。进度用独立的小脚本查:远端 `ps aux | grep <脚本名>` + 产物目录 `ls -la`。
- 本机侧包一层硬超时:`timeout N python rex2.py <hostkey> <script>` —— 工具级超时会把本地 job 变成孤儿进程(远端还在跑、输出丢失)。
- 要杀本地孤儿:只杀自己起的那次 rex2/paramiko 进程,并在汇报里一句话说明(用户对"杀进程"敏感)。

## 4. 拉回产物(重要习惯)

- 与 `rex2.py` 同目录放一个 `jget.py`(paramiko SFTP 下载器):`python jget.py <hostkey> <远端路径> [本地目录]` → 落到本地 `remote/`。
- 几 MB 的 minified JS / 页面样本**拉回本地再 grep**:本地反复写正则比在远端每次重传脚本快,且能立刻用工具链分析。

## 5. 低成本的端口/服务形态探测

- 没有 nmap 时用 python `socket` + `ThreadPoolExecutor` 扫常见端口(3.5s 超时、24 并发)。
- 先用"开放端口数量"判形态:只开 80/443 ⇒ 纯 Web 应用(别再往内网服务方向想),再决定打哪层。

## 6. 入口 IP 信誉类防护下的自检

- 跳板机不只用作出网,也可作为"干净出口"对照组:同一请求在跳板机与目标侧分别看响应差异,判定到底是我们的 IP 被拦还是目标行为。
- 第三方节点池若报 RST,先做裸 SOCKS5 握手握手探测区分"口令错"与"源 IP 白名单"(两种 greeting 都 RST/空回 = 白名单),不要来回换 user/pass 顺序。
