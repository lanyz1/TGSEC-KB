---
name: 95306-data-collection-ops
description: 95306数据池/菜单B/bot运维与菜单样式对齐, 触发词 95306 菜单B 菜单样式 补漏 采集机 采集端 机队体检 代码漂移 数据池 bot 面板对齐 计数口径 家数对不上 池内 平台
---

# 95306 数据采集/补漏/展示系统运维

12台国内采集机(SHARD 0-11)→ 主服 `207.57.167.92`(`ssh -i ~/.ssh/v6_master_key -p 12971`;旧卡写的 128.241.245.73 **实测已不通,勿再用**):/data_pool → pix_bot_server 菜单B。

**★编队名单唯一权威 = 主控 `/opt/v6/jumpers.json`**(`collectors[]` = `{shard,name,ip,port,pwd}`;`conf/master.ini` 的 `jumpers` 键指向它)。**一律现读,不按记忆/旧卡写死** —— 台会换机、名会换(曾见 杭州 sh1 → 宁波 sh1)、**端口有非标**(宁波 `114.66.40.208:25175`,其余 22)⇒ 逐台 ssh 必须按注册表里的 port 走,写死 22 会静默漏台。**读它只取 name/ip/port:`pwd` 字段是每台明文 root 口令(而 conf 注释却写「无凭据」)⇒ 一律不打印、不进报告**(实测 key 认证全通 ⇒ 可建议删 `pwd` + 文件收 600,动生产配置须用户点头)。`[relay] hosts` 是 8515 中继出口(4 台),**不是编队表**。现役快照(仅便利,以文件为准):沪0 `8.133.188.178` / 甬1 `114.66.40.208:25175` / 穗2 `8.138.236.124` / 蓉3 `47.108.152.60` / 沪4 `8.133.212.134` / 蓉5 `47.108.173.230` / 青6 `47.104.139.212` / 深7 `47.107.124.62` / 京8 `39.96.146.230` / 汉9 `47.122.107.121` / 蒙10 `8.130.150.18` / 源11 `47.115.204.175`。

<!-- split-index -->

## Section index

- [结构/静态体检三件套(改完代码必跑)](references/split-01-section.md)
- [采集率读数(三口径,回答"采集率多少/有没有提高")](references/split-02-section.md)
- [缺口「可采性」判定(别把口径差当漏采) + 审核状态口径](references/split-03-section.md)
- [发布/割接链路(本机→主控→12台,逐步停手点)](references/split-04-12.md)
- [参考文件](references/split-05-section.md)
- [采集端改动与验证纪律（每次改采集端/名单必走）](references/split-06-section.md)
- [缺口闭环的唯一杠杆](references/split-07-section.md)
- [数据流与权威基准](references/split-08-section.md)
- [⚠️ pack_map schema 契约(写前必读)](references/split-09-pack-map-schema.md)
- [stage 判定(菜单B 分组)](references/split-10-stage-b.md)
- [公告全文补拉](references/split-11-section.md)
- [★ 漏采补采机制(手搓版现役 —— 用户问「现在的漏采补采机制是什么样」先读这份)](references/split-12-section.md)
- [orch8b 补漏(手动触发/排障) ★老生产口径,割接后新链路见上节](references/split-13-orch8b.md)
- [漏采判定与定向补采(用户问"是不是漏采了"时)](references/split-14-section.md)
- [★ 报名名单缺口("企业 49/51"类)判定与账号映射修复](references/split-15-49-51.md)
- [★ 手搓重写版(`D:\95306c`)与离线自测铁律](references/split-16-d-95306c.md)
- [★答「采集端(机队)现在正常吗」= 四层证据,不许拍胸脯](references/split-17-section.md)
- [通用部署坑(本系统多次踩)](references/split-18-section.md)
- [菜单B 推送抖动取证(推送明细与表格"相位相反")](references/split-19-b.md)
- [★ 冷却模型 / 产能诊断 / 外部报告裁定](references/split-20-section.md)
- [机队实体台账 / 续费取证(用户说"续费"时)](references/split-21-section.md)
- [★ 菜单/文案样式对齐(重写版 bot ↔ 老正本)](references/split-22-bot.md)
- [★ 计数口径：行数 ≠ 家数（客户问「池内 19 / 平台 12」这类对不上时先读本卡）](references/split-23-19-12.md)
- [bot 修改部署流程](references/split-24-bot.md)
- [AI 数据助手(/ai)](references/split-25-ai-ai.md)
