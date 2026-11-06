# tools/pack —— 外发打包流水线

四步一条链，产出「干净版」压缩包：

| 脚本 | 作用 |
|---|---|
| `stage_pack.py` | 按发布口径把 `tgsec-kb` 拷成干净树（丢媒体/二进制/索引/镜像/词表、>2MB 单文件），长路径安全 |
| `sanitize_pack.py` | 凭据扫描 + 就地脱敏：AWS/阿里云 AK、openai/anthropic key、GitHub PAT、Slack、Telegram bot、JWT、Bearer、Set-Cookie、通用 `api_key|secret|password` 赋值、私钥块；名字像凭据的独立文件直接删；复扫残留必须 0 |
| `zip_pack.py` | 打包 zip（`\\?\` 长路径写、deflate 9），并拒收被驱逐的路径与扩展名 |
| `verify_pack.py` | 包内复扫：结构白名单（不含 sessions/storages/profiles/attachments/hermes-skills/arsenal.db）+ 凭据 0 命中 + 关键文件齐全，输出 PASS/FAIL |

跑法（Windows）：

```powershell
$py='C:\Users\Administrator\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
$env:PYTHONUTF8='1'
& $py tools\pack\stage_pack.py
& $py tools\pack\sanitize_pack.py C:\Users\Administrator\Desktop\TGSEC-Qtzuu-clean-20261105
& $py tools\pack\zip_pack.py
& $py tools\pack\verify_pack.py
```

脱敏判定：文档里的示意占位（`xxx` / `your_*` / `<...>` / `0{8,}`）保留原样，长随机串一律 `<REDACTED>`。`verify_pack.py` 退出码 0 才能外发。