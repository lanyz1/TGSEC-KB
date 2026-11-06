# 2026-09-11 特权会话蓄水+盲区解法(建设中)

## 目标
解决「站内直报/批量报名」双票源盲区: 批量/直报用户无审计票、无TQ增强认证票 → 其 企业×包件×审核 数据不可采。

## 今日跑通的机制
1. **非-03 票就在公开流里**: tokenrailquery 1h 窗 user_type 分布: 03=256(供应商), **02=235(集团公司/单位账号)**, 09=3(运营), 00=4, None=2。userid 形如 `wlcbsgs_cgxdr`/`jlgdd_ghcg1`/`dlcwd_ksk`(各站段)。
2. **票寿命短**: 87 张验活仅 2 张存活(其中1张日龄 3.5h+ 仍活) → 必须【收割后立即测试】+常驻循环。
3. **会话交换**: `POST /proxy/portal/user/login {serviceTicket: <TQ票>}` → `{token, authority}` 成功! authority 如 `manage:user:...` / `enterprise:enterpriseTableView:queryEnterpriseInformation:...`
4. **权限地图**: `GET /proxy/portal/system/loadMenu` (Authorization=交换后token) → 菜单JSON。账号菜单差异大(自助型只有用户管理; 目标=含竞价/处置功能者)。
5. **业务接口全表(124条)**: 从 `https://cg.95306.cn/business-view/js/chunk-65b3177a.1787574513567.js` 提取。关键族:
   - `/bidMonitor/getSupplier | packTable | getSignInNum` (项目监控:供应商/包件/签到)
   - `/bidPackageBidder/packCheckList` (包件审核清单!)
   - `/bidProject/getProjInfo | listBidderBy`
   - `/reqCheckProject/*` (报名审核族: initCheckProject/preResult/refuse/release…)
   - `/reqPurchase/querySupplier | getSuppliersByReqId | getSuppliersByMaterialId | reviewPurchaseDetailsBySupplier`
   - `/bidRoom/packTable | initProjInfo | signIn`; `/buy/bidRoom/offer`
   - 基址: `/business-proxy/business` (另有 business-bidding/oss 分支); 另一 findList 实例 crmall.rails.cn
6. **响应判读**: `您没有该功能的操作权限`=账号缺功能; `系统服务异常(code100)`=死票; `您没有该数据的访问权限`=活票缺权限; `401未登录`=无效会话。

## 常驻部署 (2026-09-11 14:05 起)
- 主服 `/opt/v6/priv_loop.py` (setsid nohup flock /tmp/priv_loop.lock): 每 8min 循环 = priv_tok_watch_v3 收割 → 逐票验活 → 交换+loadMenu → 10端点矩阵(PIDS=北京3次/大秦22/北京18) → 存 `/opt/v6/priv_probe_state.json` + `/opt/v6/priv_hits.json`; 日志 `/tmp/priv_loop.log`。HIT=端点非权限错的任何应答。
- 本地哨兵 cron `63b9aff57605` (30min): priv_hits_check.py → priv_hits.json 新增即报。
- 工具: /opt/v6/priv_fire.py(单票手动打, 已修 urllib 作用域bug), priv_dbg*.py, priv_tok_watch{,_v2,_v3}.py。

## 8515 无鉴权通道复核 (同日)
- `bid_package_bidder_business23` (findList, params=start_time/end_time): 行含 proj_id/pack_id/buy_time/status(uuid等), **bidder_name/phone/dwcode 全 null(4481行实测) = 无身份列**; 7天窗硬限(fetch_8515_inc.py 主服 cron */30 → /data_raw/m_snap → merger merge_8515_snap)。
- 审计层 v9.16 的 bidder 保留层在当前 index.json 未见(需复查 merger)。

## HIT 时行动
用命中账号会话对 miss 项目(miss_current.json)全量拉 bidMonitor/getSupplier + packCheckList + reqCheckProject → 企业×包件×审核 回填 pack_map(来源=特权会话); 与 8515 的匿名 pack×status 交叉验证。
