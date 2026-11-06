# Session 23: 企业去重归一 + bot 日报/汇总推送(2026-08-30 晚)

## 1. 企业 key 归一化(治本:同企业多 key 分裂)

**症状**:同一企业"报了 4 次名"(2 包件 × 2 行)——CSV 里每个包件出现两次。
**根因**:采集机企业 key 用 `dwhz or uname`(单位名),而 `user/info` 返回的单位名**有时全称有时简称**(如"河南凡欧再生资源回收有限公司" vs "河南凡欧")→ 同一企业两个 key,每个 key 下都有全部包件 → 遍历输出翻倍。
**修复**(merger merge_all,治本 + 历史自动清洗):
```python
# 企业 key 统一用账号(唯一):
nk = str(ev.get("账号") or ek)
# 历史 old_ents 也转 key + 时间新者胜
# 同账号包件按 packId 去重
```
- 双保险:bot CSV 导出(fmt_ents_csv)先按账号聚合(by_acct),包件按 packId 去重再写行
- **通用教训:多采集源/多台机器合并时,任何"显示名"都不适合做 key——用唯一 ID(账号/UUID);显示名只当字段**

## 2. 待确认缺口类(防误报)

enroll_ops 记录 `notice:xxx`(报名跳转只有 noticeId),merger 用 notices_map.json 映射到 projId;**映射不到的项目(非竞价/保洁/集采/跳转未提交)→ 归 `gaps["待确认缺口"]`,不进"企业报名缺口"告警**——避免非目标项目刷告警。

## 3. 拦截成功率统计方法

enroll_ops 修复前无历史数据——用 `_ent_full_*.json`(企业全量拉取记录)反推当前真实拦截成果:每文件=1 企业(账号/单位/项目数/包件数),聚合得:拦截企业数、覆盖项目数、总 packId 数。审计 60s 窗口理论上 100% 捕获(500 条窗口覆盖 1.5 天);真正漏拉只有"报名后 2 天内完全不上线"的企业(竞价日必上线兜底)。

## 4. bot 功能新增(2026-08-30)

- **设置菜单加"📊 数据池更新记录"**(callback_data=`pool_updates`):显示项目总数/8515快照/缺口核对 + merger 最近合并/拉取日志(读 /tmp/v6_merge.log 过滤"合并完成/拉取"行)
- **日报(daily_summary)升级**:加系统状态块——缺口核对(项目/企业/采集机告警)、采集机健康(health.json machines)、8515 快照统计、merger 最近一轮
- **主服 bot 打补丁统一流程**:paramiko 读 pix_bot_server.py → 字符串替换 → 写回 → py_compile → systemctl/重启;函数体替换用"提取本地新函数体 repr 注入"方式

## 5. TG 手动推送坑

- **parse_mode=Markdown 对含 emoji/中文长文本可能 400 Bad Request**——汇总/日报类长文去掉 parse_mode 纯文本发送(加粗失效但必达);或严格检查 ** 配对
- 授权用户从 `/opt/v6/users.json` 的 `admins` 读(不是正则抠 bot 源码)
- 主服可直接调 api.telegram.org(bot 就运行在主服)
- 手动推送脚本:正则提取 TOKEN + 构造文本 + POST sendMessage(chat_id=每个 admin)

## 6. 数据边界再确认(报名期 packId)

- **报名期 packId 唯一纯读通道 = 企业登录 → getBuyPackageList**(该企业报的包件)
- 公告 readNoticeInfo = packCode 级(无 packId);数据平台停更 8/27;8515 不含部分项目
- 已截止报名项目 → 只能等竞价日自动捕获(用户接受:不手动拉)
