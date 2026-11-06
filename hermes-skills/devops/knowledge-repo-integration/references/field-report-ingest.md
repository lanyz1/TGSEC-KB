# 实战报告包吸收（报告.zip 实录，2026-09-17）

适用：用户丢一批实战渗透报告（zip/rar/pdf/md 混装），要求「完整提炼吸收，去除已经重复的」。

与 PoC 合集 / 技能包分流：报告走 **双落点**——全文进 `case-reports/`，提炼卡片进 `case-lessons/`，按攻击面域分发，不新建堆叠域。

## 落点约定

```text
domains/<attack-surface>/
  case-reports/<slug>/          # 全文 + meta.md
    <原报告文件>
    meta.md                     # 来源/标签/日期
  case-lessons/<slug>.md        # 短卡片：关键发现 + 复现片段 + When to reuse
```

域映射示例：支付/钱包/发卡 → `business-logic`；TG 云控/筛号 → `api-security`；博彩盘 → `gambling-pentest`；DCR/OAuth → `auth-security`；恶意代码静态分析 → `reverse-engineering`；S3 → `cloud-security`。

总索引：`security-suite/REPORTS-INGEST-<date>-INDEX.md` + `reports/.../DIGEST-REPORTS-CN.md`。

## 去重（先于融合）

对 suite + `/root/cases` + `/root/reports` 建索引：

1. **精确重复**：整文件 sha256 命中 → SKIP（实测：777VVIP、gx3xx、xpay v6、export_summary）。
2. **规范重复**：空白折叠后前 5KB 文本相同 → SKIP（实测：77zhanghao 报告）。
3. **包内重复**：同内容不同后缀/「(2)」副本 → 留最长/最新，丢短的（实测：近期目标合集 `.md`/`.txt`/`(2).md`）。
4. **版本覆盖**：同战役旧版被已归档更大版本覆盖 → 跳过旧版（实测：xpay v2 26KB vs v6 81KB）。

不要用「文件名像」当重复——战役名相同但内容增量仍要吸。

## 特殊工件

| 类型 | 处理 |
|---|---|
| **PDF** | `pdftotext -layout` → `.txt`/`.md` 再融合（缺 poppler-utils 就先装） |
| **中文 zip 文件名** | Python `zipfile`：无 UTF-8 flag 时用 cp437→gbk/gb18030 解码，别直接 `unzip` 乱码 |
| **木马/样本 RAR** | 只吸分析文本/IOC/strings/脚本；**ELF/挖矿二进制不进知识库**（meta 注明 Binaries NOT vendored；大二进制留 staging 审计后删） |
| **STATUS / 进度备忘** | 可吸，当 case-lesson 短卡；别当正式审计报告 |

## 提炼卡片（case-lessons）要点

从全文抽：
- 标题 + 技术标签（sqli/rce/idor/payment/wallet/telegram/waf/malware…）
- Key findings：含「漏洞/未授权/高危/Critical」等行的列表项，最多 ~8 条
- Repro snippets：前几个代码块裁剪
- When to reuse：标签命中时先读卡片再开全文

## 推荐流水线

1. 解压 + 文件名修复 + PDF/RAR 预处理。
2. `INVENTORY.json`：hash/norm 去重 + 战役命中 + 技术标签。
3. 手写/半自动 `MAP`：报告 → `(domain, slug, title, techniques[])`。
4. `fuse_reports.py`：SKIP_DUP → copy 全文 → 写 meta → distill lesson → 域 README 追加 `<!-- fused:case-reports-<date> -->`。
5. 验证：各域 `case-lessons`/`case-reports` 计数；木马包 `file` 扫描确认无 ELF。
6. 收尾：删 `raw/`/`raw_rar/`（可省 20MB+），留脚本+JSON；`MEDIA:` 发 DIGEST + INDEX。

## 用户偏好

- 「完整提炼吸收，去除掉已经重复的」= 去重后**缺的全吸**，按攻击面散落，不要整包堆一个 `reports-dump/`。
- 渗透调用：先 `case-lessons/` 短卡，再 `case-reports/` 复现。
- Suite 变大后若 AI「调不到实战报告」：优先补 **CASE 总索引 + ROUTING**，不要先怪报告丢失——见 `suite-discoverability-and-case-index.md`。

## 实测数字（2026-09-17 报告.zip）

- 包内 52 文件 → FUSED 44 / SKIP_DUP 10
- 域分布：business-logic 13、web-attack 8、api-security 6、gambling-pentest 5、recon 5、其余散落
- 情梦后门：18 个 evidence 文本/脚本入库，0 ELF

## 可发现性快照（2026-09-20）

- 全库约 44 个 `case-reports/<slug>`、~52 个 `case-lessons` 文件，分散 10 域
- 缺 `domains/CASE-INDEX.md` 时，关键词「实战报告」只能命中 ROUTING 里少数老条目
