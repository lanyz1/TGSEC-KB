# Session16: packId 缺失因素穷举 + 接口语义实测 + systemd 常驻坑(2026-08-30)

## 核心问答(用户三连问的实锤答案)

### 1. ST 未利用 → 是否直接导致 packId 拉不到?
**是,直接因果。** packId 来自 `getBuyPackageList?projId=X`,按企业有效 ST 鉴权:
- 无 ST → 401 / data 空
- ST 过期 → `code:100 系统服务异常`
- ST 有效且该企业报了此项目 → 200 + 包件数组(packId/packCode/packName/保证金/报价模式/物资条数/审核状态/审核码)

### 2. "捕捉一个企业就能反出全项目包件 id?" → 不能
实测:zjjqdw123(张家界帅帅,ST 有效,user/info 200)→ 拉西安局69次 → `data:null`(他没报该项目)。
**getBuyPackageList 按企业隔离,一票只能拉"该企业自己报名的包件"。全量 = 每个报名企业各自活 ST。**

### 3. packId 缺失的全部因素(穷举清单)
| # | 因素 | 处置 |
|---|---|---|
| 1 | 企业报名后**再无操作** → 无 ST 产生(西安局69次 8/22-24 报名,采集机 8/28 才部署 → 22 家全缺) | 等竞价日登录自动捕获 / 审核员账号主动拉 |
| 2 | 审计只拉第 1 页(旧) | 已修:5 页×100=500 条,ST 池 18→49/轮 |
| 3 | ST 过期(旧判断 30min TTL) | **实测 TTL ≥3 小时**(09:45 票 12:39 仍有效);重试窗口放宽 |
| 4 | 采集机停机/重启循环(空窗漏票) | 已修:main 改 while True + 60s(见下) |
| 5 | 失败票一次性放弃(seen 永久标记) | 已修:重试队列 TTL 内每轮重试,成功才 seen |
| 6 | 审计里 30min 内旧 seen 失败票不补拉 | 已修:cutoff 补拉逻辑 |
| 7 | 包件解析正则窄(全角冒号/千分位) | 前轮已修 |
| 8 | merger 去重"先到先得"覆盖全字段 | 前轮已修 |
| 9 | bot 搜索拆词/排序 live 置底 | 前轮已修 |

### 判定技巧:数据池对比法
6,247 个有 pack_map 的项目中,6,225 个企业包件非空(8515 历史导入)vs **22 个实时项目企业包件空** —— 实时项目包件只能靠 ST 拉,空的 = 无任何企业活票。

## 接口语义与渠道侦察(95306 实证)

### 审计(唯一无鉴权表)
- findList `funcId=auditlog` 无鉴权 200;**其他 funcId 全部 403/不存在** —— 审计是唯一无鉴权业务表
- ST 正则:`operation_details` 里 `serviceTicket=([0-9a-f]{32})`
- **带 ST 的操作类型**:`redirectEnrollUrl`(cg.95306.cn/business-proxy/business/notice/redirectEnrollUrl?noticeId=...) 报名跳转 ✅
- **不带 ST 的操作**:`skipJoinPage`(bid.95306.cn/api/execute-server/page/skipJoinPage,只带 bulletinId+token)、标识更新定时任务、查看类
- 同账号会话级复用同一 ST(YNHKSMYXGS 11:06 与 12:15 操作同 ST ccc32e47)——"审计 ST N,新 0"≠ 没新操作,可能是同会话票被 seen
- 审计返回 `{"code":900000,"msg":"服务器异常"}` = 临时故障/限流,重试即恢复;condition 传 dict 与字符串格式要跟 collector 一致(字符串 `'{"operation_details":{"like":"%"}}'`)
- 审计能暴露系统动态:定时任务(48h 标记更新 727 公告)、竞价 DNS 异常(UnknownHostException: cg.95306.cn = 上游系统故障)

### 业务接口带 ST 直接调(bfwz 网关)
- 头:`Authorization: <ST>` + `Referer: https://cg.95306.cn/bfwz-view/`(防盗链,缺 Referer = 403 CSRF token session not found)
- `GET /user/info` → `data.username/dwhz/dwdm` 识别企业
- `GET /supplierPackage/getBuyPackageList?projId={pid}` → 当前企业报名包件
- GET-only 路由用 POST → 403 CSRF;探测时注意方法差异

### 报名全量 CSV 的坑
`D:\渗透\95306_历史数据_导入\2026年8月报名全量_含进行中项目_8515条.csv`(proj_name/proj_code/bulletin_reldate/bidder_name/un_social_cr_code/buy_time):proj_code 里 `OY002026081918259265` 中 **"69" 是序列号不是"第69次"**——按名称/确切 code 匹配,别按数字猜。

## 🔴 systemd 常驻循环坑(本次最大事故)

**症状**:采集机日志出现 5-7 秒一轮的轮询(应为 60s);上游系统出现 `UnknownHostException: cg.95306.cn`(高频轰炸打瘫);日志空窗(上海 18 分钟、杭州 2 小时)漏掉新票。

**根因**:collector 的 `__main__` 只有 `run_once()`(单次执行),systemd 服务 `Restart=always` 把正常退出当崩溃 → **无限重启循环**:启动→跑一轮→exit 0→5s 后重启→再跑一轮。4 台机器每 5-7 秒全量审计 5 页 + 43 项目拉包件 → 高频轰炸。

**识别**:`systemctl status` 显示 `Active: activating (auto-restart)` + `Process: ... (code=exited, status=0/SUCCESS)` = 死循环信号。

**修复模板**:
```python
if __name__ == "__main__":
    while True:
        try:
            run_once()
        except Exception as e:
            log(f"⚠️ 轮询异常: {str(e)[:80]}")
        time.sleep(60)
```
**部署纪律**:任何 systemd 服务化的脚本,`__main__` 必须是常驻循环(while True + sleep + try/except),绝不能是单次函数;部署后从日志验证轮询间隔符合预期(60s),而不是只看 `active`。

## 采集机 ST 处理状态机(最终版)
```
审计 5页(500条) → tickets
seen(成功永久) vs retry_st{st:{acct,tm,tries}}(失败,30min TTL 每轮重试)
candidates = 新票 + retry 未过期 + 审计里 30min 内票(含旧 seen 失败票补拉)
proc = 按时间倒序取前 15 → user/info → 成功:seen + 拉全部目标项目包件;失败:retry tries+1
state: seen_st[-2000:] / retry_st / st_times / targets / last_st
日志每轮:审计 ST N, 新 M | 目标项目 N | 识别 N, 重试队列 N | 🎯 pid[:8] N 包
```

## 采集链路健康判定
- **心跳文件 /tmp/v6_heartbeat.json(采集机)**,merger 从主服拉 4 台
- 日志空窗 = 停机(不是"没变化")
- 心跳恢复 ≠ 数据已落地(merger 轮次时序),用户侧"无变化"要查数据池 mtime / pack_map 企业数
- 数据池验证:西安局69次 f4d6e6e2-eb16-4b59-8c82-25944fea99df(bidStarttime 2026-08-31 09:00,status 19);dff20093(8/29 报名 27 家全量)
