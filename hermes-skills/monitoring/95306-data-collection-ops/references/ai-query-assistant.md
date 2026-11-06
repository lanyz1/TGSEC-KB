# AI 数据查询助手(/ai)— 架构与扩展指南

2026-09 上线。bot 里发 `/ai` 或点菜单「🤖 AI 查询」进入对话,直接自然语言查数据池,1-3 秒回复。

## 文件(主服 /opt/v6/)

| 文件 | 职责 |
|---|---|
| ai_query.py | 查询引擎:8 个只读函数 + TOOLS 定义(function calling schema)+ call_tool 分发 |
| ai_agent.py | DeepSeek 调用循环:system prompt + tools → 解析 tool_calls → call_tool → 回填 → 最终答案 |
| .ds_key | DeepSeek API key(chmod 600;代码读 KEY_FILE) |
| pix_bot_server.py | AI_MODE/AI_HIST/AI_BUSY 全局 + ai_enter/ai_exit/ai_reply_async(后台线程)+ handle_text 拦截 |

## 8 个查询函数(全只读)

search_projects(关键词/局/物资/状态/bid_date/reg_before/reg_after/no_ent)
project_detail(name/code)→ 公告/包件/截止
project_enterprises(name)→ 平台全量 + 采集 + 待补(pending)
search_enterprise(name)→ 企业实时报名
bid_calendar(day)
deadline_alerts(days, only_empty)
notice_search(keyword)→ 公告全文
audit_status(name)

调用链:model → TOOLS 参数 JSON → call_tool → 结果截断 6000 字符回填 → 继续循环(≤5 轮)。

## 系统提示词要点(ai_agent.py SYSTEM)

- 先调工具不编造;工具报错如实说
- 列表 >8 条只列前 8 + 总数
- {today} 注入日期,换算"今天/本周"
- 状态词映射(正在报名→报名中;没人报→no_ent)
- 项目名匹配用关键词(局+次数+物资),不要要求全名

## 名称匹配算法(ai_query._match_name)

用户说的名和全名之间常隔"集团有限公司"等 → 纯连续匹配失败。算法:
1. norm(去空格/括号转半角/大写)连续命中优先
2. 数字独立提取(findall \d+)→ 在名称里**精确独立出现**(正则 (?<!\d)N(?!\d)),防"68次"错配"17次"
3. 中文片段按 年月日时分秒次第号包 等切分(数字是分隔),每片段 ≥2 字都需在名称里

教训:早期版本把数字当切分符导致 "乌鲁木齐68次废钢轨" 只匹配到 "乌鲁木齐+废钢轨",17 次项目也命中——**数字必须参与匹配**。

## bot 集成注意

- send_msg 独立 HTTP 调用 → 线程安全,AI 回答放 threading.Thread(ask 耗时 1-3s,同步会卡死 bot 主循环 getUpdates)
- AI_BUSY 每用户防重;AI_HIST 每用户最近 8 轮(ask history 参数)
- AI 模式拦截规则:AI_MODE[cid] 且文本不以 "/" 开头 → 进 AI;"退出/exit" 退出
- 只读护栏:模型只能调 8 个查询函数,无写/推送/订阅函数
- 回答用 send_msg Markdown(自带解析失败降级纯文本)

## 扩展新查询

1. ai_query.py 写函数(纯只读,读 /data_pool 缓存 _C idx 45s/plat 240s)
2. TOOLS 加 schema(description 中文、参数说明含可选值)
3. FUNCS 注册
4. 重启 bot(分步 kill/start)

## 主服 AI 部署约束(实测)

- 硬件:4C8T E3-1230v3/7.7G 内存/无 GPU → **不可本地 7B**,3B Q4 也只剩 ~3.5G 系统内存
- 海外主服直连 api.deepseek.com 335ms 可用(openai 25ms/dashscope 579ms)
- 模型 deepseek-chat,temperature 0.2,max_tokens 1200;成本:查询量小(几分/千次)
