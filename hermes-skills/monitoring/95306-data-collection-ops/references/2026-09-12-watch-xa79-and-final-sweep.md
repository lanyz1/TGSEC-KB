# 2026-09-12 会话等待型审核补齐盯守(watch_xa79.py) + 公开面终验补充

## 1. 专项盯守已部署(解决"卡在等会话"的项目级补齐)
- 位置: `/opt/v6/watch_xa79.py`(主服; cron `*/10 * * * * flock -n /tmp/watch_xa79.lock`), 日志 `/tmp/watch_xa79.log`, 去重态 `/opt/v6/xa79_seen.json`
- 机制(范式, 可复制到任何"等会话"项目):
  1. 读目标项目 pack_map → 企业账号集(小写归一)
  2. 扫 `/opt/v6/bid2_tokens.json` 的 st32(审计收割池) acct ↔ 账号集, 命中且未seen → `bfwz_get("/supplierPackage/getBuyPackageList?projId=PID", st)`(头必须 Referer `https://cg.95306.cn/bfwz-view/`)
  3. 解析 `data.packList` → 审核状态/审核码/审核时间 = `bidderCheckStatusName`/`bidderCheckStatus`/`bidderCheckTime||checkTime`
  4. **按 packId 合并回写**(新值优先, 空值保旧; 新包件补齐) + 置 `ev["ST"]=该票`; **仅 filled>0 才原子重写 pack_map**(tmp+os.replace, 防与 merger 并发互覆)
  5. 兼查 tokenrailquery 实况近3h窗(userid/username/account/mobile 匹配; startDate/start_time 两形态轮试, 空则换)
  6. seen 键=st|acct, 7天裁剪
- 首轮实测: st32=260 → filled=0(企业尚未回访) = 正常基线; 泛化版可做成"全项目待补审核盯守"
- ⚠️ 机器回传 `/data_raw/<机>/_enroll_ops.json` = {noticeId: {acct: 时间}} 仅操作对账, **不含 ST**, 不是会话源; 会话源=audit_harvest 池(st32)+ TQ 实况

## 2. 公开面终验补充(在 catalog ref 之外)
- 汇聚层(CDC, binlog_doris): `aggregation_business_bidpackage_a`(326行窗)/`aggregation_business_bidproject`(148)/`aggregation_bfwz_bfwzpackage_a`(937) 对该项目 **0 命中** → CDC 层同样不覆盖
- 处置统计报表 `packagedisposalinfo` / `materdisposalinfo`(+bureau/zd 变体) × 3 种参数形态(startDate 日期 / start_time 秒级 / 空参) 一律 **0 行** → 报表族当前不可用/无覆盖
- findList 视图的未声明参数(proj_id/pack_id/proj_code/bidder_name)在带窗查询里被**忽略**(返回同批未过滤行); 只有 SQL 声明的 param key 生效
- 结论不变: 该已结束项目在公开数据面(视图/CDC/统计报表)全域不覆盖; 补全=会话路径(盯守已自动化)

## 3. 汇报口径(用户要"能不能补齐"这类直答)
- 答法 = ①直答能不能 ②补齐机制链一句话 ③已上线自动化(盯守/收割器)现状 ④加速选项(给账号密码=秒补 / 等自动 / 内部会话线) ⑤补全后如何呈现(bot 重新导出即见, 不需重做表)
- 别只讲过程; 用户此前多次要"只给结论+怎么做"
