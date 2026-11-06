# 通告：技能库换代 2178 → 2146（2026-10-22）

> 给「还在用旧版仓库」的人 / AI。本页三种说法，按场合挑一段直接复制。

## 一、短版（贴群 / 贴给人）

```
TGSEC-Qtzuu 技能库换代了（2026-10-22，master）。

技能卡 2178 → 2146：删掉 31 张 redteam-*-detail-pack 模板卡 + 1 张被完全覆盖的 laravel-app-pentest，
停用 6 张 macOS/办公卡；72stack 的 46MB H1 报告搬出技能树；回收约 325MB。
检索补了全文召回（headings + body_fts），重建后带 8 项门禁。

升级（仓库目录里跑）：
  git pull origin master && bash scripts/apply-arsenal-20261022.sh
验收：脚本最后必须打印 GATE OK，且「索引卡数 == 磁盘 SKILL.md 数」。
      库不全的机器会打印 `GATE OK（portable，N 条基线不适用）`——那是正常结论，不是失败；
      判定细则见 docs/UPGRADE-20261022-ARSENAL.md §5.1（portable≠满分，full 基线要搬全量库）。
说明：docs/UPGRADE-20261022-ARSENAL.md
```

## 二、给 AI 的完整指令（整段复制进对话框）

```
你所在的机器在用 TGSEC-Qtzuu 旧版技能库（2178 卡那版）。现在要求升级到 2026-10-22 版，按下面做，不要跳步：

1) 进仓库目录，拉最新：
   git pull origin master
   若报 divergent branches：git stash -u && git fetch origin && git reset --hard origin/master
   （本批中途 amend 过一次历史，只在报这个错时才用 reset）

2) 跑升级脚本（幂等，重复跑不会重复删）：
   bash scripts/apply-arsenal-20261022.sh
   它做 6 件事：安装 tools/arsenal 检索栈 → 备份待删卡 → 删 31 张 redteam-*-detail-pack + laravel-app-pentest
   → 把 72stack-sec/references/h1-reports 搬到 /root/archive/72stack-h1-reports
   → 把 6 张 macOS/办公卡写进 ~/.hermes/config.yaml 的 skills.disabled
   → 清旧周快照 / arsenal.db.bak-* / findcache.pkl → 重建索引 + 跑门禁

3) 脚本跑不了就手工做，步骤和命令在 docs/UPGRADE-20261022-ARSENAL.md §4，一步不许省。

4) 验收（全过才算完）：
   - python3 ~/.hermes/arsenal/arsenal_build.py      # 结束打印 total/enabled/disabled
   - python3 ~/.hermes/arsenal/post_rebuild_gate.py  # 退出码 0；gate_last.json 里 tier=full 或 portable
   - 索引卡数 == find ~/.hermes/skills -name SKILL.md | wc -l
   - ls ~/.hermes/skills/security | grep -c detail-pack   # 必须是 0
   - python3 ~/.hermes/arsenal/skill_find.py "宝塔 面板 密码 忘了" --top 1   # 有 bt-panel-pentest 的机器必须命中它；没有则该条不适用

5) 汇报格式（缺一项算没做完）：
   删了几张卡 / 停用几张 / 索引卡数 / 门禁 8 项结果 / 索引体积 / 重建耗时 / 有没有报错。

禁止：
- 不许跳过重建索引（arsenal.db 不入仓，不重建就还在检索已删的卡）；
- 不许拿 use_count=0 当删卡依据（归档卡计数记在目录卡上）；
- 不许把全量 SKILL.md 提交进仓库（只存 15 张伞形卡）；
- 不许在评测/门禁/selftest 里漏掉 SKILL_FIND_NOLOG=1（会污染 query.log 真实统计）；
- 删卡前必须确认备份 tar 已生成，本仓库不再包含那些卡。

背景数字（你的机器卡数不同属正常，判标准是「索引卡数 == 磁盘卡数」+ GATE OK）：
卡数 2146（启用 372 / 归档 1774）· 索引 342MB · 重建 65–80s · 查询 0.3–0.7s
门禁：YAML 全过 / selftest 30/30 / core96 TOP1 94/96 TOP3 96/96 / 三 phase TOP3 满分 / 标题词 7/7 / 正文词 7/8
```

## 三、只想要新代码、不想动自己技能库的机器

```
cd TGSEC-Qtzuu && git pull origin master
cp tools/arsenal/*.py tools/arsenal/*.json ~/.hermes/arsenal/
cp tools/arsenal/arsenal_keeper.py ~/.hermes/scripts/
python3 ~/.hermes/arsenal/arsenal_build.py && python3 ~/.hermes/arsenal/post_rebuild_gate.py
```
不删卡也能用新检索栈和门禁；卡数保持你本机的实际值。

## 四、一句话验收

> 脚本末行 `GATE OK` + 索引卡数等于磁盘 `SKILL.md` 数 + `detail-pack` 计数为 0。
> 库不全的机器会带 `portable` 后缀并列出不适用基线数：**这是真话，不是满分**（要 full 基线就搬库，见 UPGRADE §5.1）。

出问题回滚：`docs/UPGRADE-20261022-ARSENAL.md §6`（tar 解回 + 从 `skills.disabled` 删 6 个名字 + 重建）。
