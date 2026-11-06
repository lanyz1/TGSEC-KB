# Session 21: 全量项目发现 + 竞价系统 SM4 逆向 + 采集运维坑(2026-08-30)

## 1. 全量在网项目发现(selectSelfSellList 按 status 过滤)

**问题**:旧逻辑只翻 3 页 + 只收"竞价开始 48h 内"项目——默认排序把已结束项目(14=成交 1118 个)排前面,发布中/待竞价项目被淹没。用户例子项目(郑州局9次二次,OF002026081916151982, 9/1 14:22 竞价)翻 15 页都找不到,按名称搜索才命中。

**解法**:
```
POST /business-proxy/business/bidProject/selectSelfSellList
body: {...,"status":"<code>","bidType":"02","pageVo":{"pageNum":n,"pageSize":100},...}
按 status 分别拉(每 status 翻页到不满 100 为止):
  13 = 竞价中(1 个)
  19 = 发布中/未开始(169 个)  ← 用户例子项目在此
  22 = 待竞价/报名中(468 个)
  30/31 = 已结束, 14 = 成交(不监控)
合计 ≈ 637 个在网未结束项目。过滤 projName 含"测试"的项目。
```
- 搜索验证:body 里 `"projName":"26081507"` 可精确搜到项目(确认接口含该项目,只是翻页排序问题)
- **4 台分片**:`SHARD_ID = int(os.environ["V6_SHARD"]); _shard_ok(pid) = int(pid.replace("-",""),16) % 4 == SHARD_ID`——每台 ~160 目标,否则 637 目标 × ST × 包件请求会打爆 WAF

## 2. 包件拉取请求优化(防爆炸)

每个 ST 处理流程改为:
1. 先拉 `GET /supplierPackage/getSupplierPackageList?statusGroup=buyed&bidType=02`(该企业**所有已报名项目**列表)
2. 只对"该企业已报名的目标项目"拉 getBuyPackageList(force 目标除外)
3. 全量记录(限频 4 次/小时)写 `_ent_full_*.json` 根文件(merger 端 merge_ent_full 自动建新项目目录+补包件)

效果:每 ST 请求从 160 → 2-5 个。**getSupplierPackageList(buyed) 也是"发现审计外新项目"的通道**(企业登录一次,他名下所有项目+包件全补上)。

## 3. 数据平台表现状(2026-08-30 实测)

`/proxy/dataplatform/api/findList` 系列:
- bid_project_business23(项目 705/8月)、bid_package_business23(包件 2185)、bid_notice_business23(公告 2247)、bid_package_bidder_business23(报名)——**全部停更于 8/27 16:57**,且**不覆盖西安局69次/郑州局9次**(按 proj_id/名称都查不到)→ 只能作历史源
- bid_package_bidder_business23 历史全量:分月拉 2025-01~2026-08(每月 ≤6000 条上限,pageSize=1000×6页),12 万条/5,231 项目/17,607 包件,buy_time 2021-11 → 2026-08-24(确认 8/24 停更)
- biddingandsellingsupplier/biddingregistrationsupplier/centralizedbidsuppliers = total 0(已停更)
- aggregation_bfwz_bfwzpackage_a = 已结束项目包件表(含 pack_id,可用)
- 8515 快照表:企业字段全 null(只有 proj_id+pack_id),只能作项目级包件覆盖核对

## 4. 公告全链路(报名期可用,带 ST)

```
1. POST /business-proxy/business/notice/queryBusinessNoticeList
   body: {"projType":"02","notTitle":"<关键词>","noticeType":"","dateType":"","pageVo":{"pageNum":1,"pageSize":100},"isjtgsCode":0,"validOr":"1","orderField":"","orderType":"","onweb":"","jointSaleType":"","noticeStatus":""}
   ⚠️ 响应结构 = data.result(不是 bidNoticeListVo.list!) totalCount=23,150
   notTitle 精确搜索可能返回 0——用短关键词("第9次废钢轨")或翻页匹配 projId
   字段: id(公告id)/projId/notTitle/pubTime/status/sellEnddate(报名截止!)/jointSaleTypeName

2. GET /business-proxy/business/notice/readNoticeInfo?noticeId=<公告id>
   → data.bidNoticeResultVo.notCont(HTML 正文)
   → 解析 "第(\d{1,3})包[：:](.*?)(?=第\d{1,3}包|包件具体内容|$)" = 包件清单(packCode+名称+保证金)
   ⚠️ 注意:同项目有多条公告(主公告 + 变更公告 17d88423 类);公告清单是 packCode 级,无 packId
```
批量应用:翻 40 页 × 100 匹配在网项目 projId → 逐个 readNoticeInfo → 存 `/data_pool/<pid>/包件清单_公告.json`(61 项目/224 包件一次拉完,0.4s 间隔)。

## 5. 竞价系统(business-view)前端 JS 逆向 + SM4

前端 = `/business-view/`(与 bfwz-view 不同!)。**webpack chunk URL 格式:`/business-view/js/chunk-<id>.1787574513567.js`**(带版本号后缀,无 hash!chunk map 在 HTML 内联 runtime:`h.p+"js/"+({...}[e]||e)+".1787574513567.js"`)。

- 路由在 app.js;**API 模块 = chunk-65b3177a.js(2.3MB 全量接口)**
- 请求封装模块 b775(app.js):`urlType:"bidding"` → baseURL=`/business-proxy/business-bidding`;默认 → `/business-proxy/business`
- 竞价接口:bidRoom/packTable(GET)、bidRoom/packDetail、bidRoom/initProjInfo、bidRoom/packInfo、bidMonitor/packTable、buy/bidRoom/offer(POST 出价)、notice/getNoticeList
- **加密协议(SM4-ECB,每日动态密钥)**:
  ```
  密钥 y = (YYYYMMDD + "$e9s20@2o4u^r2")[:16]   # 例:20260830$e9s20@2,北京日期!
  请求(带 encryption):params → {data: base64(SM4-ECB-PKCS7(y, JSON.stringify({...params, r: 时间戳+随机})))}
  响应:裸 base64(SM4 密文),base64 解码 → SM4 解密 → 明文 JSON
  ```
- **写接口(participateInProject,普通 business 网关)密钥 = (YYYYMMDD + "+memberserver")[:16] = "20260830+members"**(8/28 报告验证过可通)
- 纯 Python SM4 实现已验(国标测试向量 0123456789abcdeffedcba9876543210 → 681edf34d206965e86b3e94f536e4246)
- **未解**:bidRoom/packTable 请求 HTTP 200(说明服务器接受了 SM4 密文),但响应(112B=16倍数)用 y/g 及日期变体都解不开——响应密钥存疑,9/1 竞价时继续攻。明文请求(无 data 参数)也返回 200+密文响应。

## 6. 采集/合并系统运维坑(多机)

- **单实例锁**:`fcntl.flock` 非阻塞;`except: sys.exit(0)` **必须 import sys**(否则 NameError 崩溃且 cron 循环报错)
- **rsync(主服→采集机 paramiko sftp)无超时会卡死**:解法 = ①mtime 增量(listdir_attr 比对本地 mtime <2s 跳过)②每台 110s 时间预算 ③ThreadPoolExecutor + `f.result(timeout=125)` 防挂死(挂死线程随进程退出被杀)
- **审计滚动日志**:5 页×100 全满是**常态**(覆盖 1.5 天),不能当溢出!真溢出判断 = 页1 内 60 秒内操作数 ≥100
- **run_once 内局部变量作用域**:`now_ts = datetime.now()` 定义在函数中段,前段(如溢出检测)用它 → UnboundLocalError——提前引用一律用 `datetime.now()`
- **审计报名记录正则**:报名跳转 URL 是 `noticeId=xxx` 不是 `projId=xxx`!enroll_ops 需记录 `notice:xxx` 前缀 key,merger 端用 notices_map.json(公告id→projId,由公告批量拉取产物)映射
- **bot 补丁方式**:主服真身是 pix_bot_server.py(不是 pix_bot_v3.py!)——用 paramiko 读文件→字符串替换→写回→py_compile,绝不整体覆盖(主服版本可能更新)

## 7. 纪律(用户强要求)

- **95306 相关一切操作通过主服(128.241.245.73:12971)执行,严禁用本机浏览器/本机网络**(用户多次强调"不要用本机!给你那么多跳板机要你干啥的")——browser_exec 等本机工具不要用于目标平台
- 主服连接用私钥 `v6_master_key`,不用密码;采集机只能通过主服中转连接(本机直连超时)
