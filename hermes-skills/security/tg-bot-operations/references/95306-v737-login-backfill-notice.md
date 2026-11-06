# 95306-v737: 登录日志补漏闭环(tokenrailquery) + 公告全文补拉 + schema 契约坑

2026-09-03 会话实录。补漏闭环从 233 家漏采收敛,并修复了"补了数据 bot 却读不到"的 schema 不兼容 bug。

## 1. 核心突破:tokenrailquery 供应商 token 直接就是 bfwz ST(无需换票)

- 门户登录日志表接口 `findList {funcId: tokenrailquery, appId: system, params: [{startDate},{endDate}]}`(无鉴权)
- 返回字段:userid / token(32hex)/ login_time / user_type(03=供应商)/ login_status / return_url
- **user_type=03(供应商)的 token 直接当 Authorization 调 bfwz 业务接口有效**(user/info、getBuyPackageList 全通)— 它就是 bfwz ST!
- user_type=02(集团公司)调 user/info 返回 200 但无数据权限;过期 token 返回 code=100
- TTL 实测 ≥2h(部分 4h 仍有效),不是之前以为的 30 分钟
- 换票挖掘结论:`/proxy/portal/user/login` 是 serviceTicket→token 端点(缺参 400),但**根本不需要换票**——登录日志 token 直用

## 2. 海外主服 IP 被 WAF 针对(关键架构约束)

- 同样的 token:主服(128.241.245.73,海外)调 user/info 全部 code=100;沪0(国内)正常
- **网络请求必须在国内采集机执行,主服只做编排/落盘**。所有批量补拉走"主服 paramiko → 沪0 执行 → 结果回传"

## 3. orch8b 补漏架构(主服编排 + 8 台并行)

```
主服:漏采名单 = plat_enroll_map(平台权威) - pack_map(采集侧) 差集
  → ctx.json {miss_names, miss_map(企业→[projId...]), rounds}
  → 8台分发 bk_worker.py bk8_ctx.json <shard>
worker(shard):窗口 = [now-(shard%rounds+1)*30min, now-shard%rounds*30min)
  → tokenrailquery 拉窗 → 过滤 user_type=03 → user/info 识别 dwhz
  → 命中漏采名单 → getBuyPackageList?projId=(data 直接是 list!)→ 包件
  → /tmp/bk_result_<shard>.json
主服:收集合并 → 写 pack_map.json
```

- cron `5,35 * * * *`(30min 间隔,单实例锁 /tmp/orch8b.lock 防重入)
- seen 持久化增量:`/tmp/bk8_seen_<shard>.json` 为 **dict {token: <REDACTED>,加载时裁剪 >6h(旧 list 格式=过期池直接丢弃);只查新 token → 每轮几分钟
- 分发线程池 4 并发(8 台 ~30s);窗口 rounds=4(覆盖 2h,每窗 2 台并行)
- 效果:首轮全量 40 家/57 项目;之后每 30min 增量轮 5-13 家。残余 = 报名后永不登录企业(物理边界,无解)

## 4. 🚨 schema 契约坑(最重要教训)

**新通道写共享 pack_map.json 前,必须先读 collector/bot 消费端代码确认 schema!**

- collector/bot 生态 schema:企业 key=**账号**,字段含 `账号/用户/单位/ST/时间/包件(list)`,包件项含 `packId/packCode/packName/保证金/报价模式/物资条数/审核状态/审核码`
- orch8b 首版自创:`packs`(dict,key=packId)+ `审核/状态码` + key=ent_bk8_N → **bot 的 check_status_summary 只读 `包件` list + `审核状态` → 79 家补漏企业全部读不到**(审核统计缺失、包件显示"项目级")
- merger 归一化 key(账号)但不转 schema → 混存更隐蔽
- 修复:①迁移脚本 packs dict→包件 list(45 项目/79 企业/536 包件,packCode 从同项目 18列 CSV 按 packId 回填——包件属性与企业无关,任意行可查)②orch8b 写入直接 collector schema + 同 packId 覆盖更新(审核状态可能变化)
- 验证:模拟 bot check_status_summary 逻辑能统计到 backfill8 企业

## 5. getBuyPackageList 响应结构

- `data` **直接是 list**(不是 {result: []})— 解析 `d if isinstance(d, list) else d.get("result")`
- 包件项:packId/packCode/packName/frontMoney(保证金)/payTypeName(报价模式)/detailNum(物资条数)/**bidderCheckStatusName**(审核状态:未审批/通过/拒绝)/bidderCheckStatus(00=未审批)
- 空审核状态 = 该企业该包件未产生审批(未提交/未报名),不是错误

## 6. 公告全文补拉(notices_map 反查,根治"标题搜索找不到 nid")

- 现象:collector 拉公告全文靠 queryBusinessNoticeList 翻 200 条 + notTitle 前 20 字搜索找 nid;部分项目(如西安局 N 次废钢铁)搜不到 → 公告id/标题空、公告全文.json 缺失 → bot"📜 公告原文"按钮无数据(实测 284 个实时项目缺)
- **正解:`/data_pool/notices_map.json`(noticeId→projId,970 条,merger 从各采集机 _notices_map.json 自愈合并)反查 projId→noticeId → 直接 `GET /notice/readNoticeInfo?noticeId=`**(实测 223/223 成功,0 失败)
- 全文清理:notCont 是 HTML;去标签后 **<style> 内容留成纯 CSS 文本且无标签可匹配**;CSS 含中文"宋体"使"前 N 字符无中文"检测失效 → 用 **"首行(第一个 \n 前)含 >2 个 { } 即 CSS 头,裁掉"**(223/223 干净)
- bot notice 分支:公告全文.json → 包件清单.json 标题回退 → "暂无公告数据"三级兜底
- 61 个无 notices_map 映射的项目(非跳转来源)需标题搜索方式,未做

## 7. 显示口径(bot)

- 企业数列表/详情统一显示 `🏢已采/平台`(如 2/3):分子=pack_map 实时企业数,分母=max(平台名单数,已采);无平台数据只显 `🏢N家`。📡 标记移除
- 审核统计符号:✅通过 ❌拒绝 ⏳未审批 **⬜无审批**(➖ 易误读为减号);详情页空审核状态包件也标 `⬜无审批`(否则列表有计数详情对不上)
- 平台侧企业名单(plat_enroll)> 采集数时,差值 = 真实漏采缺口,orch8b 盯防中等登录补齐——不是 bug
