# 2026-09-12 审计流收割层 + bid2(bid.95306.cn)模型 + 票源资格铁律(全文)

## 1. auditlog = 近实时富矿(公开无鉴权)
- 查询: findList funcId=auditlog, appId=system, condition {"operation_details":{"like":"%"}}; 行字段 operation_account/operation_time/operation_details
- 近实时(分钟级); 详情含完整跳转链与凭证, 正则:
  - bid2 JWT: token=<REDACTED>,}) —— 12h TTL, payload 有 org.name/信用码/ln
  - 32hex票: "token":"([0-9a-f]{32})" 与 serviceTicket=([0-9a-f]{32})

## 2. 链条样例与收割器
- 报名按钮 → bid.95306.cn/api/execute-server/page/skipJoinPage 参数{bulletinId,token} → 返回 data.url 含 JWT; redirectEnrollUrl → business-view URL 含 serviceTicket(=采集机所捕票本源)
- 平台故障也在此暴露(UnknownHostException=平台DNS抖动; 曾解释上游不稳)
- 已部署: /opt/v6/audit_harvest.py (cron */10, flock -n 单实例), 池 /opt/v6/bid2_tokens.json {jwt:{...},st32:{...}}, 日志 /tmp/audit_harvest.log; 首轮600行→265 JWT+244票(增量+去重正常)

## 3. bid2 API 模型
- 头 X-Token:<JWT> + JSON; 基址 api/{user,consign,execute,project,doubt,mongo}-server/
- 未带票=请先登录; 供应商JWT有效但员工功能→4003 无此功能权限; bidRoomRecord/*=评标室/员工类(≠竞价室); 页面从URL取 token/serviceTicket

## 4. cg API 探测铁律(仿采集机请求头)
- 头: 完整Chrome UA + Referer https://cg.95306.cn/bfwz-view/ + Authorization=<ST>; Referer 不对会误导成"无功能权限"
- 错误类: [100]系统服务异常=票死/不对; 500无功能权限=角色门; 100无数据权限=票活且非本项目参与方; 成功=数据
- 实证: 供应商票仅见自己参与项目; /bidRoom/initProjInfo 等内部房控=员工功能 → 竞价拉取0命中根因即此

## 5. TQ 停摆模型修正 + 管道坑
- 停摆=生产空洞(老窗有数据+近窗全0, 非保留期删除), 可达17h级; 边界探测=从now-2h逐小时后扫至首个非空窗; 无平替(crmall镜像超时/他funcId不存在/appId仅system)
- merger 扫描器只认 _pack_map.json/_项目信息.json 注册 pid → 新产物类型必须加独立全局 sweep
- 远端批量部署: 备份→上传→md5核对→install→restart→is-active 逐台; write_file 分片<600B, 拼接 `for f in ...; do cat "$f"; echo; done > out`(普通 cat 会粘连尾行)

## 6. 待续(下次先看)
- 下一探测: compete/manage/allProject + deal/reverseBidResult?token= (供应商视角房间数据)
- 乌局73(09-12 13:40场)后查审计有无"房间进入/出价"类操作; 有则用其新JWT试供应商房接口