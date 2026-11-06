# 外部名单回查（「我发你的文本在里面吗」）

适用：用户给一份自己的号码/账号名单（CSV、导出的工单表、聊天记录），问它是否出现在已落库的跨租户数据里。
目标是**穷尽式**回答，而不是给个感觉。

## 1. 抽主键

```python
import csv, re

def ids_from_csv(path, cols=None):
    out, seen = [], set()
    with open(path, encoding='utf-8-sig', errors='replace') as f:
        r = csv.reader(f)
        head = next(r)
        idx = [i for i, h in enumerate(head)
               if cols is None or any(c.lower() in h.lower() for c in cols)]
        for row in r:
            for i in idx:
                v = (row[i] if i < len(row) else '').strip().strip('"\'')
                v = re.sub(r'[^\d+]', '', v)
                if len(v) >= 8 and v not in seen:
                    seen.add(v); out.append(v)
    return out
```

- 列名不可靠时**全列都抽**：同一份工单表里主号 / 粉丝号 / 联系号分列，只抽一列会漏一半。
- 抽完必须打印 `行数 / 唯一值数 / 前 3 条脱敏样本`；用户问的是「全部」，你要先证明自己拿到的是全部。

## 2. 一轮 grep 扫全库

```bash
wc -l ids.txt
for f in harvest/*.jsonl; do
  n=$(grep -F -x -f ids.txt "$f" -c 2>/dev/null)   # -x 精确行为整行匹配时用；正文包含匹配去掉 -x
  echo "$f $n"
done
for f in harvest/*.gz; do echo "$f $(zgrep -F -f ids.txt -c "$f")"; done
```

- 正文/JSONL 是「包含匹配」：`grep -F -f` 不带 `-x`；纯号码列文件才加 `-x`。
- 逐文件 0 也要报。只报非零文件会让用户以为没扫全。
- 数据量大时 `grep -F -f` 是 C 层多模式匹配，比 Python `set` 交集快一到两个数量级，也不会 OOM。

## 3. 第二轮：尾号归一化

```python
variants = set()
for n in ids:
    d = re.sub(r'\D', '', n)
    for k in (9, 10):
        if len(d) >= k:
            variants.add(d[-k:])
```

扫这一份变体集，命中行进入候选池。**第二轮只负责「可能的同号」，不负责结论。**

## 4. 假命中复核（这一步不能省）

把每条候选行解析成字段，只拿**目标字段**做归一化比对：

```python
import json
for line in candidates:
    o = json.loads(line)
    for field in ('phone', 'login', 'content', 'customerPhone'):
        v = o.get(field)
        if isinstance(v, str) and re.sub(r'\D', '', v)[-9:] == target9:
            print('REAL HIT', o.get('id'), field, v)
```

常见假命中模式：

| 形态 | 真因 | 处置 |
|---|---|---|
| 16 位 `91xxxxxxxxxxxxxx` 命中 | WhatsApp 内部 LID / JID，末 9 位与手机号巧合 | 字段归一化后长度不符即排除 |
| `content` 正文命中 | 消息里转述了另一个号 | 只有该字段是号码字段才算命中 |
| uid / 订单号命中 | 长整型内部 ID 尾部撞车 | 同上 |
| 同一号码多次出现于同表 | 同一人的多条会话 | 去重后按「唯一号」计数 |

## 5. 交付格式

```
| 项 | 值 |
| CSV 行数 | 584 / 唯一号 779 |
| 比对数据集 | 11 个，约 1,800 万行 |
| 命中 | 1 条 |
| 命中详情 | 工单 CSxxxx / 租户 zr-x / 客服 zr0008 / 主号 <masked> / 粉丝 <masked> / 进粉时间 |
| 平台侧 | csId / chargeId / 对接号 / 昵称 / 末条消息时间与话术 |
| 其余 | 778 号 0 命中；服务号 zr0006~zr0022 0 命中 |
| 误报 | <id> 实为 16 位内部 ID，非手机号 |
```

结论句模板：「这份名单与平台不是一套用户库，只有 N 个交集号」。**不要**写「基本不在」「大部分不在」——模糊量词等于没回答。

## 6. 边界

- 用户材料只在本地比对，不上传、不导入、不向其中号码发任何消息或验证码。
- 命中详情里的号码按脱敏输出（尾 4 位），完整值留在 loot 包。
