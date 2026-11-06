# 95306 报名误报筛选:buyed 证据矩阵(2026-09-01 实装)

症状:「企业报名缺口」大量误报——审计 enroll_ops 显示企业报名,实际只是**打开了报名页没提交**。用户问题:「打开报名页但未提交成功 这种可以筛选出来不要误报吗」。

## 核心事实(代码级+接口级实锤)

1. **审计日志不记提交接口**:拉审计 500 条,URL 只有两种——`notice/redirectEnrollUrl`(72 条,打开报名页)和系统任务(428 条,无账号)。**没有任何 submit/save/apply 事件** → 审计侧永远区分不了"打开"和"提交"。
2. **redirectEnrollUrl 事件形态**:`det = "URL:...redirectEnrollUrl?noticeId=<36位UUID>, 参数:{}, 调用结果:{data: https://cg.95306.cn/business-view/#/...}"`——调用结果是前端跳转 URL,不带 serviceTicket,不带 projId。
3. **readNoticeInfo 无报名企业字段**(字段列表实锤:projId/projCode/notTitle/bidStartTime/... 无企业列表、无报名数)→ 公告详情拿不到已报名名单。
4. **enroll_ops 只记 acct+time,不记 ST** → 存量缺口无法直接关联 ST。

## 权威判定:业务侧提交证据

真实提交的企业,用**它自己的 ST** 调:

```
GET /business-proxy/business/supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02&pageNum=1&pageSize=50
Headers: Referer=https://cg.95306.cn/bfwz-view/ + Authorization=<ST>
→ data.result = 该企业已报名(购买)的项目列表;非空 = 真提交;空 = 未提交(或没报任何项目)
```

## 全量历史清洗(存量)

**历史 ST 时效实测远超 30 分钟 TTL**:8/30 的票 9/1 仍能过 user/info + buyed(222 个 ST 全扫,只有 4 个 ST 有效有数据)。存量缺口因此可用全量扫描清洗:

1. 遍历 st_times 全部 ST:`user/info` 拿 `dwhz`(单位名);`buyed` 拿已报名项目列表
2. 构建 `_buyed_matrix.json`:`{ST: {"acct": "", "unit": "丹阳市江腾再生资源有限公司", "projs": [{projId, name}, ...]}}`
3. 与缺口交叉:项目在矩阵中 = 该项目有真实提交(真缺口候选);不在 = 该账号只打开页面(疑似,不告警)

实测:222 ST → 4 家有报名(丹阳江腾 4 项目/保定祥贺 9/保定苒策 7/保定翔众昊 1)→ 18 个项目有提交证据;263 条缺口只有 3 个账号命中项目证据,251 条无证据。

## merger 分流(账号级,已实装)

```python
# 证据集:projId → {提交单位}
_evid_units.setdefault(_p["projId"], set()).add(str(_m.get("unit") or _s[:8]))
# 账号→单位映射:遍历数据池所有 pack_map enterprises(账号字段优先,fallback key)
# 分流:
if pid in _evid and _acct_unit.get(acct, "") in _evid_units.get(pid, set()):
    gaps["企业报名缺口"].append(...)   # 真缺口,告警
else:
    gaps["疑似仅打开页面"].append(...)  # 不告警、不进推送签名
```

**必须账号级,不能项目级**:项目有他人提交 ≠ 该账号提交(案例:Xiongyao1993 打开 88e0d82c,项目证据是保定祥贺——Xiongyao1993 无提交证据,项目级判定会误留,账号级正确归疑似)。

## 真漏采补采(实装案例)

矩阵命中但 pack_map 缺失的企业(如 Ajt3211→fc0404aa,丹阳江腾真提交 9 包件没采到):
- 用矩阵 ST 调 `getBuyPackageList?projId=<完整36位UUID>` 拉包件
- **写 pack_map 的企业 key 必须用缺口账号**(Ajt3211),不是单位名、不是 ST 前 8 位——merger 按 `账号 or key` 匹配
- 目录是**完整 36 位 UUID**,检查时别用前 8 位

## 坑(全部实踩)

1. **API 路径缺前缀假阳性**:`https://cg.95306.cn/user/info` 返回空 dict,校验 `j.get('success') or j.get('code') is None` 在空 dict 时 `code is None` 为真 → 误判"✅有效"。**必须带 `/business-proxy/business` 前缀**,且校验要看 data 非空。
2. **Python for 循环变量泄漏**:`for s0, m in bm.items()` 结束后再引用 `m` = 最后一个元素 → 补采记录账号/单位写错。补采循环里必须用循环元组的值,不许复用循环变量。
3. **4 台采集机缺口 ×4 重复**:每台采集机各自存 `_enroll_ops.json`(同一审计源),merger 循环 RAW_DIR 逐台处理 → 同一条缺口出现 4 次。用 `(pid, acct)` seen 集合去重。
4. **远程补丁锚点要 grep 精确文本**:采集机上 log 行插在 json.dump 与 except 之间,锚点少一行就断言失败。先 `sed -n` 抓实际文本再写 old_string。
5. **merger 手动跑被 flock 静默退出**:cron 实例持锁时手动运行 `sys.exit(0)` 无任何输出 → 等下一轮 cron,或直接对数据文件操作(如把映射直接写主服 notices_map.json,不等 rsync)。
6. **readNoticeInfo 反查需完整 36 位 UUID**:gaps 只记 8 位前缀;完整 ID 从 `_enroll_ops.json` 的 `notice:` 前缀 key 提取。30 个 notice 全反查成功,仅 1 个(7fd26400)要跨采集机找(杭州的 enroll_ops 有)。

## 结果

263 条企业报名缺口 → 0 真缺口告警 + 69 条"疑似仅打开页面"(不告警)+ 1 条真漏采补采(9 包件);待确认缺口 187 → 0;notices_map 72 → 905 条自动维护。
