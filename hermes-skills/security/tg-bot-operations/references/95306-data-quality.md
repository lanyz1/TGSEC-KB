# 95306 数据池质量治理 — 实战案例(2026-08-29 会话)

## 症状与用户反馈

- "数据池还没补":部分项目没有数据
- "最新的,又出现不显示的问题了"
- "还是有简称"(企业名简称/全称混杂)
- "不同的文件,内容接口可能不同,导致内容有差异"(用户 VOKE 的猜测,正确!)
- "信息有,但有时候会产生幻觉"(同一项目时有时无)

## 根因:企业数据获取机制

```
getBuyPackageList(projId, st) 只返回"该 ST 企业"在该项目的报名包件
ST 来自审计日志 redirectEnrollUrl(报名操作),TTL 30 分钟
→ 能拉到多少企业 = 审计日志里最近出现的、且报名了该项目的企业数量
→ 报名截止早的项目(如武汉局69次 8/19 截止)所有企业 ST 已过期 → 实时拉不到 → 企业 0
→ 不同时刻审计 ST 不同 → 同一项目时有时无 = "幻觉"
```

## 数据源分层(每个数据文件的语义)

| 数据源 | 内容 | 局限 |
|---|---|---|
| 实时 getBuyPackageList | 当前 ST 企业的报名包件(pack_id 级) | 需活 ST;只覆盖当天活跃报名企业 |
| 8515.csv(26,977 条) | 官方报名快照:proj_name/proj_code/proj_business_type/bulletin_reldate/bidder_name/un_social_cr_code/buy_time | 部分项目只有公告行(bidder_name 空 = 真无企业数据);不含快照后新报名 |
| 08文件(615,267 条,19列) | 已结束项目全量 企业→pack_id→审核状态 | 不含进行中项目 |
| 供应商主数据(369,710 家) | 官方工商全称/手机/法人/信用代码 | 只有注册信息 |

**8515 补导方法**:按 proj_code → index 中 live projId → 合并进 pack_map(项目级:包件空 + 信用代码字段)→ 更新 enterpriseCount。一次全量补导 27 项目/401 条。

**8515 空行判定**:只有 bulletin_reldate、bidder_name 为空的 = 公告行,不算企业数据。这类项目要么真没企业报名(竞价前 1-2 天才集中报名),要么是重复公告(同一 projCode 两个 projId,如沈阳82次 08:30 真场次 vs 09:30 重复)。

## 企业名归一化

- dwhz(实时)= 企业注册时自填,可能是简称(河南凡欧/嘉楠兴)
- 官方全称在供应商主数据文件名里
- 归一化算法:
  1. 去后缀提取核心名:后缀表 = 再生资源回收有限公司/再生资源有限公司/环保科技有限公司/机械设备有限公司/商贸有限公司/物资回收有限公司/回收有限公司/科技有限公司/有限公司/公司(注意顺序:长后缀在前)
  2. 构建 核心名→全称 映射(启动时一次遍历 369K 文件,缓存;**禁止每企业每次遍历 369K**)
  3. 精确命中 → 包含匹配兜底(len>=3,k in fk or fk in k)
  4. merger 合并 pack_map 时调用(防复发);bot 展示层再兜底一次
- "?" 空名:按账号查其他项目同账号真实名补全
- 同账号多条记录:合并,包件按 packId 去重

## 诊断流程(企业 0 项目)

```
1. index enterpriseCount vs pack_map 实际 len(enterprises)
2. 8515.csv 按 proj_code 计数
3. 看该行 bidder_name 是否有值(空 = 快照真无数据)
4. 区分:未报名(等竞价前报名高峰自动捕获)/ 重复公告(同 code 两 projId)
```

## 分类管线(classify_all)

- merger 合并后调用 → /data_pool/分类/{按路局,按物资,按状态,按时间}.json + 分类总览.json
- 每类存项目摘要:pid/name/code/bid/packs/ents/live(每类上限 500)
- 状态:live 用 bid_status.json;历史用 index status(14=已结束,22=流标)
- 时间:今日/明日/未来7天/本月/历史
- bot:分类浏览 4 维菜单 + 分页(catopen/catpage 回调)

## 运维坑补充

- **paramiko exec_command 里 heredoc 不可靠**(`python3 << 'EOF'` 静默失败)→ 一律 sftp.put 脚本再执行
- 批量长任务:setsid nohup 后台 + 轮询日志到 DONE;输出为空先查进程/日志文件是否存在
- 时区:采集机 UTC / 主服 UTC+8,health gap 计算要 ±8h 容错
- 分类/正则相关函数要 import re(merger 顶部 import 缺 re 会 NameError,易漏)
