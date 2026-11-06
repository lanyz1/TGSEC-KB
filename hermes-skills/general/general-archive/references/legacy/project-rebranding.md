<!-- archived from /root/.hermes/skills/software-development/project-rebranding/SKILL.md on 2026-10-21 -->

---
name: project-rebranding
description: "Use when 把开源项目去品牌化/换品牌：删原作者标记与git地址、换logo与品牌名。"
---

> 归档卡：原目录 `/root/.hermes/skills/software-development/project-rebranding`。卡内 `references/…`、`scripts/…`、`templates/…` 均相对原目录；读取用 `read_file('/root/.hermes/skills/software-development/project-rebranding/…')`，不要相对 `references/legacy/` 解析。

# 项目去品牌化 / 换品牌

把 clone 来的开源项目洗成自己的品牌（删原作者标识 + git 仓库地址 + 旧 logo，换新名新 logo）。

## 定位品牌标识（四类，逐个查）

1. **名称全部大小写变体**：`grep -rhoiE "<品牌>[-_]?ai|<品牌>" --include='*.{md,yaml,py,go,html,js,css,sh,json,mod,sum}' . | sort | uniq -c | sort -rn`。品牌名常有 8+ 种变体（驼峰/全小写/全大写/连字符/下划线），漏一个就替换不干净。
2. **logo 图片**：`find . -name '*.png' -o -name '*.ico' -o -name '*.jpg'` + 前端 `grep -rn 'logo\|favicon\|icon' web/` 找引用位置（README 大图 + 前端 brand-logo + favicon 三处最常见）。
3. **git 仓库地址**：README 的 `git clone` 命令、`upgrade.sh`/`install.sh` 里的 GITHUB_REPO 变量、前端 header 的 GitHub 按钮、LICENSE 附录的 Copyright 作者名、外链徽章（404StarLink/TCH 等）。
4. **版权/徽章**：LICENSE 版权行、README 底部的「已加入 XX 计划」章节、二维码图片（微信群等）。

## 批量替换品牌名

- **按长→短顺序**：先 `brand-ai`→`newname-hacker`、`BrandAI`→`NewName`、`BRAND_AI`→`NEW_NAME`，最后才 `brand`→`newname`。短词先替换会把长词拆坏（`BrandAI` 若先被 `Brand`→`X` 替换会变 `XAI`）。
- 用 Python `os.walk` + 文本扩展名白名单（.md/.yaml/.py/.go/.html/.js/.css/.sh/.json/.mod/.sum/.tmpl/.java/.cjs/.gradle/.gitignore 等）遍历替换；排除 `.git`/`venv`/`node_modules`/`__pycache__`/`target`/`data`/`log`。
- 白名单之外的扩展名（.tmpl/.java/.cjs/.gitignore/.lst）第一次替换会漏，跑完残留扫描后补一批。

## 换 logo

- PIL 多尺寸：大图 `resize((1254,1254), LANCZOS)` 覆盖原 logo.png；favicon 用 `save(path, format='ICO', sizes=[(16,16),(32,32),(48,48),(64,64)])`（ICO 读回只显示最大尺寸）。
- 中文文字 logo 需 CJK 字体，先 `fc-list | grep -i cjk` 找（无字体时 PIL 画中文乱码）；常见路径 `/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`。
- 替换前 `shutil.copy2` 备份原 logo（可回滚）。

## 编译产物与二进制

- 编译二进制（Go ELF 100M+ / target 目录 / config.yaml.backup）是原作者痕迹，删除或重新编译；备份时二进制可排除（源码能 re-build）。
- 改了 go.mod module 名，`internal/`/`cmd/` 里的 `import "旧module/..."` 必须同步替换，否则编译全失败（长→短顺序保证 module 名先被替换）。

## 验证（残留扫描）

`grep -rlI -E "<品牌>|<原作者名>" . | grep -v '/.git/' | grep -v '/venv/' | grep -v '/log/' | grep -v '/data/' | grep -v '\.log\|\.bak\|\.backup'` → 目标 0 残留。

## 坑（实测硬教训）

- **批量替换会按文件名重命名正在运行服务的二进制**：os.walk 对含品牌名的文件名 rename，把 `cyberstrike-ai`（100M+ ELF）改名/删除，磁盘二进制没了 → 服务重启起不来。替换前 `ps aux | grep <二进制名>` 确认是否在跑；替换后二进制若消失，立即 `go build -o <新名> cmd/server/main.go` 重编译。
- **前端品牌字标若是分段 span 会漏改后缀**：`<span class=brand__core>Brand</span><span class=brand__ai>AI</span>` 替换 Brand→X 后剩 `<span>AI</span>` 拼成 "XAI"。替换后 grep 前端 title/brand 显示文字核对拼接结果，把后缀也改掉（AI→Hacker）。
- **残留扫描要排除第三方依赖目录**：venv/（impacket 等）和 node_modules 里的同名字符串是误报，`grep -rl` 后必须 `grep -v` 过滤，否则被几十个第三方文件淹没、漏看真正的源代码残留。
- **根目录名也是标记**，但改名要配合重启（进程引用旧路径）+ 更新引用它的脚本（备份脚本等）；代码层清理完再动目录名，作为最后一步由用户拍板。
