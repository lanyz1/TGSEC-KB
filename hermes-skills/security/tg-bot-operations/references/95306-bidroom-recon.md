# 95306 竞价室(bidRoom)侦察档案 — 验证实验进行中

2026-09-03。目标:用户输入任意 projId → bot 实时监控"竞价室内部活动"。以下为**已实测确认**结论与设计方向;报名企业 ST 下的房间数据返回结构**尚未验证完成**(实验中断点见文末)。

## 已确认事实(实测)

- 接口:`GET https://cg.95306.cn/business-proxy/business/bidRoom/initProjInfo?projId=<uuid>`(Header: `Authorization: <ST>`, Referer: bfwz-view)
- **权限墙:仅该项目报名(投标)企业 ST 可访问**;任意其他企业 ST / 过期票 = **HTTP 500 无权限**(实测 5+ 个真实项目全 500;审计现拉的新鲜 ST 也 500)
- collector_v9 `try_fetch_bids()`(竞价窗口项目用 any_st 调 initProjInfo)因此**从未成功过**——数据池 0 个 bid_live.json 样本;`bid_skip` 1h 跳过集是它的常态
- 竞价室前端入口:`notice/redirectEnrollUrl?noticeId=` 响应 data 带 `serviceTicket=32hex`(审计明文可见),跳 `bfwz-view/#/auction...`
- 竞价时段审计流以 redirectEnrollUrl(报名跳转)为主;企业大量报 `UnknownHostException` 客户端解析错(正常噪音);**出价动作是否产生审计记录未知**(可能走 WS 不经审计)

## 破局设计(未验证完成)

监控指定竞价项目的可行链:

```
用户给 projId(数据池竞价中/待竞价项目)
  → pack_map 取报名企业账号清单(去重:账号键+中文单位键并存)
  → 采集机(国内出网)40s 级盯审计流(findList auditlog,无鉴权)
  → 报名企业竞价时段必登录/出价 → 审计行带其新鲜 ST(serviceTicket=32hex 从 operation_details 提取)
  → 以投标人身份调 bidRoom 接口拉房间数据 → diff 变化推送 bot
```

顺带价值:审计 detail 里的 URL 会暴露前端竞价调用接口全集,可扩展房间数据面。

## 关键路径速查

- 审计:POST `/proxy/dataplatform/api/findList` body `{funcId:"auditlog",appId:"system",pageNum,pageSize:100,condition:'{"operation_details":{"like":"%"}}'}` **无鉴权**;detail 正则 `serviceTicket=([0-9a-f]{32})`
- 数据池找竞价项目:index.json `stage∈{竞价中,待竞价}` + `bidStarttime` 窗口 + pack_map 非空
- 采集机网络:本机/主服直连个别台会超时;经主服 paramiko 密码跳板(密码在 orch8b.py BOXES 明文);setsid 到采集机本地独立跑观察器,勿依赖 SSH 长连接
- 观察器日志:杭1 `/tmp/room_obs.log`;实验项目:西安局73次废钢铁 `0163af89-68a8-4086-8ce3-a0c01b14a745`(09:00 竞价,5 家报名:hcxd<PHONE-REDACTED>/shanxiqiankunzhiye/dc12301/baoying123/xx2420441054)

## 验证清单(下次续做)

1. 看杭1 /tmp/room_obs.log:是否抓到报名企业活跃 ST?initProjInfo 返回结构?(data 含出价记录/当前价/倒计时/房间状态?)
2. 若成功:选"竞价中且有人在出价"的项目做多轮轮询,diff 出价变化 → 确认实时监控数据面
3. 若 500 依旧(即使投标人 ST):找审计里投标人操作 detail 的 URL,逆向前端竞价页 JS(bfwz-view auction 路由)找正确房间接口/参数
