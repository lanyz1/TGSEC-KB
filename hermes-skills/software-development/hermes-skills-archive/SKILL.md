---
name: hermes-skills-archive
description: "整理技能库时使用: 按主题分类归档 Hermes 技能到项目并生成索引文档。"
---

# Hermes 技能库归档整理

把 `~/AppData/Local/hermes/profiles/123/skills/security/` 下全部技能(每个 = SKILL.md + scripts/references/templates)按 9 大主题分类复制进目标项目目录,并自动生成 README 索引、技能明细、统计文档。

## 工作流

1. **定位技能源目录**(安全技能):
   ```bash
   ls ~/AppData/Local/hermes/profiles/123/skills/security/   # 133 个技能目录
   find ~/AppData/Local/hermes/profiles/123/skills/ -name "SKILL.md" | wc -l   # 总数
   ```

2. **分类映射**: 维护 `organize_skills.py` 里的 `CATEGORIES` 字典
   - 键 = 技能目录名,值 = (分类目录, 中文备注)
   - 9 大分类: `01-web渗透` `02-逆向破解` `03-网络渗透` `04-云安全` `05-移动硬件无线` `06-密码OSINT社工` `07-恶意软件取证` `08-红队C2` `09-综合辅助`
   - 脚本会自动: 创建目录 → 复制技能(先删旧再复制,保证同步) → 对未分类技能报警 → 生成 `_index/skills_index.json`

3. **执行归档**:
   ```bash
   cd <项目>/技能库/_index && python organize_skills.py
   ```

4. **生成文档**(README.md / 技能明细.md / 技能库统计.md):
   ```bash
   cd <项目>/技能库/_index && python gen_docs.py
   ```
   - `gen_docs.py` 从 skills_index.json 读取,按 CAT_ORDER 分组输出 markdown 表格
   - README 含: 目录结构表(9类+数量+覆盖范围)、每类技能速查表(链接直达 SKILL.md)、快速导航
   - 技能明细含: 每个技能的位置/备注/描述/触发词

5. **提炼实战案例集**: 从长期记忆(用户偏好/实战情报/环境陷阱)提炼成 `实战案例集.md` 放项目根目录
   - 含: 环境陷阱(v2rayN 双劫持点)、各目标平台情报(fndata/EMSHOP/RTG/m9600)、方法论沉淀、交付偏好
   - 用 memory 工具回顾或直接查记忆注入内容

## 复用模板

复制到新项目时,把 `organize_skills.py` + `gen_docs.py` 一起拷过去(`_index/` 目录),然后:
1. 改 `DST` 为目标项目路径
2. 如需换源,改 `SRC`(默认指向 Hermes security 技能目录)
3. 新技能出现时,只需在 `CATEGORIES` 补一行映射,重跑两步即可增量更新

## 已归档实例

- `D:\博彩通杀\技能库\` — 133 技能 / 439 文件 / 239 脚本,9 大分类
- 源: `C:\Users\Administrator\AppData\Local\hermes\profiles\123\skills\security\`

## 注意事项

- 复制用 `shutil.copytree` 先 `rmtree` 旧目录,保证技能更新后归档同步
- 分类覆盖不到的新技能会在脚本输出 `⚠️ 未分类`,需补进 CATEGORIES
- 脚本用 Python3 跑,无第三方依赖
- description 清洗: 用 `Trigger:` 截断,去掉触发词部分(触发词单独提取展示)
- 中文目录名在 README 链接里直接可用(`./01-web渗透/xxx/SKILL.md`),Windows 下无碍
