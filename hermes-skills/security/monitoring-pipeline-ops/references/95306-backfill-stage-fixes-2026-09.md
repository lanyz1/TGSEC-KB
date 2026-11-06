# 95306 管道 2026-09 运维实录(补漏闭环 + stage 修复)

实测验证过的运维教训(采集-合并-bot 管道)。此前系列 reference 的延续。

## 远程 exec 三模式(可靠性排序)

1. `exec_command(cmd)` 后**不 read 直接 close → 命令可能根本没执行**(命令还在 channel 缓冲)。dispatch 前必须 read(即使超时)。
2. read 超时(PipeTimeout)是常态——try/except 吞掉,**命令实际已执行**;用 `ps/tail 文件` 验证,不要重试导致双实例。
3. **最稳 = 命令输出重定向文件 + setsid nohup 后台 + 轮询日志文件**:`cd /tmp && setsid nohup python3 x.py > x.log 2>&1 < /dev/null & echo UP`,主控轮询远端 log 的 `DONE` 标记。
4. 内嵌脚本 base64 传输:relay 字符串**用 f-string 拼接 b64**,不要 `r'''...''' % b64` 嵌套格式化(内层 exec 命令也有 `%s` → NameError: b64 not defined 或 format char 报错)。

## pkill -f 自杀(kill/start 必须分两个 exec)

`pkill -f 'xxx.py'` 匹配 **bash -c 的完整命令行**——若同一命令串里含启动串(`... && setsid nohup python3 xxx.py ...`),pkill 把分发 shell 自己杀了 → 后续全不执行(表现为:worker 没启动、旧结果文件没被 rm、日志无更新)。`'[x]xx.py'` 技巧**防不住**(命令行里有 `python3 xxx.py` 字面)。**修复:kill 和 start 放两个独立 exec_command**;或验证 ps 计数为 0 再启动。

## pack_map schema 契约(新写入通道必须对齐,否则 bot 读不到)

collector/bot 生态的 pack_map schema:
```json
{"enterprises": {"<账号key>": {"账号","用户","单位","ST","时间","来源","包件": [
  {"packId","packCode","packName","保证金","报价模式","物资条数","审核状态","审核码"}]}}}
```
- 新补漏通道(orch8b)最初写了 `packs`(dict,key=packId)+ `审核` → **79 家企业 45 项目 bot 读不到**(bot 只读 `包件` list + `审核状态`)→ check_status_summary/企业包件展示全空。修:worker 全字段提取 + 写入用兼容 schema(key=账号),存量写迁移脚本(18列 CSV 按 packId 回填 packCode 等包件属性——包件属性与企业无关,任意企业行可查)。
- **同单位多 key 重复**:历史导入(来源 `01三态+映射链`)key=单位名,采集 key=账号 → merger 归一化不合并(不同 key)→ 同一公司两条。修:**bot 展示层按单位合并**(merge_ents_by_unit:包件去重合并、账号并列、时间取最新);ent 统计/待补判断都基于合并后单位名。

## merger 项目信息合并:字段级非空优先(不是覆盖)

多采集机同项目多个 `_项目信息.json`:join 源字段全(sellEnddate/status),buyed 源(报名即发现)字段少。`projs[pid]["info"] = data` **直接覆盖会丢 sellEnddate**(GTCLJJ-142 的 09-07 18:00 被空值覆盖)→ stage 误判。修:
```python
old_info = projs[pid]["info"]
if not old_info: projs[pid]["info"] = data
else:
    for k, v in data.items():
        if v not in (None, "", 0) or not old_info.get(k):
            old_info[k] = v
```

## 项目 stage 生命周期判定(菜单B 分组)

`_stage_of(pid, info)`:报名中(公示~报名截止,需 sellEnddate)→ 待竞价(报名截止~竞价开始)→ 竞价中(有包件结束时间且 now≥bidStarttime)→ 待发布(now≥包件最大结束)→ 已结束。
- **平台 status 22 = 报名中/待竞价混合期**(collector 注释:22=待竞价/报名中),不能只靠 status 分组。
- **sellEnddate 缺失 = 无法判"报名中" → 误落"待竞价"**(🟡 报名结束组出现报名未结束的项目,用户报 bug)。
- 兜底:**从公告全文解析报名截止**——正则 `报名截止时间[:：]?\s*(20\d{2})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2})时(?:(\d{1,2})分)?`;处置项目公告里必有;采集机文件在 /data_raw/<城市>/<pid>_公告全文.json 或主服 /data_pool/<pid>/公告全文.json。
- 修完重跑 merger 一次即全量重算 stage(daemon 循环每次重新加载 py 文件,无需重启)。

## 公告全文补拉链(collector 标题搜索失败时)

- collector 找公告 id:queryBusinessNoticeList 翻页(2×100)匹配 projId → 失败再按标题前 20 字搜 → 常搜不到(项目名长/特殊字符)→ 全文缺失、bot「公告原文」按钮"暂无数据"。
- **notices_map.json(noticeId→projId,报名跳转产物,merger 自动自愈合并 970 条)**反查 projId→noticeId → `GET /business-proxy/business/notice/readNoticeInfo?noticeId={nid}`(带 ST + Referer bfwz-view)直拉全文。批量补拉 223/223 成功。
- 补拉后清理:**<style> 标签被去后 CSS 文本残留首行**(含"宋体"等中文,不能按"无中文"判断)——按**首行含 >2 个 `{` 即裁掉**。
- bot 按钮 notice:{pid} 读 `/data_pool/<pid>/公告全文.json` 的 `全文` 字段。

## bot 推送体系与"首轮基线不推"

- 推送线程分工:check_subscriptions 60s(订阅项目秒级明细:新报名/审核变化/竞价状态)、mb_monitor_loop 180s(菜单B 计数广播+本轮新增:项目明细 diff)、check_data_updates 20min(数据池:新项目/新企业明细)、check_gaps_alert(缺口签名变化才推)、check_health 5min。
- 完善推送 = 数字 + 明细(上限 4-6 条,超出折叠),**状态文件无基线时首轮只建基线不推送**(旧版状态文件缺 live_ents → 首轮会把全量当新增误报)。

## 认证域(招标域)对照

- 招标域认证:Header X-Token(JWT) + body 注入 app_id=9/user/reqtime/sign;sign=MD5("reqtime=..&user=..&token=..").upper();4003=登录无权限。处置域(bfwz):Authorization=ST + Referer bfwz-view。
- 审核状态字段 = getBuyPackageList 返回的 `bidderCheckStatus`/`bidderCheckStatusName`(值:00 未审批);bot 统计空状态显示 ⬜(企业未提交报名/无审批动作),不是错误。
