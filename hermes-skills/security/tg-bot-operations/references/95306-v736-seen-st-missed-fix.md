# 95306 v736 — seen_st 吞票漏采根治(2026-09-01)

## 背景

数据池出现漏采:十堰 5d75257d 项目(报废空调),审计日志显示企业打开报名页,
但 pack_map 里没有该企业。用户要求"全面修复,全部执行完"。

## 漏采三层断裂(实锤)

1. **seen_st 吞票**:collector.py `for t in proc:` 循环里 `if st in seen: continue`
   在 `enroll_st` 补拉队列入队**之前**。企业此前登录过 → ST 已进 seen →
   后续报名操作(同 ST 再次出现于审计)被静默跳过 → 补拉队列永不入队。
   同时 `proc` 名额截断(新票 15 + 重试 3)也会让排后的报名票进不了处理。
2. **静态映射表**:notices_map.json 是 8/30 一次性生成的 72 条静态文件,
   **没有任何代码更新它**。报名审计只记 `noticeId`(redirectEnrollUrl 跳转不带 projId),
   merger 把映射不到的记录归"待确认缺口",且该分类**不计入 new 变化 → 不告警不处理**。
3. **窗口盲区**:竞价项目不在 48h 监控窗口 → 主循环不查。

## 修复(已部署 4 台采集机 + 主服 merger)

### ① collector.py:enroll 入队移到 seen 检查之前(根治吞票)

```python
# 在 proc 循环前,遍历全部 tickets(不受 seen/名额限制):
for _t in tickets:
    if _t.get("enroll") and _t["st"] not in state.get("enroll_st", {}):
        state.setdefault("enroll_st", {})[_t["st"]] = {
            "acct": _t["acct"], "tm": _t.get("time", ""),
            "at": now_ts.strftime("%Y-%m-%d %H:%M:%S"), "tries": 0}
```

删除 proc 内旧的入队块(位置在 `if st in seen: continue` 之后)。

### ② 采集机:公告映射表自动维护(每 30min)

- 用最新 ST 调 `POST /business-proxy/business/notice/queryBusinessNoticeList`
  body:`{"projType":"02","notTitle":"","noticeType":"01","dateType":"","pageVo":{"pageNum":pg,"pageSize":100},"isjtgsCode":0,"validOr":"1","orderField":"","orderType":"","onweb":"","jointSaleType":"","noticeStatus":""}`
- 分页 ≤8 页,提取 `{id: projId}` 写 `/tmp/targets/_notices_map.json`(随 rsync 回主服)
- state 里 `notices_map_ts` 控制 1800s 间隔

### ③ merger.py:notices_map 合并自愈(零请求兜底)

- 加载数据池 `notices_map.json` 后:
  1. 遍历 `/data_raw/<机>/_notices_map.json` 合并
  2. 遍历 `/data_pool/<projId>/包件清单.json` 提取 `公告id→projId`(零请求!)
- 变化即写回 notices_map.json → "待确认缺口"自动归位为"企业报名缺口"→ 触发 bot 告警
- 实测:72 → 868 条

## 关键验证/定案手段

- `GET /business-proxy/business/notice/readNoticeInfo?noticeId=<uuid>` → 返回
  `data.bidNoticeResultVo.projId` 是**公告归属定案唯一权威**(比 enroll_ops 时间戳推断可靠)。
- 实锤:4b7aa2c2 → d74a341a(乌鲁木齐),映射表本来就对;enroll_ops 里 ACE666 的时间戳
  与 5d75257d pack_map 一致只是巧合(同一批审计日志时间)。

## 语义陷阱(重要)

- **enroll_ops 记录"打开报名页"(redirectEnrollUrl 跳转),≠ 提交成功**。
  用它判断"谁报名了"会高估;用它判断"缺谁"才是安全的(缺口=打开了报名页但 pack_map 没有)。
- 时间戳逐字一致可能只是审计日志同一处理批次,不是同一操作。

## 未完成收尾(交接)

- 待确认缺口 187 条 = 30 个 notice 不在公告清单(近7天/02类型)里(b8b17a40 24家等),
  需验证公告清单接口返回是否覆盖全部公告,或对 30 个 notice 逐个 readNoticeInfo 反查。
- 上海机 `_notices_map.json` 是补丁前遗留文件(796 条),需确认补丁后每 30min 是否更新。
- 四台采集机已全打 seen_fix + 映射表补丁并重启 active。
