# Worked Example: CC-Panes (wuxiran/cc-pane) Audit + Wallpaper Config

Full worked example of `third-party-repo-audit` on a real Tauri 2 desktop app (Aug 2026). Result: **clean, no backdoors**. Also documents CC-Panes specifics learned while auditing/deploying it.

## Verdict table produced

| 检查项 | 结果 | 说明 |
|---|---|---|
| Git remote | ✅ | 仅官方 origin，689 commits，无额外分支可疑 |
| 硬编码 URL | ✅ | 官方 API (opencode.ai / api.moonshot.cn / api.telegram.org / api.xiaomimimo.com) + 示例占位符 (provider.example 等) |
| IP 地址 | ✅ | 仅 100.64.0.5 (Tailscale CGNAT) + 回环 |
| base64/hex payload | ✅ | 无（唯一长 base64 = updater minisign pubkey，解码验证合法） |
| NSIS installer hooks | ✅ | 只杀旧进程 + 卸载清理用户数据，无下载执行 |
| Build scripts | ✅ | cargo build + 复制文件，无网络外发 |
| Updater endpoint | ✅ | 官方 GitHub Release + minisign 公钥 |
| CLI SessionStart hook | ✅ | 只 POST 到本地 daemon (127.0.0.1:47821) 带 Bearer token |
| daemon/web bind | ✅ | 默认 127.0.0.1，远程需显式开启 + 只读保护 |
| API key 处理 | ✅ | 只注入子进程 env (ANTHROPIC_API_KEY 等)，不外传 |
| 遥测/统计 | ✅ | 完全没有 |

**值得知道但非后门**：cc-notify 可选通知通道 (TG/DingTalk/Lark/Slack/Webhook，默认关闭)；语音输入需自配 DashScope/小米 MiMo key；skill 市场从作者 GitHub raw 拉取（有 SHA256 校验）；README 有作者赞助中转站推广链接。

## 关键审计命令速查（Windows git-bash）

```bash
git remote -v && git log --oneline | head -30
grep -rnoE "https?://[a-zA-Z0-9\.\-]+" --include="*.rs" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.json" --include="*.toml" . | grep -v node_modules | grep -v "/target/" | grep -v "\.lock"
grep -rnoE "([0-9]{1,3}\.){3}[0-9]{1,3}" --include="*.rs" --include="*.ts" --include="*.tsx" --include="*.js" --include="*.toml" . | grep -v "\.lock"
echo "<pubkey>" | base64 -d   # 验证 updater 公钥为 minisign 格式
```

注意：在 git-bash 里 `grep -rniE` 匹配 `eval\(` 等模式会命中大量正常文件（terminal/pty/shell 代码），需要逐个看上下文判断，不能只看文件名列表。

## CC-Panes 应用知识（部署/配置用）

### 数据与配置位置（release 版，非 dev）

- 数据目录：`C:\Users\<user>\.cc-panes\`
- 配置文件：`C:\Users\<user>\.cc-panes\config.toml`（含 `[wallpaper]` 段）
- 壁纸库目录：`<data_dir>/wallpapers/`（配置只存相对文件名）
- SQLite：`~/.cc-panes/data.db`；运行时 daemon manifest `~/.cc-panes/runtime/daemon-manifest.json`
- orchestrator 端口：`~/.cc-panes/mcp-orchestrator.json`（动态端口，如 47821）

### 壁纸配置段（config.toml）

```toml
[wallpaper]
enabled = true
kind = "image"            # none | image | video
file = "bg-musashi.png"   # wallpapers/ 下相对文件名
fit = "cover"             # cover | contain | tile | center
opacity = 1.0
blur = 4.0                # 高斯模糊 0..64
dim = 0.3                 # 压暗遮罩 0..0.9，白字可读性关键
terminalOpacity = 0.0     # 0 = 终端全透明，字浮在壁纸上
glassBlur = 0.0           # 面板玻璃模糊 0..24
```

改壁纸两种方式：GUI（设置→Wallpaper→选图）或直接改 config.toml。直接改文件时**必须先关应用再改再启动**，否则运行中的实例会覆盖 config.toml。

### 找终端友好壁纸（白字可读）

1. wallhaven API 搜索暗色系：`https://wallhaven.cc/api/v1/search?q=anime+dark&categories=010&purity=100&sorting=toplist&atleast=1920x1080`
2. 下载候选图后用 PIL 分析亮度分布，选暗部占比高（~50%）的：

```python
from PIL import Image
im = Image.open(f).convert('L').resize((200,120))
px = list(im.getdata()); n = len(px)
dark = sum(1 for p in px if p < 60)/n*100
print(f'dark={dark:.0f}%')   # 终端壁纸目标：dark 40-60%，纯黑 98% 太素
```

3. 经验：**纯黑背景+居中主体的图最适合终端**（四周黑=白字零干扰，中间有内容好看），配 blur=4 + dim=0.3 效果最佳。
4. 壁纸下载后可直接复制进 `~/.cc-panes/wallpapers/` 再改 config.toml 指向。

### CC-Panes 支持矩阵

- 内置 CLI 适配器（8 个）：claude, codex, cursor, gemini, glm, grok, kimi, opencode
- **不支持 Hermes**（全代码库 grep 零匹配）。可用 `cliLaunchers.overrides` 挂自定义命令把任意 CLI 塞进终端跑，但无会话恢复/MCP 编排（有壳无肉）。
