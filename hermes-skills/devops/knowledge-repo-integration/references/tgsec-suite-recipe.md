# TGSEC Security Suite 实战记录 (2026-09-01)

## 场景

用户命令: 吸收多个安全仓库 → 推送到 GitHub 自有仓库 → 精细整合 + AI 引导。

## 吸收清单

- reverse-skill (https://github.com/zhaoxuya520/reverse-skill) — 路由引擎 + 43 路由规则
- hack-skills (yaklang) — 102 SKILL.md, 三层路由
- SecAtlas (shuaiqideyu) — 46 技术卡 + 136 知识条目 + 17 案例
- AboutSecurity (wgpsec) — 68MB, 1884 文件, 200+ 技能
- Claude-BugHunter (elementalsouls) — 83 技能 + 681 报告模式
- Stopen (swfk2154) — OODA 渗透 Agent
- web-sec (ReAbout) — 38 利用 + 21 渗透流程
- /www/wwwroot/skill — 本地技能目录(后为空;内容消失在会话中途,注意用户会自己增删目录,先 ls 再操作)

## 整合要点(第二轮修正)

第一版是 `knowledge/<库名>/` 七库平铺 → 用户纠正「你没有帮我整合起来好吗」
第一版 README 保留上游作者标注 → 用户纠正「不要有其他仓库的说明」

最终结构:
```
/root/TGSEC-Qtzuu/
├── MASTER.md          # 21主题导航 + 5步路由
├── README.md          # 详细简介
├── AGENTS.md          # AI 引导(自动配置/缺工具自动装)
├── scripts/
│   ├── tools-manifest.json   # 55 工具 / 10 分类
│   ├── check-tools.sh        # 检测
│   └── install-tools.sh      # 多通道安装
├── domains/<21主题>/s
└── skills/            # 7 入口
```

## 踩坑细节

### 1. 嵌入式 .git → gitlink

```bash
cp -rL /root/AboutSecurity knowledge/AboutSecurity   # 复制了 .git
cd security-suite && git add -A
# warning: adding embedded git repository → mode 160000, 只推 15 文件
```
修复:
```bash
rm -rf knowledge/*/.git
# 嵌套: rm -rf knowledge/reverse-skill/reverse-skill/.git(两层嵌套)
git rm -r --cached knowledge/ -q
git add -A   # 这次是实体内容, 3364 文件
git push origin master --force   # 覆盖旧 gitlink 版本
```

### 2. skill_manage description 长度限制

新 skill 的 description 必须 ≤ 60 chars(触发词开头,句号结尾)。实测 70/62 chars 全被拒,58 chars 通过。
触发词 + 行为一行,细节全部放 SKILL.md body。

### 3. PAT 权限诊断

```bash
# fine-grained (github_pat_):
curl -s -H "Authorization: Bearer $TOKEN" https://api.github.com/user   # 身份 OK
curl -s -X PUT ... /contents/probe.md    # → Resource not accessible by personal access token
curl -sI ... | grep x-accepted-github-permissions   # metadata=read ← 铁证
# classic (ghp_):
curl -sI ... | grep x-oauth-scopes   # repo, delete_repo, admin... ← 写权限全有
```
结论: fine-grained 只有读,classic 勾 repo 才有写/建仓库。别让用户反复测试同一个 token,先探测再下结论。

### 4. 用户会自己改目录内容

- /www/wwwroot/skill 从 380 文件 → 19 报告 → 空目录,全程用户自己操作,
- 遇到「你清空了技能」指控时,先查 stat mtime / bash 历史 / 自己会话内写过什么,用证据说话。

### 5. 校验输出被管道截断的坑

`cmd | head -20` 在失败时 exit_code=0 但输出无效——本环境 terminal 会提示;重要校验(文件数、语法)不要用管道截断,看完整输出。

## 验证清单

```bash
python3 -c "import json; d=json.load(open('scripts/tools-manifest.json')); print(len(d['tools']))"
bash -n scripts/check-tools.sh
bash scripts/check-tools.sh          # 检测运行
bash scripts/install-tools.sh --dry-run --category mobile   # 预览
bash scripts/install-tools.sh --category mobile              # 实际装一个验证通道
# 推送后:
git ls-tree -r origin/master --name-only | wc -l    # 远程文件数
curl -s -H "Authorization: Bearer $TOKEN" .../contents/  # 远程结构
```