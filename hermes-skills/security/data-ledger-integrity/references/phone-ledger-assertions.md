# 台账断言脚本与常见错数模式

## 1. 归一化函数（菲律宾号 / 通用 E.164）

```python
import re

def norm_ph(x):
    """任意写法的菲律宾手机号 -> '+63' + 10 位 (13 字符)；无法识别返回 None"""
    if not x:
        return None
    s = re.sub(r'[^\d+]', '', str(x))
    if s.startswith('00'):
        s = s[2:]
    if s.startswith('+'):
        s = s[1:]
    if s.startswith('63'):
        s = s[2:]
    elif s.startswith('0'):
        s = s[1:]
    if len(s) != 10:
        return None
    return '+63' + s
```

用法纪律：**先 `map(norm_ph)` 再 `set()`**。顺序反了就等于没归一化。

## 2. 三条必跑断言

```python
def audit(mapped, ledger, base_uids):
    m = {norm_ph(v) for v in mapped.values()} - {None}
    l = {norm_ph(v) for v in ledger} - {None}
    orphan = m - l                      # 1) 映射是否越出台账
    print('映射唯一值', len(m), '台账唯一值', len(l), '越界', len(orphan))
    assert not orphan, list(orphan)[:3] # 越界=源不同或格式漏网
    print('绑定 uid', len(mapped), 'uid 基数', base_uids,
          '覆盖率 %.1f%%' % (100 * len(mapped) / base_uids))
```

要点：报「覆盖率」必须同时打印分母（uid 基数）。没有分母的百分比不可复核。

## 3. 常见错数模式（对号入座）

| 现象 | 真因 | 处置 |
|---|---|---|
| 映射数 > 台账数 | 两边没归一到同一形态 | 重跑归一化，断言包含关系 |
| 交集=0 但两边明显同源 | 一边 `+63`、一边 `09`、一边 `63` | 同上；先看差集样本 |
| 唯一值数每次都变 | 计数在归一化之前做 / 有空白与全角字符 | 统一走 `norm_ph` |
| 覆盖率忽高忽低 | 分母换了（有时用 uid 基数，有时用有记录数） | 固定分母并写进报告 |
| 文件看着全是 `****` | 显示层打码，不是数据问题 | 用 `fullmatch` + 长度断言验证 |
| 抽了几千条就报总数 | 抽样当全量 | 必须先算上限（索引总数/字段明文数） |

## 4. 覆盖报告模板（交付时附在表头或同目录 README）

```
数据集: USER_DB_FINAL.csv        行数: 7000   大小: 252,515 B
字段覆盖:
  phone      156   (上限 339 唯一号, 来源 sms 索引 1579 条/342 明文)
  device     536
  nickname   581   (其中真人姓名 391)
  ...
绑定覆盖率: 156 / 7000 uid = 2.2%
未取到: password_hash(不入 ES), kyc 证件(仅对象存储, 未授权), 全量手机(打码, 明文上限 342)
```

三行必须齐：真值、上限来源、缺失原因。缺一行就等着被打回。

## 5. 旧文件处置

重生成后，旧版本（`*_MAP.json`、`*_55.csv` 之类）必须在文件名或首行标注作废，或在 README 里列 `SUPERSEDED BY`。否则后续会话会挑到旧的那份继续算，同一个错数会被复述第二遍。
