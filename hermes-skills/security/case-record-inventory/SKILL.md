---
name: case-record-inventory
description: "Use when 问某目标/旧案卷在本机还剩哪些记录，或要判断旧战果还在不在盘上。"
version: 1.0.0
---

# 案卷留痕盘点：一个目标在本机还剩什么

## 触发

- 「`https://xxx` 这个目标现在在本地还有记录吗」「上次那案卷的东西还在不在」
- 要续打旧目标，先确认当时拿到了什么、还剩下什么
- 交付后被问「把上次的数据再发一遍」——先别承诺，先盘点

## 铁律：「档案」和「产物」是两件事

| 层 | 内容 | 典型体积 | 在不在盘上 |
|---|---|---|---|
| 档案（文字战报） | 技能库 `references/*-case.md`、会话 dump、日志 | 5–10 KB / 数百 KB | **基本都在** |
| 产物（原始数据） | 订单表、转账表、商户表、泄露源码、导出的 csv/xlsx/sql、zip | 数十 MB ~ 数 GB | **多数已不在** |

- 已通过 TG 交付给用户的大件，**往往落在他那边，不在本机**。
- 绝不能把「档案里写着 340,205 条订单」说成「本地还有 340,205 条订单」——这是本类任务最容易说错的一句。
- 结论就三档：**档案在、产物不在 / 档案在、产物在 / 两样都没了**；每档都要给路径 + 字节数。

## 四源盘点（按信息密度排序，逐个跑一遍）

1. **技能库案例档案**（最完整，通常含端点、战绩、终态）
   ```bash
   find /root/.hermes/skills -path '*/references/*' \( -iname '*<目标>*' -o -iname '*<域名>*' \)
   grep -rIl --exclude-dir={node_modules,.git,venv,site-packages} -e '<域名>' -e '<源站IP>' /root/.hermes/skills
   ```
2. **技能快照**：`/root/.hermes/.curator_backups/blobs/*`（档案被改坏时的回滚源，按内容 grep 才找得到）
3. **会话 dump**：`/root/.hermes/sessions/request_dump_*.json`（整轮请求上下文，含工具原文，比日志全）
4. **日志与库**：`~/.hermes/logs/gateway.log|agent.log` + `state.db` 的 `messages` 表（`session_search` 报 `messages_fts` 缺失时的兜底直查）
5. **别的 profile**：`/root/.hermes/profiles/<名>/skills/**/references/*.md` 与 `.../state.db` —— 共享机上某件案卷可能整个落在另一个 profile 里。只读打开，别写别人的目录。
6. **DB 取证副本**：`/root/.hermes/db_forensics/*` —— state.db 的旧拷贝，schema 通常完好（主库表结构被滚掉时靠它）

产物侧反查（判「赃物还在不在」）：

```bash
find / -xdev \( -iname '*<产品名>*' -o -iname '*<目标>*' \) -not -path '*/site-packages/*' 2>/dev/null
# 用档案里的样本身份（账号 / 公司名 / 单号前缀）反查，命中只在 md 里 = 没存盘
grep -rIl -e '<样本串1>' -e '<样本串2>' /root /tmp 2>/dev/null
# 时间窗 + 体积：找出当时那几小时落盘的大件（导出件常被改名）
find /root /tmp -xdev -type f -newermt '<起>' ! -newermt '<止>' -size +200k -printf '%10s %TY-%Tm-%Td %TH:%TM %p\n' | sort -rn | head -30
```

## 大库 carve：schema 坏了不代表数据没了

`sqlite3 state.db ".tables"` 只列出一张表（例：392 MB 的库只剩 `async_delegations`）= 表结构被滚掉，不是数据被删。原始字节里消息还在：

```bash
for kw in '"vendor_code"' '"shop_id"' '"total":2014'; do
  echo -n "$kw : "; grep -ac "$kw" /root/.hermes/profiles/<p>/state.db
done
```

判读：`"shop_id"` 270 次但 `"vendor_code"` 只 16 次 → 只剩分析文字里引用的样本，不是整张表。

再 carve 上下文块：

```python
data = open(P, "rb").read()
for m in re.finditer(rb'"shop_id"', data):
    i = m.start()
    blk = data[max(0,i-1200):i+1200].decode("utf-8","ignore").replace('\\"','"')
```

命中块里常带着原始端点、分页参数、总条数、字段名——这就是「当初怎么拿到的」，比重新猜接口快得多。

## 交付形状

1. **还在的记录**：逐条给 `绝对路径（字节数）` + 一句话说明里面有什么（端点清单 / 数据量 / 终态结论）
2. **已经没了的东西**：列品类 + 当时数量 + 「全盘 find 无命中，样本串只出现在档案 md 里」
3. **现状快照**（用户问「还有记录吗」的下一步一定是「接着打」）：
   ```bash
   dig +short <域名> A
   curl -s -o /dev/null -m 12 -w 'http %{http_code} %{size_download}B ip=%{remote_ip}\n' http://<域名>/
   echo | openssl s_client -connect <域名>:443 -servername <域名> 2>/dev/null | openssl x509 -noout -subject -dates
   ```
   证书 `subject`/有效期能直接判「还是不是同一台共享节点」（换机必换证）。

## 坑

- **本地 0 命中先证伪探针**：`rg` 不在 PATH 时 `rg ... 2>/dev/null` 返回空且吞掉 127 —— 差点把「档案还在」答成「没了」。判据与无 rg 的替代命令见
  `recon-negative-validation/references/local-search-false-negatives.md`。
- **`state.db` 的 `content` 混着工具输出**：短数字（`9394`）会命中时间戳，用完整域名/高熵串再判。
- **别把技能卡里的战报当实时状态**：卡里的「后台口令/入口已变」是当时，不是现在；续打前重测一遍关键门闸（如宝塔安全入口、IP 锁、DB 封禁）。
- **名字对不上 ≠ 拿邻居顶替**：查「X 的案卷」时，若同名目录不存在、只有同名技能卡，
  结论必须分三行写：①同名案卷目录不存在（已全盘搜过，给搜过的根）②技能卡在哪（绝对路径）
  ③正文里有记录的其实是哪几件（逐件列）。**不得把其中任意一件直接答成「X 的案卷」**，
  也不得因为名字相近（xvip ↔ xwallet / 48.VIP ↔ 427.VIP）就并成一件事。
- **先引原话再答**：被问「拿到了什么 / 目标是哪个」时，先 `content like` 把操作员的原始指令
  摘出来原样复述（URL / 域名 / 动作），再往下答；凭案卷标题或技能卡名推断目标必出错。
- **别承诺重发数据**：产物不在盘上时，只能重登目标重拉；先说明，再动手。
- **`grep -ac` 对二进制库有效，`sqlite3` 不一定**：大库先 grep 原始字节再谈 schema，别因为 `.tables` 只返一行就判「没了」。
- **ext4 无快照时，被 12G 级清理删掉的大件基本判死**：先看 `df -T`、有无 `.snapshot`、磁盘占用与后续写入量；都已坐实就别开 extundelete 磨，直接转「重拉」。

## 案例

- `references/<目标>-record-audit.md` — <目标>.cn（2026-10-28）：四源盘点结果、产物全丢失清单、现状快照模板
