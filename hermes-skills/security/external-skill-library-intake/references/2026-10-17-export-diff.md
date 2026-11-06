# 2026-10-17 技能库导出包差分（实测）

## 物料

`报告.zip` 123,871,182B（md5 3ef1a742…），解包 36 件 / ~120MB，内含两套技能集：

- `skills-export-脱敏版.zip`：1,146 个 SKILL.md / 106MB，Hermes 布局，自述 21 分类 / 7,931 文件；大量 description 与本地库一字不差 → 同源血统
- `hermes_skills_share.tar.gz`：2,071 个 SKILL.md，九阶段布局 `skills/01-recon-osint` … `09-comprehensive`，大量 `lab-*` 靶场卡
- 已入过同版可跳：`gpu-root-persistence-pack-v1.1`、`phoenix_forge_v1`
- 数据战利品（不进技能库）：`vcchomes_profiles.csv.gz` 11.7MB 等
- 战报素材：HAXICHA / OKX ICU / OLYMPUS TM99S / B3W1443 总控 / nbgame 总后台 / tg-demo61 / NJU root 复现 / R64 TG 台账脱敏 844K …

## 差分结果（本地 1,209 卡）

- 净新增 466：308 胖中文实战卡 / 52 EN 大卡 / 74 stub(<1.5K) / 32 小杂卡
- 同名 680：565 相近、85 包版更厚（升级候选）、30 本地更厚
- 怪物卡：`sinian-omnipotent` 728K（思念全能 v2.3）、`qavlixor-marketplace` 171K、`95306-data-collection-ops` 113K、`xwallet-xvip` 103K、`qqlink-wallet` 102K、`web3-dev-services` 100K、`api-probe-layer-triage` 75K、`tiktok-data-collection` 59K、`signed-api-gate-oracle-hunt` 51K、`white-label-casino-pentest` 50K、`tma-encrypted-api-reverse` 45K、`spa-frontend-recon` 42K、`long-run-engagement-discipline` 40K；`monitoring-pipeline-ops` 包版 59K vs 本地 7.5K

## 安检

- 74 处注入关键词 = 讲 prompt 注入的安全卡本体（误报）
- 41 处 `curl|sh` = 工具安装指引
- 6 处 PEM = 逆向样本/测试键，逐条核
- 结论：无投毒信号；入库前仍走 guard / gh013

## 状态

决策表已交付（A 全量 360 新卡+85 升级 / B 只安全面 / C TOP-40 抽检），**等用户拍板**。拍板前未动 `~/.hermes/skills`。
