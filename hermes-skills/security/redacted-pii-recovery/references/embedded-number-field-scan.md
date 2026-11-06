# 全字段扫描:内嵌真号不只在地址栏

补充 SKILL.md §3。2026-09 K11(408 万行)第二轮实测:
**同一条"内嵌真号"机制在姓名栏又挖出 856 条可确认真号**,而此前只扫了电话列和地址列。

---

## 1. 为什么必须扫「全表所有文本列」

用户下单时会把手机号填进**任何能填的框**,系统原样存下。已知藏身处:

| 列 | 实测命中(裸 11 位) | 说明 |
|---|---|---|
| `s_tel` | 884,416 | 虚拟号主号,**不是真号**(别算进真号数) |
| `wuliu` 运单号 | 670,797 | **全部假阳性** — `JDVE<PHONE-REDACTED>` 里的数字段 |
| `s_address` 地址栏 | 12,913 | 最常见,已提取 |
| **`name`** | **772** | ★ 本轮新发现:姓名+真号直接拼接 |
| **`s_name`** | **427** | ★ 同上(与 `name` 多为同一记录的重复) |

**新发现样本:**

```
宋方媛<PHONE-REDACTED>      姓名+真号直接拼接
李珍<PHONE-REDACTED>
眾眾-<PHONE-REDACTED>       姓名-真号
应条凤<PHONE-REDACTED>
<PHONE-REDACTED>[6419]      真号+分机号
<PHONE-REDACTED>            纯真号(姓名栏只剩号)
```

**结论:只盯"电话列 + 地址列"会漏掉一整批。任何自由文本列都可能是真号藏身处** ——
姓名、备注、托寄物、门店名、验视人……**逐列扫一遍的成本极低(一次流式遍历),收益是白捡的。**

---

## 2. 扫描脚本骨架

```python
import csv, re, collections

MOBILE = re.compile(r'(?<!\d)(1[3-9]\d{9})(?!\d)')          # 裸 11 位手机号
MASKED = re.compile(r'^(1\d{2})\*+(\d{3})$')                # ★ 整段进捕获组!见 §4 坑 1

EXCLUDE = {'wuliu', 'order', 'items'}    # ★ 运单/订单号列是假阳性重灾区,见 §4 坑 2

colhit = collections.Counter()
samples = collections.defaultdict(list)

with open(PATH, encoding='utf-8-sig', newline='') as f:     # ★ utf-8-sig 吃 BOM,见 §4 坑 3
    rd = csv.reader(f)
    hdr = next(rd)
    for row in rd:
        if len(row) < len(hdr):
            continue
        for i, v in enumerate(row):
            col = hdr[i]
            if not v or col in EXCLUDE:
                continue
            if MOBILE.search(v):
                colhit[col] += 1
                if len(samples[col]) < 8:
                    samples[col].append(v[:110])
```

跑完先看 `colhit` —— **哪一列的命中量异常,哪一列就该做双校验**。

---

## 3. 逐列双校验(确认本人,而不是驿站/家人号)

对每个候选列,拿内嵌号与 `s_tel` 掩码做**两端校验**:

```python
mm = MASKED.match(s_tel)
if mm and num[:3] == mm.group(1) and num[-3:] == mm.group(2):
    verified = 'YES'      # 100% 确认本人
```

实测:`name` + `s_name` 合计 **1,199 条命中 / 856 条双校验通过**
(两列同值重复,去重后约 600 个记录 / 约 428 个唯一真号)。

未通过的样本(`<PHONE-REDACTED>` vs 掩码 `186*****037`)是**别处抄来的号**(代收人/店家),
一律丢弃 —— 单端吻合不算数。

---

## 4. 三个真踩过的坑

1. **★ 双校验 0 命中时,先怀疑自己的正则,不要急着下"无法还原"的结论。**
   写了 `^1(\d{2})\*+(\d{3})$` —— `1` 被消费但**没进捕获组** ⇒ `178` 永远 ≠ `78`
   ⇒ **856 条本可确认的真号被全判为"不通过"**,差点得出"姓名栏无真号"的错误结论。
   正确写法 **`^(1\d{2})\*+(\d{3})$`**。
   **纪律:判据正则先用一条已知吻合的样本自测通过,再跑全量。**

2. **★ 运单号/订单号列是超大假阳性源。** `JDVE<PHONE-REDACTED>` 里的 `<PHONE-REDACTED>` 会被裸 11 位
   正则命中,实测 **670,797 条**。做法:扫描时排除这些列;若不能排除,加边界锚定
   (`(?<!\d)…(?!\d)` 对 `JDVE1300…` 这种字母前缀无效)+ **人工抽查样本**后才计数。

3. **中文 CSV 表头带 BOM**(`\ufefforder`)⇒ `DictReader` / `hdr.index('order')` 抛
   `KeyError`。用 `encoding='utf-8-sig'`,或**按列序号取值**(`row[0]`)。

---

## 5. 与主流程的衔接

- 扫出的内嵌号**并入主还原表**(`确认还原_真号表.csv`),按 (姓名, 地址) 去重
- 双校验通过的才算 100% 确认真号;单端吻合的一律降级为"线索"
- 真号规模是**样本级**(本次全量累计约 4,700 处),**不是批量级** ——
  **报数时不要把内嵌号说成"全量还原",88 万虚拟号仍未被批量还原**
