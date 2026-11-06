# 整库合并（技能索引瘦身）实战手册

2026-10-21 本机实测：2,157 张 → 361 张启用（359 进索引）；索引 183,732 chars → 约 31K chars / 38,608 bytes；system prompt 199,596 → 46,919 chars（-76.5%，约省 5 万 token）。1,799 张 disabled，1,856 份 legacy 副本；60 张超长卡已拆。

## 0. 前提

- 先备份：`cp ~/.hermes/config.yaml /root/backups/config.premerge.$(date +%s).yaml`
- 写清单：`/root/skill_merge_manifest.json`，至少存 `keep[]` / `merged{name:bucket}` / `catalogs{}` / `enabled_total` / `disabled_total`。
- **不删原目录**：禁用即可回滚；原目录里的 `scripts/`、字典、模板继续用绝对路径访问。

## 1. 量账

```bash
hermes prompt-size --json > /root/ps_before.json
python3 - <<'PY'
import json
b=json.load(open('/root/ps_before.json'))
print(len(b['skills_breakdown']), b['skills_index'], b['system_prompt'])
print(sorted(b['skills_breakdown'], key=lambda x:-x['index_line_total_bytes'])[:10])
PY
```

`skills_breakdown[]` 每项含 `name/path/skill_md_bytes/index_line_total_bytes`；`skills_index.chars` 才是常驻索引成本。

## 2. 定 keep 集

- `~/.hermes/skills/.usage.json`：`{name: {use_count, last_used_at, pinned}}`。
- keep = `use_count>=2` OR 最近 14 天用过 OR essential OR 目录母卡。
- 2026-10-21 实测：`use_count>=2` 得 313 张 / 31.6KB，够 300 左右目标；`>=5` 只有 275 张。
- 不要拿“名字相似”当合并依据；同域但不同决策路径的卡应留在目录里，不要硬塞一张卡。

## 3. 目录卡映射（可复用）

| bucket | 母卡 |
|---|---|
| 博彩/白标/TG/发卡 | `whitelabel-gambling-pentest` |
| CMS/PHP | `php-framework-pentest` |
| Java/中间件 | `java-audit-pipeline` |
| 云/容器/CI | `cloud-security-pentesting` |
| AD/Windows/内网 | `ad-windows-router` |
| 移动/APK/固件 | `mobile-app-pentest` |
| AI/LLM/Agent | `llm-security` |
| CVE/1day | `1day-nuclei-kit` |
| 工具/扫描器 | `pentest-tools` |
| Web 注入 | `injection-checking` |
| Web 认证 | `auth-sec` |
| Web API | `api-sec` |
| Web 侦察 | `recon-for-sec` |
| Web 通用 | `web-sec` |
| 逆向/二进制 | `reverse-engineering` |
| 长尾安全 | `security-archive-index` |
| 非安全 | `general-archive` |

## 4. legacy 目录结构

```
<母卡>/
  SKILL.md                     # 只留判据 + MERGED-INDEX 指针
  references/
    index.md                   # name — desc — references/legacy/<name>.md — 原目录
    legacy/<name>.md           # 原 SKILL.md 全文（首行写 archived-from 注释）
```

- index 行格式（每行一条）：
  ```
  - **<name>** — <desc> · `references/legacy/<name>.md` · `<原目录>`
  ```
- 非安全卡按**原路径分类**搬去 `general-archive`，别按名字猜。
- 目录卡 SKILL.md 的 H1 后插 `<!-- MERGED-INDEX:START -->` 块，只写指针与“先本卡后子卡”的纪律。

## 5. 禁用（官方 API，不手改 YAML）

```python
import sys
sys.path.insert(0, '/usr/local/lib/hermes-agent')
from hermes_cli.config import load_config, save_config
cfg = load_config()
cfg.setdefault('skills', {})['disabled'] = sorted(set(cfg['skills'].get('disabled') or []) | set(merged))
save_config(cfg)
```

## 6. 补链（必做）

- 扫 enabled 卡正文的 `](../<name>/SKILL.md)`；目标是 disabled 就回开。
- 实测：只补 40 张核心子卡，注入/认证/API/侦察路由就全通了；CTF 密码学链会再拉 3–5 张，追 2–3 层就停。
- 不补链的后果：`injection-checking` 的 Skill Map 18 条里 16 条指向 disabled，模型点进去全报 disabled。

## 7. 验收

```bash
hermes prompt-size --json
# 期望：enabled ~360，skills_index < 40KB，system_prompt 明显下降
hermes skills list | grep -c enabled
```

- `skill_view(旧名)` → `Skill 'x' is disabled`（预期）。
- `skill_view(母卡, file_path='references/legacy/<name>.md')` → 全文可读。
- `references/index.md` 条目数 = `references/legacy/*.md` 数。
- `yaml.safe_load(config.yaml)` 通过。

## 8. 本次实测坑

- `skill_view(file_path=...)` 少写 `.md` 直接 not found。
- description 是 `>-` 多行 YAML 时，`m.group(1)[:-1] + ...` 会把 YAML 拼坏；只改单行 description，多行跳过。
- 目录卡 description 里的“含 N 张”在搬走非安全卡后会过期；以 `## 归档子卡（已合并 N 张）` 的 N 为准回写。
- `hermes skills list` 与 `prompt-size` 的 enabled 数差 1–2，属正常（pinned/essential/平台过滤），别为追平反复改配置。
- 大目录卡（`cloud-security-pentesting` 70KB）加载仍重；合并只解决索引，解决不了单卡正文，下一步仍要拆 references。

## 9. 回滚

```bash
cp /root/backups/config.premerge.<ts>.yaml ~/.hermes/config.yaml
```

或只清空 `skills.disabled`；目录卡与 legacy 副本可留着，不影响原卡恢复。

## 10. 拆超长卡：字符预算（2026-10-21 实测）

- 选目标用**字符数**：`len(open(path).read()) > 15000`，不要用 `skill_md_bytes`（UTF-8 字节，中文约 3 倍）。
- 每张 SKILL.md 保留 frontmatter + H1 + 前 N 个 `##` 节，累计 **≤12,000 字符**；其余原样写 `references/full.md`，末尾插 `## 全文导航（已拆分）`。
- 若第一个 `##` 节本身 >12,000 字符：在 `###` 或编号列表项边界再切，别只留引言。
- 验证：原 H2 标题集合 = 新 SKILL.md + full.md 的 H2 集合（Counter 等值）；原文字符数 ≈ 新 SKILL + full + 导航开销；`yaml.safe_load(frontmatter)` 通过。
- 本次 60 张；`pentest-execution` 100K → 8.6K 字符；启用卡最大正文降到 14,738 字符。

## 11. 目录索引分片

- 触发：`references/index.md` >20KB。按 `- **name**` 行顺序切 `index-part-01.md`…，每片 ≤12KB 字节；master `index.md` 写片名、首尾条目、条数。
- **同步改目录卡 MERGED-INDEX 块**：旧 `index-a-c.md` / `index-v-z.md` 在重分片后已删除，块内改成 `references/index.md`，否则目录卡自己指空。
- 验收：各片条目合计 = `## 归档子卡（已合并 N 张）`；全库 1,856 条 0 重复；每条 `references/legacy/<name>.md` 存在。本次 59 片，单片最大 11.8KB。

## 12. full.md 二次分片

- 触发：nav 指向的 `full.md` >20,000 字符。按 `## ` 打包到 `references/parts/part-01.md`…（≤12K 字符/片）+ `parts/index.md`（节名→片路径）。
- **不重写原 nav 列表**，只在末尾追加一行分片说明；保留 `full.md` 整包。单节 >12K 时独立成片，`parts/index.md` 标明“超长单节独立成片”。
- 本次 18 张、62 片；`pentest-execution` 86.6K 字符 → 8 片，`parts/index.md` 可直接 `skill_view`。

## 13. 本次验收数字与坑

- 361 启用（359 进索引；`research-paper-writing`、`teams-meeting-pipeline` 平台限定不进索引），1,799 disabled，17 目录卡，1,856 归档条。
- 索引 38,608 bytes；system prompt 46,919 chars（原 199,596，-76.5%）；启用卡最大正文 14,738 字符。
- 坑：`skill_view(file_path=...)` 必须带 `.md`；`skill_view(目录卡, 'references/index.md')` 只返回 master，读片要再指 `index-part-NN.md`。
- 坑：description 为 `>-` 多行 YAML 时，把“含 N 张”追加到**最后一个缩进行**，不要 `rstrip('"')` 硬拼；改完 `yaml.safe_load` 复验。
- 145 处原卡自带的 `references/*.md` 历史悬空引用（不是合并/拆卡造成），不要伪造文件去填；报告里单列。
