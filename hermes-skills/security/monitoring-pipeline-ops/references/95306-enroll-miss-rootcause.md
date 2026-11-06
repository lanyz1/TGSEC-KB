# 95306 报名漏采根因与补采(2026-09-01 实锤)

症状:「菜单B 已拦截竞价未结束」项目报名企业/包件详情不增加;审计 enroll_ops 显示有企业报名,数据池 pack_map 却查无此人。

## 三层根因(全部代码级实锤)

1. **collector.py `if st in seen: continue`(约 630 行)吞掉已见 ST 的报名操作**
   - 企业 ST 在更早轮次出现过(seen_st 永久去重),报名时同 ST 再次出现在审计 → 直接跳过
   - `enroll_st` 延迟补拉队列入队逻辑(约 650 行)在 seen 检查**之后** → 已见企业的报名永远不触发补拉
   - 对比:报名时是新 ST 的企业(如 ACE666)走完整流程被采到;老 ST 企业(Ajt3211)漏采

2. **notices_map.json 是 8/30 一次性静态文件(72 条),没有任何代码更新它**
   - 报名审计只记 `noticeId=xxxx`(不记 projId);merger 靠 notices_map 翻译成 projId
   - 缺映射 → merger 归入「待确认缺口」→ **不告警、不处理、不显示**
   - 修正后:待确认缺口 300 条 → 重跑 merger 后 187 条,企业报名缺口 0 → 80 条归位

3. **merger check_gaps 只写 gaps.json 告警,不自动反查补采**
   - getBuyPackageList 是单企业视角,每个 ST 只能查自己报名的项目
   - 8515 快照(投标人表)不含报名期数据,救不了报名漏采

## 补采方法论(已验证可跑)

```python
# 读采集机 /tmp/v6_state.json 的 st_times 全票
# 逐票 GET /business-proxy/business/supplierPackage/getBuyPackageList?projId=<目标>
#   Headers: Referer=https://cg.95306.cn/bfwz-view/ + Authorization=ST (带 Referer 否则 500)
#   sleep 0.4-1s 防 WAF;非空返回 = 该企业报名了此项目 → 拉完整包件
# 命中 ST → user/info 或 getSupplierPackageList?statusGroup=buyed 解出企业身份
# 写采集机 /tmp/targets/<projId>/pack_map.json → 等下一轮 rsync + merger 合并
```

- ST 过期(401)不可用;审计窗口滚出后无法找回报名 ST(按账号过滤审计 0 条 = 已滚出),只能等新票
- 补采后 pack_map 是覆盖写,先读旧内容合并再写,别丢已有企业(踩过:补采 Ajt3211 覆盖 ACE666)

## 误判教训(重要)

**notice→projId 映射可能错!** 4b7aa2c2 一度被公告清单(queryBusinessNoticeList)映射为乌鲁木齐 d74a341a,实际是十堰 5d75257d 的公告。实锤方法:**报名时间戳交叉核对**——ACE666 在 enroll_ops(notice:4b7aa2c2)的报名时间 `2026-08-31 21:32:32` 与 pack_map(5d75257d)逐字一致 → 同一个公告。别只信映射表,时间戳逐字一致是硬证据。

## 修复方向(代码级,2026-09-01 未部署)

1. collector:enroll_st 入队逻辑移到 seen 检查之前(已见 ST 的报名也强制补拉)
2. merger:notices_map 自动维护(每轮从公告清单反查刷新,替代静态文件)
3. merger:缺口自动反查补采闭环(gaps.json → readNoticeInfo → projId → 补采)
4. bot:企业报名缺口(gaps.json 80 条级)推送告警
