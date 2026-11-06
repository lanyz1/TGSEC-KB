---
name: rebranding-open-source-tool
description: Use when 把开源工具去品牌化/洗白成自己的名字与logo。
---

# 去品牌化/洗白开源工具

把 clone 来的开源工具彻底改成自己的品牌(如 CyberStrikeAI → 思念黑客/SinianHacker)，删掉原作者一切痕迹。

## 流程

### 1. 侦察(先摸清，再动手)
```bash
# 品牌名所有大小写变体
cd <repo> && grep -rhoiE "cyberstrike[-_]?ai|cyberstrike" --include='*.md' --include='*.go' --include='*.yaml' --include='*.py' --include='*.html' --include='*.js' --include='*.css' --include='*.java' --include='*.sh' --include='*.json' . | sort | uniq -c | sort -rn
# git 地址 + 作者名(用户名=git owner)
grep -rn "git clone\|github.com/<owner>\|<OwnerName>\|404StarLink" --include='*.md' --include='*.sh' --include='*.html' .
# logo 位置
ls images/ web/static/ 2>/dev/null | grep -iE "logo|favicon|icon"
# 服务启动方式(改名前必查，避免删了正在运行的二进制)
systemctl --user list-units 2>/dev/null | grep -i <brand>; ps aux | grep -i <brand>
```

### 2. 品牌名批量替换(长→短顺序，避免部分替换)
Python 遍历文本文件，映射按「最具体→最泛」排序：
```python
REPL = [
  ('cyberstrike-ai','sinian-hacker'),  # 带连字符的最先
  ('CyberStrikeAI','SinianHacker'),
  ('CYBERSTRIKE_AI','SINIAN_HACKER'),
  ('CyberStrike','Sinian'),
  ('CYBERSTRIKE','SINIAN'),
  ('cyberstrike','sinian'),           # 最泛最后
]
```
- 扩展名白名单要全：.md/.yaml/.py/.go/.html/.js/.css/.sh/.json/.mod/.java/.tmpl/.cjs/.gradle/.properties + `.gitignore`(无扩展名，单独判断)
- 排除：.git/ venv/ node_modules/ __pycache__/ target/ data/ log/
- 目录/文件名也含品牌时：os.walk 收集后 os.rename(从深到浅)

### 3. git 地址删除(这些都要清)
- README 的 `git clone https://github.com/<owner>/<repo>.git` 行
- 加入的组织标识(如 404StarLink/星链计划)章节 + 图片
- 比赛/荣誉标识(如 TCH)章节 + 图片
- `upgrade.sh`/自动升级脚本里的 GITHUB_REPO(整个删，是 GitHub 下载工具)
- 前端 GitHub 按钮
- LICENSE 里的 `Copyright <year> <OwnerName>` → 改成自己

### 4. logo 替换(PIL，多位置)
```python
from PIL import Image
im = Image.open('你的logo图').convert('RGBA')
im.resize((1254,1254),Image.LANCZOS).save('images/logo.png','PNG')
im.resize((64,64),Image.LANCZOS).save('images/logo_small.png','PNG')
im.resize((1280,1280),Image.LANCZOS).save('web/static/logo.png','PNG')
im.convert('RGB').save('web/static/favicon.ico',format='ICO',sizes=[(16,16),(32,32),(48,48),(64,64)])
```
- 中文 logo 用 PIL 生成需中文字体：`/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`(文泉驿，`fc-list | grep -i wqy` 确认)

### 5. 编译产物清理
- Go 二进制(101MB 级别，可 `go build` 重建)→ 删除；重建用 `GOPROXY=https://goproxy.cn,direct go build -o <新名> cmd/...`
- maven/gradle 的 `target/`、`config.yaml.backup`、`*.log`、`*.bak` → 删除

### 6. systemd 改名 + 重启(长驻服务)
```bash
systemctl --user stop <旧服务>                    # 先停，否则删二进制断服务
mv /root/<旧目录> /root/<新目录>
# 写新 .service: Description/WorkingDirectory/ExecStart/StandardOutput 全改新名
systemctl --user daemon-reload
systemctl --user enable --now <新服务>            # enable + start 一步到位
```
- 同步更新备份脚本里的路径/包名/`--exclude`(二进制名变了)

### 7. 验证(必须残留=0)
```bash
grep -rlI -E "<旧品牌>|<OwnerName>" . | grep -v '/.git/' | grep -v '/venv/' | grep -v '/log/' | grep -v '/tmp/' | grep -v '/data/' | wc -l   # 必须 0
curl -s http://localhost:8080/ | grep -oE '<title>[^<]*</title>'    # 新品牌
systemctl --user is-active <新服务>                                    # active
```

## 坑(实测踩过)
- 删正在运行的二进制会断服务：先 `systemctl --user stop` 或查 `ps aux`
- 前端 brand-wordmark 常分段(`<span>CyberStrike</span><span>AI</span>`)，只替换 core 段会漏后半段 → 变成 `SinianAI`，需单独改 `__ai` 段
- Go module 名用连字符(`sinian-hacker`)合法，import 路径会同步替换
- 打包备份排除二进制(可重建)，否则 106MB 二进制打进包超 Telegram 50M 限制
- .git 目录不替换(部署时不带)，但 LICENSE/README 里的 owner 名必须改
