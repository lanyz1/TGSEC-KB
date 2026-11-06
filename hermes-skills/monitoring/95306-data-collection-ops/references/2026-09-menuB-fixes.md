# 2026-09 Menu-B 抖动/截断/断链 修复记录

## 1. Menu-B "审核通过 23↔21" 假推送 — pack_map 原子写

- 症状:bot 每 3min 推 "审核通过 23 → 21 → 23" 循环假变化
- 根因:orch8b(cron 5,35,8台并行收结果)与 merger 直接 `open(pmp,"w")` 非原子写 pack_map.json;bot mb_monitor_loop 读中半写文件 → json.load 抛错 → 该项目贡献被零化 → 计数掉 2,写完恢复 → 循环
- 修复:全部写点 → `_tmp = pmp + ".tmp"` + `json.dump(...)` + `os.replace(_tmp, pmp)`(orch8b 汇总段 L~197、merger 各写点)
- 附带修复 pix_bot_server.py L3925:`for pid, (op0, cu0) in diffs[:4]` → `for pid, op0, cu0 in diffs[:4]`(真审核变化会崩 detail 推送);验证:十堰车务段 ✅4→6 明细推送成功
- 教训:文本级替换 patch 会毁缩进(缩进空格被保留错位)→ 用整段正则/整文件替换;远程改代码用 SFTP 上传脚本再执行,勿在 ssh 命令串嵌 python(引号嵌套炸)
- 教训:观察器 grep 只匹配关键词 → 用户操作行不匹配 → 输出看似静止重复,实为历史日志。核实用 ps lstart vs 文件 mtime + 全量日志时序

## 2. AI 工具截断误导("平台18家=采6+待补10",缺 2 家)

- 缺的 2 家 = 名单第 17/18 位(成都收荒匠、四川和记鑫城),被 `pending[:10]` 切掉
- 修复模式见 ai-query-assistant.md「截断误导 LLM 铁律」:total 字段 / {total,rows} 包装 / 12000 回填上限 / SYSTEM 规则 15
- 同轮修复:ents 账号键+单位键并存重复计数(去重)、audit_status 30→100
- 新工具 coverage():"问数据全不全/漏了多少/吻合吗"→ 返回 {proj, gap_proj, gap_ent, rows};注册 TOOLS+FUNCS+SYSTEM 路由

## 3. 补漏双通道断链(merger 退休后审计联动停摆 28h)

- 断点① gen_gap_projects.py 不在 cron(gap_projects.json 停在 09-02 03:00)
- 断点② 其输入 gaps.json"企业报名缺口"由已退休 merger 生成 → 恒 0
- 修复:gen_gap_projects.py 新增 `_plat_diff_ent_gaps()`:plat_enroll_map vs pack_map 差集(自算,覆盖 报名中+竞价未开始待竞价),企业名→账号从其他进行中项目 pack_map 映射;cron 注册 15,45
- 验证:58 项目/129 账号缺口复活,推送 8/8 台;collector 60s 重读 gap_projects.json 即生效
- 物理边界:纯新人(任何项目都没采到过账号)无法转账号级 → 只靠 orch8b token 轨迹窗口

## 4. 菜单B 报名总表(用户要的融合视图)

- 平台权威名单做基底(保持平台顺序)一行一家;我方采集数据就地填充(时间/账号/手机号/逐包件);未采 ⏳ 留原位;平台名单外采集追加表尾;CSV 加"数据状态"列
- 实现:pix_bot_server fmt_project_ents/fmt_ents_csv 重写 + proj_menu_buttons 两按钮合并为 "📋 报名总表(平台N·采M)"
