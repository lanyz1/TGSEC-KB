# 2026-09 round7: sync 快照防回退 + "平台外"最终实证(sync_plat_enroll v2)

日期:2026-09-05。round6 遗留的"平台外=norm 匹配 bug"假设被推翻,真根因=覆盖式快照回退;sync_plat_enroll v2 防回退已部署。同时记录主服 UTC 时区坑为类级规则。

## 1. "平台外"最终实证:不是 norm 差异,是快照回退

**推翻 round6 假设的证据链**:
1. repr 直接对比:博涛 pack_map 单位名 = "长葛市博涛金属有限公司" = 名册原文**一字不差**;25 家直接对照 MATCH 10 家(MISS 15 = 真待补),博涛是 MATCH。
2. 时间线:CSV mtime **15:18**(生成时名册快照 24 家、无博涛)→ plat_enroll_map updated **22:30**(25 家含博涛,第 19 位)。
3. 复现验证:用现名册调 `fmt_ents_csv(pid)` 重生成 → **平台外=0,博涛 6 包归位 ✅已采(60=54+6),待补 15 不变**。

**根因**:sync 每 30min 全量覆盖 plat_enroll_map + biddingandsellingsupplier 接口偶发漏行(分页抖动)→ 快照从 25 家回退到 24 家 → 该窗口内生成的报名总表把博涛标成"平台外"(同时名册位置写 ⏳待补空行 = 同一企业两行)。**历史疑问"企业数 25↔23↔21 波动"= 同一根因**。

## 2. sync_plat_enroll.py v2 防回退(已部署)

```python
# 主流程:拉全量 → 对比上轮(prev = 旧文件 projs 的企业数) → 有减少则 sleep(30) 整轮重拉 → 覆盖写
shrunk = [k for k, v in projs.items() if k in prev and v["企业数"] < prev[k]]
if shrunk:
    time.sleep(30)
    projs = {}; pull_all(projs)   # 第二轮为准(两轮并集语义:重拉结果仍少才接受减少)
```
- 拉取逻辑抽成 `pull_all(projs)` 以便重拉;窗口与 updated 字段统一 `_bjnow()`(北京时,原版 datetime.now() 主服 UTC 又偏 8h)
- cron `*/30 * * * * cd /opt/v6 && python3 sync_plat_enroll.py` 原样兼容
- 验证:首轮 419 项目、updated 北京时、无 shrunk 触发(正常路径);漯阜 A 名册 25 家含博涛
- 真撤报名:平台真移除需连续出现于两轮重拉才接受,最多滞后 1h

## 3. 类级规则(本轮沉淀,重复踩坑)

- **主服时区=UTC**:跑在主服/海外机的任何脚本,凡与平台时间戳(bidStarttime/regEndtime/sellEnddate,北京时)比较,先 date 确认;统一 `_bjnow()`(gen_gap_projects 已修,sync_plat_enroll v2 已修)。_ent_full 文件 mtime 来自国内采集机(UTC+8)= 北京时可直接比;跨机时区不一致要逐台确认。
- **任何"全量覆盖型"状态快照文件必须防回退**:平台接口偶发漏行/分页抖动会让权威数字倒退,污染下游展示与导出(CSV 平台外假象、按钮数字波动)。通用模式:对比上轮 → 减少则重拉确认 + 并集兜底。
- **数据差异先实证再解释**(用户对"平台应该最全"的质疑是对的):排查顺序=①两边原文 repr 对比 ②快照时间线(产物 mtime vs 源文件 updated)③重生成复现。不要照代码注释猜语义。
- 报名总表 CSV 位置:`/data_pool/汇总/报名总表_<projCode>.csv`(不在项目目录);index 条目字段名是 `projCode`(不是 code),按 code 找 pid 用值扫描 `"ON0..." in str(vals)`。
- bot 项目详情点"📥 企业包件表"可动态重生成 CSV(fmt_ents_csv),修复后对存量 CSV 重生成即可消除假"平台外",无需动历史数据。
