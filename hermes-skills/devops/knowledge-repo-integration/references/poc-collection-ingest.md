# PoC 合集吸收（批次 D 实录，2026-09-17）

适用：用户丢一批 CVE PoC 合集仓（索引仓 / 克隆合集 / 监控链接仓），要差分融进 `domains/0day-exploits/<product>/<CVE>/`。

与「方法论技能包」分流：技能包走整包/散卡；**PoC 合集走产品/CVE 条目**，每条 `analysis.md` + `summary.md` + 原 exploit。

## 三种仓形态（先分流再动手）

| 形态 | 信号 | 怎么吸 |
|---|---|---|
| **精选 PoC 索引**（如 SecureWithUmer/CVE-2026-PoCs） | `2026/CVE-…/` 下嵌套真实 exploit 仓，MIT，几十～上百 CVE | 按 CVE 差分：本地缺的整条目融合 |
| **批量克隆合集**（如 XZ1r0/cve-2026-poc-collection） | `web/linux/windows/…` 分类，上百子仓，百 MB 级 | **只融本地仍缺**；同 CVE 多变体可挂 `-xz-<name>` |
| **监控索引仓**（如 zulloper/cve-poc） | 只有 README 表 + SQLite + `main.py`，**无 PoC 本体** | 抠链接写 `_indexes/…/INDEX.md`；对 Web/RCE 关键词优先浅克隆（设 CAP，控磁盘） |

判断「监控索引」：tree 只有个位数文件、`main.py` 调 GitHub Search、README 全是外链表。

## 严格「已融合」判定（致命坑）

**坑**：用全文 `CVE-…` 字符串命中当「已有」→ 提及几千条，差分会报「0 new」（批次 D 首轮 inventory 翻车）。

**正确**：只认正规条目目录：

```text
domains/0day-exploits/<product>/<CVE-…>/
  且存在 analysis.md 或 summary.md 或 exploit/ 或代码文件
```

排除 `_ingest_*` 暂存。目录名带后缀（`CVE-2026-23918-poc`）用正则抽出 CVE 再比。

## 投毒：HARD 跳过 / SOFT 标注仍融合

PoC 仓和技能库不同——反弹壳、`curl|bash` 安装说明在 PoC 里是常态。

| 级别 | 模式 | 动作 |
|---|---|---|
| **HARD** | `xmrig` / `stratum+tcp` / 矿池 / `discord.com/api/webhooks/<id>/<token>` | **整条跳过** |
| **SOFT** | `/dev/tcp/`、文档里的 `curl … \| bash`、`base64 -d \| sh` | **仍融合**，`analysis.md` 写 `SOFT_FLAG` |

**白皮书误报**：教学文档里的 XSS payload 示例 `eval(base64_decode($_GET['cmd']))` 会撞 HARD。命中后**打开上下文**：若在 whitepaper/assessment 叙述里而非可执行入口 → 人工补吸，analysis 注明 `FALSE_POSITIVE`。

## 落点与产品映射

```text
domains/0day-exploits/<product-slug>/<CVE>/
  analysis.md   # 来源仓、投毒结论、README 摘要
  summary.md    # 产品/CVE/路径一行表
  <原 PoC 文件>
```

- 产品 slug：先查手写 `PRODUCT_MAP`（高价值 CVE），再从嵌套仓名/README 关键词猜（n8n/langflow/nextjs/nginx/…），兜底 `misc-cve`。
- 同 CVE 已有条目：XZ/zulloper 变体用 `<CVE>-xz-…` / `<CVE>-zul`，不覆盖。
- 批次总索引：`INGEST-<date>D-INDEX.md`；监控仓剩余链接：`_indexes/<name>-<date>/INDEX.md`。

## 推荐流水线

1. GitHub API 元数据 + README/tree（三仓并行）。
2. 浅克隆真 PoC 仓；监控仓可只 clone 小仓或只拉 README。
3. `diff_strict.py`：正规融合集合 ∩ 来料 CVE → `umer_missing` / `xz_need` / `zul_new`。
4. `fuse_*.py`：HARD/SOFT 扫描 → copytree（跳过 `.git`）→ 写 analysis/summary → 更新 INDEX + `DIGEST-*-CN.md`。
5. zulloper：prio 关键词（rce/sqli/upload/unauth/wordpress/langflow/…）浅克隆 ≤ CAP（实测 25）；其余只进 INDEX。
6. 收尾：删 staging 克隆（可省 200MB+），留 `_ingest_<batch>/` 脚本+JSON+日志；`MEDIA:` 发 DIGEST + INDEX。

## 用户偏好（本类任务）

- 首次问「有没有可以吸」→ **先评估再动手**（「先告诉我 让我做决定」）。
- 用户说「完整吸收少的 / 方便渗透调用」→ **缺的全差分吸**，不要再缩成子集请示。
- 目标：渗透时能直接 `domains/0day-exploits/<产品>/` 或翻批次 INDEX 调 PoC。

## CVE 情报清单驱动（无合集仓 URL 时）

用户贴「近 24h 严重/高危/在野」CVE 列表时，走 **`references/cve-intel-batch-ingest.md`**：本地严格已有判定 → NVD+GitHub → PoC/分析分流；**mock 教学 lab 与 kernel 预编译二进制跳过**；写 `INGEST-<date>-INDEX.md` 并更新 README「〇、本轮更新」（别只改第十节）。

## 实测数字（批次 D）

- SecureWithUmer：73 CVE，缺 69 → FUSED 69（含 1512 误报补吸）
- XZ1r0：增量 FUSED 64
- zulloper：优先克隆 FUSED 25；INDEX 剩余 ~51
- HARD skip：1（后证实 FP）；CLONE fail：0
- 库内 `CVE-*` 目录约 49 → ~227
