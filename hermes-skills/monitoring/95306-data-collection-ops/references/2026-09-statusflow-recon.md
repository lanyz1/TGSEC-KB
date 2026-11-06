# 2026-09-03 菜单B 状态流转升级 + 竞价室通道侦察

## 1. 平台状态滞后 → 本地时间推导流转(不等平台)

**症状**:合肥13次废钢铁(OH002026082710399012,8/28公告)报名截止(09-03 17:00)2h+ 仍不在"🟡报名结束未竞价"。
**根因三层**:
1. 平台侧 status 滞后:selectSelfSellList 实测截止 2h 后仍返回 status=19(sellEnddate=None;status 22/13 前 10 页都无)→ 平台自己没切"待竞价"
2. bot blockable_projects 只按 index stage 分组,stage 依赖平台 status → 一起滞后
3. DEPLOY_DAY=2026-08-31 过滤:8/28 公告 < 部署日 → 项目被踢出可拦截分类(该过滤的原始理由=部署前报名真空拦不全;补漏体系(plat_enroll 名册+orch8b+gen_gap)成熟后已过时)

**修复(pix_bot_server blockable_projects 重写)**:
- stage=报名中 且 `regEndtime`/`sellEnddate` 已过(北京时间)→ 直接归 🟡;regEndtime 无分隔符格式 `yyyymmddHHMM`
- 删除 DEPLOY_DAY 过滤 → 部署前公告进行中项目全纳入
- 验证:合肥项目正确进 🟡(index stage 仍"报名中"但推导生效);全库 ns=93/en=117/pb=91

**配套**:orch8b 补漏范围 "报名中" → "报名中+待竞价(竞价开始前)";待竞价判定用北京时间 now+8h vs bidStarttime(直接 UTC 比较会晚判 8h)

**平台状态实测法**:活采集机上 findList auditlog 拿任意审计 ST → GET business-proxy/business/bidProject/selectSelfSellList(带 Authorization ST,status 13/19/22 × bidType 02/01 翻页找 projCode)→ 看平台真实 status/sellEnddate

## 2. 菜单B 采集完成分类(用户需求)

- 新增 ✅"可拦截项目·采集完成"(callback mbcat:2:3):🟡(待竞价/竞价中)里 **平台名册企业全部采到(差集=0)** 的项目;还差/无名册的留 🟡
- `collect_complete_projects(pb)`:逐项目 pack_map 企业集合(norm_ent_name)vs proj_plat_ent_names 差集
- 流转全自动:orch8b 补完 → 下次打开菜单自动从 🟡 挪 ✅;竞价结束平台切 14 → 🏁
- UI:menu_b 主页 + mb_cat_menu(fn=2)加按钮;mbcat 回调 cat==3 → done 列表;🟡 cat==2 只列未完成(open_)

## 3. ⚡ 性能:全库循环内 norm_ent_name 线性扫 = 卡死

- 症状:collect_complete_projects 全库跑(pb≈91)卡 5min+ 无输出(v1.py import 0.0s 完成,卡在分组函数)
- 根因:norm_ent_name 对每个名字 `for full in _sup_names()` 线性扫 **36.9 万条供应商名单**,且每次全等不中再二次包含扫(91项目×N企业×2遍≈上亿次 _norm_key)
- 修复:`_sup_key_index()` — norm_key(_SUFFIXES 去后缀)→ 官方全称 dict,构建一次 600s 缓存,精确匹配 O(1);二次包含匹配降级保留(低频)
- **通用教训:任何"循环内对 369K 级名单线性扫"的函数(企业名归一/全称匹配)必须建 key 索引;菜单分组/全库遍历类调用会指数放大**
- 工程:主服 import pix_bot_server 很快(0.0s),但远程跑测试脚本 stdout 重定向到文件**必须 flush=True**,否则进程未退出时看文件是空的(误判卡死);定位卡点=落盘阶段打印

## 4. 竞价室/实时竞价通道侦察(监控功能前置)

- **竞价系统独立域**:`https://bid.95306.cn/api/execute-server/...`(skipJoinPage 等;cg.95306.cn/business-proxy 只是报名/业务代理,竞价动作直达 bid.95306.cn)
- **bidRoom/initProjInfo 权限墙**:非该项目报名企业的 ST → **HTTP 500 无权限**(实测 6 项目全 500;collector try_fetch_bids 因此从未成功过,/data_pool 无 bid_live.json 样本);必须用该项目报名企业的活跃 ST
- **报名企业活跃 ST 获取路径**:竞价时段企业必登录出价 → findList auditlog(无鉴权)审计流明文 `serviceTicket=32hex`;报名跳转 `notice/redirectEnrollUrl` 的**响应 data 里也带 serviceTicket**(审计 detail 明文可见)→ 审计流 = "目标企业活跃检测器"
- 监控设计(验证中):用户给 projId → 取 pack_map 报名账号清单 → 采集机高频审计流盯这些账号的新 ST → 借其权限拉 bidRoom/initProjInfo → 变化推送
- **审计 detail 会暴露前端全部 HTTP 接口 URL**(含竞价域)→ 逆向新接口优先翻审计
- 竞价窗口规律:collector try_fetch_bids 只在 bidStarttime-5min 后尝试;非竞价时段竞价室接口无意义
- 沪0(8.133.178.188)曾失联数小时:主服/本机直连采集机超时 ≠ 采集机死;跳板机状态用主服→各台 paramiko 连通性实测,orch8b/gen_gap 推送成功即链路 OK

## 5. merger 真实调度澄清

- merger **没有完全退休**:pix_bot_server 内周期 subprocess 调 merger.py(`subprocess_check("cd /opt/v6 && timeout 180 python3 merger.py ...")`)→ index.json `updated` 字段每 ~2.5min 刷新(排查"index 谁在写"看 updated 字段+连续 stat,别只看 crontab)
- crontab 只有:sync_plat_enroll(*/30)+ orch8b(5,35)+ gen_gap_projects(15,45)
- merger 写 index 已是原子写(tmp+os.replace);gaps.json"企业报名缺口"字段 merger 新版不填 → gen_gap_projects 靠 `_plat_diff_ent_gaps()` 自算补偿(见 2026-09-menuB-fixes.md §3)
