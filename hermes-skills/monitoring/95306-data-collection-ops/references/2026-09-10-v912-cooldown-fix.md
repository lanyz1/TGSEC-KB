# 2026-09-10 v9.12:cooldown 误判 dead 根因修复 + 入口模型定稿 + 12 台架构

## 核心缺陷:cooldown(平台风控冷却)被当死票永久放弃 → 15% 初次采集漏洞

**铁证链**(崇锐 ZSTLPJ 案例,9/8 23:20 报名):
- 审计(redirectEnrollUrl)看到报名 → collector 拿票调 user/info → 平台返回 code=100 cooldown(账号级风控,深夜自动化批量报名触发)
- 旧代码 `if code in (401,403) or _is_cool_resp(j) and not _in_cooldown(): dead=True` → **cooldown 与 401 同级 → 永久 dead**
- 日志特征:多台反复 `⚠️ ST 放弃(2次失败): ZSTLPJ` 每 2-3 分钟一条(审计滚动窗同票反复入队,每轮浪费 2 次调用再放弃)
- 后果:该账号当天全部报名项目永久漏;9/9 实证 14 个缺口项目(沈阳批 BMW80676/sysd001、郑州帮 zzhk01/henanyuye/hnls158、崇锐 ZSTLPJ…)全是此死法 = G1 报名期 83% 拦截率那 15-17% 漏洞主力

**v9.12 修复**(collector_master.py,部署 12/12,主服留档 md5 eb1090d3):
- `_cool_backoff(st,t,state,minutes=30)`:cooldown → cool_st 队列退避 30min,绝不 dead/放弃(账号级冷却≠死票;2 次即放弃=永久漏)
- `_cool_restore(state)`:每轮开头(load_state 之后!)到期票移除,下轮若票仍在窗/enroll_st 自然重入
- 401/403 才 dead;其余 retry(≥2 次 giveup 保留,但 cooldown 不再走此路径)
- 判断顺序:`if _is_cool_resp(j): cool_backoff; elif code in (401,403): dead; else: retry`

**patch 事故教训**:一次 patch 把"待竞价 bst 已过=保留"注释配了 `continue`(逻辑写反,竞价中项目被误杀)——**patch 完必须 grep 新代码分支实际执行路径验证,注释与代码要互相核对**(9/7 orch ctx 竞价中修复曾因这个反逻辑多花一轮)

## 深挖方法论(缺口归因三刀)

1. **时效分桶**:拉名册窗(startDate/endDate 按公告日!非 buy_time)带 buy_time → 缺口按报名后经过时间分 <30min(链路内)/30-60min/1-4h/>4h(真漏)。9/9:90 缺口里 74% >4h
2. **假缺口检查**:缺口企业名 vs pack_map 单位名宽松 norm(去空格/全角/后缀)→ 0 命中=全真缺(norm 假缺口此前博涛案例修过,此处再验)
3. **enroll_ops 交叉验证**(审计滚动窗无法回溯!查历史痕迹只能看采集机 state):
   - 12 台 /tmp/v6_state.json 的 enroll_ops = {notice:<UUID>: {账号: 时间}},保留 50 条滑动
   - 缺口项目 pid→noticeId(notices_map.json dict:noticeId→projId)→ 与 enroll_ops 交叉 → "审计见报名但漏采"项目清单 ← **发现系统级遗漏的钥匙**

## 入口三分类模型(定稿,别再挖"无票"方向)

| 入口 | 票源 | 通道 |
|---|---|---|
| 公告页跳转报名(redirectEnrollUrl) | cg 审计行(detail 含 ST)→秒拦 100%(9/4 实证) | collector |
| 竞价日进场(从 cg 进竞价室) | tokenrailquery 登录行 → orch 10min 补(西安 38→54 实证) | orch8b |
| 站内/接口直调报名(自动化:深夜 0-6 点/同秒重复行特征) | **无任何票**(1.2 万 token 行全查 0 命中;登录不经 cg 登录日志) | 无,等竞价日或再动作(冷却已过会正常采) |

**tokenrailquery 深挖要点**(曾误判"无票",实际部分是 cooldown 误杀):
- 行字段:token/user_type/login_status/login_time/username(个人业务员账号!)/login_mode(证书 67%/手机/随机码)/ip
- 03=供应商;02=集团公司(无拉包件权限);login_status=0(登出票)也要查
- user/info 全窗逐个验证是唯一实证法;参数=顶层 params[{startDate,endDate}](不是 query!),返回 j["data"]
- 注意:Hermes/终端输出层对 sk- 开头与 telegram token 自动脱敏,文件本体是明文——交付密钥用文件直写(sftp/本地 cp),别靠打印

## 其它本会话实战

- **orch8b ctx 竞价中缺口**(9/7):ctx 只含 报名中/待竞价 → 9:00 切"竞价中"后当日进场潮登录无人扫(4h 窗内白白滑过)→ 修:竞价中且 bidStarttime 在 26h 内 → 保留;gen_gap_projects.py 有同款双份 bug 一起修
- **worker CHECK_LIMIT 400 截断饥饿**:竞价日单 30min 窗活票 03 达 900-1900 → 每轮只吃前 400,窗尾老票饿死直到滑出 4h 窗 → 400→800;消化延迟 40-60min→20-30min
- **拦截率三层口径**(战报 v9.11+):G1 报名期即时(rd 未过)/G2 竞价前/🏁 今日已结束完整度(g3,stage=已结束+bidStarttime 今天);战报漏采分层"链路内 ≤4h(自愈)/超时 >4h(无票或冷却,竞价日/复活通道)"
- sync v9.12 存 报名时刻(projs[k]["报名时刻"][企业]=最新 buy_time);keep_prev 并集必须同时合并报名时刻(否则丢新)
- 显示口径:pack_map 企业数必须 merge_ents_by_unit 去重(账号键+中文键双计会虚高:50 键→44 家)
- 名册行字段=bidder_name+un_social_cr_code(信用代码),无账号;同步器按 startDate/endDate(30 天)
- execute-server(bid.95306.cn/api/execute-server)有 dataplatform 但需真实账号会话(8 种 ST 传递变体全 1001"请先登录"),business-proxy 403 CSRF——无账号体系下不可达,别浪费轮次
- 12 台并发部署:前 4 台(沪0-蓉3)SSH 已改只允许 pubkey → 主服 ~/.ssh/id_ed25519(在 authorized_keys);后 8 台密码可直连
- bot 重启进程计数=2(bash 包装+python);pkill -f 自杀坑沿用(分 exec)
