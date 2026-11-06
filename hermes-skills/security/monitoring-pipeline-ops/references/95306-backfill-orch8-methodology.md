# 95306 补漏编排方法论(orch8b 成熟版,2026-09)

登录日志补漏通道的完整实现与全部坑。前提:审计通道只覆盖跳转式报名(~25%),
tokenrailquery(登录日志)可补"登录过的企业"——供应商 token 直接当 bfwz ST 用。

## 1. tokenrailquery 通道规则(实测)

- 无鉴权:`POST /proxy/dataplatform/api/findList {"funcId":"tokenrailquery","appId":"system",
  "pageNum":N,"pageSize":500,"params":[{"key":"startDate","value":"YYYY-MM-DD HH:MM:SS"},{"key":"endDate",...}]}`
- **user_type=03(供应商)的 token 可直接当 bfwz ST**(Authorization 头调 /business-proxy/business/*)。
  02(集团)无 bfwz 权限(success=false,白费请求);login_status=1 才有效。
- `code=100 系统服务异常` = token 过期 **或请求来自海外 IP 被 WAF 标记**。
  **业务接口必须国内 IP 执行**:主服(海外 128.241.x)直连 token 全 100;8 台采集机正常。
  编排铁律 = 主服生成任务文件 → sftp 传采集机 → setsid nohup 执行 → 结果文件拉回。
- token TTL 实测 >2h(部分 4h 仍有效);30min 窗最多拉 6 页×500=3000 条封顶(分页拉满判断 `len(r2)<500 break`)。
- 识别企业:`GET /business-proxy/business/user/info` Authorization=token → data.dwhz(单位全称)。

## 2. orch8b 编排模板(8 台并行增量补漏)

- ctx = `{miss_names:[平台企业名], miss_map:{企业名:[projId...]}, rounds}`;
  漏采 = plat_enroll_map(projs[projCode].企业) - pack_map(单位名),norm 匹配
  (去空格/全角括号转半角/upper)。
- 分片:shard i 扫窗口 `i % rounds`(每窗 30min,rounds=4 → 2h 覆盖,每窗 2 台并行)。
- **seen 持久化增量**:`/tmp/bk8_seen_N.json` 存 `{token: <REDACTED>,加载时裁剪 >6h 项;
  旧 list 格式直接弃(全过期)。每轮只查新 token,请求量骤降。
- worker 命中流:拉 token(滤 03)→ user/info → miss_norm 匹配 → **直接 getBuyPackageList?projId=**
  (**不要先 getSupplierPackageList?statusGroup=buyed 前置过滤**——buyed 对部分 token 返回空,
  会把命中企业全部 continue 掉,结果文件空 `{}` 且无报错)。
- `getBuyPackageList` 的 `data` **直接是 list**(不是 {result:[]}),解析两形态兼容。
- 回写 pack_map 必须用 collector 生态 schema(见第 6 节),否则 bot 读不到。
- 主服 cron `5,35 * * * *` + 单实例锁 `/tmp/orch8b.lock`(pid 存活检测,死 pid 自动接管)。

## 3. pkill 自杀陷阱(本会话实踩 2 次)

- `pkill -9 -f '[b]k8_worker'` 若 bash -c 命令串本身含真实 `bk8_worker.py`
  (如 `... python3 bk8_worker.py ...`),正则仍匹配自身 → **整个分发 shell 被杀,
  后续 rm/启动全不执行且无任何报错**(表现为 worker 从没启动、结果文件是旧的)。
  `[x]` 字符类技巧挡不住——命令行里同时含真实目标串。
- 修复:**kill 与 start 拆成两条独立 exec_command**;或命令串里根本不放 pkill。
- 判断 worker 是否真启动:exec 后 `ps aux | grep` 查进程数——**不要 grep 旧日志的 DONE**
  (旧 log 残留会让轮询误判完成,读到旧结果文件)。

## 4. paramiko exec_command 管道坑

- **fire-and-forget(exec 后不 read 直接 close)命令可能根本没发出**;必须 read
  (超时异常吞掉即可,命令已执行)。现象:8 台静默全没启动,文件时间戳全旧。
- 嵌套 relay(base64 脚本字符串再在 relay 里 `% b64`)易 NameError/格式错乱 →
  **外层用 f-string 直接拼** b64,内部不再有 % 格式化。
- setsid nohup 后台任务输出落文件(`> /tmp/x.log 2>&1 < /dev/null`),轮询文件判断完成,
  不要依赖 exec stdout 管道(频繁 PipeTimeout)。

## 5. merger 多源合并坑(2026-09 修复)

- **同项目多采集机 `_项目信息.json` 直接覆盖** = bug:buyed 源(报名即发现,字段少)
  覆盖 join 源(有 sellEnddate/status)→ 丢报名截止 → stage 误判。修复:**字段级合并非空优先**
  (`v not in (None,"",0) or not old.get(k)` 才写)。
- `_stage_of` 判定"报名中"依赖 sellEnddate(报名截止)。平台列表接口常缺该字段 →
  **从公告全文正则解析兜底**:`报名截止时间[:：]?\s*(20\d{2})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})时(?:\d{1,2}分)?`
  → 存 info["regEndtime"]。落地后 merger 全量重跑 stage 自动修正。
- **status 22 = 报名期+待竞价期混合**(平台整个报名窗都用 22),必须用截止时间细分,
  不能 stage=待竞价 直接归"报名结束未竞价"组。症状:菜单B 🟡 组混入大量报名未截止项目。
- merger daemon 是 `while true; python3 merger.py; sleep 120` 的 bash 循环 →
  改 merger.py 无需重启 daemon,下轮自动用新代码;验证可手动跑一次 merger。

## 6. pack_map schema 契约(写入方必须对齐,否则 bot 静默读不到)

- 生态标准(collector/merger/bot 消费端):
  ```
  企业 key = 账号;ev = {账号, 用户, 单位, ST, 时间, 包件: [
    {packId, packCode, packName, 保证金, 报价模式, 物资条数, 审核状态, 审核码}]}
  ```
- 审核状态字段名:`bidderCheckStatusName`(未审批/通过/拒绝)+ `bidderCheckStatus` 码;
  bot 统计读 `ev.get("包件")`(list)+ `pk.get("审核状态")`。
- 历史导入(来源"01三态+映射链")key=单位名且账号空 → merger 归一有账号的为账号;
  无账号保留单位名 → 同单位双记录。**bot 展示按单位合并**(merge_ents_by_unit:
  包件全并 packId 去重、账号逗号并列、时间取最新),勿期待数据层唯一。
- 反例教训:orch8b 初版写 `packs`(dict)+`审核`+key=ent_bk8_N → 45 项目 79 家企业
  bot 全读不到(审核统计 0、包件显示"项目级")。迁移 = 转生态 schema,packCode/保证金等
  从同项目 18列CSV 按 packId 回填(包件属性,任意企业行可查)。

## 7. 公告全文补拉(2026-09)

- collector 找 nid 靠 queryBusinessNoticeList 翻 2 页 + 前 20 字标题搜,常失败
  (西安局/采购类都中过)→ 公告全文缺失,bot"📜 公告原文"按钮显示暂无数据。
- **根治**:`/data_pool/notices_map.json`(noticeId→projId,merger 自愈 30min 维护,970+ 条)
  反查 noticeId → `readNoticeInfo?noticeId=` 直拉,**100% 命中**。实测一轮补 223/223。
- HTML 清理顺序坑:先 `re.sub(r"<style[^>]*>.*?</style>","",txt,flags=S|I)` 删样式块,
  **再**去标签——直接去标签会留下 CSS 纯文本(含"宋体"等中文,中文检测不可靠);
  CSS 头兜底按"首行含 ≥3 个 {}"裁到第一个 \n。
- 落盘 `/data_pool/<pid>/公告全文.json` = `{"公告id","公告标题","全文"[:20000]}`,
  bot notice 回调直读;无全文回退包件清单标题,再无则"暂无公告数据"。
- 61/284 无 noticeId 映射(非跳转来源)需标题搜索兜底,量小留待。

## 8. bot 展示口径(2026-09 用户要求)

- 项目列表/详情企业数统一 `🏢 已采/平台`(分母 max(平台,已采)防平台名单滞后),
  平台侧企业名(load_plat_enroll 5min 缓存,projCode 键)全列出,未采到的标
  `⏳ 企业名 — 平台已报名,数据待补`,计数 = 采集+待补。
- 列表分子用 pack_map 实时企业数(详情页读文件,不用可能滞后的 index enterpriseCount)。
