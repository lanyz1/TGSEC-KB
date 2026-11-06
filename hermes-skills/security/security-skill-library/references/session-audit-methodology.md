# 会话→技能沉淀审计方法论(2026-09 实证)

用途: 用户要求"整理历史所有会话/把没沉淀成 skill 的一起整理"时,系统化定位缺口,避免逐条翻会话。

## 会话库结构

```
DB = %LOCALAPPDATA%\hermes\profiles\<profile>\state.db
表 sessions: id / title / source / message_count / started_at / last_activity_at / ...
表 messages: id / session_id / role(user|assistant|tool) / content / tool_calls / timestamp / ...
```

- profile 会话库可能很大(123 profile: 520 sessions / 182k messages),cron 会话占多数
- cron 会话 id 以 `cron_` 开头且 source='cron';用户桌面会话 source='desktop'
- 全局库 `%LOCALAPPDATA%\hermes\state.db` 只是默认 profile 小库;实际工作 profile 在 profiles\<p>\state.db

## 1) 列出全部非 cron 会话

```sql
SELECT id, title, source, message_count, started_at FROM sessions
WHERE source='desktop' AND message_count > 1 AND id NOT LIKE 'cron%'
ORDER BY started_at;
```

## 2) 判断会话是否已产出过 skill(关键)

messages.tool_calls 是**转义 JSON 字符串**(`[{"function":{"name":"skill_manage","arguments":"{\"...\"}"}}]`),
正则解析 arguments 里的 action/name 常因转义失败 → 直接用子串检测最稳:

```python
import sqlite3, json, re, os
DB = os.path.expandvars(r'%LOCALAPPDATA%\hermes\profiles\123\state.db')
db = sqlite3.connect(DB)

# 每个会话的 skill_manage 调用(raw 子串,不解析 JSON)
rows = db.execute('''
  SELECT session_id, COUNT(*) FROM messages
  WHERE tool_calls LIKE '%skill_manage%'
  GROUP BY session_id''').fetchall()

# 要区分 create vs patch: 子串含 '"action": "create"' 或 '"action":\\"create\\"'(转义层不同)
# 稳妥做法: 对 tool_calls 含 skill_manage 的消息, 在 content/tool_calls 里找技能名关键词再人工复核
```

解析 action 用 `json.loads` 试两次: 先直接 loads(tool_calls), 失败则 loads 整个字符串(有些消息把 list 再包一层 str)。

## 3) 双向关键词核对(找缺口)

对每个会话提取目标/主题关键词(域名、系统名、品牌、漏洞特征),在技能库全文检索:

```bash
cd `本地工作目录`
for pat in 'EMSHOP' 'TokenPay' 'Shopline'; do
  echo "[$pat]"; grep -rli --include='*.md' "$pat" . | head -20
done
```

判读:
- 命中 SKILL.md 主文件 + references 案例 → 已沉淀
- 只在 references 出现 → 已沉淀(案例文件也算)
- 完全零命中 → **缺口候选**,深挖会话尾部 assistant 长消息判断价值

注意: 很多技能是**用户安装的 zip**(USER-OWNED,不可 patch),references 可能已含案例——判断"是否沉淀"看内容不看所有权。

## 4) 深挖缺口会话

会话总结/方法论通常在**尾部 assistant 长消息**(>200 字符),读取定位:

```python
msgs = db.execute('''SELECT role, content FROM messages WHERE session_id=?
                    ORDER BY id''', (sid,)).fetchall()
assts = [m['content'] for m in msgs if m['role']=='assistant'
         and m['content'] and len(m['content'])>200]
for a in assts[-3:]:
    print(a[:1500])
```

## 5) 交付

- 审计结论落盘 `会话沉淀对照.md`: 一行一会话 → 沉淀位置/排除原因(排除类: TSec跑分已有技能、运营类、元会话)
- 新缺口 → 按既有家族归类建技能(用户偏好类级拓展,拒绝窄技能)

## 陷阱(实测)

- skill_manage action 解析易失败,别依赖;用"该会话是否有 skill_manage + references 是否含主题"双信号
- 会话标题可能是误导(如 20260825_020946 标题"sd2模型"实际内容是 dsh2shell RCE 分析)——按内容不按标题
- 文件名/窗口 id 匹配要用会话 id 前缀,多个会话同秒启动是并行子代理
- 用户技能库 196+ 技能、397 references,大多数实战会话早已沉淀——先审计再建,别默认"都没整理"
