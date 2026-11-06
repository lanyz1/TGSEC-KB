# 95306 session25 — 竞价日实战:审计盲区、join/buyed 语义、WebSocket 竞价室、数据平台下线

日期:2026-08-31(周一竞价日)。v6 系统 4 采集机 + merger + bot 全链路运行中。

## 1. 审计盲区完整清单(实测确认,决定拦截能力边界)

| 操作 | 审计? | 证据 |
|---|---|---|
| 报名跳转 redirectEnrollUrl | ✅ 审计,调用结果 data 里带 serviceTicket | 100+ 条/天 |
| 报名提交 participateInProject | ❌ 不审计 | 0 条 |
| 查看包件/审核 getBuyPackageList / getSupplierPackageList | ❌ 不审计 | 0 条 |
| mypackage/checkStatus 页面 | ❌ 不审计 | 0 条 |
| 竞价室 business-bidding 网关(HTTP+WS) | ❌ 完全不审计 | 0 条 |

**推论**:审计 ST 只在"企业点报名跳转"时产生一次。跳转时报名可能未提交 → buyed 空 → 拉不到包件。对策 = **延迟补拉**:跳转来源 ST 入 `enroll_st` 队列,5/10/15 分钟(3 次)重拉 buyed+getBuyPackageList,成功即删。ST TTL 30min 内覆盖正常提交时序。

**竞价期完全盲区**:企业只进竞价室(WebSocket)操作 → 无审计 ST → 竞价中 packId 拿不到。报名期错过(采集机部署前)的项目,竞价日也只能拦截"竞价前登录 bfwz 查审核"的企业(大概率行为,非保证)。

## 2. join/buyed 接口语义(全量监控的正确来源)

- `getSupplierPackageList?statusGroup=join&bidType=02` = 可参与项目列表(报名中)——**全量监控目标源**
  - 字段含:projId/id/projCode/projName/bidStarttime/**sellEnddate(报名截止)**/bidEndtime/statusName/**projectAttendStatus(0=未参与)**/tipsMsg
  - join 全量约 96 个(8/31 实测),90 个未参与
- `getSupplierPackageList?statusGroup=buyed&bidType=02` = 该企业已报名项目——**审核状态+包件编号的唯一来源**
  - join 里点"参与"提交报名后 → 项目进 buyed → getBuyPackageList 返回 packId/packCode/bidderCheckStatusName
- 采集机目标发现 = selectSelfSellList(status 13/19/22)+ join 合并(join 优先级高,带 sellEnddate 直接落盘)

## 3. 竞价室 WebSocket 协议(已破解,待报名企业 ST 才能用)

```
wss://cg.95306.cn/business/msg/websocket/<enc1>/<type>/<enc2>
enc = base64(sm4encryptEcb(key, value)).replace("/", "jingjia")
key = (北京日期YYYYMMDD + "$e9s20@2o4u^r2")[:16]   # 每日变更
type: 00=竞价室(offer) 01=监视(monitorOffer) 02=监控(surveilOffer)
消息: JSON.parse(sm4decryptEcb(key, frame_payload))
msgType: heartbeat / offer / monitorOffer / surveilOffer
```

- radio = 当前选中包件 packId;URL 两个 enc 参数 = enc(radio) + enc(projId?)(c["a"]() 未完全确认)
- **连接需要"报过该包件的企业 ST"**:无权限 → 握手 101 后立即收到关闭帧 `\x03\xe8`(1000)。试过全部参数组合/鉴权头(cookie/Authorization/token/URL 带 ST)均无效——服务器只认报名企业身份。
- 纯 Python 最小 WS 客户端(原始 socket 握手+帧解析)可行;SM4 实现须过国标测试向量 `0123456789abcdeffedcba9876543210 → 681edf34d206965e86b3e94f536e4246`。
- HTTP 侧(bidRoom/packTable/initProjInfo,urlType=bidding → `/business-proxy/business-bidding`)请求 200 但响应密文解不开(y/g key 均乱码)——响应加密另有机制,未通;WS 才是竞价室实时数据通道。
- SM4 密钥体系(JS b775 模块):`p="memberserver"`(memServer 用 g=(v+"+memberserver")[:16]),`b="$e9s20@2o4u^r2"`(encryption 用 y=(v+b)[:16]);写接口 participateInProject 用 g(报告 8/28 验证过)。

## 4. 数据平台整体下线(8/31 重大环境变化)

bid_xxx_business23 系列**全部返回 0 条**(8/28 还能拉:项目 705/包件 2185/公告 2247/8515 124;8/31 全 0):
- bid_project_business23 / bid_package_business23 / bid_notice_business23 / bid_package_bidder_business23(8515)/ aggregation_bfwz_bfwzpackage_a(已结束包件表)
- **后果**:8515 快照增量失效(表清空)、已结束项目兜底通道失效、历史核对(gaps 2617/5360)只能依赖已入库数据
- **主链路不受影响**:审计 ST → bfwz 业务接口(business-proxy/business/*)仍然全活——实时拦截继续
- **教训**:数据平台的表随时可能整体下线/清空,能拉的全量尽快入库;实时依赖必须建立在审计 ST 链路上

## 5. merger 数据工程(本会话踩坑)

- **企业 key 账号归一化**:同一企业 user/info 返回单位名有时全称有时简称 → pack_map 双 key → CSV 导出"每个包件两行"假重复。修:合并时 `nk = str(ev.get("账号") or ek)` 统一 key + packId 去重 + bot CSV 导出按账号聚合双保险。
- 单实例锁 `fcntl.flock(LOCK_EX|LOCK_NB)` 防 cron 堆积(必须 import sys,sys.exit 用得上);rsync 按 mtime 增量 + 每台 120s 时间预算(ThreadPoolExecutor future.result(timeout=125))。
- 审计窗口溢出检测:滚动日志 5 页全满是常态(500 条覆盖 1.5 天)——**真溢出 = 页1 内 60s 内 ≥100 条操作**。

## 6. 竞价日实测数据(8/31)

- 当天 28 场竞价;9:00 批次 8 场(含西安局69次/郑州7次/南昌94次/成都37次/广西沿海17次/武汉72次)
- join 全量 96 个:90 个未参与(企业 0),5 个已有人参与
- 报名期项目拦截成功率:审计 60s 窗口理论 100% 捕获;实测 dff20093(沈阳82次)40 家企业 80 包件全入库
- 西安局69次:22 家报名企业 pack_map 只有占位(8/20-25 报名,采集机 8/28 部署前)——竞价日无 bfwz 操作 → packId 拿不到,等审核员账号或放弃
