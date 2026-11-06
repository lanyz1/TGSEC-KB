# 候选仓评估 / 投毒甄别 / 覆盖差异 — 命令与实测坑

2026-09-17 实录(PoC 批次 A/B/C + Qtzuu + web-security-skills + rev-skills 评估)。

## 1. 存在性与元数据(最便宜的一步)

```bash
unset ALL_PROXY all_proxy HTTP_PROXY HTTPS_PROXY http_proxy https_proxy
curl -fsSL -H "Accept: application/vnd.github+json" -H "User-Agent: hermes" \
  "https://api.github.com/repos/<owner>/<repo>"
```

取 `full_name` / `description` / `language` / `stargazers_count` / `size`(KB) / `updated_at` / `license.spdx_id` / `private`。
返回体含 `"message": "Not Found"` → 仓不存在或私有, 直接判死, 别再猜。

## 2. 浅克隆探测(不污染主战场)

```bash
D=/root/TGSEC-Qtzuu/_probe_<name>; rm -rf $D; mkdir -p $D; cd $D
git clone --depth 1 -q <url>
du -sh <repo>; ls -la <repo>
find <repo> -name 'SKILL.md' -not -path '*/.git/*' | wc -l
find <repo> -type f -not -path '*/.git/*' \
  \( -name '*.sh' -o -name '*.ps1' -o -name '*.py' -o -name '*.exe' -o -name '*.so' \) | head -40
```

- 技能包的结构特征: `SKILL.md` 数量 = 技能数; 文件总数 300~400 量级的 6M 级仓库 = 纯 markdown 知识库。
- 定位判据: 入口带 `type: entry` + 网关层 + 原子层 = **路由型技能包**; 主体是应用源码 = **产品本体, 不整仓吸**。

## 3. 投毒甄别(逐条跑, 结论写进报告)

```bash
cd <repo>
rg -n "postinstall|preinstall|prepare|prepublish" package.json bin lib 2>/dev/null
rg -n "curl[^\n]*\|\s*(bash|sh)|wget[^\n]*\|\s*(bash|sh)|eval\(|atob\(|Buffer\.from\([^)]*base64" -g '!*.md' .
rg -n "xmrig|stratum\+tcp|ngrok|webhook|child_process|execSync|execFileSync|fetch\(" -g '!*.md' .
rg -o "https?://[a-zA-Z0-9._/-]+" -g '!*.md' . | sort -u   # 逐个 URL 判合法性
for f in $(find . -name '*.sh' -not -path './.git/*'); do echo "--- $f"; cat "$f"; done  # 少就通读
```

实测结论(rev-skills): 无 npm 钩子、无混淆、无矿/回连; 唯一外连 `bbs.kanxue.com`(看雪论坛) 合法;
唯一 shell 是纯环境探测 `probe.sh`; `ccgen.nim` 内容是 `404: Not Found`(提交事故)。→ 干净可用。

### PoC 合集：HARD vs SOFT（别把反弹壳当挖矿）

| 级别 | 典型命中 | 动作 |
|---|---|---|
| HARD | `xmrig` / `stratum+tcp` / 矿池 / 带 token 的 discord webhook | 整条 CVE 跳过 |
| SOFT | `/dev/tcp/`、README/INSTALL 里的 `curl\|bash`、`base64 -d\|sh` | **仍融合**，analysis 标 `SOFT_FLAG` |

**误报**：whitepaper/assessment 里的 payload 示例（如 `eval(base64_decode($_GET['cmd']))`）会撞 HARD——打开命中行上下文，叙述性文档则人工补吸并写 `FALSE_POSITIVE`（批次 D：`CVE-2026-1512`）。

**「已融合」别用全文提及**：只数 `domains/0day-exploits/<product>/<CVE>/` 且含 `analysis.md|summary.md|exploit|代码` 的目录；用 mention 集会假报 0 new。PoC 合集全流程见 `references/poc-collection-ingest.md`。

## 4. 覆盖差异 — 关键词判据过松的坑

**坑(实测)**: 拿主题关键词在本地全部 md 里做 `in` 匹配 → 本地语料一大(如 892 个 md), 
`ctf`、`取证`、`内核` 这类泛词必然命中, 结果 122 个技能里 98 个被误判 "已覆盖", 完全失去判别力。

**正确判据(三层, 按强度递减)**:
1. 技能目录名 / 文件名精确比对本地技能目录集(最强信号)。
2. **区分性强**的关键词 `grep -ril`(如 `trustzone`、`javacard`、`freertos`、`zephyr`), 避免 `ctf`/`取证`/`内核`。
3. 人工扫一眼本地技能目录清单, 再下结论。

```bash
# 本地技能目录名清单(先建立基线)
for r in <local roots>; do find $r -maxdepth 2 -name SKILL.md -o -maxdepth 2 -name 'skill.md' \
  | xargs -r -n1 dirname | xargs -r -n1 basename | sort -u; done
# 区分性关键词探测
for k in trustzone javacard freertos zephyr hypervisor uefi ebpf flutter; do
  echo "$k -> $(grep -ril --include='*.md' "$k" <local roots> 2>/dev/null | wc -l) files"
done
```

实测: 关键词判据给 24/122 新增; 换成「技能名重叠」判据只剩 **1/122**(只剩 `re-anti-analysis`), 
而本地与来料是**两个不同的仓**——名字不重叠但主题粗粒度重叠, 所以结论要写「按目录名重叠 X / 按主题粗覆盖 Y / 真纵深增量 Z」。

## 5. 文件级 diff(融合前必做)

```python
import hashlib
from pathlib import Path
def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for c in iter(lambda: f.read(1 << 16), b''): h.update(c)
    return h.hexdigest()
# 对两侧所有相对路径求 sha → identical / changed / new / local_only 四类
```

- `changed` 里只挑 `q_size > l_size + 200` 的覆盖, 其余保留本地。
- 覆盖前 `shutil.copy2` 到 `_ingest_*/backup_local_<skill>/<相对路径>`, 并写 `TGSEC-BRIDGE.md` 记来源/日期/备份位置。
- 融合后必抽查: 关键新文件存在 + 备份目录存在 + 域 README 挂了指针。

## 6. 收尾

- 融合完删暂存克隆的 `.git`(省空间, 留文件供审计)。
- 报告落 `/root/reports/poc-ingest-<date>/DIGEST-*.md`, 用 Telegram `MEDIA:` 发文件。
