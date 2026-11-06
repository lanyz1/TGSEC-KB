## bot 修改部署流程

拉取→本地 patch→py_compile→上传→分步重启:
```
sftp 拉 /opt/v6/pix_bot_server.py → patch → python -m py_compile
上传后: pkill -9 -f 'pix_bot_serve[r].py'(单独 exec)→ setsid nohup python3 pix_bot_server.py > /opt/v6/bot.log(单独 exec)
```
查看运行日志 /opt/v6/bot.log;数据文件 /data_pool/index.json(分钟级)/health.json/gaps.json

**新树版 bot(`v6m.py bot`)的发布链 / 割接后核验 / 「bot 没反应」三级判定 / 已修缺陷台账见 `references/bot-release-and-no-response-diagnosis.md`**。★**按钮「没做进去」类报障(搜索/筛选出来只能看不能点)的定位与修法、真池真码探针、离线夹具的两个静默洞(头值类型 / 文案来源键)、bot「真活着」验收与启动横幅重复的判读见 `references/2026-10-07-bot-search-button-and-fixture-gaps.md`
- `references/bot-export-parity-and-fixture-verification.md` — **复刻老导出件（BOM/CRLF/列数/三类行）的流程 + 平台名单静默降级陷阱 + 真数据对拍口径 + 夹具必须重定向 `export_dir`/按钮断言要用真实 `Menus`**。用户丢来历史导出件说「还按这个格式来就行」、或动 `bot` 导出/菜单按钮时先读这份。上一份（2026-10-07）`。**发布链固化顺序 = scp → **两端 tar sha256 必比** → `--stage --tar … --sha …` → `--plan`(只读) → **staged 树真数据探针** → `--activate --yes` → `--verify` → **手动串行**停/起(方括号 pkill + `ssh -n -f` 起 `setsid nohup flock -n … python3 -u`) → 行号锚健康证据。**activate 不会重启 bot**(在跑进程仍持旧代码)。

